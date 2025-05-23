# File: core/main_window.py
import sys
import time
import logging
import os

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QScrollArea,
                               QLabel, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, 
                               QMenu, QApplication, QMessageBox, QComboBox, QLineEdit, QTextEdit, QTextBrowser) 
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint, QMetaObject, QEvent, QObject, QRect 
from PySide6.QtGui import QIcon, QMouseEvent, QPixmap, QShowEvent, QHideEvent, QCloseEvent 

import utils
from images_load import load_default_pixmap
from logic import CounterpickLogic, TEAM_SIZE 
from top_panel import TopPanel
from right_panel import HERO_NAME_ROLE 
from log_handler import QLogHandler
# ИЗМЕНЕНО: Импортируем HotkeyCaptureLineEdit для type hinting, если понадобится, но в eventFilter будем проверять по objectName
from dialogs import (LogDialog, HotkeyDisplayDialog, show_about_program_info,
                     show_hero_rating, show_hotkey_settings_dialog, HotkeyCaptureLineEdit)
from hotkey_manager import HotkeyManager 
from mode_manager import ModeManager, MODE_DEFAULT_WINDOW_SIZES 
from win_api import WinApiManager
from recognition import RecognitionManager
from ui_updater import UiUpdater
from action_controller import ActionController
from window_drag_handler import WindowDragHandler
from appearance_manager import AppearanceManager

from core.lang.translations import get_text


try:
    import keyboard 
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    keyboard = None
    logging.error("'keyboard' library not found. Global hotkeys will be disabled.")

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
        logging.info(">>> MainWindow.__init__ START")
        self.logic = logic_instance
        self.hero_templates = hero_templates_dict
        self.app_version = app_version
        if hasattr(self.logic, 'main_window'): 
            self.logic.main_window = self

        self._setup_logging_and_dialogs() 

        self.appearance_manager = AppearanceManager(self)
        self.current_theme = self.appearance_manager.current_theme 

        self.hotkey_manager = HotkeyManager(self) 
        
        self.ui_updater = UiUpdater(self) 
        self.action_controller = ActionController(self)

        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)
        
        self.drag_handler = WindowDragHandler(self, lambda: getattr(self, 'top_frame', None))
        
        self.hotkey_manager.load_hotkeys() 

        self.mode = self.mode_manager.current_mode
        logging.info(f"Initial mode from ModeManager: {self.mode}")

        self._init_ui_attributes()
        self._setup_window_properties() 
        self._create_main_ui_layout() 
        
        if self.appearance_manager: 
            self.appearance_manager._apply_qss_theme(self.appearance_manager.current_theme, on_startup=True)
        
        self._connect_signals()
        
        self._initial_ui_update_done = False
        self._is_applying_flags_operation = False 
        self._geometry_before_flags_change: QRect | None = None 

        logging.info(f"<<< MainWindow.__init__ FINISHED. Initial self.windowFlags(): {self.windowFlags():#x}")

    def _setup_logging_and_dialogs(self):
        self.log_dialog = LogDialog(self) 
        self.log_handler = QLogHandler(self) 
        if hasattr(self.log_handler, 'message_logged') and hasattr(self.log_dialog, 'append_log'):
            self.log_handler.message_logged.connect(self.log_dialog.append_log)
        
        log_format = '%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
        formatter = logging.Formatter(log_format, datefmt='%H:%M:%S')
        self.log_handler.setFormatter(formatter)
        
        logging.getLogger().addHandler(self.log_handler)
        if logging.getLogger().level == logging.NOTSET: 
             logging.getLogger().setLevel(logging.DEBUG) 
        
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
            logging.warning(f"Mode toggle (from slot) ignored due to debounce ({current_time - self._last_mode_toggle_time:.2f}s < {debounce_time}s)")
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
        self._num_columns_cache = 1
        self.hotkey_display_dialog = None 

        self._last_applied_flags = Qt.WindowFlags() 
        self._geometry_before_flags_change = None


    def _setup_window_properties(self):
        logging.debug(f"    [WindowProps] START. Current flags before setup: {self.windowFlags():#x}")
        self.setWindowTitle(f"{get_text('title')} v{self.app_version}")
        
        icon_path_logo = utils.resource_path("logo.ico") 
        icon_pixmap_logo = QPixmap(icon_path_logo) if os.path.exists(icon_path_logo) else None
        if icon_pixmap_logo and not icon_pixmap_logo.isNull():
            self.setWindowIcon(QIcon(icon_pixmap_logo))
        else:
            icon_path_fallback = utils.resource_path("resources/icon.png") 
            icon_pixmap_fallback = QPixmap(icon_path_fallback) if os.path.exists(icon_path_fallback) else load_default_pixmap((32,32))
            if not icon_pixmap_fallback.isNull(): self.setWindowIcon(QIcon(icon_pixmap_fallback))
            else: logging.warning("Failed to load any application icon.")
        
        initial_width = MODE_DEFAULT_WINDOW_SIZES.get(self.mode, {}).get('width', 950)
        initial_height = MODE_DEFAULT_WINDOW_SIZES.get(self.mode, {}).get('height', 600) 
        
        self.setMinimumSize(300, 70) 
        
        self._last_applied_flags = self.windowFlags() 
        logging.debug(f"    [WindowProps] END. Initial self._last_applied_flags set to: {self._last_applied_flags:#x}")

        app_instance = QApplication.instance()
        if app_instance:
            app_instance.installEventFilter(self) 
        else:
            logging.warning("QApplication instance not found, cannot install event filter on MainWindow.")


    def _create_main_ui_layout(self):
        logging.info("    MainWindow: _create_main_ui_layout START")
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
        logging.info("    MainWindow: _create_main_ui_layout END")


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
        logging.info("    Connecting signals...") 
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
            logging.info("    ActionController signals connected.")
        else:
            logging.error("    ActionController not initialized, cannot connect signals.")

        if hasattr(self, 'rec_manager') and self.rec_manager:
            if hasattr(self.rec_manager, 'recognition_complete_signal'):
                self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
            if hasattr(self.rec_manager, 'error'):
                self.rec_manager.error.connect(self._on_recognition_error)
            logging.info("    RecognitionManager signals connected.")

        if self.tray_mode_button and hasattr(self, 'update_tray_button_property_signal'):
             self.update_tray_button_property_signal.connect(self._update_tray_button_property)
        if self.win_api_manager and hasattr(self.win_api_manager, 'topmost_state_changed'):
            self.win_api_manager.topmost_state_changed.connect(self._handle_topmost_state_change)
        logging.info("    MainWindow general signals connected.")

    def _apply_window_flags_and_show(self, new_flags: Qt.WindowFlags, reason: str):
        logging.debug(f"    [ApplyFlags] START _apply_window_flags_and_show. Reason: '{reason}'. Current flags: {self.windowFlags():#x}, Target new flags: {new_flags:#x}, Last applied: {self._last_applied_flags:#x}")

        if self._is_applying_flags_operation:
            logging.warning(f"    [ApplyFlags] Skipped due to _is_applying_flags_operation already True. Reason: {reason}")
            return

        self._is_applying_flags_operation = True
        
        current_actual_flags = self.windowFlags()
        flags_need_change = (current_actual_flags != new_flags)

        if flags_need_change:
            logging.info(f"    [ApplyFlags] Flags differ. Current actual: {current_actual_flags:#x}, New target: {new_flags:#x}. Applying. Reason: {reason}")
            
            self._geometry_before_flags_change = self.geometry() 
            was_visible = self.isVisible()
            was_minimized = self.isMinimized()
            
            self.setWindowFlags(new_flags) 
            self._last_applied_flags = new_flags 

            logging.info(f"    [ApplyFlags] After setWindowFlags. New actual flags: {self.windowFlags():#x}. Window visible: {self.isVisible()}, minimized: {was_minimized}")

            if was_visible and not was_minimized:
                if not self.isVisible(): 
                    logging.info(f"    [ApplyFlags] Window became hidden by setWindowFlags. Calling show(). Reason: {reason}")
                    self.show() 
                else: 
                    logging.info(f"    [ApplyFlags] Window remained visible after setWindowFlags. No explicit show() needed. Reason: {reason}")

                if self.isVisible() and self._geometry_before_flags_change and self._geometry_before_flags_change.isValid():
                    logging.info(f"    [ApplyFlags] Restoring geometry to {self._geometry_before_flags_change}. Reason: {reason}")
                    self.setGeometry(self._geometry_before_flags_change)
            elif was_minimized:
                logging.info(f"    [ApplyFlags] Window was minimized, flags applied. Not calling show(). Reason: {reason}")
        else:
            logging.info(f"    [ApplyFlags] Target flags {new_flags:#x} are same as current window flags {current_actual_flags:#x}. No setWindowFlags needed. Reason: {reason}")
            if not self.isVisible() and self.windowState() != Qt.WindowState.WindowMinimized and reason != "force_taskbar_update_hide":
                 logging.info(f"    [ApplyFlags] Window not visible but should be (not minimized). Calling show(). Reason: {reason}")
                 self.show()


        self._is_applying_flags_operation = False
        logging.debug(f"    [ApplyFlags] END _apply_window_flags_and_show. Reason: {reason}")


    def _calculate_target_flags(self) -> Qt.WindowFlags:
        is_min_mode = (self.mode == "min")
        if is_min_mode:
            base_flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        else:
            base_flags = Qt.WindowType.Window | Qt.WindowType.WindowSystemMenuHint | \
                         Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint | \
                         Qt.WindowType.WindowMaximizeButtonHint
        
        topmost_flag_to_add = Qt.WindowType.WindowStaysOnTopHint if self._is_win_topmost else Qt.WindowType(0)
        transparent_flag_to_add = Qt.WindowType.WindowTransparentForInput if getattr(self, 'mouse_invisible_mode_enabled', False) else Qt.WindowType(0)
        
        return base_flags | topmost_flag_to_add | transparent_flag_to_add

    def _apply_mouse_invisible_mode(self, reason: str):
        logging.debug(f"--> _apply_mouse_invisible_mode called. Reason: '{reason}'")
        target_flags = self._calculate_target_flags()
        self._apply_window_flags_and_show(target_flags, reason)
        logging.debug(f"<-- _apply_mouse_invisible_mode finished. Reason: '{reason}'")


    def _force_taskbar_update_internal(self, reason_suffix="unknown"): 
        caller_reason = f"force_taskbar_update_{reason_suffix}"
        if self._is_applying_flags_operation and not self.sender():
             logging.warning(f"    [TaskbarUpdate] Skipped _force_taskbar_update_internal due to _is_applying_flags_operation flag. Caller reason: {caller_reason}")
             return
        
        self._is_applying_flags_operation = True
        logging.debug(f"    [TaskbarUpdate] START _force_taskbar_update_internal. Caller reason: {caller_reason}")

        if self.isVisible() and not self.isMinimized() and sys.platform == 'win32':
            logging.info(f"    [TaskbarUpdate] Actual Force taskbar update: Hiding briefly for mode {self.mode}. Caller reason: {caller_reason}")
            
            geom_before_hide = self.geometry()
            self.hide() 

            def _reshow_after_taskbar_hide():
                logging.debug(f"    [TaskbarUpdate] Reshowing window. Minimized: {self.isMinimized()}. Caller reason: {caller_reason}")
                if not self.isMinimized():
                    current_target_flags = self._calculate_target_flags() 
                    self._apply_window_flags_and_show(current_target_flags, f"reshow_after_taskbar_for_{reason_suffix}")
                    if self.isVisible() and geom_before_hide.isValid(): 
                        self.setGeometry(geom_before_hide)

                self._is_applying_flags_operation = False 
                logging.debug(f"    [TaskbarUpdate] END _reshow_after_taskbar_hide. Caller reason: {caller_reason}")
            
            QTimer.singleShot(100, _reshow_after_taskbar_hide)
        else:
            logging.debug(f"    [TaskbarUpdate] Skipped actual hide/show. Visible={self.isVisible()}, Minimized={self.isMinimized()}, Platform={sys.platform}. Caller reason: {caller_reason}")
            self._is_applying_flags_operation = False 
            logging.debug(f"    [TaskbarUpdate] END _force_taskbar_update_internal (skipped). Caller reason: {caller_reason}")


    def showEvent(self, event: QShowEvent):
        logging.info(f">>> showEvent START. Visible: {self.isVisible()}, Active: {self.isActiveWindow()}, isApplyingFlags: {self._is_applying_flags_operation}, initialDone: {self._initial_ui_update_done}")
        super().showEvent(event)
        
        if self._is_applying_flags_operation:
            logging.debug("    showEvent: Called during _is_applying_flags_operation. Restoring geometry if needed.")
            if self._geometry_before_flags_change and self._geometry_before_flags_change.isValid():
                if self.geometry() != self._geometry_before_flags_change:
                    self.setGeometry(self._geometry_before_flags_change)
            logging.info("<<< showEvent END (during flag operation)")
            return

        if not self._initial_ui_update_done:
            logging.info("    showEvent: Performing initial setup (_initial_ui_update_done is False).")
            
            if hasattr(self, 'ui_updater') and self.ui_updater:
                QTimer.singleShot(10, lambda: self.ui_updater.update_interface_for_mode(new_mode=self.mode) if self.ui_updater else None)
            else: 
                QTimer.singleShot(10, lambda: self._apply_mouse_invisible_mode("initial_show_no_ui_updater"))

            if KEYBOARD_AVAILABLE and IS_ADMIN:
                 if hasattr(self, 'hotkey_manager'): 
                     QTimer.singleShot(200, lambda: self.hotkey_manager.start_listening() if self.hotkey_manager else None) 
            self._initial_ui_update_done = True
        else:
            current_actual_flags_on_show = self.windowFlags()
            if current_actual_flags_on_show != self._last_applied_flags:
                logging.warning(f"    showEvent: Flags mismatch! Current: {current_actual_flags_on_show:#x}, Last Applied: {self._last_applied_flags:#x}. Re-applying flags.")
                self._apply_mouse_invisible_mode("show_event_flags_mismatch")
            else:
                logging.debug(f"    showEvent: Repeated show, flags consistent {current_actual_flags_on_show:#x}. No action.")

        logging.info("<<< showEvent END")


    def hideEvent(self, event: QHideEvent):
        logging.info(f"MainWindow hideEvent triggered. isApplyingFlags: {self._is_applying_flags_operation}")
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
        self._apply_mouse_invisible_mode("_handle_topmost_state_change")
        logging.debug(f"<-- _handle_topmost_state_change finished")


    @Slot()
    def _handle_toggle_mouse_invisible_mode_independent(self):
        logging.debug("--> _handle_toggle_mouse_invisible_mode_independent triggered.")
        if hasattr(self, 'mouse_invisible_mode_enabled'):
            self.mouse_invisible_mode_enabled = not self.mouse_invisible_mode_enabled
            self._apply_mouse_invisible_mode("_handle_toggle_mouse_invisible_mode_independent")
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
        logging.info(f"--> MainWindow: change_mode to: {mode_name} (Current: {self.mode})")
        if self.mode == mode_name: 
            logging.info(f"    Mode is already {mode_name}. No change.")
            logging.info(f"<-- MainWindow: change_mode finished (no change)")
            return
            
        old_mode = self.mode
        if self.isVisible(): self.mode_positions[old_mode] = self.pos()
        
        self.hotkey_cursor_index = -1
        if self.right_list_widget and self.right_list_widget.isVisible() and self.right_list_widget.viewport():
            self.right_list_widget.viewport().update()

        if hasattr(self, 'mode_manager'): self.mode_manager.change_mode(mode_name)
        self.mode = mode_name 
        
        if hasattr(self, 'ui_updater') and self.ui_updater:
            self.ui_updater.update_interface_for_mode(new_mode=self.mode) 
        
        target_pos = self.mode_positions.get(self.mode)
        if target_pos and self.isVisible():
            QTimer.singleShot(0, lambda: self._move_window_safely(target_pos))
        elif self.isVisible(): 
            self.mode_positions[self.mode] = self.pos()
        
        self._reset_hotkey_cursor_after_mode_change()
        logging.info(f"<-- MainWindow: change_mode to {mode_name} FINISHED")

    def _move_window_safely(self, target_pos: QPoint):
        if self.isVisible(): self.move(target_pos)

    @property
    def _is_win_topmost(self):
        return self.win_api_manager.is_win_topmost if hasattr(self, 'win_api_manager') and self.win_api_manager else False

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes):
        logging.info(f"MainWindow: Recognition complete. Heroes: {recognized_heroes}")
        if recognized_heroes and hasattr(self, 'logic'):
            self.logic.set_selection(set(recognized_heroes))
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_ui_after_logic_change()
            self._reset_hotkey_cursor_after_clear()
        elif not recognized_heroes:
            logging.info("No heroes recognized.")

    @Slot(str)
    def _on_recognition_error(self, error_message):
        logging.error(f"MainWindow: Recognition error: {error_message}")
        QMessageBox.warning(self, get_text('error'), f"{get_text('recognition_error_prefix')}\n{error_message}")

    def _calculate_columns(self) -> int:
        list_widget = self.right_list_widget
        if not (list_widget and list_widget.isVisible() and self.mode != 'min'):
            self._num_columns_cache = 1; return 1
        
        viewport = list_widget.viewport()
        if not viewport: return self._num_columns_cache
        
        vp_width = viewport.width(); grid_size = list_widget.gridSize(); spacing = list_widget.spacing()
        if grid_size.width() <= 0: return self._num_columns_cache
        effective_grid_width = grid_size.width() + spacing
        if effective_grid_width <= 0: return self._num_columns_cache
        
        cols = max(1, int(vp_width / effective_grid_width))
        if cols != self._num_columns_cache: self._num_columns_cache = cols
        return cols


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
                self._calculate_columns()
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
                logging.info("Hotkey settings dialog saved. HotkeyManager should have reregistered hotkeys via its save_hotkeys method.")
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
            key_event = event # QKeyEvent
            
            active_modal_widget = QApplication.activeModalWidget()
            # Проверяем, активно ли главное окно ИЛИ один из его модальных диалогов
            is_our_window_active = self.isActiveWindow()
            if not is_our_window_active and active_modal_widget:
                 # Проверяем, является ли модальный диалог потомком MainWindow
                 # или был создан с MainWindow в качестве родителя
                 parent_dialog = active_modal_widget
                 while parent_dialog:
                     if parent_dialog == self:
                         is_our_window_active = True
                         break
                     parent_dialog = parent_dialog.parent()


            if key_event.key() == Qt.Key_Tab and is_our_window_active:
                focus_widget = QApplication.focusWidget()
                
                # Разрешаем Tab для стандартных QLineEdit, QComboBox, QTextEdit, но не для HotkeyCaptureLineEdit
                if isinstance(focus_widget, (QComboBox, QTextEdit)) or \
                   (isinstance(focus_widget, QLineEdit) and getattr(focus_widget, 'objectName', lambda: '')() != "HotkeyCaptureLineEdit"):
                    logging.debug(f"MainWindow.eventFilter: Tab in a standard input widget ({type(focus_widget)}), allowing. Watched: {watched.objectName() if hasattr(watched, 'objectName') else type(watched)}")
                    return False # Стандартная обработка Tab

                # Блокируем Tab для HotkeyCaptureLineEdit и других случаев в наших окнах
                logging.debug(f"MainWindow.eventFilter: Tab key press consumed. Watched: {watched.objectName() if hasattr(watched, 'objectName') else type(watched)}, Focus: {focus_widget.objectName() if hasattr(focus_widget, 'objectName') else type(focus_widget) if focus_widget else 'None'}")
                return True 

        return super().eventFilter(watched, event)


    def closeEvent(self, event: QCloseEvent): 
        logging.info("MainWindow closeEvent triggered.")
        
        if hasattr(self, 'log_dialog') and self.log_dialog and self.log_dialog.isVisible() : 
            self.log_dialog.close() 
        
        # hotkey_settings_dialog_instance создается и управляется локально в show_hotkey_settings_window
        # поэтому здесь проверять его не нужно, если он не хранится в self.
        
        if hasattr(self, 'hotkey_display_dialog') and self.hotkey_display_dialog and self.hotkey_display_dialog.isVisible():
             self.hotkey_display_dialog.reject() 

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
