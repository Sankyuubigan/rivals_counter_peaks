# File: core/main_window.py
import sys
import time
import threading
import os
import logging
import cv2 # Для сохранения скриншота

from PySide6.QtWidgets import (
    QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QScrollArea,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QMenu, QStyleFactory, QApplication, QMessageBox
)
# --- ИСПРАВЛЕНИЕ 2: Импорт Q_ARG ---
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QPoint, QModelIndex, QMetaObject, Q_ARG, QRect
# ------------------------------------
from PySide6.QtGui import QIcon, QMouseEvent, QColor, QBrush, QPixmap

import translations
import utils_gui
import logic
import delegate
import dialogs
import display
import horizontal_list # Импортируем модуль
import images_load
from mode_manager import ModeManager, PANEL_MIN_WIDTHS, MODE_DEFAULT_WINDOW_SIZES
from win_api import WinApiManager, user32 as winapi_user32, is_window_topmost
from recognition import RecognitionManager, RecognitionWorker
from top_panel import TopPanel
from left_panel import LeftPanel, create_left_panel
from right_panel import RightPanel, HERO_NAME_ROLE
import utils

from translations import get_text, set_language, SUPPORTED_LANGUAGES
from utils_gui import copy_to_clipboard
from logic import CounterpickLogic, TEAM_SIZE
from images_load import get_images_for_mode, SIZES, load_default_pixmap, is_invalid_pixmap
from horizontal_list import update_horizontal_icon_list, update_enemy_horizontal_list, clear_layout as clear_layout_util
from display import generate_counterpick_display

try:
    import keyboard
    IS_ADMIN = False
    try:
        if sys.platform == 'win32': import ctypes; IS_ADMIN = ctypes.windll.shell32.IsUserAnAdmin() != 0
        elif sys.platform == 'darwin' or sys.platform.startswith('linux'): IS_ADMIN = (os.geteuid() == 0)
    except Exception as e_admin_check: logging.warning(f"Admin check failed: {e_admin_check}")
    if not IS_ADMIN: logging.warning("No admin rights, 'keyboard' hotkeys might not work globally.")
    else: logging.info("Admin rights detected.")
except ImportError: logging.error("'keyboard' library not found. pip install keyboard"); keyboard = None


class MainWindow(QMainWindow):
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()
    toggle_mode_signal = Signal()
    clear_all_signal = Signal()
    recognize_heroes_signal = Signal()
    recognition_complete_signal = Signal(list)
    debug_capture_signal = Signal()
    # Сигнал для хоткея topmost (Tab+Num7)
    toggle_topmost_signal = Signal()
    # Сигнал для хоткея невидимости мыши (Tab+Num9)
    toggle_mouse_invisible_mode_signal = Signal()
    # Сигнал для обновления свойства кнопки (испускается из _handle_topmost_state_change)
    update_topmost_button_property_signal = Signal(bool)


    def __init__(self, logic_instance: CounterpickLogic, hero_templates_dict: dict, app_version: str):
        super().__init__()
        logging.info("Initializing MainWindow...")
        self.logic = logic_instance; self.hero_templates = hero_templates_dict
        self.app_version = app_version
        self.logic.main_window = self
        logging.info(f"App Version used by MainWindow: {self.app_version}")
        self.win_api_manager = WinApiManager(self); self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)
        self.mode = self.mode_manager.current_mode; logging.info(f"Initial mode: {self.mode}")
        # Инициализация позиций окна (сохраняем начальную, если видимо)
        initial_pos = self.pos() if self.isVisible() else None
        initial_geom = self.geometry() if self.isVisible() else None
        logging.info(f"[Init] Initial Pos: {initial_pos}, Initial Geom: {initial_geom}")
        self.mode_positions = {
            "min": None,
            "middle": initial_pos,
            "max": None
        }
        # Флаг для ручного режима невидимости мыши
        self.mouse_invisible_mode_enabled = False
        self.is_programmatically_updating_selection = False
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_panel_instance: TopPanel | None = None; self.right_panel_instance: RightPanel | None = None
        self.main_layout: QVBoxLayout | None = None; self.top_frame: QFrame | None = None
        self.author_button: QPushButton | None = None; self.rating_button: QPushButton | None = None
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
        self.inner_layout: QHBoxLayout | None = None; self.left_panel_widget: QWidget | None = None
        self.canvas: QScrollArea | None = None; self.result_frame: QFrame | None = None
        self.result_label: QLabel | None = None; self.update_scrollregion = lambda: None
        self.right_panel_widget: QWidget | None = None; self.right_frame: QFrame | None = None
        self.right_list_widget: QListWidget | None = None; self.selected_heroes_label: QLabel | None = None
        self.hero_items: dict[str, QListWidgetItem] = {}; self.hotkey_cursor_index = -1
        self._num_columns_cache = 1; self._keyboard_listener_thread: threading.Thread | None = None
        self._stop_keyboard_listener_flag = threading.Event(); self._mouse_pressed = False
        self._old_pos: QPoint | None = None; self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        self._last_mode_toggle_time = 0

        self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
        icon_path = images_load.resource_path("resources/icon.png")
        icon_pixmap = QPixmap(icon_path) if os.path.exists(icon_path) else load_default_pixmap((32, 32))
        if not icon_pixmap.isNull(): self.setWindowIcon(QIcon(icon_pixmap))
        else: logging.warning("Failed to load application icon.")
        if not self.isVisible(): self.setGeometry(100, 100, 950, 350)
        self.setMinimumSize(400, 100)
        self._create_main_ui_layout();
        QTimer.singleShot(0, lambda: self._update_interface_for_mode())
        self._connect_signals() # Перемещаем connect_signals после _create_main_ui_layout
        if keyboard: self.start_keyboard_listener()
        else: logging.warning("Keyboard library not available or no admin rights, hotkeys disabled.")
        logging.info("MainWindow.__init__ finished")

    def _create_main_ui_layout(self):
        logging.debug("Creating main UI layout...")
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        if not hasattr(self, 'change_mode'): raise AttributeError("MainWindow is missing change_mode method")
        self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
        self.top_frame = self.top_panel_instance.top_frame
        # Сохраняем ссылки на кнопки из TopPanel
        self.author_button = self.top_panel_instance.author_button
        self.rating_button = self.top_panel_instance.rating_button
        self.close_button = self.top_panel_instance.close_button # Сохраняем ссылку
        self.topmost_button = self.top_panel_instance.topmost_button # Сохраняем ссылку
        # ---
        self.main_layout.addWidget(self.top_frame); logging.debug("Top panel created and added.")
        self._create_icons_scroll_area_structure()
        self.main_layout.addWidget(self.icons_scroll_area); logging.debug("Icons scroll area structure created and added.")
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
        self.inner_layout.setContentsMargins(0,0,0,0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1); logging.debug("Main widget and inner_layout created and added.")
        logging.debug("Main UI layout creation finished.")

    def _create_icons_scroll_area_structure(self):
        self.icons_scroll_area = QScrollArea(); self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea#icons_scroll_area { border: none; background-color: #f0f0f0; padding: 0px; margin: 0px; }")

        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content.setStyleSheet("background-color: transparent;")

        self.icons_main_h_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_main_h_layout.setObjectName("icons_main_h_layout")
        self.icons_main_h_layout.setContentsMargins(5, 2, 5, 2)
        self.icons_main_h_layout.setSpacing(10)
        self.icons_main_h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.counters_widget = QWidget()
        self.counters_widget.setObjectName("counters_widget")
        self.counters_layout = QHBoxLayout(self.counters_widget)
        self.counters_layout.setObjectName("counters_layout")
        self.counters_layout.setContentsMargins(0, 0, 0, 0)
        self.counters_layout.setSpacing(4)
        self.counters_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_main_h_layout.addWidget(self.counters_widget, stretch=1)

        self.enemies_widget = QWidget()
        self.enemies_widget.setObjectName("enemies_widget")
        self.enemies_widget.setStyleSheet("QWidget#enemies_widget { border: none; padding: 1px; }")
        self.enemies_layout = QHBoxLayout(self.enemies_widget)
        self.enemies_layout.setObjectName("enemies_layout")
        self.enemies_layout.setContentsMargins(2, 2, 2, 2)
        self.enemies_layout.setSpacing(4)
        self.enemies_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_main_h_layout.addWidget(self.enemies_widget, stretch=0)
        self.enemies_widget.hide()

        if self.horizontal_info_label.parentWidget():
            current_layout = self.horizontal_info_label.parentWidget().layout()
            if current_layout:
                current_layout.removeWidget(self.horizontal_info_label)
            self.horizontal_info_label.setParent(None)

        self.icons_scroll_area.setWidget(self.icons_scroll_content)
        logging.debug("Icons scroll area structure created.")

    # --- ИСПРАВЛЕНИЕ 2: Отдельный слот для установки свойства ---
    @Slot(bool)
    def _update_topmost_button_property(self, is_active):
        if self.topmost_button:
            logging.debug(f"Setting topmostActive property to: {is_active}")
            self.topmost_button.setProperty("topmostActive", is_active)
            # Принудительно обновляем стиль после изменения свойства
            self.topmost_button.style().unpolish(self.topmost_button)
            self.topmost_button.style().polish(self.topmost_button)
            self.topmost_button.update()
        else:
            logging.warning("Attempted to update property on non-existent topmost_button")
    # -----------------------------------------------------------

    def _connect_signals(self):
        logging.debug("Connecting signals...")
        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)
        self.toggle_mode_signal.connect(self._handle_toggle_mode)
        self.clear_all_signal.connect(self._handle_clear_all)
        self.recognize_heroes_signal.connect(self.rec_manager.recognize_heroes_signal.emit)
        self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
        self.rec_manager.error.connect(self._on_recognition_error)
        self.debug_capture_signal.connect(self._handle_debug_capture)
        # Подключение сигнала topmost (от хоткея)
        self.toggle_topmost_signal.connect(self.toggle_topmost_winapi)
        # Подключение сигнала невидимости мыши (от хоткея)
        self.toggle_mouse_invisible_mode_signal.connect(self._handle_toggle_mouse_invisible_mode)

        # --- ИСПРАВЛЕНИЕ 2: Корректное подключение сигнала к слоту ---
        # Убедимся, что кнопка уже создана
        if self.topmost_button:
             self.update_topmost_button_property_signal.connect(self._update_topmost_button_property)
             logging.debug("Connected update_topmost_button_property_signal to _update_topmost_button_property slot.")
        else:
            logging.error("Cannot connect update_topmost_button_property_signal: topmost_button is None!")
        # -----------------------------------------------------------

        # Подключение сигнала об изменении состояния topmost (от WinApiManager)
        if self.win_api_manager:
            self.win_api_manager.topmost_state_changed.connect(self._handle_topmost_state_change)
        logging.debug("Signals connected.")

    @Slot(bool)
    def _handle_topmost_state_change(self, is_topmost):
        """Обновляет свойство кнопки и принудительно отключает невидимость, если в min режиме."""
        logging.debug(f"[MainWindow] Received topmost_state_changed signal: {is_topmost}.")
        # Испускаем сигнал для обновления свойства кнопки
        self.update_topmost_button_property_signal.emit(is_topmost)
        logging.debug(f"Emitted update_topmost_button_property_signal({is_topmost})")

        # Проверяем, нужно ли принудительно отключить режим невидимости
        if self.mode == 'min' and is_topmost:
            if self.mouse_invisible_mode_enabled:
                logging.info("Topmost enabled while in min mode. Forcing mouse invisible mode OFF.")
                self.mouse_invisible_mode_enabled = False
                # Флаги окна больше не меняем здесь

    @Slot()
    def _handle_toggle_mouse_invisible_mode(self):
        """Обрабатывает нажатие хоткея Tab+Num9 для переключения режима невидимости мыши."""
        logging.info("[Hotkey Handler] Toggle mouse invisible mode requested.")
        current_state = self.mouse_invisible_mode_enabled
        new_state = not current_state
        is_min_topmost = (self.mode == 'min' and self._is_win_topmost)

        if new_state is True and is_min_topmost:
            logging.warning("Cannot ENABLE mouse invisible mode when in 'min' mode and 'topmost' is active. Keeping it OFF.")
            new_state = False

        if current_state != new_state:
            logging.info(f"Setting mouse invisible mode to: {new_state}")
            self.mouse_invisible_mode_enabled = new_state
            logging.debug(f"Internal mouse_invisible_mode_enabled set to {self.mouse_invisible_mode_enabled}")
            # Флаги окна больше не меняем
        else:
            logging.debug(f"Mouse invisible mode state remains: {current_state}")

    # --- ИСПРАВЛЕНИЕ 3: Метод _apply_mouse_invisible_mode больше не нужен ---
    # def _apply_mouse_invisible_mode(self):
    #     ...
    # -------------------------------------------------------------------

    def closeEvent(self, event):
        logging.info("Close event triggered."); self.stop_keyboard_listener()
        if hasattr(self, 'rec_manager') and self.rec_manager: self.rec_manager.stop_recognition()
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
             logging.info("Waiting for keyboard listener thread..."); self._keyboard_listener_thread.join(timeout=0.5)
             if self._keyboard_listener_thread.is_alive(): logging.warning("Keyboard listener thread did not exit cleanly.")
             else: logging.info("Keyboard listener thread joined.")
        super().closeEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        # Игнорируем нажатие, если включен ручной режим невидимости
        if self.mouse_invisible_mode_enabled:
            logging.debug("Mouse press ignored (mouse invisible mode enabled)")
            event.ignore()
            return
        # Стандартная логика перетаскивания для min режима
        if self.mode == "min" and self.top_frame and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton: self._mouse_pressed = True; self._old_pos = event.globalPosition().toPoint(); event.accept(); return
        self._mouse_pressed = False; super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Игнорируем движение, если включен ручной режим невидимости
        if self.mouse_invisible_mode_enabled:
             logging.debug("Mouse move ignored (mouse invisible mode enabled)")
             event.ignore()
             return
        # Стандартная логика перетаскивания для min режима
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos; self.move(self.pos() + delta); self._old_pos = event.globalPosition().toPoint(); event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        # Игнорируем отпускание, если включен ручной режим невидимости
        if self.mouse_invisible_mode_enabled:
             logging.debug("Mouse release ignored (mouse invisible mode enabled)")
             event.ignore()
             return
        # Стандартная логика перетаскивания для min режима
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton: self._mouse_pressed = False; self._old_pos = None; event.accept()
        else: super().mouseReleaseEvent(event)

    def change_mode(self, mode_name: str):
        """Изменяет режим отображения окна (min, middle, max)."""
        logging.info(f"--- Attempting to change mode to: {mode_name} (Current: {self.mode}) ---")
        if self.mode == mode_name: logging.info(f"Mode '{mode_name}' is already set."); return
        start_time = time.time()

        # 1. Сохраняем позицию ТЕКУЩЕГО режима ПЕРЕД изменениями UI
        old_mode = self.mode
        old_pos = self.pos() if self.isVisible() else None
        old_geom = self.geometry() if self.isVisible() else None
        logging.info(f"[ChangeMode START] From: {old_mode}, To: {mode_name}")
        logging.info(f"[ChangeMode SavePos] Visible: {self.isVisible()}, OldPos: {old_pos}, OldGeom: {old_geom}")
        if old_pos:
            self.mode_positions[old_mode] = old_pos
            logging.info(f"[ChangeMode SavePos] Saved position for mode '{old_mode}': {old_pos}")
        else:
            logging.info(f"[ChangeMode SavePos] Window not visible, skipping position save for mode '{old_mode}'.")

        # 2. Сбрасываем курсор хоткея
        old_cursor_index = self.hotkey_cursor_index; self.hotkey_cursor_index = -1
        if self.right_list_widget and self.right_list_widget.isVisible() and old_cursor_index >= 0:
            try: logging.debug("Updating viewport to remove old hotkey highlight."); self.right_list_widget.viewport().update()
            except Exception as e: logging.warning(f"Failed to update viewport for hotkey reset: {e}")

        # 3. Устанавливаем новый режим в менеджере и окне
        logging.info(f"[ChangeMode SetMode] Setting internal mode to '{mode_name}'")
        self.mode_manager.change_mode(mode_name); self.mode = mode_name; logging.info(f"Mode set to '{self.mode}'")

        # 4. Обновляем интерфейс под НОВЫЙ режим (включая show(), resize(), setWindowFlags())
        logging.info(f"[ChangeMode PreUpdate] Pos: {self.pos()}, Geom: {self.geometry()}")
        self._update_interface_for_mode(new_mode=self.mode)
        logging.info(f"[ChangeMode PostUpdate] Pos: {self.pos()}, Geom: {self.geometry()}")

        # 5. Восстанавливаем позицию для НОВОГО режима ПОСЛЕ обновления UI (с задержкой)
        target_pos = self.mode_positions.get(self.mode)
        logging.info(f"[ChangeMode PreRestore] TargetPos: {target_pos}, CurrentPos: {self.pos()}, Visible: {self.isVisible()}")
        if target_pos and self.isVisible():
            logging.info(f"[ChangeMode RestorePos] Scheduling restore position for mode '{self.mode}': {target_pos}")
            QTimer.singleShot(0, lambda: self._move_window_safely(target_pos))
        elif self.isVisible():
             current_pos_after_resize = self.pos()
             logging.info(f"[ChangeMode RestorePos] No saved position found for mode '{self.mode}'. Using current position after resize: {current_pos_after_resize}")
             self.mode_positions[self.mode] = current_pos_after_resize
        else:
            logging.debug(f"[ChangeMode RestorePos] Window not visible after mode change, skipping position restore for mode '{self.mode}'.")

        # 6. Принудительно отключаем режим невидимости мыши, если перешли в min + topmost
        if self.mode == 'min' and self._is_win_topmost:
             if self.mouse_invisible_mode_enabled:
                 logging.info(f"Entered 'min' mode while 'topmost' is active. Forcing mouse invisible mode OFF.")
                 self.mouse_invisible_mode_enabled = False
                 # Флаги окна больше не меняем

        # 7. Сбрасываем курсор хоткея для нового режима (если нужно)
        self._reset_hotkey_cursor_after_mode_change()
        end_time = time.time();
        logging.info(f"--- Mode change to {mode_name} FINISHED (initial phase took: {end_time - start_time:.4f} sec) ---")
        final_pos = self.pos(); final_geom = self.geometry()
        logging.info(f"[ChangeMode END] Final Pos (before scheduled move): {final_pos}, Final Geom: {final_geom}")

    def _move_window_safely(self, target_pos: QPoint):
        """Перемещает окно в target_pos, вызывается через QTimer."""
        if self.isVisible():
            logging.info(f"[MoveSafely] Moving window to {target_pos}. Current pos: {self.pos()}")
            self.move(target_pos)
            QTimer.singleShot(0, lambda: logging.info(f"[MoveSafely] Pos after move (async check): {self.pos()}"))
        else:
            logging.warning("[MoveSafely] Window not visible, move cancelled.")


    def _update_interface_for_mode(self, new_mode=None):
        """Обновляет UI в соответствии с выбранным режимом."""
        if new_mode is None: new_mode = self.mode
        t0 = time.time(); current_mode = new_mode
        logging.info(f"Updating interface for mode '{current_mode}'")
        logging.info(f"[UpdateIface START] Mode: {current_mode}, Pos: {self.pos()}, Geom: {self.geometry()}")
        current_selection_ids = set(self.logic.selected_heroes)
        logging.debug(f"Current logic selection (before UI update): {current_selection_ids}"); t1 = time.time(); logging.debug("Clearing old panel widgets...")
        # Очистка старых виджетов панелей
        widgets_to_delete = []
        if self.left_panel_widget: widgets_to_delete.append(self.left_panel_widget)
        if self.right_panel_widget: widgets_to_delete.append(self.right_panel_widget)
        if self.inner_layout:
            for widget in widgets_to_delete: self.inner_layout.removeWidget(widget); widget.setParent(None); widget.deleteLater()
        else: logging.warning("inner_layout is None during cleanup")
        # Сброс ссылок
        self.left_panel_widget=None; self.canvas=None; self.result_frame=None; self.result_label=None; self.update_scrollregion=lambda:None
        self.right_panel_widget=None; self.right_frame=None; self.selected_heroes_label=None; self.right_list_widget=None; self.hero_items.clear(); self.right_panel_instance=None
        logging.debug("Old panel widget references cleared."); t2=time.time(); logging.debug(f"[TIMING] -> Clear/Detach old panels: {t2-t1:.4f} s")
        # Загрузка изображений
        t1=time.time()
        try: self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(current_mode)
        except Exception as e: logging.critical(f"Image loading error: {e}"); QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображения: {e}"); return
        logging.debug(f"Images loaded/retrieved for mode '{current_mode}'"); t2=time.time(); logging.debug(f"[TIMING] -> Load/Get images: {t2-t1:.4f} s")
        # Создание левой панели
        t1=time.time(); logging.debug("Creating left panel...")
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.main_widget)
        parent_widget = self.canvas.parentWidget()
        if isinstance(parent_widget, QFrame): self.left_panel_widget = parent_widget; self.left_panel_widget.setObjectName("left_panel_container_frame")
        else: logging.error(f"Left panel parent is not QFrame: {type(parent_widget)}"); self.left_panel_widget = self.canvas
        self.left_panel_widget.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('left', 0))
        self.inner_layout.addWidget(self.left_panel_widget, stretch=1); logging.debug(f"Left panel widget added to inner_layout."); t2=time.time(); logging.debug(f"[TIMING] -> Create left panel: {t2-t1:.4f} s")
        # Создание правой панели (если не min режим)
        t1=time.time()
        if current_mode != "min":
            logging.debug("Creating right panel..."); self.right_panel_instance = RightPanel(self, current_mode)
            self.right_panel_widget = self.right_panel_instance.frame; self.right_panel_widget.setObjectName("right_panel_container_frame")
            self.right_frame = self.right_panel_instance.frame; self.selected_heroes_label = self.right_panel_instance.selected_heroes_label
            self.right_list_widget = self.right_panel_instance.list_widget; self.hero_items = self.right_panel_instance.hero_items
            if self.right_list_widget:
                logging.debug("Connecting signals and setting delegate for new right_list_widget"); delegate_instance = delegate.HotkeyFocusDelegate(self); self.right_list_widget.setItemDelegate(delegate_instance)
                try: self.right_list_widget.itemSelectionChanged.disconnect()
                except RuntimeError: pass
                try: self.right_list_widget.customContextMenuRequested.disconnect()
                except RuntimeError: pass
                self.right_list_widget.itemSelectionChanged.connect(self.handle_selection_changed); self.right_list_widget.customContextMenuRequested.connect(self.show_priority_context_menu)
            else: logging.warning("right_list_widget is None after RightPanel creation.")
            self.right_panel_widget.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('right', 0))
            self.inner_layout.addWidget(self.right_panel_widget, stretch=1); logging.debug(f"Right panel widget added to inner_layout.")
            left_widget_for_stretch = self.left_panel_widget
            if left_widget_for_stretch: self.inner_layout.setStretchFactor(left_widget_for_stretch, 2)
            self.inner_layout.setStretchFactor(self.right_panel_widget, 1)
        else: logging.debug("Right panel skipped for 'min' mode.")
        t2=time.time(); logging.debug(f"[TIMING] -> Create/Hide right panel: {t2-t1:.4f} s")

        # Настройка окна (флаги, высота, видимость элементов)
        t1=time.time(); logging.debug("Configuring window flags and top panel visibility...")
        top_h = self.top_frame.sizeHint().height() if self.top_frame else 40; horiz_size = SIZES.get(current_mode, {}).get('horizontal', (35,35)); h_icon_h = horiz_size[1]
        icons_h = h_icon_h + 12
        spacing = self.main_layout.spacing() if self.main_layout else 0; base_h = top_h + icons_h + spacing
        if self.icons_scroll_area:
             self.icons_scroll_area.setFixedHeight(icons_h); logging.debug(f"Icons scroll area height set to {icons_h}")
        self.setMinimumHeight(0); self.setMaximumHeight(16777215)
        is_min_mode = (current_mode == "min")
        current_flags_before = self.windowFlags()
        current_topmost_state = self._is_win_topmost
        logging.debug(f"[UpdateIface Flags] Current flags BEFORE update: {current_flags_before:#x}, Is Topmost: {current_topmost_state}")

        # --- Собираем ОСНОВНЫЕ флаги окна (тип, рамка, topmost) ---
        target_flags = Qt.WindowType(0)
        if is_min_mode:
            target_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        else:
            target_flags = Qt.WindowType.Window

        if current_topmost_state:
            target_flags |= Qt.WindowType.WindowStaysOnTopHint
        # --- ---

        # --- ИСПРАВЛЕНИЕ 3: Не добавляем флаги невидимости здесь ---
        # --------------------------------------------------------

        # Применяем основные флаги окна
        logging.debug(f"[UpdateIface Flags] Setting BASE window flags: {target_flags:#x}")
        self.setWindowFlags(target_flags)
        logging.info(f"[UpdateIface Flags] Pos after setWindowFlags(Base): {self.pos()}, Geom: {self.geometry()}")

        current_flags_after = self.windowFlags()
        logging.debug(f"[UpdateIface Flags] Final flags AFTER setWindowFlags: {current_flags_after:#x}")

        # Настройка видимости элементов верхней панели и других виджетов
        lang_label = self.top_frame.findChild(QLabel, "language_label"); lang_combo = self.top_frame.findChild(QComboBox, "language_combo")
        version_label = self.top_frame.findChild(QLabel, "version_label");
        # Используем сохраненные ссылки на кнопки
        close_button = self.close_button
        author_button = self.author_button
        rating_button = self.rating_button
        # ---

        if version_label: logging.debug(f"Version label found. Text: '{version_label.text()}', Visible: {version_label.isVisible()}")
        else: logging.warning("Version label not found in top_frame.")

        # Специфичные настройки для каждого режима
        if is_min_mode:
            logging.debug("Setting up MIN mode UI specifics...")
            if lang_label: lang_label.hide()
            if lang_combo: lang_combo.hide()
            if version_label: version_label.hide()
            if author_button: author_button.hide()
            if rating_button: rating_button.hide()
            if close_button: close_button.show() # Показываем в min
            else: logging.warning("Close button ref is None for MIN mode setup")

            self.setWindowTitle(""); calculated_fixed_min_height = base_h + 5; self.setMinimumHeight(calculated_fixed_min_height); self.setMaximumHeight(calculated_fixed_min_height); logging.debug(f"Set fixed height: {calculated_fixed_min_height}")
            if self.left_panel_widget: self.left_panel_widget.hide()
            if self.icons_scroll_area: self.icons_scroll_area.show()
            if self.enemies_widget: self.enemies_widget.show()
            if self.counters_widget: self.counters_widget.show()
            if self.icons_main_h_layout:
                self.icons_main_h_layout.setStretchFactor(self.counters_widget, 1)
                self.icons_main_h_layout.setStretchFactor(self.enemies_widget, 0)
        else: # middle или max
            logging.debug(f"Setting up {current_mode.upper()} mode UI specifics...")
            if lang_label: lang_label.show()
            if lang_combo: lang_combo.show()
            if version_label: version_label.show()
            if close_button: close_button.hide() # Скрываем НЕ в min
            else: logging.warning("Close button ref is None for MIDDLE/MAX mode setup")

            self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
            if self.left_panel_widget: self.left_panel_widget.show()
            if self.icons_scroll_area: self.icons_scroll_area.show()
            if self.enemies_widget: self.enemies_widget.hide()
            if self.counters_widget: self.counters_widget.show()
            if self.icons_main_h_layout:
                self.icons_main_h_layout.setStretchFactor(self.counters_widget, 1)
                self.icons_main_h_layout.setStretchFactor(self.enemies_widget, 0)
            if current_mode == "max":
                calculated_min_h = base_h + 300; self.setMinimumHeight(calculated_min_h); logging.debug(f"Set min height for max mode: {calculated_min_h}");
                if author_button: author_button.show() # Показываем в max
                if rating_button: rating_button.show() # Показываем в max
            else: # middle
                calculated_min_h = base_h + 200; self.setMinimumHeight(calculated_min_h); logging.debug(f"Set min height for middle mode: {calculated_min_h}");
                if author_button: author_button.hide() # Скрываем в middle
                if rating_button: rating_button.hide() # Скрываем в middle

        # Показываем окно ПОСЛЕ применения флагов И настройки виджетов
        logging.info("Calling window.show() after updating flags and UI visibility."); self.show();
        logging.info(f"[UpdateIface Visibility] Pos after show(): {self.pos()}, Geom: {self.geometry()}")
        t2 = time.time(); logging.debug(f"[TIMING] -> Setup window flags/visibility: {t2-t1:.4f} s")

        # Обновление языка, layout'ов и геометрии
        t1 = time.time(); self.update_language(); self.main_layout.activate();
        if self.inner_layout: self.inner_layout.activate()
        self.updateGeometry();
        logging.info(f"[UpdateIface Geometry] Pos after updateGeometry(): {self.pos()}, Geom: {self.geometry()}")
        t2 = time.time(); logging.debug(f"[TIMING] -> Update language/layout/geometry: {t2-t1:.4f} s")

        # Установка размера окна
        t1 = time.time(); target_size = MODE_DEFAULT_WINDOW_SIZES.get(current_mode, {'width': 800, 'height': 600})
        target_w = target_size['width']; target_h = target_size['height']; min_w = self.minimumSizeHint().width(); actual_min_h = self.minimumHeight()
        if current_mode == 'min': final_w = max(target_w, min_w); final_h = self.minimumHeight() # Используем фиксированную высоту для min
        else: final_w = max(target_w, min_w); final_h = max(target_h, actual_min_h)
        logging.debug(f"Resizing window to: {final_w}x{final_h}"); self.resize(final_w, final_h);
        logging.info(f"[UpdateIface Resize] Pos after resize(): {self.pos()}, Geom: {self.geometry()}")
        t2 = time.time(); logging.debug(f"[TIMING] -> Resize window: {t2-t1:.4f} s")

        # Обновление состояния UI после смены режима
        t1 = time.time(); logging.info("Updating UI state after mode change...")
        self.update_ui_after_logic_change()
        logging.debug(f"Restoring selection state to UI. Logic selection: {current_selection_ids}")
        if self.right_list_widget:
            QTimer.singleShot(50, lambda: self._update_list_item_selection_states(force_update=True))
            logging.debug("Scheduled _update_list_item_selection_states with force_update=True after 50ms delay.")
        else: logging.debug("Right list widget not available, skipping selection state restoration.")
        t2 = time.time(); logging.info(f"[TIMING] -> Restore UI state (scheduling selection): {t2-t1:.4f} s")
        t_end = time.time(); logging.info(f"[TIMING] _update_interface_for_mode: Finished (Total: {t_end - t0:.4f} s)")
        logging.info(f"[UpdateIface END] Pos: {self.pos()}, Geom: {self.geometry()}")

    def _reset_hotkey_cursor_after_mode_change(self):
        logging.debug("_reset_hotkey_cursor_after_mode_change called")
        list_widget = self.right_list_widget
        if list_widget and list_widget.isVisible() and self.mode != 'min':
            count = list_widget.count(); logging.debug(f"Right list count: {count}")
            if count > 0:
                self.hotkey_cursor_index = 0; self._calculate_columns(); self._update_hotkey_highlight(old_index=None)
                first_item = list_widget.item(0)
                if first_item: list_widget.scrollToItem(first_item, QAbstractItemView.ScrollHint.EnsureVisible)
                logging.debug(f"[Hotkey] Cursor reset to index 0 in mode {self.mode}")
            else: self.hotkey_cursor_index = -1; logging.debug(f"[Hotkey] List is empty, cursor set to -1 in mode {self.mode}")
        else:
            self.hotkey_cursor_index = -1; list_visible_status = list_widget.isVisible() if list_widget else 'No list'
            logging.debug(f"[Hotkey] Cursor set to -1 (mode: {self.mode}, list visible: {list_visible_status})")

    @property
    def _is_win_topmost(self):
        """Возвращает текущее состояние topmost из WinApiManager."""
        if not hasattr(self, 'win_api_manager'): logging.warning("win_api_manager not found."); return False
        return self.win_api_manager.is_win_topmost

    def set_topmost_winapi(self, enable: bool):
        """Устанавливает состояние topmost через WinApiManager."""
        if hasattr(self, 'win_api_manager'):
            self.win_api_manager.set_topmost_winapi(enable)
        else:
            logging.warning("win_api_manager not found.")

    def toggle_topmost_winapi(self):
        """Переключает состояние topmost через WinApiManager."""
        if hasattr(self, 'win_api_manager'):
            self.win_api_manager.set_topmost_winapi(not self.win_api_manager.is_win_topmost)
        else:
             logging.warning("win_api_manager not found.")


    @Slot(str)
    def _handle_move_cursor(self, direction):
        logging.debug(f"[GUI Slot] _handle_move_cursor received direction: {direction}")
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': logging.debug(f"Move cursor ignored (list widget: {list_widget is not None}, visible: {list_widget.isVisible() if list_widget else 'N/A'}, mode: {self.mode})"); return
        count = list_widget.count();
        if count == 0: return
        old_index = self.hotkey_cursor_index; num_columns = max(1, self._calculate_columns())
        if self.hotkey_cursor_index < 0: new_index = 0
        else:
            current_row = self.hotkey_cursor_index // num_columns; current_col = self.hotkey_cursor_index % num_columns; new_index = self.hotkey_cursor_index
            if direction == 'left':
                if current_col > 0: new_index -= 1
                elif current_row > 0: new_index = (current_row - 1) * num_columns + (num_columns - 1); new_index = min(new_index, count - 1)
                else: new_index = count - 1
            elif direction == 'right':
                if current_col < num_columns - 1 and self.hotkey_cursor_index < count - 1: new_index += 1
                elif self.hotkey_cursor_index < count - 1: new_index = (current_row + 1) * num_columns
                else: new_index = 0
                new_index = min(new_index, count - 1)
            elif direction == 'up':
                new_index -= num_columns
                if new_index < 0:
                   last_row_index = (count - 1) // num_columns
                   potential_index = last_row_index * num_columns + current_col
                   new_index = min(potential_index, count - 1)
            elif direction == 'down':
                new_index += num_columns
                if new_index >= count:
                    potential_index = current_col
                    new_index = min(potential_index, count - 1);
                    if new_index >= count : new_index = 0

            new_index = max(0, min(count - 1, new_index))
        if old_index != new_index:
            self.hotkey_cursor_index = new_index; self._update_hotkey_highlight(old_index=old_index); logging.debug(f"Cursor moved to index {new_index}")
        elif 0 <= self.hotkey_cursor_index < count:
             current_item = list_widget.item(self.hotkey_cursor_index)
             if current_item: list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)

    @Slot()
    def _handle_toggle_selection(self):
        logging.info("[GUI Slot] _handle_toggle_selection triggered")
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min' or self.hotkey_cursor_index < 0:
            logging.warning(f"Toggle selection ignored (list: {list_widget is not None}, visible: {list_widget.isVisible() if list_widget else 'N/A'}, mode: {self.mode}, index: {self.hotkey_cursor_index})")
            return
        if 0 <= self.hotkey_cursor_index < list_widget.count():
            item = list_widget.item(self.hotkey_cursor_index)
            if item:
                try:
                    is_selected = item.isSelected(); new_state = not is_selected
                    logging.info(f"Toggling selection for item {self.hotkey_cursor_index} ('{item.data(HERO_NAME_ROLE)}'). State: {is_selected} -> {new_state}")
                    item.setSelected(new_state)
                except RuntimeError: logging.warning(f"RuntimeError accessing item during toggle selection (index {self.hotkey_cursor_index}). Might be deleting.")
                except Exception as e: logging.error(f"Error toggling selection via hotkey: {e}", exc_info=True)
            else: logging.warning(f"Item at index {self.hotkey_cursor_index} is None.")
        else: logging.warning(f"Invalid hotkey cursor index: {self.hotkey_cursor_index}")

    @Slot()
    def _handle_toggle_mode(self):
        logging.info("[GUI Slot] _handle_toggle_mode triggered")
        debounce_time = 0.3
        current_time = time.time()
        if current_time - self._last_mode_toggle_time < debounce_time:
            logging.warning(f"Mode toggle ignored due to debounce ({current_time - self._last_mode_toggle_time:.2f}s < {debounce_time}s)")
            return
        self._last_mode_toggle_time = current_time
        target_mode = "middle" if self.mode == "min" else "min"; self.change_mode(target_mode)

    @Slot()
    def _handle_clear_all(self):
        logging.info("[GUI Slot] _handle_clear_all triggered");
        self.logic.clear_all(); self.update_ui_after_logic_change(); self._reset_hotkey_cursor_after_clear()

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes):
        logging.info(f"Recognition complete. Heroes: {recognized_heroes}")
        if recognized_heroes:
            self.logic.set_selection(set(recognized_heroes)); self.update_ui_after_logic_change(); self._reset_hotkey_cursor_after_clear()
        else: logging.info("No heroes recognized."); QMessageBox.information(self, "Распознавание", get_text('recognition_failed', language=self.logic.DEFAULT_LANGUAGE))

    @Slot(str)
    def _on_recognition_error(self, error_message):
        logging.error(f"Recognition error: {error_message}"); QMessageBox.warning(self, get_text('error', language=self.logic.DEFAULT_LANGUAGE), f"{get_text('recognition_error_prefix', language=self.logic.DEFAULT_LANGUAGE)}\n{error_message}")

    @Slot()
    def _handle_debug_capture(self):
        logging.info("[Debug Capture] Received debug_capture_signal. Capturing screen area...")
        try:
            screenshot = utils.capture_screen_area(utils.RECOGNITION_AREA)
            if screenshot is not None:
                filename = "debug_screenshot_test.png"; project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'));
                filepath = os.path.join(project_dir, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                cv2.imwrite(filepath, screenshot); logging.info(f"[Debug Capture] Screenshot saved to: {filepath}")
                QMessageBox.information(self, "Debug Screenshot", f"Тестовый скриншот сохранен как:\n{filepath}")
            else:
                logging.warning("[Debug Capture] Failed to capture screenshot (capture_screen_area returned None).")
                QMessageBox.warning(self, "Debug Screenshot", "Не удалось сделать тестовый скриншот.")
        except Exception as e:
            logging.error(f"[Debug Capture] Error during debug capture: {e}", exc_info=True)
            QMessageBox.critical(self, "Debug Screenshot Error", f"Ошибка при сохранении скриншота:\n{e}")

    def update_ui_after_logic_change(self):
        """Обновляет все элементы интерфейса, зависящие от состояния логики."""
        logging.info("Updating UI after logic change."); start_time = time.time()
        self._update_selected_label()
        self._update_counterpick_display()
        self._update_horizontal_lists()
        self._update_list_item_selection_states()
        self._update_priority_labels()
        end_time = time.time(); logging.info(f"UI Update Finished in {end_time - start_time:.4f} sec.")


    def _update_selected_label(self):
        label_to_update = self.selected_heroes_label
        if label_to_update and self.right_panel_widget and self.right_panel_widget.isVisible():
             try: label_to_update.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass
             except Exception as e: logging.error(f"Error updating selected label: {e}")

    def _update_counterpick_display(self):
        if self.mode == "min":
             logging.debug("Counterpick display skipped in min mode.")
             return

        if not self.result_frame or not self.canvas: logging.warning("result_frame or canvas not found for counterpick display"); return

        images_ok = bool(self.left_images) and bool(self.small_images)
        if not images_ok:
             logging.warning(f"Images not loaded for mode '{self.mode}' (left/small). Attempting reload.")
             try: _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
             except Exception as e: logging.error(f"Error reloading images for counterpick display: {e}"); return

        try:
            display.generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)
            if self.update_scrollregion: QTimer.singleShot(0, self.update_scrollregion)
            logging.debug("Counterpick display (left panel) updated.")
        except RuntimeError as e: logging.error(f"RuntimeError during counterpick display generation: {e}")
        except Exception as e: logging.error(f"Error generating counterpick display: {e}"); import traceback; traceback.print_exc()

    def _update_horizontal_lists(self):
        """Обновляет горизонтальные списки контрпиков и врагов."""
        logging.debug("Updating horizontal lists...")
        if not self.counters_layout or not self.enemies_layout or not self.horizontal_info_label:
            logging.error("Horizontal list layouts or info label not initialized.")
            return

        if self.horizontal_info_label.parentWidget():
            parent_layout = self.horizontal_info_label.parentWidget().layout()
            if parent_layout:
                parent_layout.removeWidget(self.horizontal_info_label)
            self.horizontal_info_label.setParent(None)
        self.horizontal_info_label.hide()

        clear_layout_util(self.counters_layout)
        clear_layout_util(self.enemies_layout)

        if not self.logic.selected_heroes:
            self.horizontal_info_label.setText(get_text("select_enemies_for_recommendations", language=self.logic.DEFAULT_LANGUAGE))
            self.counters_layout.addWidget(self.horizontal_info_label)
            self.horizontal_info_label.show()
            self.counters_layout.addStretch(1)
            self.enemies_layout.addStretch(1)
            logging.debug("Showing 'select enemies' message in horizontal list.")
        else:
            horizontal_list.update_horizontal_icon_list(self, self.counters_layout)
            if self.mode == "min":
                horizontal_list.update_enemy_horizontal_list(self, self.enemies_layout)
            else:
                 self.enemies_layout.addStretch(1)

            counters_items_count = sum(1 for i in range(self.counters_layout.count()) if self.counters_layout.itemAt(i).widget())
            enemies_items_count = sum(1 for i in range(self.enemies_layout.count()) if self.enemies_layout.itemAt(i).widget())

            show_no_recs = counters_items_count == 0

            if show_no_recs:
                 self.horizontal_info_label.setText(get_text("no_recommendations", language=self.logic.DEFAULT_LANGUAGE))
                 self.counters_layout.insertWidget(0, self.horizontal_info_label)
                 self.horizontal_info_label.show()
                 if self.counters_layout.count() == 0 or self.counters_layout.itemAt(self.counters_layout.count() - 1).spacerItem() is None:
                     self.counters_layout.addStretch(1)

                 logging.debug("Showing 'no recommendations' message in horizontal list.")

        if self.icons_scroll_area:
            QTimer.singleShot(0, self.icons_scroll_area.updateGeometry)
            QTimer.singleShot(10, lambda: self.icons_scroll_content.adjustSize() if self.icons_scroll_content else None)

    def _update_list_item_selection_states(self, force_update=False):
        list_widget = self.right_list_widget; hero_items_dict = self.hero_items
        if not list_widget or not list_widget.isVisible(): logging.debug("Skipping selection state update (no list widget or not visible)"); return
        if not hero_items_dict or list_widget.count() == 0 or list_widget.count() != len(hero_items_dict):
             logging.warning(f"Selection state update skipped: mismatch or empty (list:{list_widget.count()} vs dict:{len(hero_items_dict)})")
             if not hero_items_dict and list_widget.count() > 0 and self.right_panel_instance:
                  logging.warning("Hero items dictionary is empty but list widget is not. Re-populating...")
                  self.right_panel_instance._populate_list_widget()
                  hero_items_dict = self.hero_items
                  if not hero_items_dict:
                       logging.error("Failed to repopulate hero items dictionary.")
                       return
             elif not hero_items_dict:
                  return

        self.is_programmatically_updating_selection = True; items_changed_count = 0
        try:
            list_widget.blockSignals(True); current_logic_selection = set(self.logic.selected_heroes)
            items_to_check = list(hero_items_dict.items())
            for hero, item in items_to_check:
                if item is None: logging.warning(f"Item for hero '{hero}' is None"); continue
                try:
                    is_currently_selected_in_widget = item.isSelected(); should_be_selected_in_logic = (hero in current_logic_selection)
                    if is_currently_selected_in_widget != should_be_selected_in_logic or force_update:
                        item.setSelected(should_be_selected_in_logic); items_changed_count += 1
                except RuntimeError: logging.warning(f"RuntimeError accessing item for hero '{hero}'"); continue
                except Exception as e: logging.error(f"Error updating selection state for hero '{hero}': {e}")
            self._update_selected_label()
            if list_widget and list_widget.viewport(): QMetaObject.invokeMethod(list_widget.viewport(), "update", Qt.ConnectionType.QueuedConnection)
        except Exception as e: logging.error(f"Unexpected error in _update_list_item_selection_states: {e}", exc_info=True)
        finally:
            try:
                if list_widget: list_widget.blockSignals(False)
            except RuntimeError: pass
            self.is_programmatically_updating_selection = False

    def _update_priority_labels(self):
        list_widget = self.right_list_widget; hero_items_dict = self.hero_items
        if not list_widget or not list_widget.isVisible(): return
        priority_color = QColor("lightcoral"); default_brush = QBrush(Qt.GlobalColor.transparent)
        focused_index = self.hotkey_cursor_index
        for hero, item in hero_items_dict.items():
             if item is None: continue
             try:
                 item_index = list_widget.row(item); is_priority = hero in self.logic.priority_heroes
                 is_hotkey_focused = (item_index == focused_index and self.mode != 'min'); is_selected = item.isSelected()
                 target_brush = default_brush
                 if is_priority and not is_selected and not is_hotkey_focused: target_brush = QBrush(priority_color)
                 if item.background() != target_brush: item.setBackground(target_brush)
             except RuntimeError: continue
             except Exception as e: logging.error(f"Error updating priority label for hero '{hero}': {e}")

    def handle_selection_changed(self):
        if self.is_programmatically_updating_selection: logging.debug("Selection change ignored (programmatic)"); return
        list_widget = self.right_list_widget
        if not list_widget: logging.warning("handle_selection_changed called but list_widget is None"); return
        logging.info("Handling selection changed by user...")
        selected_items = list_widget.selectedItems(); current_ui_selection_names = set(item.data(HERO_NAME_ROLE) for item in selected_items if item.data(HERO_NAME_ROLE))
        if len(current_ui_selection_names) > TEAM_SIZE: logging.warning(f"UI selection count ({len(current_ui_selection_names)}) exceeds TEAM_SIZE ({TEAM_SIZE}). Relying on logic.set_selection to handle.")
        current_logic_selection = set(self.logic.selected_heroes); logging.debug(f"UI Selection: {current_ui_selection_names} ({len(current_ui_selection_names)}), Logic Selection before update: {current_logic_selection} ({len(current_logic_selection)})")
        if current_logic_selection != current_ui_selection_names:
            logging.debug(f"Selection mismatch detected. Updating logic with UI state.")
            try:
                self.logic.set_selection(current_ui_selection_names)
                self.update_ui_after_logic_change()
            except RuntimeError as e:
                 logging.error(f"Unhandled RuntimeError during selection change update: {e}", exc_info=True)
                 raise e
            except Exception as e:
                logging.error(f"Unexpected error during selection change update: {e}", exc_info=True)
        else: logging.debug("UI selection matches logic. No logic update needed.")

    def show_priority_context_menu(self, pos: QPoint):
        list_widget = self.right_list_widget;
        if not list_widget or not list_widget.isVisible(): return
        item = list_widget.itemAt(pos);
        if not item: return
        hero_name = item.data(HERO_NAME_ROLE);
        if not hero_name: return
        global_pos = list_widget.viewport().mapToGlobal(pos); menu = QMenu(self)
        is_priority = hero_name in self.logic.priority_heroes; is_selected = item.isSelected()
        action_text_key = 'remove_priority' if is_priority else 'set_priority'; action_text = get_text(action_text_key, language=self.logic.DEFAULT_LANGUAGE)
        priority_action = menu.addAction(action_text); priority_action.setEnabled(is_selected)
        action = menu.exec(global_pos)
        if priority_action and action == priority_action:
            if hero_name in self.logic.selected_heroes: self.logic.set_priority(hero_name); self.update_ui_after_logic_change()
            else: logging.warning(f"Cannot change priority for '{hero_name}' (not selected).")

    def switch_language(self, lang_code: str):
        logging.info(f"Switching language to {lang_code}")
        if lang_code not in SUPPORTED_LANGUAGES: logging.warning(f"Unsupported language: {lang_code}"); return
        if self.logic.DEFAULT_LANGUAGE != lang_code:
            set_language(lang_code); self.logic.DEFAULT_LANGUAGE = lang_code; self.update_language(); self.update_ui_after_logic_change()
            if self.hotkey_cursor_index != -1: QTimer.singleShot(50, self._update_hotkey_highlight)
        else: logging.info(f"Language already {lang_code}")

    def update_language(self):
        logging.info("Updating language for UI elements..."); current_lang = self.logic.DEFAULT_LANGUAGE
        self.setWindowTitle(f"{get_text('title', language=current_lang)} v{self.app_version}")
        if self.top_panel_instance: self.top_panel_instance.update_language()
        if self.right_panel_instance and self.right_panel_widget and self.right_panel_widget.isVisible():
            self.right_panel_instance.update_language()
            list_widget = self.right_list_widget; hero_items_dict = self.hero_items
            if list_widget:
                 focused_tooltip_base = None; current_focused_item = None
                 if 0 <= self.hotkey_cursor_index < list_widget.count():
                      try:
                          current_focused_item = list_widget.item(self.hotkey_cursor_index)
                          if current_focused_item: focused_tooltip_base = current_focused_item.data(HERO_NAME_ROLE)
                      except RuntimeError: logging.warning(f"RuntimeError getting focused item ({self.hotkey_cursor_index})")
                 for hero, item in hero_items_dict.items():
                      if item is None: continue
                      try: item_text = hero if self.mode == "max" else ""; item.setText(item_text); item.setToolTip(hero)
                      except RuntimeError: continue
                 if focused_tooltip_base and current_focused_item:
                     try: current_focused_item.setToolTip(f">>> {focused_tooltip_base} <<<")
                     except RuntimeError: pass

        try:
            if self.result_label and not self.logic.selected_heroes:
                self.result_label.setText(get_text('no_heroes_selected', language=current_lang))

            if self.horizontal_info_label and self.horizontal_info_label.isVisible():
                 if not self.logic.selected_heroes:
                     self.horizontal_info_label.setText(get_text('select_enemies_for_recommendations', language=current_lang))
                 else:
                     counters_items_count = 0
                     if self.counters_layout:
                         counters_items_count = sum(1 for i in range(self.counters_layout.count()) if self.counters_layout.itemAt(i).widget())
                     if counters_items_count == 0:
                         self.horizontal_info_label.setText(get_text('no_recommendations', language=current_lang))
        except RuntimeError as e:
            logging.error(f"RuntimeError during language update (label access?): {e}")
        except Exception as e:
             logging.error(f"Unexpected error during language update: {e}", exc_info=True)

        logging.info("Language update finished.")


    def _calculate_columns(self) -> int:
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': self._num_columns_cache = 1; return 1
        try:
            viewport = list_widget.viewport();
            if not viewport: return self._num_columns_cache
            vp_width = viewport.width(); grid_size = list_widget.gridSize(); spacing = list_widget.spacing()
            if grid_size.width() <= 0:
                 logging.warning("Grid size width is zero or negative, cannot calculate columns.")
                 return self._num_columns_cache
            effective_grid_width = grid_size.width() + spacing
            if effective_grid_width <= 0:
                 logging.warning("Effective grid width is zero or negative, cannot calculate columns.")
                 return self._num_columns_cache
            cols = max(1, int(vp_width / effective_grid_width))
            if cols != self._num_columns_cache: logging.debug(f"Calculated columns: {cols} (vp_width={vp_width}, grid_w={grid_size.width()}, spacing={spacing})"); self._num_columns_cache = cols
            return cols
        except Exception as e: logging.error(f"Error calculating columns: {e}"); return self._num_columns_cache

    def _update_hotkey_highlight(self, old_index=None):
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': return
        count = list_widget.count();
        if count == 0: return
        new_index = self.hotkey_cursor_index; logging.debug(f"Updating hotkey highlight: old={old_index}, new={new_index}")
        needs_viewport_update = False
        if old_index is not None and old_index != new_index and 0 <= old_index < count:
            try:
                old_item = list_widget.item(old_index)
                if old_item:
                    hero_name = old_item.data(HERO_NAME_ROLE); current_tooltip = old_item.toolTip()
                    if hero_name and current_tooltip and current_tooltip.startswith(">>>"): old_item.setToolTip(hero_name)
                    self._update_priority_labels()
                    needs_viewport_update = True
            except RuntimeError: pass
            except Exception as e: logging.error(f"Error restoring old item state (idx {old_index}): {e}")
        if 0 <= new_index < count:
            try:
                new_item = list_widget.item(new_index)
                if new_item:
                    hero_name = new_item.data(HERO_NAME_ROLE); focus_tooltip = f">>> {hero_name} <<<"
                    if hero_name and new_item.toolTip() != focus_tooltip: new_item.setToolTip(focus_tooltip)
                    self._update_priority_labels()
                    list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
                    needs_viewport_update = True
            except RuntimeError: pass
            except Exception as e: logging.error(f"Error setting new item state/scrolling (idx {new_index}): {e}")
        if list_widget.viewport() and needs_viewport_update:
             logging.debug("Scheduling viewport update for hotkey highlight")
             QMetaObject.invokeMethod(list_widget.viewport(), "update", Qt.ConnectionType.QueuedConnection)

    def start_keyboard_listener(self):
        if not keyboard: logging.warning("Keyboard library not available."); return
        if self._keyboard_listener_thread is None or not self._keyboard_listener_thread.is_alive():
            logging.info("Starting keyboard listener thread..."); self._stop_keyboard_listener_flag.clear()
            self._keyboard_listener_thread = threading.Thread(target=self._keyboard_listener_loop, daemon=True); self._keyboard_listener_thread.start()
        else: logging.info("Keyboard listener already running.")

    def stop_keyboard_listener(self):
        if not keyboard: return
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
            logging.info("Signalling keyboard listener to stop..."); self._stop_keyboard_listener_flag.set()
        else: logging.info("Keyboard listener not running or already stopped.")

    def _keyboard_listener_loop(self):
        if not keyboard: return
        logging.info("[Hotkey] Listener thread started.")
        # Карта хоткеев
        hotkeys_map = {
            'tab+up': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+up -> Move Up"), self.move_cursor_signal.emit('up')), True),
            'tab+down': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+down -> Move Down"), self.move_cursor_signal.emit('down')), True),
            'tab+left': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+left -> Move Left"), self.move_cursor_signal.emit('left')), True),
            'tab+right': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+right -> Move Right"), self.move_cursor_signal.emit('right')), True),
            'tab+num 0': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+num 0 -> Toggle Selection"), self.toggle_selection_signal.emit()), True),
            'tab+num -': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+num - -> Clear All"), self.clear_all_signal.emit()), True),
            'tab+-': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+- -> Clear All"), self.clear_all_signal.emit()), True),
            'tab+decimal': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+decimal -> Toggle Mode"), self.toggle_mode_signal.emit()), True), # Num . (NumLock ON)
            'tab+delete': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+delete -> Toggle Mode"), self.toggle_mode_signal.emit()), True), # Num Del (NumLock OFF) / Standard Delete
            'tab+.': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+. -> Toggle Mode"), self.toggle_mode_signal.emit()), True), # Обычная точка
            'tab+num /': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+num / -> Recognize"), self.recognize_heroes_signal.emit()), True),
            'tab+/': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+/ -> Recognize"), self.recognize_heroes_signal.emit()), True), # Обычный слеш
            'tab+num *': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+num * -> Debug Capture"), self.debug_capture_signal.emit()), True),
            'tab+*': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+* -> Debug Capture"), self.debug_capture_signal.emit()), True), # Обычная * (Shift+8)
            'tab+num 7': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+num 7 -> Toggle Topmost"), self.toggle_topmost_signal.emit()), True), # Переключение Topmost
            'tab+num 9': (lambda: (logging.info("[Hotkey Listener] HOOK: tab+num 9 -> Toggle Mouse Invisible Mode"), self.toggle_mouse_invisible_mode_signal.emit()), True), # Переключение невидимости мыши
        }
        hooks_registered_count = 0
        try:
            logging.info(f"Registering {len(hotkeys_map)} hooks...")
            for hotkey, (callback_or_signal_emit, suppress_flag) in hotkeys_map.items():
                try:
                    keyboard.add_hotkey(hotkey, callback_or_signal_emit, suppress=suppress_flag, trigger_on_release=False)
                    hooks_registered_count += 1
                    logging.debug(f"Registered hotkey: {hotkey}")
                except ValueError as e:
                    logging.warning(f"Hook registration failed for '{hotkey}'. Error: {e}. Raw Error: {repr(e)}")
                    try:
                        err_args = getattr(e, 'args', None)
                        if err_args and isinstance(err_args, tuple) and len(err_args) > 0:
                            logging.warning(f"  Error message details: {err_args[0]}")
                            if isinstance(err_args[0], str) and "not mapped to any known key" in err_args[0]:
                                problematic_key = err_args[0].split("'")[1] if "'" in err_args[0] else "[unknown key]"
                                logging.warning(f"  -> Problematic key seems to be: '{problematic_key}'")
                    except Exception as inner_e:
                        logging.warning(f"  (Could not extract further details from ValueError: {inner_e})")
                except Exception as e: logging.error(f"Hook registration failed for '{hotkey}': {e}", exc_info=True)
            logging.info(f"Hooks registered: {hooks_registered_count}/{len(hotkeys_map)}")
            if hooks_registered_count < len(hotkeys_map):
                 logging.warning(f"Some hotkeys failed to register ({len(hotkeys_map) - hooks_registered_count} failed). Check warnings above.")
            if hooks_registered_count == 0 and len(hotkeys_map) > 0:
                logging.error("No keyboard hooks were registered successfully! Hotkeys will not work.")
            else:
                self._stop_keyboard_listener_flag.wait(); logging.info("[Hotkey Listener] Stop signal received.")
        except ImportError: logging.error("keyboard library requires root/admin privileges.")
        except Exception as e: logging.error(f"Error in keyboard listener loop: {e}", exc_info=True)
        finally:
            logging.info("Unhooking all keyboard hotkeys...");
            try: keyboard.unhook_all()
            except Exception as e_unhook: logging.error(f"Error during keyboard.unhook_all(): {e_unhook}")
            logging.info("[Hotkey] Listener thread finished.")

    def copy_to_clipboard(self): copy_to_clipboard(self.logic)

    def _reset_hotkey_cursor_after_clear(self):
         list_widget = self.right_list_widget
         if list_widget and list_widget.isVisible() and self.mode != 'min':
            old_index = self.hotkey_cursor_index; count = list_widget.count()
            self.hotkey_cursor_index = 0 if count > 0 else -1
            if self.hotkey_cursor_index != old_index or old_index != -1:
                 self._update_hotkey_highlight(old_index)
            if self.hotkey_cursor_index == 0:
                first_item = list_widget.item(0)
                if first_item: list_widget.scrollToItem(first_item, QAbstractItemView.ScrollHint.EnsureVisible)
         else:
             self.hotkey_cursor_index = -1
