# File: core/main_window.py
import sys
import time
import logging
import os
import datetime 
from pathlib import Path 
import tempfile 
import shutil 

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QScrollArea,
                               QLabel, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, 
                               QMenu, QApplication, QMessageBox, QSlider) 
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint, QMetaObject, QEvent, QRect, QObject 
from PySide6.QtGui import QIcon, QMouseEvent, QPixmap, QShowEvent, QHideEvent, QCloseEvent, QKeySequence, QKeyEvent 

import utils
from images_load import load_default_pixmap, get_images_for_mode, SIZES 
from logic import CounterpickLogic, TEAM_SIZE 
from top_panel import TopPanel
from right_panel import HERO_NAME_ROLE, TARGET_COLUMN_COUNT, RightPanel 
from log_handler import QLogHandler
from dialogs import (LogDialog, HotkeyDisplayDialog, show_about_program_info,
                     show_hero_rating, show_author_info) 
from core.ui_components.hotkey_capture_line_edit import HotkeyCaptureLineEdit 
from core.hotkey_config import HOTKEY_ACTIONS_CONFIG 
# from hotkey_manager import HotkeyManager, PYNPUT_AVAILABLE # Старый менеджер
from core.keyboard_hotkey_adapter import KeyboardHotkeyAdapter, KEYBOARD_AVAILABLE # Новый адаптер
from mode_manager import ModeManager, MODE_DEFAULT_WINDOW_SIZES 
from win_api import WinApiManager
from recognition import RecognitionManager 
from ui_updater import UiUpdater
from action_controller import ActionController
from window_drag_handler import WindowDragHandler
from appearance_manager import AppearanceManager
from core.window_flags_manager import WindowFlagsManager 
from core.app_settings_manager import AppSettingsManager 
from core.settings_window import SettingsWindow 

from core.lang.translations import get_text
import cv2 
import re 


IS_ADMIN = False
if sys.platform == 'win32':
    try: 
        import ctypes
        IS_ADMIN = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception: pass


class MainWindow(QMainWindow):
    # Сигналы для действий остаются теми же
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
    action_copy_team = Signal()
    action_decrease_opacity = Signal() 
    action_increase_opacity = Signal() 

    recognition_complete_signal = Signal(list) 
    update_tray_button_property_signal = Signal(bool) 
    
    clear_hotkey_state_signal = Signal() # Сигнал для адаптера хоткеев

    def __init__(self, logic_instance: CounterpickLogic, app_version: str):
        super().__init__()
        logging.info(">>> MainWindow.__init__ START") 
        self.logic = logic_instance
        self.app_version = app_version
        if hasattr(self.logic, 'main_window'): 
            self.logic.main_window = self

        self.app_settings_manager = AppSettingsManager() 

        self._set_application_icon() 
        self._setup_logging_and_dialogs() 
        
        self.appearance_manager = AppearanceManager(self, self.app_settings_manager)
        self.current_theme = self.appearance_manager.current_theme 
        
        # Заменяем HotkeyManager на KeyboardHotkeyAdapter
        self.hotkey_adapter = KeyboardHotkeyAdapter(self) 
        self.clear_hotkey_state_signal.connect(self.hotkey_adapter.clear_pressed_keys_state)
        
        self.ui_updater = UiUpdater(self) 
        self.action_controller = ActionController(self)
        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)
        
        self.drag_handler = WindowDragHandler(self, lambda: getattr(self, 'top_frame', None))
        
        self.mode = self.mode_manager.current_mode 
        logging.info(f"Начальный режим окна: {self.mode}") 
        
        self._init_ui_attributes() 
        self.flags_manager = WindowFlagsManager(self) 
        self._setup_window_properties() 
        self._create_main_ui_layout() 
        
        if self.appearance_manager: 
            self.appearance_manager._apply_qss_theme_globally(self.appearance_manager.current_theme, on_startup=True)
        
        self._connect_signals() 
        self._initial_ui_update_done = False 

        self.setWindowOpacity(1.0) # Начальная непрозрачность

        logging.info(f"<<< MainWindow.__init__ FINISHED. Начальные флаги окна: {self.windowFlags():#x}")

    # ... (методы _set_application_icon, _setup_logging_and_dialogs, _do_toggle_mode_slot, 
    # switch_language, update_language, switch_theme, apply_theme_qss, _init_ui_attributes,
    # _setup_window_properties, _create_main_ui_layout, _create_icons_scroll_area_structure без изменений) ...

    def _set_application_icon(self):
        icon_path_logo = utils.resource_path("logo.ico")
        app_icon = QIcon() 

        if os.path.exists(icon_path_logo):
            loaded_icon = QIcon(icon_path_logo)
            if not loaded_icon.isNull():
                app_icon = loaded_icon
            else:
                pixmap = QPixmap(icon_path_logo)
                if not pixmap.isNull():
                    app_icon = QIcon(pixmap)
                else:
                    app_icon = QIcon(load_default_pixmap((32,32))) 
        else:
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
        
        self.log_handler.setLevel(logging.DEBUG) 
        logging.getLogger().addHandler(self.log_handler)
        
        if logging.getLogger().level > logging.DEBUG: 
             logging.getLogger().setLevel(logging.DEBUG) 
        
        logging.info("GUI Log Handler initialized and added to root logger.")
        self.hotkey_display_dialog = None 
        self.settings_window_instance: SettingsWindow | None = None 

    @Slot() 
    def _do_toggle_mode_slot(self):
        logging.debug("MainWindow: _do_toggle_mode_slot executing in main thread.")
        debounce_time = 0.3 
        current_time = time.time()
        
        if not hasattr(self, '_last_mode_toggle_time'):
             self._last_mode_toggle_time = 0 

        if current_time - self._last_mode_toggle_time < debounce_time:
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
        logging.debug(f"--> MainWindow.switch_theme called for: {theme_name}")
        if self.appearance_manager:
            self.appearance_manager.switch_theme(theme_name) 
            self.current_theme = self.appearance_manager.current_theme
        logging.debug(f"<-- MainWindow.switch_theme finished for: {theme_name}")

    def apply_theme_qss(self, theme_name: str, on_startup=False): 
        if self.appearance_manager:
            self.appearance_manager._apply_qss_theme_globally(theme_name, on_startup=on_startup)

    def _init_ui_attributes(self):
        initial_pos = self.pos() if self.isVisible() else QPoint(100,100) 
        self.mode_positions = { "min": initial_pos, "middle": initial_pos, "max": initial_pos }
        self.mouse_invisible_mode_enabled = False
        self.is_programmatically_updating_selection = False
        self._last_mode_toggle_time = 0 
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_panel_instance: TopPanel | None = None
        self.right_panel_instance: RightPanel | None = None 
        self.main_layout: QVBoxLayout | None = None
        self.top_frame: QFrame | None = None 
        self.tray_mode_button: QPushButton | None = None     

        self.icons_scroll_area: QScrollArea | None = None
        self.icons_scroll_content: QWidget | None = None
        self.icons_main_h_layout: QHBoxLayout | None = None
        self.counters_widget: QWidget | None = None
        self.counters_layout: QHBoxLayout | None = None
        self.enemies_widget: QWidget | None = None
        self.enemies_layout: QHBoxLayout | None = None
        
        self.result_label: QLabel | None = None 
        
        self.horizontal_info_label: QLabel | None = None 
        
        self.main_widget: QWidget | None = None
        self.inner_layout: QHBoxLayout | None = None
        self.left_panel_widget: QWidget | None = None 
        self.canvas: QScrollArea | None = None 
        self.result_frame: QFrame | None = None 
        
        self.update_scrollregion_callback = lambda: None 
        
        self.right_panel_widget: QWidget | None = None 
        self.right_frame: QFrame | None = None 
        self.right_list_widget: QListWidget | None = None 
        self.selected_heroes_label: QLabel | None = None 
        
        self.hero_items: dict[str, QListWidgetItem] = {}
        self.hotkey_cursor_index = -1
        self.opacity_slider_step = 5 

    def _setup_window_properties(self):
        logging.debug(f"    [WindowProps] START. Current flags before setup: {self.windowFlags():#x}")
        self.setWindowTitle(f"{get_text('title')} v{self.app_version}")
        
        current_icon = self.windowIcon()
        if current_icon.isNull():
            self._set_application_icon() 

        self.setMinimumSize(300, 70) 
        
        logging.debug(f"    [WindowProps] END. Initial self.flags_manager._last_applied_flags set to: {self.flags_manager._last_applied_flags:#x}")

        app_instance = QApplication.instance()
        if app_instance:
            app_instance.installEventFilter(self)

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
                if self.top_frame: self.main_layout.addWidget(self.top_frame)
        
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
        self.enemies_layout.setContentsMargins(2, 2, 2, 2); 
        self.enemies_layout.setSpacing(4) 
        self.enemies_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_main_h_layout.addWidget(self.enemies_widget, stretch=0); self.enemies_widget.hide() 
        
        if not self.horizontal_info_label:
            self.horizontal_info_label = QLabel("Info Label Placeholder") 
            self.horizontal_info_label.setObjectName("horizontal_info_label")
            self.horizontal_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.horizontal_info_label.hide() 
            if self.counters_layout:
                self.counters_layout.addWidget(self.horizontal_info_label)
            
        self.icons_scroll_area.setWidget(self.icons_scroll_content)
        logging.debug("    MainWindow: _create_icons_scroll_area_structure END")

    def _connect_signals(self):
        logging.info("    MainWindow: Подключение сигналов...")
        if not hasattr(self, 'action_controller') or not self.action_controller:
            logging.error("    ActionController не инициализирован, подключение сигналов невозможно.")
            return

        # Сигналы действий подключаются к ActionController как и раньше
        self.action_move_cursor_up.connect(lambda: self.action_controller.handle_move_cursor('up'))
        self.action_move_cursor_down.connect(lambda: self.action_controller.handle_move_cursor('down'))
        self.action_move_cursor_left.connect(lambda: self.action_controller.handle_move_cursor('left'))
        self.action_move_cursor_right.connect(lambda: self.action_controller.handle_move_cursor('right'))
        self.action_toggle_selection.connect(self.action_controller.handle_toggle_selection)
        self.action_toggle_mode.connect(self._do_toggle_mode_slot) 
        self.action_clear_all.connect(self.action_controller.handle_clear_all)
        self.action_copy_team.connect(self.action_controller.handle_copy_team)
        
        if hasattr(self, 'rec_manager') and self.rec_manager and hasattr(self.rec_manager, 'recognize_heroes_signal'):
            self.action_recognize_heroes.connect(self.rec_manager.recognize_heroes_signal.emit)
            self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
            self.rec_manager.error.connect(self._on_recognition_error)
        
        self.action_debug_capture.connect(lambda: self._save_debug_screenshot_internal("manual_hotkey")) 
        self.action_toggle_tray_mode.connect(self.toggle_tray_mode) 
        
        self.action_decrease_opacity.connect(self.decrease_window_opacity)
        self.action_increase_opacity.connect(self.increase_window_opacity)

        if self.tray_mode_button and hasattr(self, 'update_tray_button_property_signal'):
             self.update_tray_button_property_signal.connect(self._update_tray_button_property)
        
        if self.win_api_manager and hasattr(self.win_api_manager, 'topmost_state_changed'):
            self.win_api_manager.topmost_state_changed.connect(self._handle_topmost_state_change)
        
        logging.info("    MainWindow: Подключение сигналов завершено.")


    def showEvent(self, event: QShowEvent):
        is_applying_flags = self.flags_manager._is_applying_flags_operation if hasattr(self, 'flags_manager') else False
        logging.debug(f">>> showEvent START. Visible: {self.isVisible()}, Active: {self.isActiveWindow()}, isApplyingFlags: {is_applying_flags}, initialDone: {self._initial_ui_update_done}, Spontaneous: {event.spontaneous()}")
        
        current_pos_before_super = self.pos() 
        super().showEvent(event) 
        
        if is_applying_flags and not event.spontaneous(): 
            logging.debug(f"    showEvent: Вызван во время операции с флагами (не спонтанно). Геометрия сейчас: {self.geometry()}")
            logging.debug("<<< showEvent END (во время операции с флагами, не спонтанно)")
            return

        if not self._initial_ui_update_done:
            logging.info("    showEvent: Первоначальная настройка UI (_initial_ui_update_done is False).")
            t_initial_setup_start = time.perf_counter()
            
            initial_mode_pos = self.mode_positions.get(self.mode)
            initial_width = MODE_DEFAULT_WINDOW_SIZES.get(self.mode, {}).get('width', 950)
            initial_height = MODE_DEFAULT_WINDOW_SIZES.get(self.mode, {}).get('height', 600)
            
            if initial_mode_pos and initial_mode_pos != QPoint(0,0): 
                logging.info(f"    showEvent: Восстановление геометрии из mode_positions: P={initial_mode_pos}, S=({initial_width}x{initial_height})")
                self.setGeometry(initial_mode_pos.x(), initial_mode_pos.y(), initial_width, initial_height)
            else: 
                screen_geo = QApplication.primaryScreen().availableGeometry()
                initial_x = (screen_geo.width() - initial_width) // 2
                initial_y = (screen_geo.height() - initial_height) // 2
                self.setGeometry(initial_x, initial_y, initial_width, initial_height)
                logging.info(f"    showEvent: Установлена начальная (центрированная) геометрия: {self.geometry()}")
            
            self.mode_positions[self.mode] = self.pos() 

            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_interface_for_mode(new_mode=self.mode) 
            else: 
                if hasattr(self, 'flags_manager'):
                    self.flags_manager.apply_mouse_invisible_mode("initial_show_no_ui_updater")

            # Измененный блок запуска хоткеев
            if KEYBOARD_AVAILABLE: 
                if hasattr(self, 'hotkey_adapter'): 
                    # Загружаем хоткеи из настроек и регистрируем их
                    loaded_hotkeys_from_settings = self.app_settings_manager.get_hotkeys()
                    QTimer.singleShot(1000, lambda: self.hotkey_adapter.load_and_register_hotkeys(loaded_hotkeys_from_settings) if self.hotkey_adapter else None)
                    logging.info("    showEvent: Запланирована загрузка и регистрация хоткеев через KeyboardHotkeyAdapter (с задержкой 1000мс).")
                else:
                    logging.warning("    showEvent: HotkeyAdapter (keyboard) не найден, хоткеи не будут загружены/зарегистрированы.")
            else:
                 logging.warning("    showEvent: KEYBOARD_AVAILABLE is False, хоткеи не будут активны.")
            
            self._initial_ui_update_done = True
            logging.info(f"    showEvent: Первоначальная настройка UI завершена. Время: {(time.perf_counter() - t_initial_setup_start)*1000:.2f} ms")
        else:
            logging.debug(f"    showEvent: Повторный вызов или спонтанное событие. Текущие флаги: {self.windowFlags():#x}")
            if self.pos() != current_pos_before_super and not (hasattr(self, 'drag_handler') and self.drag_handler._mouse_pressed):
                logging.debug(f"    showEvent: Позиция изменилась ({current_pos_before_super} -> {self.pos()}), не из-за drag.")
                if self.mode_positions.get(self.mode) != self.pos():
                    self.mode_positions[self.mode] = self.pos() 

        if self.isVisible():
            current_icon = self.windowIcon() 
            if current_icon.isNull():
                self._set_application_icon()
        
        logging.debug(f"<<< showEvent END. Финальная геометрия: {self.geometry()}")


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
    def toggle_tray_mode(self):
        logging.info("MainWindow: toggle_tray_mode slot triggered.")
        if hasattr(self, 'win_api_manager'):
            target_topmost_state = not self._is_win_topmost 
            self.win_api_manager.set_topmost_winapi(target_topmost_state) 
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
        if self.isVisible(): 
            self.mode_positions[old_mode] = self.pos()
            logging.debug(f"    Сохранена позиция для режима '{old_mode}': {self.mode_positions[old_mode]}")
        else: 
            logging.debug(f"    Окно невидимо, позиция для '{old_mode}' не обновлена.")


        self.hotkey_cursor_index = -1 
        if self.right_list_widget and self.right_list_widget.isVisible() and self.right_list_widget.viewport():
            self.right_list_widget.viewport().update() 

        self.mode = mode_name 
        if hasattr(self, 'mode_manager'): self.mode_manager.change_mode(mode_name) 
        
        t_ui_update_start = time.perf_counter()
        if hasattr(self, 'ui_updater') and self.ui_updater:
            self.ui_updater.update_interface_for_mode(new_mode=self.mode) 
        logging.debug(f"    change_mode: ui_updater.update_interface_for_mode took {(time.perf_counter() - t_ui_update_start)*1000:.2f} ms")
        
        target_pos = self.mode_positions.get(self.mode)
        if target_pos and self.isVisible() and self.pos() != target_pos:
            logging.debug(f"    Попытка восстановить позицию для режима '{self.mode}' на {target_pos} (текущая: {self.pos()})")
            QTimer.singleShot(50, lambda: self._move_window_safely(target_pos)) 
        elif self.isVisible(): 
            current_pos_for_new_mode = self.pos()
            if self.mode_positions.get(self.mode) != current_pos_for_new_mode:
                 self.mode_positions[self.mode] = current_pos_for_new_mode
                 logging.debug(f"    Сохранена текущая позиция для нового режима '{self.mode}': {current_pos_for_new_mode}")
        
        self._reset_hotkey_cursor_after_mode_change()
        
        if self.isVisible(): 
            current_icon = self.windowIcon() 
            if not current_icon.isNull(): self.setWindowIcon(current_icon)
            else: self._set_application_icon()

        if hasattr(self, 'flags_manager'):
            QTimer.singleShot(100, lambda: self.flags_manager.force_taskbar_update_internal(f"after_mode_{mode_name}_change"))
        
        logging.info(f"<-- MainWindow: change_mode to {mode_name} FINISHED. Total time: {(time.perf_counter() - t_change_mode_start)*1000:.2f} ms")


    def _move_window_safely(self, target_pos: QPoint):
        if self.isVisible() and self.pos() != target_pos: 
            logging.debug(f"    _move_window_safely: Перемещение окна на {target_pos}")
            self.move(target_pos)
        elif self.isVisible() and self.pos() == target_pos:
             logging.debug(f"    _move_window_safely: Окно уже на {target_pos}, перемещение не требуется.")


    @property
    def _is_win_topmost(self):
        return self.win_api_manager.is_win_topmost if hasattr(self, 'win_api_manager') and self.win_api_manager else False

    @Slot(list) 
    def _on_recognition_complete(self, recognized_heroes_original_names: list):
        recognized_heroes_normalized_names = [utils.normalize_hero_name(name) for name in recognized_heroes_original_names]
        recognized_heroes_normalized_names = [name for name in recognized_heroes_normalized_names if name] 

        logging.info(f"MainWindow: Распознавание завершено. Оригинал: {recognized_heroes_original_names}, Нормализовано для логики: {recognized_heroes_normalized_names}")
        
        if hasattr(self, 'app_settings_manager'):
            should_save = self.app_settings_manager.get_save_screenshot_flag()
            num_recognized = len(recognized_heroes_normalized_names) 
            if should_save and num_recognized < 6: 
                self._save_debug_screenshot_internal(
                    reason="auto", 
                    recognized_heroes_for_filename=recognized_heroes_original_names 
                )

        if recognized_heroes_normalized_names and hasattr(self, 'logic'):
            self.logic.set_selection(set(recognized_heroes_normalized_names))
            if hasattr(self, 'ui_updater') and self.ui_updater:
                self.ui_updater.update_ui_after_logic_change()
            self._reset_hotkey_cursor_after_clear()
        elif not recognized_heroes_normalized_names: 
            logging.info("Герои не распознаны или список пуст после нормализации.")

    def _save_debug_screenshot_internal(self, reason="manual", recognized_heroes_for_filename: list | None = None):
        logging.info(f"Запрос на сохранение скриншота. Причина: {reason}")
        try: 
            area_to_capture = utils.RECOGNITION_AREA 
            if reason == "manual_hotkey_fullscreen_debug_only": 
                 area_to_capture = {'monitor': 1, 'left_pct': 0, 'top_pct': 0, 'width_pct': 100, 'height_pct': 100}
            
            logging.debug(f"Область для захвата скриншота (_save_debug_screenshot_internal): {area_to_capture}")
            screenshot_cv2 = utils.capture_screen_area(area_to_capture)

            if screenshot_cv2 is not None:
                logging.debug("Скриншот успешно захвачен.")
                save_path_str = self.app_settings_manager.get_screenshot_save_path()
                logging.debug(f"Путь из настроек: '{save_path_str}'")
                
                save_dir: Path
                if save_path_str and Path(save_path_str).is_dir(): 
                    save_dir = Path(save_path_str)
                    logging.debug(f"Используется указанный путь: {save_dir}")
                else: 
                    if save_path_str: 
                        logging.warning(f"Указанный путь для сохранения скриншотов '{save_path_str}' не является директорией. Используется путь по умолчанию.")
                    if hasattr(sys, 'executable') and sys.executable:
                        save_dir = Path(sys.executable).parent
                    else:
                        save_dir = Path.cwd()
                    logging.debug(f"Используется путь по умолчанию: {save_dir}")
                
                if not save_dir.exists():
                    try:
                        save_dir.mkdir(parents=True, exist_ok=True)
                        logging.info(f"Создана директория для скриншотов: {save_dir}")
                    except OSError as e:
                        logging.error(f"Не удалось создать директорию для скриншотов {save_dir}: {e}")
                        if reason == "manual_hotkey":
                            QMessageBox.warning(self, get_text('error'), get_text('screenshot_save_failed', error=str(e)))
                        return
                elif not save_dir.is_dir(): 
                     logging.error(f"Путь для сохранения скриншотов {save_dir} существует, но не является директорией. Скриншот не сохранен.")
                     if reason == "manual_hotkey":
                         QMessageBox.warning(self, get_text('error'), get_text('screenshot_save_failed', error=f"{save_dir} не директория"))
                     return

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename_base_part = ""
                heroes_source_for_name = recognized_heroes_for_filename if recognized_heroes_for_filename is not None else []

                if reason == "auto" and heroes_source_for_name:
                    clean_names_for_file = []
                    for name in heroes_source_for_name:
                        name_no_digit_suffix = re.sub(r'_\d+$', '', name) 
                        name_no_common_suffixes = re.sub(r'(_icon|_template|_small|_left|_right|_horizontal|_adv)$', '', name_no_digit_suffix, flags=re.IGNORECASE)
                        safe_name = re.sub(r'[^\w\s-]', '', name_no_common_suffixes).strip() 
                        safe_name = re.sub(r'[-\s]+', '_', safe_name) 
                        if safe_name: clean_names_for_file.append(safe_name)
                    
                    unique_clean_names = sorted(list(set(clean_names_for_file)))
                    if unique_clean_names:
                        filename_base_part = ",".join(unique_clean_names)
                        max_name_len = 100 
                        if len(filename_base_part) > max_name_len:
                            filename_base_part = filename_base_part[:max_name_len] + "..."
                    else: 
                        filename_base_part = f"recognized_{len(heroes_source_for_name)}_unknown_names"
                else: 
                    filename_base_part = reason
                base_filename = f"rcp_{filename_base_part}_{timestamp}.png"
                
                final_filepath = save_dir / base_filename
                temp_file_path = ""
                # Используем try-except для временного файла
                temp_file_created = False
                try:
                    temp_file_handle, temp_file_path_str = tempfile.mkstemp(suffix=".png", prefix="rcp_temp_")
                    os.close(temp_file_handle)
                    temp_file_path = Path(temp_file_path_str) # Конвертируем в Path
                    temp_file_created = True
                    logging.debug(f"Временный файл для сохранения: {temp_file_path}")
                except Exception as e_temp:
                    logging.error(f"Ошибка создания временного файла: {e_temp}")
                    if reason == "manual_hotkey":
                        QMessageBox.warning(self, get_text('error'), get_text('screenshot_save_failed', error=f"Temp file error: {e_temp}"))
                    return
                
                if not temp_file_created: return # Выход если временный файл не создан

                write_ok_temp = False; error_msg_cv2 = ""
                try:
                    write_ok_temp = cv2.imwrite(str(temp_file_path), screenshot_cv2) # cv2.imwrite ожидает строку
                    if not write_ok_temp: error_msg_cv2 = "cv2.imwrite (temp) вернул False."
                except cv2.error as e_cv2:
                    error_msg_cv2 = f"OpenCV ошибка (temp): {e_cv2}"
                    logging.error(f"Ошибка cv2.imwrite (temp) при сохранении в {temp_file_path}: {e_cv2}")
                except Exception as e:
                    error_msg_cv2 = f"Общее исключение (temp): {e}"
                    logging.error(f"Общее исключение при cv2.imwrite (temp) для {temp_file_path}: {e}", exc_info=True)

                if write_ok_temp:
                    logging.info(f"Скриншот успешно сохранен во временный файл: {temp_file_path}")
                    try:
                        logging.debug(f"Перемещение из '{temp_file_path}' в '{final_filepath}'")
                        shutil.move(str(temp_file_path), str(final_filepath)) # shutil.move также ожидает строки
                        logging.info(f"Скриншот успешно перемещен в: {final_filepath}")
                        if reason == "manual_hotkey": 
                             QMessageBox.information(self, get_text('success'), get_text('screenshot_saved', filepath=str(final_filepath)))
                    except Exception as e_move:
                        logging.error(f"Ошибка перемещения файла из {temp_file_path} в {final_filepath}: {e_move}")
                        if reason == "manual_hotkey":
                             QMessageBox.warning(self, get_text('error'), get_text('screenshot_save_failed', error=f"Ошибка перемещения: {e_move}"))
                        if temp_file_path.exists(): # Проверяем существование перед удалением
                            try: temp_file_path.unlink()
                            except: pass
                else:
                    final_error = error_msg_cv2 if error_msg_cv2 else "Неизвестная ошибка записи во временный файл."
                    logging.warning(f"Не удалось сохранить скриншот во временный файл {temp_file_path}. Ошибка: {final_error}")
                    if reason == "manual_hotkey":
                         QMessageBox.warning(self, get_text('error'), get_text('screenshot_save_failed', error=final_error))
                    if temp_file_path.exists(): 
                        try: temp_file_path.unlink()
                        except: pass
            else:
                logging.warning("Не удалось сделать скриншот (capture_screen_area вернул None).")
                if reason == "manual_hotkey":
                     QMessageBox.warning(self, get_text('error'), get_text('recognition_no_screenshot'))
        except Exception as e:
            logging.error(f"Ошибка при сохранении скриншота (внешний try-except): {e}", exc_info=True)
            if reason == "manual_hotkey":
                 QMessageBox.critical(self, get_text('error'), get_text('screenshot_save_failed', error=str(e)))


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
                    self.ui_updater.update_hotkey_highlight(old_index=old_index) 
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
        # Используем KeyboardHotkeyAdapter для получения актуальных хоткеев
        current_hotkeys_internal_format = {}
        if hasattr(self, 'hotkey_adapter'):
            current_hotkeys_internal_format = self.hotkey_adapter.get_current_hotkeys_config_for_settings()
        else:
            logging.warning("HotkeyAdapter не найден, информационное окно хоткеев может быть неактуальным.")

        # Создаем диалог каждый раз, чтобы он подхватывал актуальные хоткеи и тему
        # HotkeyDisplayDialog должен быть адаптирован для работы с KeyboardHotkeyAdapter или принимать конфиг
        # Пока оставим как есть, предполагая, что HotkeyDisplayDialog будет адаптирован
        # или будет использовать глобальный доступ к менеджеру хоткеев (менее предпочтительно).
        # ПРАВИЛЬНЕЕ: передавать ему актуальный конфиг хоткеев.
        # TODO: Адаптировать HotkeyDisplayDialog для получения конфига.
        # Временное решение: он все еще может пытаться получить конфиг из self.parent_window.hotkey_manager
        # что теперь будет self.parent_window.hotkey_adapter.
        
        if self.hotkey_display_dialog: 
            self.hotkey_display_dialog.update_html_content() # Этот метод должен уметь работать с новым адаптером
        else:
            self.hotkey_display_dialog = HotkeyDisplayDialog(self) # Передаем MainWindow как родителя
        self.hotkey_display_dialog.exec()


    @Slot()
    def show_settings_window(self):
        logging.info("[MainWindow] show_settings_window called.")
        if not self.settings_window_instance:
            logging.debug("  Creating new SettingsWindow instance.")
            # Передаем AppSettingsManager и ссылку на MainWindow (parent)
            self.settings_window_instance = SettingsWindow(self.app_settings_manager, self)
            # Сигнал settings_applied_signal уже есть в SettingsWindow
            self.settings_window_instance.settings_applied_signal.connect(self.on_settings_applied)
            self.settings_window_instance.finished.connect(self._on_modal_dialog_closed)
        else:
            logging.debug("  Using existing SettingsWindow instance.")
        
        # SettingsWindow сам загрузит настройки через AppSettingsManager при открытии (в open/exec)
        self.settings_window_instance.exec()
        logging.info("[MainWindow] SettingsWindow closed.")

    @Slot(int)
    def _on_modal_dialog_closed(self, result: int):
        # Этот слот вызывается, когда любое модальное окно, использующее finished.connect, закрывается.
        # Например, HotkeyCaptureLineEdit диалог или SettingsWindow.
        logging.info(f"Модальное окно закрыто с результатом: {result}. Очистка состояния хоткеев (если это был диалог ввода).")
        
        # Мы не можем точно знать, какой диалог закрылся, только по этому сигналу.
        # HotkeyCaptureLineEdit уже сам обрабатывает сброс своего состояния.
        # KeyboardHotkeyAdapter не хранит глобальное состояние нажатых клавиш, которое нужно сбрасывать.
        # Поэтому дополнительная очистка здесь может быть не нужна.
        
        # Если это было окно настроек, то on_settings_applied уже должно было сработать, если нажали OK/Apply.
        # Если нажали Cancel, то _on_modal_dialog_closed сработает с QDialog.Rejected.
        
        # if hasattr(self, 'clear_hotkey_state_signal'):
        # self.clear_hotkey_state_signal.emit() # Это может быть избыточным или даже вредным
        pass


    @Slot()
    def on_settings_applied(self):
        logging.info("MainWindow: Настройки были применены из SettingsWindow.")
        if self.hotkey_adapter:
            # KeyboardHotkeyAdapter сам загрузит актуальные настройки из AppSettingsManager
            # при вызове load_and_register_hotkeys
            new_hotkeys_from_settings = self.app_settings_manager.get_hotkeys()
            self.hotkey_adapter.load_and_register_hotkeys(new_hotkeys_from_settings) 
        
        new_lang = self.app_settings_manager.get_language()
        if self.appearance_manager and self.appearance_manager.current_language != new_lang:
            self.appearance_manager.switch_language(new_lang)
        
        new_theme = self.app_settings_manager.get_theme()
        if self.appearance_manager and self.appearance_manager.current_theme != new_theme:
            self.appearance_manager.switch_theme(new_theme)

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
        # Логика eventFilter для Tab и перетаскивания остается почти такой же.
        # Важно, чтобы Tab не перехватывался KeyboardHotkeyAdapter, если он не зарегистрирован как хоткей.
        # Библиотека 'keyboard' обычно не перехватывает Tab по умолчанию, если он не часть хоткея.
        if event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event # type: ignore 
            
            if key_event.key() == Qt.Key_Tab:
                focus_widget = QApplication.focusWidget()
                logging.debug(f"MainWindow.eventFilter: Tab pressed. FocusWidget: {type(focus_widget).__name__ if focus_widget else 'None'}, ObjectName: {focus_widget.objectName() if focus_widget and hasattr(focus_widget, 'objectName') else 'N/A'}")

                # Если фокус на поле ввода хоткея, передаем Tab ему
                if isinstance(focus_widget, HotkeyCaptureLineEdit) and focus_widget.objectName() == "HotkeyCaptureLineEdit":
                    logging.debug("    Tab for HotkeyCaptureLineEdit. Forwarding to widget.")
                    return False # Стандартная обработка QLineEdit для Tab (если он ее делает)

                # Если открыто окно настроек и фокус внутри него (но не на поле ввода хоткея)
                if self.settings_window_instance and self.settings_window_instance.isVisible() and self.settings_window_instance.isActiveWindow():
                    is_hcl_in_settings = False
                    parent_widget_iter = focus_widget
                    while parent_widget_iter is not None:
                        if parent_widget_iter == self.settings_window_instance:
                            if isinstance(focus_widget, HotkeyCaptureLineEdit):
                                is_hcl_in_settings = True
                            break
                        parent_widget_iter = parent_widget_iter.parentWidget()
                    
                    if is_hcl_in_settings:
                         logging.debug("    Tab for HotkeyCaptureLineEdit inside SettingsWindow. Forwarding.")
                         return False 
                    logging.debug("    Tab inside active SettingsWindow (not on capture field). Standard Qt focus processing.")
                    return False # Позволяем Qt обрабатывать Tab для навигации по виджетам в диалоге

                # В остальных случаях (например, Tab нажат, когда фокус на основном окне)
                # мы хотим предотвратить стандартное переключение фокуса Qt,
                # так как Tab может быть частью глобального хоткея.
                # Библиотека 'keyboard' сама обработает Tab, если он часть хоткея.
                # Если он не часть хоткея, то это событие просто "съестся" здесь,
                # чтобы избежать нежелательного переключения фокуса.
                logging.debug("    Global Tab press (not for capture field, not in settings dialog). Consuming to prevent focus switch if Tab is not a hotkey.")
                # Если Tab *является* глобальным хоткеем, зарегистрированным через 'keyboard',
                # то 'keyboard' его перехватит и подавит, если suppress=True.
                # Если Tab *не является* глобальным хоткеем, то мы его "съедаем" здесь,
                # чтобы он не вызвал стандартное переключение фокуса Qt.
                return True # Перехватываем Tab

        # Логика перетаскивания
        if self.mode == "min" and hasattr(self, 'drag_handler') and self.drag_handler:
            if event.type() == QEvent.Type.MouseButtonPress:
                mouse_event: QMouseEvent = event # type: ignore
                if self.drag_handler.mousePressEvent(mouse_event): return True 
            elif event.type() == QEvent.Type.MouseMove:
                mouse_event: QMouseEvent = event # type: ignore
                if self.drag_handler.mouseMoveEvent(mouse_event): return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                mouse_event: QMouseEvent = event # type: ignore
                if self.drag_handler.mouseReleaseEvent(mouse_event): return True
                    
        return super().eventFilter(watched, event)

    @Slot()
    def handle_opacity_change(self, value: int):
        opacity = value / 100.0
        self.setWindowOpacity(opacity)

    @Slot()
    def decrease_window_opacity(self):
        if self.top_panel_instance and self.top_panel_instance.transparency_slider:
            slider = self.top_panel_instance.transparency_slider
            new_value = max(slider.minimum(), slider.value() - self.opacity_slider_step)
            slider.setValue(new_value) 
            logging.debug(f"Opacity decreased by hotkey to {new_value}%")

    @Slot()
    def increase_window_opacity(self):
        if self.top_panel_instance and self.top_panel_instance.transparency_slider:
            slider = self.top_panel_instance.transparency_slider
            new_value = min(slider.maximum(), slider.value() + self.opacity_slider_step)
            slider.setValue(new_value) 
            logging.debug(f"Opacity increased by hotkey to {new_value}%")


    def closeEvent(self, event: QCloseEvent): 
        logging.info("MainWindow closeEvent triggered.")
        
        if hasattr(self, 'clear_hotkey_state_signal'): # Сигнал для KeyboardHotkeyAdapter
            self.clear_hotkey_state_signal.emit()

        if self.log_dialog and self.log_dialog.isVisible() : 
            self.log_dialog.close() 
        
        if self.hotkey_display_dialog and self.hotkey_display_dialog.isVisible():
             self.hotkey_display_dialog.reject() 
        
        if self.settings_window_instance and self.settings_window_instance.isVisible():
            self.settings_window_instance.reject() 

        if hasattr(self, 'hotkey_adapter'): # Используем новый адаптер
            logging.info("Остановка KeyboardHotkeyAdapter перед закрытием...")
            self.hotkey_adapter.stop_listening()
        if hasattr(self, 'rec_manager') and self.rec_manager: 
            logging.info("Остановка процессов распознавания перед закрытием...")
            self.rec_manager.stop_recognition()
        
        logging.info("Вызов super().closeEvent(event)")
        super().closeEvent(event) 
        
        if event.isAccepted():
            logging.info(f"closeEvent завершен. Event accepted: True")
            app_instance = QApplication.instance()
            if app_instance and not app_instance.quitOnLastWindowClosed():
                logging.info("quitOnLastWindowClosed is False, вызов QApplication.quit() из MainWindow.closeEvent")
                QTimer.singleShot(0, QApplication.quit) 
        else:
            logging.info(f"closeEvent завершен. Event accepted: False (проигнорировано)")


    @Slot(str) # Слот для вызова из KeyboardHotkeyAdapter
    def _emit_action_signal_slot(self, action_id: str):
        """
        Этот слот вызывается из HotkeyAdapter для выполнения действия в основном потоке.
        Он эмитирует соответствующий сигнал действия.
        """
        logging.debug(f"MainWindow: _emit_action_signal_slot для action_id: '{action_id}'")
        action_config = HOTKEY_ACTIONS_CONFIG.get(action_id)
        if action_config:
            signal_name = action_config.get('signal_name')
            if signal_name and hasattr(self, signal_name):
                signal_instance = getattr(self, signal_name)
                if isinstance(signal_instance, Signal): # Проверка, что это действительно сигнал
                    logging.info(f"MainWindow: Эмитирование сигнала '{signal_name}' для действия '{action_id}'.")
                    signal_instance.emit()
                else:
                    logging.error(f"MainWindow: Атрибут '{signal_name}' не является сигналом Qt для действия '{action_id}'.")
            else:
                logging.error(f"MainWindow: Сигнал для действия '{action_id}' (имя: {signal_name}) не найден.")
        else:
            logging.error(f"MainWindow: Конфигурация для действия '{action_id}' не найдена.")
