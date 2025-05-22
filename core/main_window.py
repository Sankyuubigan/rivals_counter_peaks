# File: core/main_window.py
import sys
import time
import logging
import os

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QScrollArea,
                               QLabel, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, # QAbstractItemView здесь
                               QMenu, QApplication, QMessageBox, QComboBox, QLineEdit, QTextEdit) # Добавил недостающие QComboBox, QLineEdit, QTextEdit, QTextBrowser
# ИЗМЕНЕНО: Добавлены QObject и QEvent
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint, QMetaObject, QEvent, QObject
from PySide6.QtGui import QIcon, QMouseEvent, QPixmap # Убрал QColor, QBrush, они не используются напрямую в MainWindow после рефакторинга

# Локальные импорты
import utils
from images_load import load_default_pixmap
from logic import CounterpickLogic, TEAM_SIZE # TEAM_SIZE используется
from top_panel import TopPanel
from right_panel import HERO_NAME_ROLE # Используется в MainWindow для handle_selection_changed и show_priority_context_menu
from log_handler import QLogHandler
from dialogs import (LogDialog, HotkeyDisplayDialog, show_about_program_info,
                     show_hero_rating, show_hotkey_settings_dialog)
from hotkey_manager import HotkeyManager
from mode_manager import ModeManager
from win_api import WinApiManager
from recognition import RecognitionManager
from ui_updater import UiUpdater
from action_controller import ActionController

from core.lang.translations import get_text, set_language, SUPPORTED_LANGUAGES


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
        logging.info("Initializing MainWindow...")
        self.logic = logic_instance
        self.hero_templates = hero_templates_dict
        self.app_version = app_version
        if hasattr(self.logic, 'main_window'): # Проверка перед присвоением
            self.logic.main_window = self

        self._setup_logging_and_dialogs()
        self.hotkey_manager = HotkeyManager(self)
        self.hotkey_manager.load_hotkeys()
        
        self.ui_updater = UiUpdater(self)
        self.action_controller = ActionController(self)

        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)
        
        self.mode = self.mode_manager.current_mode
        logging.info(f"Initial mode: {self.mode}")

        self._init_ui_attributes()
        self._setup_window_properties()
        self._create_main_ui_layout()

        QTimer.singleShot(0, lambda: self.ui_updater.update_interface_for_mode() if hasattr(self, 'ui_updater') and self.ui_updater else None)
        self._connect_signals()

        if KEYBOARD_AVAILABLE and IS_ADMIN:
            if hasattr(self, 'hotkey_manager'): self.hotkey_manager.start_listening()
        elif not KEYBOARD_AVAILABLE:
            logging.warning("Keyboard library not available, global hotkeys disabled.")
        elif not IS_ADMIN:
            logging.warning("No admin rights, global hotkeys might not work.")

        logging.info("MainWindow.__init__ finished")

    def _setup_logging_and_dialogs(self):
        self.log_dialog = LogDialog(self)
        self.log_handler = QLogHandler(self)
        if hasattr(self.log_handler, 'message_logged') and hasattr(self.log_dialog, 'append_log'):
            self.log_handler.message_logged.connect(self.log_dialog.append_log)
        log_format = '%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
        formatter = logging.Formatter(log_format, datefmt='%H:%M:%S')
        self.log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("GUI Log Handler initialized.")
        self.hotkey_display_dialog = HotkeyDisplayDialog(self)

    def _init_ui_attributes(self):
        initial_pos = self.pos() if self.isVisible() else None
        self.mode_positions = { "min": None, "middle": initial_pos, "max": None }
        self.mouse_invisible_mode_enabled = False
        self.is_programmatically_updating_selection = False
        self._last_mode_toggle_time = 0
        self._mouse_pressed = False
        self._old_pos: QPoint | None = None
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_panel_instance: TopPanel | None = None
        self.right_panel_instance: RightPanel | None = None
        self.main_layout: QVBoxLayout | None = None
        self.top_frame: QFrame | None = None
        self.about_program_button: QPushButton | None = None
        self.rating_button: QPushButton | None = None
        self.close_button: QPushButton | None = None
        self.tray_mode_button: QPushButton | None = None
        self.icons_scroll_area: QScrollArea | None = None
        self.icons_scroll_content: QWidget | None = None
        self.icons_main_h_layout: QHBoxLayout | None = None
        self.counters_widget: QWidget | None = None
        self.counters_layout: QHBoxLayout | None = None
        self.enemies_widget: QWidget | None = None
        self.enemies_layout: QHBoxLayout | None = None
        self.horizontal_info_label: QLabel = QLabel()
        self.horizontal_info_label.setObjectName("horizontal_info_label")
        self.horizontal_info_label.setStyleSheet("color: gray; margin-left: 5px;")
        self.horizontal_info_label.hide()
        self.main_widget: QWidget | None = None
        self.inner_layout: QHBoxLayout | None = None
        self.left_panel_widget: QWidget | None = None
        self.canvas: QScrollArea | None = None
        self.result_frame: QFrame | None = None
        self.result_label: QLabel | None = None
        self.update_scrollregion = lambda: None
        self.right_panel_widget: QWidget | None = None
        self.right_frame: QFrame | None = None
        self.right_list_widget: QListWidget | None = None
        self.selected_heroes_label: QLabel | None = None
        self.hero_items: dict[str, QListWidgetItem] = {}
        self.hotkey_cursor_index = -1
        self._num_columns_cache = 1

    def _setup_window_properties(self):
        self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
        icon_path_logo = utils.resource_path("logo.ico") # utils.resource_path теперь указывает на корень проекта
        icon_pixmap_logo = QPixmap(icon_path_logo) if os.path.exists(icon_path_logo) else None
        if icon_pixmap_logo and not icon_pixmap_logo.isNull():
            self.setWindowIcon(QIcon(icon_pixmap_logo))
        else:
            icon_path_fallback = utils.resource_path("resources/icon.png") # Путь к иконке в resources
            icon_pixmap_fallback = QPixmap(icon_path_fallback) if os.path.exists(icon_path_fallback) else load_default_pixmap((32,32))
            if not icon_pixmap_fallback.isNull(): self.setWindowIcon(QIcon(icon_pixmap_fallback))
            else: logging.warning("Failed to load any application icon.")
        if not self.isVisible(): self.setGeometry(100, 100, 950, 350)
        self.setMinimumSize(400, 100)
        # Устанавливаем eventFilter только если QApplication.instance() существует
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.installEventFilter(self)
        else:
            logging.warning("QApplication instance not found, cannot install event filter on MainWindow.")


    def _create_main_ui_layout(self):
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        if hasattr(self, 'change_mode') and self.logic and self.app_version:
            self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
            if self.top_panel_instance:
                self.top_frame = self.top_panel_instance.top_frame
                self.about_program_button = self.top_panel_instance.about_program_button
                self.rating_button = self.top_panel_instance.rating_button
                self.close_button = self.top_panel_instance.close_button
                self.tray_mode_button = self.top_panel_instance.tray_mode_button
                if self.top_frame: self.main_layout.addWidget(self.top_frame)
        else:
            logging.error("Cannot create TopPanel due to missing attributes in MainWindow.")
            return # Не можем продолжать без TopPanel

        self._create_icons_scroll_area_structure()
        if self.icons_scroll_area: self.main_layout.addWidget(self.icons_scroll_area)
        
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget)
        self.inner_layout.setContentsMargins(0,0,0,0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1)

    def _create_icons_scroll_area_structure(self):
        self.icons_scroll_area = QScrollArea(); self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea#icons_scroll_area { border: none; background-color: #f0f0f0; padding: 0px; margin: 0px; }")
        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content.setStyleSheet("background-color: transparent;")
        self.icons_main_h_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_main_h_layout.setContentsMargins(5, 2, 5, 2); self.icons_main_h_layout.setSpacing(10)
        self.icons_main_h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.counters_widget = QWidget(); self.counters_widget.setObjectName("counters_widget")
        self.counters_layout = QHBoxLayout(self.counters_widget)
        self.counters_layout.setContentsMargins(0, 0, 0, 0); self.counters_layout.setSpacing(4)
        self.counters_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_main_h_layout.addWidget(self.counters_widget, stretch=1)
        self.enemies_widget = QWidget(); self.enemies_widget.setObjectName("enemies_widget")
        self.enemies_widget.setStyleSheet("QWidget#enemies_widget { border: none; padding: 1px; }")
        self.enemies_layout = QHBoxLayout(self.enemies_widget)
        self.enemies_layout.setContentsMargins(2, 2, 2, 2); self.enemies_layout.setSpacing(4)
        self.enemies_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_main_h_layout.addWidget(self.enemies_widget, stretch=0); self.enemies_widget.hide()
        if hasattr(self, 'horizontal_info_label') and self.horizontal_info_label and self.horizontal_info_label.parentWidget():
            parent_layout = self.horizontal_info_label.parentWidget().layout()
            if parent_layout: parent_layout.removeWidget(self.horizontal_info_label)
            self.horizontal_info_label.setParent(None)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)

    def _connect_signals(self):
        logging.debug("Connecting signals to ActionController...")
        if hasattr(self, 'action_controller') and self.action_controller:
            self.action_move_cursor_up.connect(lambda: self.action_controller.handle_move_cursor('up'))
            self.action_move_cursor_down.connect(lambda: self.action_controller.handle_move_cursor('down'))
            self.action_move_cursor_left.connect(lambda: self.action_controller.handle_move_cursor('left'))
            self.action_move_cursor_right.connect(lambda: self.action_controller.handle_move_cursor('right'))
            self.action_toggle_selection.connect(self.action_controller.handle_toggle_selection)
            self.action_toggle_mode.connect(self.action_controller.handle_toggle_mode)
            self.action_clear_all.connect(self.action_controller.handle_clear_all)
            if hasattr(self, 'rec_manager') and self.rec_manager and hasattr(self.rec_manager, 'recognize_heroes_signal'):
                self.action_recognize_heroes.connect(self.rec_manager.recognize_heroes_signal.emit)
            self.action_debug_capture.connect(self.action_controller.handle_debug_capture)
            self.action_toggle_tray_mode.connect(self.toggle_tray_mode)
            self.action_toggle_mouse_ignore_independent.connect(self._handle_toggle_mouse_invisible_mode_independent)
            self.action_copy_team.connect(self.action_controller.handle_copy_team)
        else:
            logging.error("ActionController not initialized, cannot connect signals.")

        if hasattr(self, 'rec_manager') and self.rec_manager:
            if hasattr(self.rec_manager, 'recognition_complete_signal'):
                self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
            if hasattr(self.rec_manager, 'error'):
                self.rec_manager.error.connect(self._on_recognition_error)

        if self.tray_mode_button and hasattr(self, 'update_tray_button_property_signal'):
             self.update_tray_button_property_signal.connect(self._update_tray_button_property)
        if self.win_api_manager and hasattr(self.win_api_manager, 'topmost_state_changed'):
            self.win_api_manager.topmost_state_changed.connect(self._handle_topmost_state_change)
        logging.debug("MainWindow signals connected.")

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            # Проверяем, что нажата ТОЛЬКО Tab и окно активно
            if event.key() == Qt.Key_Tab and QApplication.keyboardModifiers() == Qt.KeyboardModifier.NoModifier and self.isActiveWindow():
                 focused_widget = QApplication.focusWidget()
                 # Добавили QListWidget, чтобы Tab не работал и там
                 if not isinstance(focused_widget, (QComboBox, QLineEdit, QTextEdit, QTextBrowser, QListWidget)): 
                     logging.debug("Ignoring single Tab press to prevent focus change.")
                     return True # Игнорируем событие
        return super().eventFilter(watched, event)


    @Slot(bool)
    def _update_tray_button_property(self, is_active):
        if self.tray_mode_button:
            self.tray_mode_button.setProperty("trayModeActive", is_active)
            button_text_key = 'tray_mode_on' if is_active else 'tray_mode_off'
            self.tray_mode_button.setText(get_text(button_text_key, language=self.logic.DEFAULT_LANGUAGE))
            # Переприменение стиля для обновления кнопки
            style = self.tray_mode_button.style()
            if style:
                style.unpolish(self.tray_mode_button)
                style.polish(self.tray_mode_button)
            self.tray_mode_button.update()


    @Slot(bool)
    def _handle_topmost_state_change(self, is_topmost):
        if hasattr(self, 'update_tray_button_property_signal'):
            self.update_tray_button_property_signal.emit(is_topmost)
        if hasattr(self, 'mouse_invisible_mode_enabled') and self.mouse_invisible_mode_enabled != is_topmost:
            self.mouse_invisible_mode_enabled = is_topmost
            self._apply_mouse_invisible_mode()


    @Slot()
    def _handle_toggle_mouse_invisible_mode_independent(self):
        if hasattr(self, 'mouse_invisible_mode_enabled'):
            self.mouse_invisible_mode_enabled = not self.mouse_invisible_mode_enabled
            self._apply_mouse_invisible_mode()
            logging.info(f"Mouse invisible mode (independent) set to: {self.mouse_invisible_mode_enabled}")


    def _apply_mouse_invisible_mode(self):
        if not self.isVisible(): return
        flags = self.windowFlags()
        should_be_transparent = getattr(self, 'mouse_invisible_mode_enabled', False)
        is_currently_transparent = bool(flags & Qt.WindowTransparentForInput)
        
        if should_be_transparent != is_currently_transparent:
            current_geometry = self.geometry() # Сохраняем геометрию
            if should_be_transparent: flags |= Qt.WindowTransparentForInput
            else: flags &= ~Qt.WindowTransparentForInput
            
            self.setWindowFlags(flags)
            self.show() # Показать окно после смены флагов
            
            # Восстанавливаем геометрию. QTimer для того, чтобы окно успело обработать setWindowFlags.
            QTimer.singleShot(10, lambda: self.setGeometry(current_geometry) if self.isVisible() else None)
            logging.info(f"WindowTransparentForInput set to {should_be_transparent}")


    @Slot()
    def toggle_tray_mode(self):
        if hasattr(self, 'win_api_manager'):
            target_tray_state_on = not self.win_api_manager.is_win_topmost
            self.win_api_manager.set_topmost_winapi(target_tray_state_on)


    def closeEvent(self, event: QEvent): # QEvent вместо QCloseEvent для единообразия
        logging.info("Close event triggered.");
        if hasattr(self, 'log_dialog') and self.log_dialog: self.log_dialog.hide()
        
        # Проверка существования атрибута перед использованием
        hotkey_settings_dialog = getattr(self, 'hotkey_settings_dialog_instance', None)
        if hotkey_settings_dialog and hotkey_settings_dialog.isVisible():
            hotkey_settings_dialog.hide()
        elif hasattr(self, 'hotkey_display_dialog') and self.hotkey_display_dialog and self.hotkey_display_dialog.isVisible():
             self.hotkey_display_dialog.hide()

        if hasattr(self, 'hotkey_manager'): self.hotkey_manager.stop_listening()
        if hasattr(self, 'rec_manager') and self.rec_manager: self.rec_manager.stop_recognition()
        super().closeEvent(event)


    def mousePressEvent(self, event: QMouseEvent):
        if self.mode == "min" and self.top_frame and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_pressed = True; self._old_pos = event.globalPosition().toPoint(); event.accept(); return
        self._mouse_pressed = False; super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos; self.move(self.pos() + delta); self._old_pos = event.globalPosition().toPoint(); event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False; self._old_pos = None; event.accept()
        else: super().mouseReleaseEvent(event)

    def change_mode(self, mode_name: str):
        logging.info(f"--- MainWindow: Attempting to change mode to: {mode_name} (Current: {self.mode}) ---")
        if self.mode == mode_name: return
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
        
        QTimer.singleShot(50, self._apply_mouse_invisible_mode)
        self._reset_hotkey_cursor_after_mode_change()
        logging.info(f"--- MainWindow: Mode change to {mode_name} FINISHED ---")

    def _move_window_safely(self, target_pos: QPoint):
        if self.isVisible(): self.move(target_pos)

    @property
    def _is_win_topmost(self):
        return self.win_api_manager.is_win_topmost if hasattr(self, 'win_api_manager') and self.win_api_manager else False

    def set_topmost_winapi(self, enable: bool):
        if hasattr(self, 'win_api_manager') and self.win_api_manager: self.win_api_manager.set_topmost_winapi(enable)

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
        QMessageBox.warning(self, get_text('error', language=self.logic.DEFAULT_LANGUAGE), f"{get_text('recognition_error_prefix', language=self.logic.DEFAULT_LANGUAGE)}\n{error_message}")

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
                    self.ui_updater.update_hotkey_highlight(old_index=None) # old_index is None
                first_item = list_widget.item(0)
                if first_item: list_widget.scrollToItem(first_item, QAbstractItemView.ScrollHint.EnsureVisible)
            else: self.hotkey_cursor_index = -1
        else: self.hotkey_cursor_index = -1

    def switch_language(self, lang_code: str):
        if lang_code not in SUPPORTED_LANGUAGES: return
        if self.logic.DEFAULT_LANGUAGE != lang_code:
            set_language(lang_code); self.logic.DEFAULT_LANGUAGE = lang_code
            self.update_language()
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_ui_after_logic_change()
                if self.hotkey_cursor_index != -1:
                     QTimer.singleShot(50, self.ui_updater.update_hotkey_highlight)

    def update_language(self):
        current_lang = self.logic.DEFAULT_LANGUAGE
        self.setWindowTitle(f"{get_text('title', language=current_lang)} v{self.app_version}")
        if self.top_panel_instance: self.top_panel_instance.update_language()
        if self.right_panel_instance and self.right_panel_widget and self.right_panel_widget.isVisible():
            self.right_panel_instance.update_language()
            list_widget = self.right_list_widget; hero_items_dict = self.hero_items
            if list_widget and hero_items_dict:
                 focused_tooltip_base = None; current_focused_item = None
                 if 0 <= self.hotkey_cursor_index < list_widget.count():
                      current_item_candidate = list_widget.item(self.hotkey_cursor_index)
                      if current_item_candidate: # Проверка на None
                          current_focused_item = current_item_candidate
                          focused_tooltip_base = current_focused_item.data(HERO_NAME_ROLE)

                 for hero, item in hero_items_dict.items():
                      if item: item.setToolTip(hero)
                 
                 if focused_tooltip_base and current_focused_item:
                     current_focused_item.setToolTip(f">>> {focused_tooltip_base} <<<")
        
        if self.result_label and hasattr(self.logic, 'selected_heroes') and not self.logic.selected_heroes:
            self.result_label.setText(get_text('no_heroes_selected', language=current_lang))

    @Slot()
    def show_log_window(self):
        if self.log_dialog:
            if self.log_dialog.isVisible(): self.log_dialog.hide()
            else: self.log_dialog.show(); self.log_dialog.raise_(); self.log_dialog.activateWindow()

    @Slot()
    def _show_hotkey_info_dialog(self):
        if self.hotkey_display_dialog: self.hotkey_display_dialog.exec()

    @Slot()
    def show_hotkey_settings_window(self):
        if hasattr(self, 'hotkey_manager'):
            if show_hotkey_settings_dialog(self.hotkey_manager.get_current_hotkeys(),
                                           self.hotkey_manager.get_actions_config(),
                                           self):
                self.hotkey_manager.reregister_all_hotkeys()
        else: logging.error("HotkeyManager not found in MainWindow.")

    def handle_selection_changed(self):
        if self.is_programmatically_updating_selection: return
        list_widget = self.right_list_widget
        if not list_widget: return
        selected_items = list_widget.selectedItems()
        current_ui_selection_names = set(item.data(HERO_NAME_ROLE) for item in selected_items if item and item.data(HERO_NAME_ROLE)) # Добавлена проверка item
        if len(current_ui_selection_names) > TEAM_SIZE: pass
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
        
        global_pos = list_widget.viewport().mapToGlobal(pos) if list_widget.viewport() else self.mapToGlobal(pos) # Добавлена проверка viewport
        menu = QMenu(self)
        is_priority = hero_name in self.logic.priority_heroes; is_selected = item.isSelected()
        action_text_key = 'remove_priority' if is_priority else 'set_priority'
        priority_action = menu.addAction(get_text(action_text_key, language=self.logic.DEFAULT_LANGUAGE))
        priority_action.setEnabled(is_selected)
        action = menu.exec(global_pos)
        if priority_action and action == priority_action:
            if hero_name in self.logic.selected_heroes:
                self.logic.set_priority(hero_name)
                if hasattr(self, 'ui_updater') and self.ui_updater:
                    self.ui_updater.update_ui_after_logic_change()
