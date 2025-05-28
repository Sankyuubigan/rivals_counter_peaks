# File: core/main_window.py
import sys
import time
import logging
import os

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QScrollArea,
                               QLabel, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, 
                               QMenu, QApplication, QMessageBox, QComboBox, QLineEdit, QTextEdit, QTextBrowser, QDialog)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint, QMetaObject, QEvent, QObject, QRect 
from PySide6.QtGui import QIcon, QMouseEvent, QPixmap, QShowEvent, QHideEvent, QCloseEvent, QKeySequence 

import utils # utils теперь содержит normalize_hero_name
from images_load import load_default_pixmap 
from logic import CounterpickLogic, TEAM_SIZE 
from top_panel import TopPanel
from right_panel import HERO_NAME_ROLE, TARGET_COLUMN_COUNT 
from log_handler import QLogHandler
from dialogs import (LogDialog, HotkeyDisplayDialog, show_about_program_info,
                     show_hero_rating, show_hotkey_settings_dialog, show_author_info) 
from core.ui_components.hotkey_capture_line_edit import HotkeyCaptureLineEdit 
from hotkey_manager import HotkeyManager, PYNPUT_AVAILABLE 
from mode_manager import ModeManager, MODE_DEFAULT_WINDOW_SIZES 
from win_api import WinApiManager
from recognition import RecognitionManager 
from ui_updater import UiUpdater
from action_controller import ActionController
from window_drag_handler import WindowDragHandler
from appearance_manager import AppearanceManager
from core.window_flags_manager import WindowFlagsManager 

from core.lang.translations import get_text


IS_ADMIN = False
if sys.platform == 'win32':
    try: 
        import ctypes
        IS_ADMIN = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception: pass


class MainWindow(QMainWindow):
    action_move_cursor_up = Signal()
    action_move_cursor_down = Signal()
    action_move_cursor_left = Signal()
    action_move_cursor_right = Signal()
    action_toggle_selection = Signal()
    action_toggle_mode = Signal()
    action_clear_all = Signal()
    action_recognize_heroes = Signal()
    action_debug_capture = Signal()
    action_toggle_tray_mode = Signal()
    action_toggle_mouse_ignore_independent = Signal()
    action_copy_team = Signal()

    recognition_complete_signal = Signal(list)
    update_tray_button_property_signal = Signal(bool)


    def __init__(self, logic_instance: CounterpickLogic, hero_templates_dict: dict, app_version: str):
        super().__init__()
        logging.debug(">>> MainWindow.__init__ START") 
        self.logic = logic_instance
        # self.hero_templates теперь не используется напрямую в MainWindow для старого распознавания,
        # CV2 шаблоны загружаются в images_load и передаются в AdvancedRecognition через RecognitionManager
        self.app_version = app_version
        if hasattr(self.logic, 'main_window'): 
            self.logic.main_window = self

        self._set_application_icon() 
        self._setup_logging_and_dialogs() 
        self.appearance_manager = AppearanceManager(self)
        self.current_theme = self.appearance_manager.current_theme 
        self.hotkey_manager = HotkeyManager(self) 
        self.ui_updater = UiUpdater(self) 
        self.action_controller = ActionController(self)
        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self)
        # RecognitionManager теперь использует AdvancedRecognition, которому нужны CV2 шаблоны
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)
        
        self.drag_handler = WindowDragHandler(self, lambda: getattr(self, 'top_frame', None))
        self.hotkey_manager.load_hotkeys() 
        self.mode = self.mode_manager.current_mode
        logging.info(f"Initial mode from ModeManager: {self.mode}") 
        self._init_ui_attributes()
        self.flags_manager = WindowFlagsManager(self) 
        self._setup_window_properties() 
        self._create_main_ui_layout() 
        
        if self.appearance_manager: 
            self.appearance_manager._apply_qss_theme(self.appearance_manager.current_theme, on_startup=True)
        
        self._connect_signals()
        self._initial_ui_update_done = False
        logging.info(f"<<< MainWindow.__init__ FINISHED. Initial self.windowFlags(): {self.windowFlags():#x}")

    # ... (остальные методы без изменений до _on_recognition_complete) ...
    def _set_application_icon(self):
        icon_path_logo = utils.resource_path("logo.ico")
        app_icon = QIcon() 

        if os.path.exists(icon_path_logo):
            loaded_icon = QIcon(icon_path_logo)
            if not loaded_icon.isNull():
                app_icon = loaded_icon
                logging.debug(f"Application icon loaded successfully from: {icon_path_logo}")
            else:
                logging.error(f"Failed to load icon from {icon_path_logo}, QIcon isNull. Using fallback.")
                pixmap = QPixmap(icon_path_logo)
                if not pixmap.isNull():
                    app_icon = QIcon(pixmap)
                    logging.debug(f"Application icon created from QPixmap: {icon_path_logo}")
                else:
                    logging.error(f"Failed to load QPixmap for icon from {icon_path_logo}. Using default placeholder.")
                    app_icon = QIcon(load_default_pixmap((32,32))) 
        else:
            logging.error(f"logo.ico not found at {icon_path_logo}. Using default placeholder.")
            app_icon = QIcon(load_default_pixmap((32,32)))

        self.setWindowIcon(app_icon)
        QApplication.setWindowIcon(app_icon) 

    def _setup_logging_and_dialogs(self):
        self.log_dialog = LogDialog(self) 
        self.log_handler = QLogHandler(self) 
        if hasattr(self.log_handler, 'message_logged') and hasattr(self.log_dialog, 'append_log'):
            self.log_handler.message_logged.connect(self.log_dialog.append_log)
        
        log_format = '%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
        formatter = logging.Formatter(log_format, datefmt='%H:%M:%S')
        self.log_handler.setFormatter(formatter)
        
        self.log_handler.setLevel(logging.INFO) 
        logging.getLogger().addHandler(self.log_handler)
        
        if logging.getLogger().level == logging.NOTSET: 
             logging.getLogger().setLevel(logging.INFO) 
        
        logging.info("GUI Log Handler initialized and added to root logger.")
        self.hotkey_display_dialog = None 


    @Slot() 
    def _do_toggle_mode_slot(self):
        logging.debug("MainWindow: _do_toggle_mode_slot executing in main thread.")
        debounce_time = 0.3 
        current_time = time.time()
        
        if not hasattr(self, '_last_mode_toggle_time'):
             self._last_mode_toggle_time = 0 

        if current_time - self._last_mode_toggle_time < debounce_time:
            logging.debug(f"Mode toggle (from slot) ignored due to debounce ({current_time - self._last_mode_toggle_time:.2f}s < {debounce_time}s)")
            return
        
        self._last_mode_toggle_time = current_time
        target_mode = "middle" if self.mode == "min" else "min"
        self.change_mode(target_mode)


    def switch_language(self, lang_code: str):
        if self.appearance_manager:
            self.appearance_manager.switch_language(lang_code)

    def update_language(self): 
        if self.appearance_manager:
            self.appearance_manager.update_main_window_language_texts()

    def switch_theme(self, theme_name: str):
        logging.debug(f"--> switch_theme called for: {theme_name}")
        if self.appearance_manager:
            self.appearance_manager.switch_theme(theme_name) 
            self.current_theme = self.appearance_manager.current_theme
        logging.debug(f"<-- switch_theme finished for: {theme_name}")


    def apply_theme(self, theme_name: str, on_startup=False): 
        if self.appearance_manager:
            self.appearance_manager._apply_qss_theme(theme_name, on_startup=on_startup)

    def _init_ui_attributes(self):
        initial_pos = self.pos() if self.isVisible() else None 
        self.mode_positions = { "min": None, "middle": initial_pos, "max": None }
        self.mouse_invisible_mode_enabled = False
        self.is_programmatically_updating_selection = False
        self._last_mode_toggle_time = 0 
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_panel_instance: TopPanel | None = None
        self.right_panel_instance = None 
        self.main_layout: QVBoxLayout | None = None
        self.top_frame: QFrame | None = None 
        self.close_button: QPushButton | None = None       
        self.tray_mode_button: QPushButton | None = None    

        self.icons_scroll_area: QScrollArea | None = None
        self.icons_scroll_content: QWidget | None = None
        self.icons_main_h_layout: QHBoxLayout | None = None
        self.counters_widget: QWidget | None = None
        self.counters_layout: QHBoxLayout | None = None
        self.enemies_widget: QWidget | None = None
        self.enemies_layout: QHBoxLayout | None = None
        
        self.result_label: QLabel | None = None 
        
        self.horizontal_info_label: QLabel = QLabel("Info Label Placeholder") 
        self.horizontal_info_label.setObjectName("horizontal_info_label")
        self.horizontal_info_label.hide()
        
        self.main_widget: QWidget | None = None
        self.inner_layout: QHBoxLayout | None = None
        self.left_panel_widget: QWidget | None = None
        self.canvas: QScrollArea | None = None 
        self.result_frame: QFrame | None = None 
        
        self.update_scrollregion = lambda: None 
        
        self.right_panel_widget: QWidget | None = None 
        self.right_frame: QFrame | None = None 
        self.right_list_widget: QListWidget | None = None
        self.selected_heroes_label: QLabel | None = None 
        
        self.hero_items: dict[str, QListWidgetItem] = {}
        self.hotkey_cursor_index = -1
        self.hotkey_display_dialog = None 


    def _setup_window_properties(self):
        logging.debug(f"    [WindowProps] START. Current flags before setup: {self.windowFlags():#x}")
        self.setWindowTitle(f"{get_text('title')} v{self.app_version}")
        
        current_icon = self.windowIcon()
        if current_icon.isNull():
            logging.warning("[WindowProps] Window icon is null, attempting to re-set.")
            self._set_application_icon() 

        initial_width = MODE_DEFAULT_WINDOW_SIZES.get(self.mode, {}).get('width', 950)
        initial_height = MODE_DEFAULT_WINDOW_SIZES.get(self.mode, {}).get('height', 600) 
        
        self.setMinimumSize(300, 70) 
        
        logging.debug(f"    [WindowProps] END. Initial self.flags_manager._last_applied_flags set to: {self.flags_manager._last_applied_flags:#x}")

        app_instance = QApplication.instance()
        if app_instance:
            app_instance.installEventFilter(self)
        else:
            logging.warning("QApplication instance not found, cannot install event filter on MainWindow.")


    def _create_main_ui_layout(self):
        logging.debug("    MainWindow: _create_main_ui_layout START")
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        if hasattr(self, 'change_mode') and self.logic and self.app_version:
            self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
            if self.top_panel_instance:
                self.top_frame = self.top_panel_instance.top_frame 
                self.tray_mode_button = self.top_panel_instance.tray_mode_button 
                self.close_button = self.top_panel_instance.close_button 
                if self.top_frame: self.main_layout.addWidget(self.top_frame)
        else:
            logging.error("Cannot create TopPanel due to missing attributes in MainWindow.")
        
        self._create_icons_scroll_area_structure()
        if self.icons_scroll_area: self.main_layout.addWidget(self.icons_scroll_area)
        
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget") 
        self.inner_layout = QHBoxLayout(self.main_widget)
        self.inner_layout.setContentsMargins(0,0,0,0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1)
        logging.debug("    MainWindow: _create_main_ui_layout END")


    def _create_icons_scroll_area_structure(self): 
        logging.debug("    MainWindow: _create_icons_scroll_area_structure START")
        self.icons_scroll_area = QScrollArea(); self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_main_h_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_main_h_layout.setContentsMargins(5, 2, 5, 2); self.icons_main_h_layout.setSpacing(10)
        self.icons_main_h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.counters_widget = QWidget(); self.counters_widget.setObjectName("counters_widget")
        self.counters_layout = QHBoxLayout(self.counters_widget)
        self.counters_layout.setContentsMargins(0, 0, 0, 0); self.counters_layout.setSpacing(4)
        self.counters_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_main_h_layout.addWidget(self.counters_widget, stretch=1)
        
        self.enemies_widget = QWidget(); self.enemies_widget.setObjectName("enemies_widget")
        self.enemies_layout = QHBoxLayout(self.enemies_widget)
        self.enemies_layout.setContentsMargins(2, 2, 2, 2); self.enemies_layout.setSpacing(4)
        self.enemies_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_main_h_layout.addWidget(self.enemies_widget, stretch=0); self.enemies_widget.hide()
        
        if self.horizontal_info_label and self.horizontal_info_label.parentWidget():
            parent_layout = self.horizontal_info_label.parentWidget().layout()
            if parent_layout: parent_layout.removeWidget(self.horizontal_info_label)
            self.horizontal_info_label.setParent(None)
            
        self.icons_scroll_area.setWidget(self.icons_scroll_content)
        logging.debug("    MainWindow: _create_icons_scroll_area_structure END")


    def _connect_signals(self):
        logging.debug("    Connecting signals...")
        if hasattr(self, 'action_controller') and self.action_controller:
            self.action_move_cursor_up.connect(lambda: self.action_controller.handle_move_cursor('up'))
            self.action_move_cursor_down.connect(lambda: self.action_controller.handle_move_cursor('down'))
            self.action_move_cursor_left.connect(lambda: self.action_controller.handle_move_cursor('left'))
            self.action_move_cursor_right.connect(lambda: self.action_controller.handle_move_cursor('right'))
            self.action_toggle_selection.connect(self.action_controller.handle_toggle_selection)
            self.action_toggle_mode.connect(self._do_toggle_mode_slot) 
            self.action_clear_all.connect(self.action_controller.handle_clear_all)
            if hasattr(self, 'rec_manager') and self.rec_manager and hasattr(self.rec_manager, 'recognize_heroes_signal'):
                self.action_recognize_heroes.connect(self.rec_manager.recognize_heroes_signal.emit)
            self.action_debug_capture.connect(self.action_controller.handle_debug_capture)
            self.action_toggle_tray_mode.connect(self.toggle_tray_mode) 
            self.action_toggle_mouse_ignore_independent.connect(self._handle_toggle_mouse_invisible_mode_independent)
            self.action_copy_team.connect(self.action_controller.handle_copy_team)
            logging.debug("    ActionController signals connected.")
        else:
            logging.error("    ActionController not initialized, cannot connect signals.")

        if hasattr(self, 'rec_manager') and self.rec_manager:
            if hasattr(self.rec_manager, 'recognition_complete_signal'):
                self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
            if hasattr(self.rec_manager, 'error'):
                self.rec_manager.error.connect(self._on_recognition_error)
            logging.debug("    RecognitionManager signals connected.")

        if self.tray_mode_button and hasattr(self, 'update_tray_button_property_signal'):
             self.update_tray_button_property_signal.connect(self._update_tray_button_property)
        if self.win_api_manager and hasattr(self.win_api_manager, 'topmost_state_changed'):
            self.win_api_manager.topmost_state_changed.connect(self._handle_topmost_state_change)
        logging.debug("    MainWindow general signals connected.")


    def showEvent(self, event: QShowEvent):
        is_applying_flags = self.flags_manager._is_applying_flags_operation if hasattr(self, 'flags_manager') else False
        logging.debug(f">>> showEvent START. Visible: {self.isVisible()}, Active: {self.isActiveWindow()}, isApplyingFlags: {is_applying_flags}, initialDone: {self._initial_ui_update_done}, Spontaneous: {event.spontaneous()}")
        super().showEvent(event)
        
        if is_applying_flags and not event.spontaneous(): 
            logging.debug(f"    showEvent: Called during _is_applying_flags_operation (non-spontaneous). Current geom: {self.geometry()}")
            logging.debug("<<< showEvent END (during flag operation, non-spontaneous)")
            return

        if not self._initial_ui_update_done:
            logging.info("    showEvent: Performing initial setup (_initial_ui_update_done is False).")
            t_initial_setup_start = time.perf_counter()
            
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_interface_for_mode(new_mode=self.mode)
            else: 
                if hasattr(self, 'flags_manager'):
                    self.flags_manager.apply_mouse_invisible_mode("initial_show_no_ui_updater")

            if PYNPUT_AVAILABLE and IS_ADMIN:
                 if hasattr(self, 'hotkey_manager'): 
                     QTimer.singleShot(200, lambda: self.hotkey_manager.start_listening() if self.hotkey_manager else None) 
            self._initial_ui_update_done = True
            logging.info(f"    showEvent: Initial setup done. Time: {(time.perf_counter() - t_initial_setup_start)*1000:.2f} ms")
        else:
            logging.debug(f"    showEvent: Repeated show or spontaneous event. Current flags: {self.windowFlags():#x}")
            if self.isVisible():
                current_icon = QApplication.instance().windowIcon()
                if not current_icon.isNull():
                    self.setWindowIcon(current_icon)
                else: 
                    self._set_application_icon()


        logging.debug("<<< showEvent END") 


    def hideEvent(self, event: QHideEvent):
        is_applying_flags = self.flags_manager._is_applying_flags_operation if hasattr(self, 'flags_manager') else False
        logging.debug(f"MainWindow hideEvent triggered. isApplyingFlags: {is_applying_flags}, Spontaneous: {event.spontaneous()}")
        super().hideEvent(event)

    @Slot(bool)
    def _update_tray_button_property(self, is_active):
        if self.tray_mode_button:
            self.tray_mode_button.setProperty("trayModeActive", is_active)
            button_text_key = 'tray_mode_on' if is_active else 'tray_mode_off'
            self.tray_mode_button.setText(get_text(button_text_key)) 
            style = self.tray_mode_button.style()
            if style:
                style.unpolish(self.tray_mode_button)
                style.polish(self.tray_mode_button)
            self.tray_mode_button.update()


    @Slot(bool)
    def _handle_topmost_state_change(self, is_topmost: bool):
        logging.debug(f"--> _handle_topmost_state_change: is_topmost={is_topmost}, current mouse_invisible_mode_enabled={self.mouse_invisible_mode_enabled}")
        if hasattr(self, 'update_tray_button_property_signal'):
            self.update_tray_button_property_signal.emit(is_topmost)
        
        self.mouse_invisible_mode_enabled = is_topmost 
        if hasattr(self, 'flags_manager'):
            self.flags_manager.apply_mouse_invisible_mode("_handle_topmost_state_change")
        logging.debug(f"<-- _handle_topmost_state_change finished")


    @Slot()
    def _handle_toggle_mouse_invisible_mode_independent(self):
        logging.debug("--> _handle_toggle_mouse_invisible_mode_independent triggered.")
        if hasattr(self, 'mouse_invisible_mode_enabled'):
            self.mouse_invisible_mode_enabled = not self.mouse_invisible_mode_enabled
            if hasattr(self, 'flags_manager'):
                self.flags_manager.apply_mouse_invisible_mode("_handle_toggle_mouse_invisible_mode_independent")
            logging.info(f"    Mouse invisible mode (independent) toggled to: {self.mouse_invisible_mode_enabled}")
        logging.debug("<-- _handle_toggle_mouse_invisible_mode_independent finished.")

    @Slot()
    def toggle_tray_mode(self):
        logging.info("MainWindow: toggle_tray_mode slot triggered.")
        if hasattr(self, 'win_api_manager'):
            target_topmost_state = not self._is_win_topmost 
            self.win_api_manager.set_topmost_winapi(target_topmost_state) 
            logging.info(f"Tray mode toggle initiated. Target topmost: {target_topmost_state}")
        else:
            logging.error("MainWindow: win_api_manager not found in toggle_tray_mode.")


    def change_mode(self, mode_name: str):
        t_change_mode_start = time.perf_counter()
        logging.info(f"--> MainWindow: change_mode to: {mode_name} (Current: {self.mode})")
        if self.mode == mode_name: 
            logging.info(f"    Mode is already {mode_name}. No change.")
            if hasattr(self, 'flags_manager'): 
                QTimer.singleShot(10, lambda: self.flags_manager.force_taskbar_update_internal(f"already_in_mode_{mode_name}_refresh"))
            logging.debug(f"<-- MainWindow: change_mode finished (no change). Time: {(time.perf_counter() - t_change_mode_start)*1000:.2f} ms")
            return
            
        old_mode = self.mode
        if self.isVisible(): self.mode_positions[old_mode] = self.pos()
        
        self.hotkey_cursor_index = -1
        if self.right_list_widget and self.right_list_widget.isVisible() and self.right_list_widget.viewport():
            self.right_list_widget.viewport().update()

        if hasattr(self, 'mode_manager'): self.mode_manager.change_mode(mode_name)
        self.mode = mode_name 
        
        t_ui_update_start = time.perf_counter()
        if hasattr(self, 'ui_updater') and self.ui_updater:
            self.ui_updater.update_interface_for_mode(new_mode=self.mode) 
        logging.debug(f"    change_mode: ui_updater.update_interface_for_mode took {(time.perf_counter() - t_ui_update_start)*1000:.2f} ms")
        
        target_pos = self.mode_positions.get(self.mode)
        if target_pos and self.isVisible():
            QTimer.singleShot(0, lambda: self._move_window_safely(target_pos))
        elif self.isVisible(): 
            self.mode_positions[self.mode] = self.pos()
        
        self._reset_hotkey_cursor_after_mode_change()
        
        if self.isVisible():
            current_icon = QApplication.instance().windowIcon()
            if not current_icon.isNull(): self.setWindowIcon(current_icon)
            else: self._set_application_icon()

        if hasattr(self, 'flags_manager'):
            QTimer.singleShot(50, lambda: self.flags_manager.force_taskbar_update_internal(f"after_mode_{mode_name}_change"))
        logging.debug(f"<-- MainWindow: change_mode to {mode_name} FINISHED. Total time: {(time.perf_counter() - t_change_mode_start)*1000:.2f} ms")

    def _move_window_safely(self, target_pos: QPoint):
        if self.isVisible(): self.move(target_pos)

    @property
    def _is_win_topmost(self):
        return self.win_api_manager.is_win_topmost if hasattr(self, 'win_api_manager') and self.win_api_manager else False

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes_with_suffixes):
        # ИЗМЕНЕНО: Нормализация имен перед использованием
        normalized_heroes = [utils.normalize_hero_name(name) for name in recognized_heroes_with_suffixes]
        # Удаляем пустые строки, если normalize_hero_name вернула их для нераспознанных суффиксов
        normalized_heroes = [name for name in normalized_heroes if name] 
        
        logging.info(f"MainWindow: Recognition complete. Original: {recognized_heroes_with_suffixes}, Normalized: {normalized_heroes}")
        
        if normalized_heroes and hasattr(self, 'logic'):
            self.logic.set_selection(set(normalized_heroes))
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_ui_after_logic_change()
            self._reset_hotkey_cursor_after_clear()
        elif not normalized_heroes: 
            logging.info("No heroes recognized or list is empty after normalization.")


    @Slot(str)
    def _on_recognition_error(self, error_message):
        logging.error(f"MainWindow: Recognition error: {error_message}")
        QMessageBox.warning(self, get_text('error'), f"{get_text('recognition_error_prefix')}\n{error_message}")

    def _calculate_columns(self) -> int:
        return TARGET_COLUMN_COUNT


    def _reset_hotkey_cursor_after_clear(self):
         list_widget = self.right_list_widget
         if list_widget and list_widget.isVisible() and self.mode != 'min':
            old_index = self.hotkey_cursor_index
            count = list_widget.count()
            self.hotkey_cursor_index = 0 if count > 0 else -1
            if self.hotkey_cursor_index != old_index or old_index != -1:
                if hasattr(self, 'ui_updater') and self.ui_updater:
                    self.ui_updater.update_hotkey_highlight(old_index)
            if self.hotkey_cursor_index == 0 and count > 0:
                first_item = list_widget.item(0)
                if first_item: list_widget.scrollToItem(first_item, QAbstractItemView.ScrollHint.EnsureVisible)
         else: self.hotkey_cursor_index = -1
    
    def _reset_hotkey_cursor_after_mode_change(self):
        list_widget = self.right_list_widget
        if list_widget and list_widget.isVisible() and self.mode != 'min':
            count = list_widget.count()
            if count > 0:
                self.hotkey_cursor_index = 0
                if hasattr(self, 'ui_updater') and self.ui_updater:
                    self.ui_updater.update_hotkey_highlight(old_index=None) 
                first_item = list_widget.item(0)
                if first_item: list_widget.scrollToItem(first_item, QAbstractItemView.ScrollHint.EnsureVisible)
            else: self.hotkey_cursor_index = -1
        else: self.hotkey_cursor_index = -1

    @Slot()
    def show_log_window(self):
        if self.log_dialog:
            if self.log_dialog.isVisible(): self.log_dialog.hide()
            else: self.log_dialog.show(); self.log_dialog.raise_(); self.log_dialog.activateWindow()

    @Slot()
    def _show_hotkey_info_dialog(self):
        if self.hotkey_display_dialog: 
            self.hotkey_display_dialog.update_html_content()
        else:
            self.hotkey_display_dialog = HotkeyDisplayDialog(self)
        self.hotkey_display_dialog.exec()


    @Slot()
    def show_hotkey_settings_window(self):
        if hasattr(self, 'hotkey_manager'):
            if show_hotkey_settings_dialog(self.hotkey_manager.get_current_hotkeys(),
                                           self.hotkey_manager.get_actions_config(),
                                           self):
                logging.info("Hotkey settings dialog saved. HotkeyManager should have updated hotkeys and restarted listener.")
            else:
                logging.info("Hotkey settings dialog was cancelled or closed without saving.")
        else: 
            logging.error("HotkeyManager not found in MainWindow.")


    def handle_selection_changed(self):
        if self.is_programmatically_updating_selection: return
        list_widget = self.right_list_widget
        if not list_widget: return
        selected_items = list_widget.selectedItems()
        current_ui_selection_names = set(item.data(HERO_NAME_ROLE) for item in selected_items if item and item.data(HERO_NAME_ROLE)) 
        
        if hasattr(self.logic, 'selected_heroes') and set(self.logic.selected_heroes) != current_ui_selection_names:
            self.logic.set_selection(current_ui_selection_names)
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_ui_after_logic_change()

    def show_priority_context_menu(self, pos: QPoint):
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible(): return
        item = list_widget.itemAt(pos)
        if not item: return
        hero_name = item.data(HERO_NAME_ROLE)
        if not hero_name: return
        
        global_pos = list_widget.viewport().mapToGlobal(pos) if list_widget.viewport() else self.mapToGlobal(pos) 
        menu = QMenu(self)
        is_priority = hero_name in self.logic.priority_heroes; is_selected = item.isSelected()
        action_text_key = 'remove_priority' if is_priority else 'set_priority'
        priority_action = menu.addAction(get_text(action_text_key))
        priority_action.setEnabled(is_selected) 
        action = menu.exec(global_pos)
        if priority_action and action == priority_action: 
            if hero_name in self.logic.selected_heroes: 
                self.logic.set_priority(hero_name)
                if hasattr(self, 'ui_updater') and self.ui_updater:
                    self.ui_updater.update_ui_after_logic_change()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key_event = event 
            
            if key_event.key() == Qt.Key_Tab:
                focus_widget = QApplication.focusWidget()
                
                if isinstance(focus_widget, HotkeyCaptureLineEdit) and focus_widget.objectName() == "HotkeyCaptureLineEdit":
                    logging.debug(f"Application.eventFilter: Tab for HotkeyCaptureLineEdit. Watched: {type(watched)}. Forwarding to widget.")
                    return False 

                active_window = QApplication.activeWindow()
                if active_window and active_window.windowTitle() == get_text('hotkey_settings_window_title'):
                    logging.debug(f"Application.eventFilter: Tab inside HotkeySettingsDialog (not on HotkeyCaptureLineEdit). Standard processing. Focus: {type(focus_widget)}")
                    return False 
                
                logging.debug(f"Application.eventFilter: Tab key press consumed by global filter to prevent focus switching. Focus: {type(focus_widget) if focus_widget else 'None'}")
                return True 

        if self.mode == "min" and hasattr(self, 'drag_handler') and self.drag_handler:
            if event.type() == QEvent.Type.MouseButtonPress:
                if self.drag_handler.mousePressEvent(event): 
                    return True 
            elif event.type() == QEvent.Type.MouseMove:
                if self.drag_handler.mouseMoveEvent(event): 
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self.drag_handler.mouseReleaseEvent(event): 
                    return True
                    
        return super().eventFilter(watched, event)


    def closeEvent(self, event: QCloseEvent): 
        logging.info("MainWindow closeEvent triggered.")
        
        if hasattr(self, 'log_dialog') and self.log_dialog and self.log_dialog.isVisible() : 
            self.log_dialog.close() 
        
        if hasattr(self, 'hotkey_display_dialog') and self.hotkey_display_dialog and self.hotkey_display_dialog.isVisible():
             self.hotkey_display_dialog.reject() 

        active_modals = QApplication.topLevelWidgets()
        for widget in active_modals:
            if isinstance(widget, QDialog) and widget.isModal() and widget.parent() == self:
                if widget.windowTitle() == get_text('hotkey_settings_window_title') or \
                   widget.windowTitle() == get_text('hotkey_settings_capture_title'): 
                    logging.info(f"Closing active modal dialog '{widget.windowTitle()}' before main window close.")
                    widget.reject() 
        
        if hasattr(self, 'hotkey_manager'): self.hotkey_manager.stop_listening()
        if hasattr(self, 'rec_manager') and self.rec_manager: self.rec_manager.stop_recognition()
        
        logging.info("Calling super().closeEvent(event)")
        super().closeEvent(event) 
        if event.isAccepted():
            logging.info(f"closeEvent finished. Event accepted: True")
            app_instance = QApplication.instance()
            if app_instance and not app_instance.quitOnLastWindowClosed():
                logging.info("quitOnLastWindowClosed is False, calling QApplication.quit() from MainWindow.closeEvent")
                QTimer.singleShot(0, QApplication.quit) 
        else:
            logging.info(f"closeEvent finished. Event accepted: False (ignored by super class or other handler)")