# File: core/main_window.py
import sys
import time
import threading
import os
import logging

from PySide6.QtWidgets import (
    QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QScrollArea,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QMenu, QStyleFactory, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QPoint, QModelIndex, QMetaObject, Q_ARG
from PySide6.QtGui import QIcon, QMouseEvent, QColor, QBrush, QPixmap

import translations
import utils_gui
import logic
import delegate
import dialogs
import display
import horizontal_list
import images_load
from mode_manager import ModeManager, PANEL_MIN_WIDTHS, MODE_DEFAULT_WINDOW_SIZES
from win_api import WinApiManager, user32 as winapi_user32, is_window_topmost
from recognition import RecognitionManager, RecognitionWorker
from top_panel import TopPanel
from left_panel import LeftPanel, create_left_panel
from right_panel import RightPanel, HERO_NAME_ROLE

from translations import get_text, set_language, SUPPORTED_LANGUAGES
from utils_gui import copy_to_clipboard
from logic import CounterpickLogic, TEAM_SIZE
from images_load import get_images_for_mode, SIZES, load_default_pixmap, is_invalid_pixmap
from horizontal_list import update_horizontal_icon_list, clear_layout as clear_layout_util
from display import generate_counterpick_display, generate_minimal_icon_list

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

    def __init__(self, logic_instance: CounterpickLogic, hero_templates_dict: dict):
        super().__init__()
        logging.info("Initializing MainWindow...")
        self.logic = logic_instance; self.hero_templates = hero_templates_dict
        self.app_version = self.logic.APP_VERSION
        logging.info(f"App Version used by MainWindow: {self.app_version}")
        self.win_api_manager = WinApiManager(self); self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)
        self.mode = self.mode_manager.current_mode; logging.info(f"Initial mode: {self.mode}")
        self.initial_pos = self.pos(); self.mode_positions = self.mode_manager.mode_positions
        self.mode_positions["middle"] = self.initial_pos; self.is_programmatically_updating_selection = False
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_panel_instance: TopPanel | None = None; self.right_panel_instance: RightPanel | None = None
        self.main_layout: QVBoxLayout | None = None; self.top_frame: QFrame | None = None
        self.author_button: QPushButton | None = None; self.rating_button: QPushButton | None = None
        self.icons_scroll_area: QScrollArea | None = None; self.icons_scroll_content: QWidget | None = None
        self.icons_scroll_content_layout: QHBoxLayout | None = None; self.main_widget: QWidget | None = None
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

        self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
        icon_path = images_load.resource_path("resources/icon.png")
        icon_pixmap = QPixmap(icon_path) if os.path.exists(icon_path) else load_default_pixmap((32, 32))
        if not icon_pixmap.isNull(): self.setWindowIcon(QIcon(icon_pixmap))
        else: logging.warning("Failed to load application icon.")
        self.setGeometry(100, 100, 950, 350); self.setMinimumSize(400, 100)
        self._create_main_ui_layout(); self._update_interface_for_mode(); self._connect_signals()
        if keyboard: self.start_keyboard_listener()
        else: logging.warning("Keyboard library not available or no admin rights, hotkeys disabled.")
        logging.info("MainWindow.__init__ finished")

    def _create_main_ui_layout(self):
        logging.debug("Creating main UI layout...")
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
        self.top_frame = self.top_panel_instance.top_frame
        self.author_button = self.top_panel_instance.author_button
        self.rating_button = self.top_panel_instance.rating_button
        self.main_layout.addWidget(self.top_frame); logging.debug("Top panel created and added.")
        self._create_icons_scroll_area(); self.main_layout.addWidget(self.icons_scroll_area); logging.debug("Icons scroll area created and added.")
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
        self.inner_layout.setContentsMargins(0,0,0,0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1); logging.debug("Main widget and inner_layout created and added.")
        logging.debug("Main UI layout creation finished.")

    def _create_icons_scroll_area(self):
        self.icons_scroll_area = QScrollArea(); self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True); self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea#icons_scroll_area { border: none; background-color: #f0f0f0; }")
        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content_layout = QHBoxLayout(self.icons_scroll_content); self.icons_scroll_content_layout.setObjectName("icons_scroll_content_layout")
        self.icons_scroll_content_layout.setContentsMargins(5, 2, 5, 2); self.icons_scroll_content_layout.setSpacing(4); self.icons_scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)

    def _connect_signals(self):
        logging.debug("Connecting signals...")
        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)
        self.toggle_mode_signal.connect(self._handle_toggle_mode)
        self.clear_all_signal.connect(self._handle_clear_all)
        self.recognize_heroes_signal.connect(self.rec_manager.recognize_heroes_signal.emit)
        self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
        self.rec_manager.error.connect(self._on_recognition_error)
        logging.debug("Signals connected.")

    def closeEvent(self, event):
        logging.info("Close event triggered."); self.stop_keyboard_listener()
        if hasattr(self, 'rec_manager') and self.rec_manager: self.rec_manager.stop_recognition()
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
             logging.info("Waiting for keyboard listener thread..."); self._keyboard_listener_thread.join(timeout=0.5)
             if self._keyboard_listener_thread.is_alive(): logging.warning("Keyboard listener thread did not exit cleanly.")
             else: logging.info("Keyboard listener thread joined.")
        super().closeEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self.mode == "min" and self.top_frame and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton: self._mouse_pressed = True; self._old_pos = event.globalPosition().toPoint(); event.accept(); return
        self._mouse_pressed = False; super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos; self.move(self.pos() + delta); self._old_pos = event.globalPosition().toPoint(); event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton: self._mouse_pressed = False; self._old_pos = None; event.accept()
        else: super().mouseReleaseEvent(event)

    def change_mode(self, mode_name: str):
        logging.info(f"--- Attempting to change mode to: {mode_name} (Current: {self.mode}) ---")
        if self.mode == mode_name: logging.info(f"Mode '{mode_name}' is already set."); return
        start_time = time.time()
        if self.mode in self.mode_positions and self.isVisible(): self.mode_positions[self.mode] = self.pos(); logging.info(f"Position saved for mode '{self.mode}': {self.mode_positions[self.mode]}")
        old_cursor_index = self.hotkey_cursor_index; self.hotkey_cursor_index = -1
        if self.right_list_widget and self.right_list_widget.isVisible() and old_cursor_index >= 0:
            try: logging.debug("Updating viewport to remove old hotkey highlight."); self.right_list_widget.viewport().update()
            except Exception as e: logging.warning(f"Failed to update viewport for hotkey reset: {e}")
        self.mode_manager.change_mode(mode_name); self.mode = mode_name; logging.info(f"Mode set to '{self.mode}'")
        self._update_interface_for_mode()
        target_pos = self.mode_positions.get(self.mode)
        if target_pos and self.isVisible(): logging.info(f"Restoring position for mode '{self.mode}': {target_pos}"); self.move(target_pos)
        self._reset_hotkey_cursor_after_mode_change()
        end_time = time.time(); logging.info(f"--- Mode change to {mode_name} FINISHED (took: {end_time - start_time:.4f} sec) ---")

    def _update_interface_for_mode(self):
        t0 = time.time(); current_mode = self.mode
        logging.info(f"Updating interface for mode '{current_mode}'")
        current_selection_ids = set(self.logic.selected_heroes)
        logging.debug(f"Current logic selection (before UI update): {current_selection_ids}")
        t1 = time.time(); logging.debug("Clearing old panel widgets...")
        widgets_to_delete = []
        if self.left_panel_widget: widgets_to_delete.append(self.left_panel_widget)
        if self.right_panel_widget: widgets_to_delete.append(self.right_panel_widget)
        if self.inner_layout:
            for widget in widgets_to_delete: self.inner_layout.removeWidget(widget); widget.setParent(None); widget.deleteLater()
        else: logging.warning("inner_layout is None during cleanup")
        self.left_panel_widget = None; self.canvas = None; self.result_frame = None; self.result_label = None; self.update_scrollregion = lambda: None
        self.right_panel_widget = None; self.right_frame = None; self.selected_heroes_label = None; self.right_list_widget = None; self.hero_items.clear(); self.right_panel_instance = None
        logging.debug("Old panel widget references cleared."); t2 = time.time(); logging.debug(f"[TIMING] -> Clear/Detach old panels: {t2-t1:.4f} s")
        t1 = time.time()
        try: self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(current_mode)
        except Exception as e: logging.critical(f"Image loading error: {e}"); QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображения: {e}"); return
        logging.debug(f"Images loaded/retrieved for mode '{current_mode}'"); t2 = time.time(); logging.debug(f"[TIMING] -> Load/Get images: {t2-t1:.4f} s")
        t1 = time.time(); logging.debug("Creating left panel...")
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.main_widget)
        parent_widget = self.canvas.parentWidget()
        if isinstance(parent_widget, QFrame): self.left_panel_widget = parent_widget; self.left_panel_widget.setObjectName("left_panel_container_frame")
        else: logging.error(f"Left panel parent is not QFrame: {type(parent_widget)}"); self.left_panel_widget = self.canvas
        self.left_panel_widget.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('left', 0))
        self.inner_layout.addWidget(self.left_panel_widget, stretch=1); logging.debug(f"Left panel widget added to inner_layout."); t2 = time.time(); logging.debug(f"[TIMING] -> Create left panel: {t2-t1:.4f} s")
        t1 = time.time()
        if current_mode != "min":
            logging.debug("Creating right panel..."); self.right_panel_instance = RightPanel(self, current_mode)
            self.right_panel_widget = self.right_panel_instance.frame; self.right_panel_widget.setObjectName("right_panel_container_frame")
            self.right_frame = self.right_panel_instance.frame; self.selected_heroes_label = self.right_panel_instance.selected_heroes_label
            self.right_list_widget = self.right_panel_instance.list_widget; self.hero_items = self.right_panel_instance.hero_items
            if self.right_list_widget:
                logging.debug("Connecting signals and setting delegate for new right_list_widget");
                delegate_instance = delegate.HotkeyFocusDelegate(self); self.right_list_widget.setItemDelegate(delegate_instance)
                try: self.right_list_widget.itemSelectionChanged.disconnect()
                except RuntimeError: pass
                try: self.right_list_widget.customContextMenuRequested.disconnect()
                except RuntimeError: pass
                self.right_list_widget.itemSelectionChanged.connect(self.handle_selection_changed)
                self.right_list_widget.customContextMenuRequested.connect(self.show_priority_context_menu)
            else: logging.warning("right_list_widget is None after RightPanel creation.")
            self.right_panel_widget.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('right', 0))
            self.inner_layout.addWidget(self.right_panel_widget, stretch=1); logging.debug(f"Right panel widget added to inner_layout.")
            left_widget_for_stretch = self.left_panel_widget
            if left_widget_for_stretch: self.inner_layout.setStretchFactor(left_widget_for_stretch, 2)
            self.inner_layout.setStretchFactor(self.right_panel_widget, 1)
        else: logging.debug("Right panel skipped for 'min' mode.")
        t2 = time.time(); logging.debug(f"[TIMING] -> Create/Hide right panel: {t2-t1:.4f} s")

        t1 = time.time(); logging.debug("Configuring window flags and top panel visibility...")
        top_h = self.top_frame.sizeHint().height() if self.top_frame else 40
        horiz_size = SIZES.get(current_mode, {}).get('horizontal', (35,35)); h_icon_h = horiz_size[1]
        icons_h = h_icon_h + 12
        if self.icons_scroll_area: self.icons_scroll_area.setFixedHeight(icons_h); logging.debug(f"Icons scroll area height set to {icons_h}")
        spacing = self.main_layout.spacing() if self.main_layout else 0; base_h = top_h + icons_h + spacing
        self.setMinimumHeight(0); self.setMaximumHeight(16777215)
        is_min_mode = (current_mode == "min"); current_flags_before = self.windowFlags(); logging.debug(f"Window flags BEFORE update: {current_flags_before}")
        target_flags = Qt.WindowType(0); current_topmost_state = self._is_win_topmost
        if is_min_mode: target_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        else: target_flags = Qt.WindowType.Window
        if current_topmost_state: target_flags |= Qt.WindowType.WindowStaysOnTopHint
        logging.debug(f"Setting TARGET window flags: {target_flags} (current topmost state was {current_topmost_state})")
        self.setWindowFlags(target_flags); current_flags_after = self.windowFlags(); logging.debug(f"Window flags AFTER setWindowFlags: {current_flags_after}")
        lang_label = self.top_frame.findChild(QLabel, "language_label"); lang_combo = self.top_frame.findChild(QComboBox, "language_combo")
        version_label = self.top_frame.findChild(QLabel, "version_label"); close_button = self.top_frame.findChild(QPushButton, "close_button")
        if version_label: logging.debug(f"Version label found. Text: '{version_label.text()}', Visible: {version_label.isVisible()}")
        else: logging.warning("Version label not found in top_frame.")

        if is_min_mode:
            logging.debug("Setting up MIN mode UI specifics...")
            if lang_label: lang_label.hide()
            if lang_combo: lang_combo.hide()
            if version_label: version_label.hide(); logging.debug("Hiding version label in MIN mode")
            if self.author_button: self.author_button.hide()
            if self.rating_button: self.rating_button.hide()
            if close_button: close_button.show()
            self.setWindowTitle(""); calculated_fixed_min_height = base_h + 5; self.setMinimumHeight(calculated_fixed_min_height); self.setMaximumHeight(calculated_fixed_min_height); logging.debug(f"Set fixed height: {calculated_fixed_min_height}")
            if self.left_panel_widget: self.left_panel_widget.hide()
            if self.icons_scroll_area: self.icons_scroll_area.show()
        else:
            logging.debug(f"Setting up {current_mode.upper()} mode UI specifics...")
            if lang_label: lang_label.show()
            if lang_combo: lang_combo.show()
            if version_label: version_label.show(); logging.debug(f"Showing version label in {current_mode.upper()} mode")
            if close_button: close_button.hide()
            self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
            if self.left_panel_widget: self.left_panel_widget.show()
            if self.icons_scroll_area: self.icons_scroll_area.show()
            if current_mode == "max":
                calculated_min_h = base_h + 300; self.setMinimumHeight(calculated_min_h); logging.debug(f"Set min height for max mode: {calculated_min_h}")
                if self.author_button: self.author_button.show()
                if self.rating_button: self.rating_button.show()
            else: # middle
                calculated_min_h = base_h + 200; self.setMinimumHeight(calculated_min_h); logging.debug(f"Set min height for middle mode: {calculated_min_h}")
                if self.author_button: self.author_button.hide()
                if self.rating_button: self.rating_button.hide()
        logging.info("Calling window.show() after updating flags and UI visibility.")
        self.show(); t2 = time.time(); logging.debug(f"[TIMING] -> Setup window flags/visibility: {t2-t1:.4f} s")

        t1 = time.time(); self.update_language(); self.main_layout.activate()
        if self.inner_layout: self.inner_layout.activate()
        self.updateGeometry(); t2 = time.time(); logging.debug(f"[TIMING] -> Update language/layout/geometry: {t2-t1:.4f} s")

        t1 = time.time(); target_size = MODE_DEFAULT_WINDOW_SIZES.get(current_mode, {'width': 800, 'height': 600})
        target_w = target_size['width']; target_h = target_size['height']; min_w = self.minimumSizeHint().width(); actual_min_h = self.minimumHeight()
        if current_mode == 'min': final_w = max(target_w, min_w); final_h = self.minimumHeight()
        else: final_w = max(target_w, min_w); final_h = max(target_h, actual_min_h)
        logging.debug(f"Resizing window to: {final_w}x{final_h}"); self.resize(final_w, final_h); t2 = time.time(); logging.debug(f"[TIMING] -> Resize window: {t2-t1:.4f} s")

        t1 = time.time(); logging.info("Updating UI state after mode change...")
        self.update_ui_after_logic_change()
        logging.debug(f"Restoring selection state to UI. Logic selection: {current_selection_ids}")
        if self.right_list_widget:
            QTimer.singleShot(50, lambda: self._update_list_item_selection_states(force_update=True))
            logging.debug("Scheduled _update_list_item_selection_states with force_update=True after 50ms delay.")
        else: logging.debug("Right list widget not available, skipping selection state restoration.")
        t2 = time.time(); logging.info(f"[TIMING] -> Restore UI state (scheduling selection): {t2-t1:.4f} s")

        t_end = time.time(); logging.info(f"[TIMING] _update_interface_for_mode: Finished (Total: {t_end - t0:.4f} s)")

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
        if not hasattr(self, 'win_api_manager'): logging.warning("win_api_manager not found."); return False
        return self.win_api_manager.is_win_topmost

    def set_topmost_winapi(self, enable: bool):
        if hasattr(self, 'win_api_manager'): self.win_api_manager.set_topmost_winapi(enable)
        else: logging.warning("win_api_manager not found.")

    def toggle_topmost_winapi(self):
        if hasattr(self, 'win_api_manager'): self.win_api_manager.set_topmost_winapi(not self.win_api_manager.is_win_topmost)
        else: logging.warning("win_api_manager not found.")

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
                if new_index < 0: last_row_index = (count - 1) // num_columns; potential_index = last_row_index * num_columns + current_col; new_index = min(potential_index, count - 1)
            elif direction == 'down':
                new_index += num_columns
                if new_index >= count: potential_index = current_col; new_index = min(potential_index, count - 1);
                if new_index >= count : new_index = 0
            new_index = max(0, min(count - 1, new_index))
        if old_index != new_index:
            self.hotkey_cursor_index = new_index; self._update_hotkey_highlight(old_index=old_index); logging.debug(f"Cursor moved to index {new_index}")
        elif 0 <= self.hotkey_cursor_index < count:
             current_item = list_widget.item(self.hotkey_cursor_index)
             if current_item: list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)

    @Slot()
    def _handle_toggle_selection(self):
        logging.debug("[GUI Slot] _handle_toggle_selection triggered")
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min' or self.hotkey_cursor_index < 0:
            logging.debug(f"Toggle selection ignored (list: {list_widget is not None}, visible: {list_widget.isVisible() if list_widget else 'N/A'}, mode: {self.mode}, index: {self.hotkey_cursor_index})")
            return
        if 0 <= self.hotkey_cursor_index < list_widget.count():
            item = list_widget.item(self.hotkey_cursor_index)
            if item:
                try:
                    is_selected = item.isSelected()
                    new_state = not is_selected
                    logging.debug(f"Toggling selection for item {self.hotkey_cursor_index} ('{item.data(HERO_NAME_ROLE)}'). State: {is_selected} -> {new_state}")
                    item.setSelected(new_state)
                except RuntimeError:
                    logging.warning(f"RuntimeError accessing item during toggle selection (index {self.hotkey_cursor_index}). Might be deleting.")
                except Exception as e:
                    logging.error(f"Error toggling selection via hotkey: {e}", exc_info=True)
            else:
                logging.warning(f"Item at index {self.hotkey_cursor_index} is None.")
        else:
            logging.warning(f"Invalid hotkey cursor index: {self.hotkey_cursor_index}")

    @Slot()
    def _handle_toggle_mode(self):
        logging.info("[GUI Slot] _handle_toggle_mode triggered");
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

    def update_ui_after_logic_change(self):
        logging.info("Updating UI after logic change."); start_time = time.time()
        self._update_selected_label(); self._update_counterpick_display(); update_horizontal_icon_list(self)
        self._update_list_item_selection_states()
        self._update_priority_labels()
        end_time = time.time(); logging.info(f"UI Update Finished in {end_time - start_time:.4f} sec.")

    def _update_selected_label(self):
        label_to_update = self.selected_heroes_label
        if label_to_update:
             try: label_to_update.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass
             except Exception as e: logging.error(f"Error updating selected label: {e}")

    def _update_counterpick_display(self):
        if not self.result_frame or not self.canvas: logging.warning("result_frame or canvas not found"); return
        images_ok = bool(self.left_images) and (self.mode == 'min' or bool(self.small_images))
        if not images_ok:
             logging.warning(f"Images not loaded for mode '{self.mode}'. Attempting reload.")
             try: _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
             except Exception as e: logging.error(f"Error reloading images: {e}"); return
        try:
            if self.mode != "min": display.generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)
            else: display.generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
            if self.update_scrollregion: QTimer.singleShot(0, self.update_scrollregion)
        except RuntimeError as e: logging.error(f"RuntimeError during display generation: {e}")
        except Exception as e: logging.error(f"Error generating display: {e}"); import traceback; traceback.print_exc()

    def _update_list_item_selection_states(self, force_update=False):
        list_widget = self.right_list_widget; hero_items_dict = self.hero_items
        if not list_widget or not list_widget.isVisible(): logging.debug("Skipping selection state update (no list widget or not visible)"); return
        if not hero_items_dict or list_widget.count() == 0 or list_widget.count() != len(hero_items_dict):
             logging.warning(f"Selection state update skipped: mismatch or empty (list:{list_widget.count()} vs dict:{len(hero_items_dict)})")
             return
        logging.info(f"Updating list item selection states... (force_update={force_update})")
        self.is_programmatically_updating_selection = True; items_changed_count = 0
        try:
            list_widget.blockSignals(True); current_logic_selection = set(self.logic.selected_heroes)
            logging.debug(f"Applying logic selection to UI: {current_logic_selection}"); items_to_check = list(hero_items_dict.items())
            for hero, item in items_to_check:
                if item is None: logging.warning(f"Item for hero '{hero}' is None"); continue
                try:
                    is_currently_selected_in_widget = item.isSelected(); should_be_selected_in_logic = (hero in current_logic_selection)
                    if is_currently_selected_in_widget != should_be_selected_in_logic or force_update:
                        if force_update and is_currently_selected_in_widget == should_be_selected_in_logic: logging.debug(f"Forcing selection update for '{hero}': state {should_be_selected_in_logic}")
                        else: logging.debug(f"Updating selection for '{hero}': widget={is_currently_selected_in_widget}, logic={should_be_selected_in_logic} -> Setting selected to {should_be_selected_in_logic}")
                        item.setSelected(should_be_selected_in_logic); items_changed_count += 1
                except RuntimeError: logging.warning(f"RuntimeError accessing item for hero '{hero}'"); continue
                except Exception as e: logging.error(f"Error updating selection state for hero '{hero}': {e}")
            logging.debug(f"Items whose selection state was changed/forced: {items_changed_count}")
            self._update_selected_label()
            if list_widget and list_widget.viewport(): logging.debug("Calling list_widget.viewport().update() immediately after loop."); list_widget.viewport().update()
            # QTimer.singleShot(0, lambda: list_widget.viewport().update() if list_widget and list_widget.viewport() else None)
        except Exception as e: logging.error(f"Unexpected error in _update_list_item_selection_states: {e}", exc_info=True)
        finally:
            try:
                if list_widget: list_widget.blockSignals(False)
            except RuntimeError: pass
            self.is_programmatically_updating_selection = False
        logging.info("Finished updating list item selection states.")

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
            self.logic.set_selection(current_ui_selection_names); self.update_ui_after_logic_change()
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
        if self.right_panel_instance:
            self.right_panel_instance.update_language()
            list_widget = self.right_list_widget; hero_items_dict = self.hero_items
            if list_widget and list_widget.isVisible():
                 focused_tooltip_base = None; current_focused_item = None
                 if 0 <= self.hotkey_cursor_index < list_widget.count():
                      # <<< ИСПРАВЛЕНО: SyntaxError, блок try/except завершен >>>
                      try:
                          current_focused_item = list_widget.item(self.hotkey_cursor_index)
                          if current_focused_item:
                              focused_tooltip_base = current_focused_item.data(HERO_NAME_ROLE)
                      except RuntimeError:
                          logging.warning(f"RuntimeError getting focused item ({self.hotkey_cursor_index})")
                          pass # Игнорируем ошибку, если виджет удален
                      # <<< -------------------------------------------------- >>>
                 for hero, item in hero_items_dict.items():
                      if item is None: continue
                      try: item_text = hero if self.mode == "max" else ""; item.setText(item_text); item.setToolTip(hero)
                      except RuntimeError: continue
                 # Восстанавливаем тултип фокуса, если он был
                 if focused_tooltip_base and current_focused_item:
                     try: current_focused_item.setToolTip(f">>> {focused_tooltip_base} <<<")
                     except RuntimeError: pass
        if self.result_label and not self.logic.selected_heroes: self.result_label.setText(get_text('no_heroes_selected', language=current_lang))
        logging.info("Language update finished.")

    def _calculate_columns(self) -> int:
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': self._num_columns_cache = 1; return 1
        try:
            viewport = list_widget.viewport();
            if not viewport: return self._num_columns_cache
            vp_width = viewport.width(); grid_size = list_widget.gridSize(); spacing = list_widget.spacing()
            if grid_size.width() <= 0: return self._num_columns_cache
            effective_grid_width = grid_size.width() + spacing
            if effective_grid_width <= 0: return self._num_columns_cache
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
                if old_item: hero_name = old_item.data(HERO_NAME_ROLE); current_tooltip = old_item.toolTip()
                if hero_name and current_tooltip and current_tooltip.startswith(">>>"): old_item.setToolTip(hero_name)
                self._update_priority_labels(); needs_viewport_update = True
            except RuntimeError: pass
            except Exception as e: logging.error(f"Error restoring old item state (idx {old_index}): {e}")
        if 0 <= new_index < count:
            try:
                new_item = list_widget.item(new_index)
                if new_item: hero_name = new_item.data(HERO_NAME_ROLE); focus_tooltip = f">>> {hero_name} <<<"
                if hero_name and new_item.toolTip() != focus_tooltip: new_item.setToolTip(focus_tooltip)
                self._update_priority_labels()
                list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
                needs_viewport_update = True
            except RuntimeError: pass
            except Exception as e: logging.error(f"Error setting new item state/scrolling (idx {new_index}): {e}")
        if list_widget.viewport() and needs_viewport_update:
             logging.debug("Scheduling viewport update for hotkey highlight")
             QTimer.singleShot(0, lambda: list_widget.viewport().update() if list_widget and list_widget.viewport() else None)

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
        hotkeys_map = {
            'tab+up': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+up -> Signal Emit"), self.move_cursor_signal.emit('up')), True),
            'tab+down': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+down -> Signal Emit"), self.move_cursor_signal.emit('down')), True),
            'tab+left': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+left -> Signal Emit"), self.move_cursor_signal.emit('left')), True),
            'tab+right': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+right -> Signal Emit"), self.move_cursor_signal.emit('right')), True),
            'tab+num 0': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+num 0 -> Signal Emit"), self.toggle_selection_signal.emit()), True),
            'tab+keypad 0': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+keypad 0 -> Signal Emit"), self.toggle_selection_signal.emit()), True),
            'tab+num -': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+num - -> Signal Emit"), self.clear_all_signal.emit()), True),
            'tab+keypad -': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+keypad - -> Signal Emit"), self.clear_all_signal.emit()), True),
            'tab+-': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+- -> Signal Emit"), self.clear_all_signal.emit()), True),
            'tab+delete': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+delete -> Signal Emit"), self.toggle_mode_signal.emit()), True),
            'tab+del': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+del -> Signal Emit"), self.toggle_mode_signal.emit()), True),
            'tab+.': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+. -> Signal Emit"), self.toggle_mode_signal.emit()), True),
            'tab+num /': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+num / -> Signal Emit"), self.recognize_heroes_signal.emit()), True),
            'tab+keypad /': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+keypad / -> Signal Emit"), self.recognize_heroes_signal.emit()), True),
            'tab+/': (lambda: (logging.debug("[Hotkey Listener] Hook triggered: tab+/ -> Signal Emit"), self.recognize_heroes_signal.emit()), True),
        }
        hooks_registered_count = 0
        try:
            logging.info(f"Registering hooks...")
            for hotkey, (callback, suppress_flag) in hotkeys_map.items():
                try: keyboard.add_hotkey(hotkey, callback, suppress=suppress_flag, trigger_on_release=False); hooks_registered_count += 1
                except ValueError as e: logging.warning(f"Hook registration failed for '{hotkey}' (ValueError): {e}")
                except Exception as e: logging.error(f"Hook registration failed for '{hotkey}': {e}")
            logging.info(f"Hooks registered: {hooks_registered_count}/{len(hotkeys_map)}")
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
            if self.hotkey_cursor_index != old_index or old_index != -1: self._update_hotkey_highlight(old_index)
            if self.hotkey_cursor_index == 0:
                first_item = list_widget.item(0)
                if first_item: list_widget.scrollToItem(first_item, QAbstractItemView.ScrollHint.EnsureVisible)
         else: self.hotkey_cursor_index = -1
