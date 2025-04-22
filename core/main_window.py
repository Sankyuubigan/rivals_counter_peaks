# File: core/main_window.py
import sys
import time
import threading
import os

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout,
                               QMessageBox, QApplication, QScrollArea, QAbstractItemView, QMenu, QLabel, QPushButton, QComboBox)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QPoint, QModelIndex
from PySide6.QtGui import QIcon, QMouseEvent, QColor, QBrush

# <<< ИСПРАВЛЕНО: Используем абсолютные импорты от core или корня >>>
import translations
import utils_gui
import logic
import mode_manager
import win_api
import recognition
import images_load
import top_panel
import left_panel
import right_panel
import horizontal_list
import display
# <<< ----------------------------------------------------------- >>>

# Импортируем конкретные классы/функции для удобства
from translations import get_text, set_language, SUPPORTED_LANGUAGES
from utils_gui import copy_to_clipboard
from logic import CounterpickLogic, TEAM_SIZE
from mode_manager import ModeManager, PANEL_MIN_WIDTHS, MODE_DEFAULT_WINDOW_SIZES
from win_api import WinApiManager, user32 as winapi_user32
from recognition import RecognitionManager, RecognitionWorker
from images_load import load_original_images, get_images_for_mode, SIZES, load_default_pixmap
from top_panel import TopPanel
from left_panel import LeftPanel, create_left_panel
from right_panel import RightPanel, HERO_NAME_ROLE # Импортируем create_right_panel не нужно, используем класс
from horizontal_list import update_horizontal_icon_list
from display import generate_counterpick_display, generate_minimal_icon_list
# heroes_bd импортируется там, где нужен

try:
    import keyboard
except ImportError:
    print("[ERROR] Библиотека 'keyboard' не найдена. Установите ее: pip install keyboard")
    keyboard = None


class MainWindow(QMainWindow):
    # Сигналы
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()
    toggle_mode_signal = Signal()
    clear_all_signal = Signal()
    recognize_heroes_signal = Signal()
    recognition_complete_signal = Signal(list)

    def __init__(self, logic_instance: CounterpickLogic, hero_templates_dict: dict): # Используем более конкретные типы
        super().__init__()
        print("[LOG] MainWindow.__init__ started")

        # Основные компоненты
        self.logic = logic_instance
        self.hero_templates = hero_templates_dict
        self.app_version = os.environ.get("APP_VERSION", "N/A")

        # Менеджеры
        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)

        # Состояние UI
        self.mode = self.mode_manager.current_mode
        self.initial_pos = self.pos()
        self.mode_positions = self.mode_manager.mode_positions
        self.mode_positions["middle"] = self.initial_pos
        self.is_programmatically_updating_selection = False

        # Атрибуты UI
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_panel_instance: TopPanel | None = None
        self.left_panel_instance: LeftPanel | None = None
        self.right_panel_instance: RightPanel | None = None
        self.top_frame = None
        self.author_button = None
        self.rating_button = None
        self.icons_scroll_area: QScrollArea | None = None
        self.icons_scroll_content = None
        self.icons_scroll_content_layout = None
        self.canvas = None
        self.result_frame = None
        self.result_label = None
        self.update_scrollregion = lambda: None
        self.right_list_widget = None
        self.selected_heroes_label = None
        self.hero_items = {}

        # Hotkeys
        self.hotkey_cursor_index = -1
        self._num_columns_cache = 1
        self._keyboard_listener_thread = None
        self._stop_keyboard_listener_flag = threading.Event()

        # Распознавание
        self._recognition_thread = None
        self._recognition_worker = None

        # Настройка окна
        self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
        icon_pixmap = load_default_pixmap((32,32))
        if not icon_pixmap.isNull(): self.setWindowIcon(QIcon(icon_pixmap))
        self.setGeometry(100, 100, 950, 350)
        self.setMinimumSize(400, 100)

        # Создание UI
        self._create_main_ui_layout() # <<< ВОССТАНОВЛЕН вызов этого метода
        self._update_interface_for_mode()

        # Подключение сигналов
        self._connect_signals()

        # Запуск слушателя хоткеев
        if keyboard: self.start_keyboard_listener()
        else: print("[WARN] Библиотека keyboard не найдена, горячие клавиши не будут работать.")

        print("[LOG] MainWindow.__init__ finished")

    # --- Создание и настройка UI ---
    # <<< ВОССТАНОВЛЕН МЕТОД >>>
    def _create_main_ui_layout(self):
        """Создает базовую структуру виджетов и layout'ов окна."""
        print("[LOG] MainWindow._create_main_ui_layout() started")
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        # Верхняя панель
        self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
        self.top_frame = self.top_panel_instance.top_frame
        self.author_button = self.top_panel_instance.author_button
        self.rating_button = self.top_panel_instance.rating_button
        self.main_layout.addWidget(self.top_frame)

        # Горизонтальный список иконок
        self._create_icons_scroll_area()
        self.main_layout.addWidget(self.icons_scroll_area)

        # Контейнер для левой и правой панелей
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
        self.inner_layout.setContentsMargins(0, 0, 0, 0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1)
        print("[LOG] MainWindow._create_main_ui_layout() finished")
    # <<< ------------------- >>>

    # _create_icons_scroll_area остается как есть
    # _connect_signals остается как есть

    # --- Обработка событий окна ---
    # closeEvent, mousePress/Move/ReleaseEvent остаются без изменений

    # --- Управление режимами окна ---
    def change_mode(self, mode_name: str):
        """Слот для изменения режима отображения (вызывается из TopPanel)."""
        print(f"--- Попытка смены режима на: {mode_name} (в MainWindow) ---")
        if self.mode == mode_name:
            print(f"Режим '{mode_name}' уже установлен.")
            return

        start_time = time.time()
        # 1. Сохраняем позицию
        if self.mode in self.mode_positions and self.isVisible():
            self.mode_positions[self.mode] = self.pos()
            print(f"Позиция для режима '{self.mode}' сохранена: {self.mode_positions[self.mode]}")

        # 2. Сбрасываем фокус хоткея
        old_cursor_index = self.hotkey_cursor_index
        self.hotkey_cursor_index = -1
        if self.right_list_widget and self.right_list_widget.isVisible() and old_cursor_index >= 0:
            self._update_hotkey_highlight(old_cursor_index)

        # 3. Устанавливаем новый режим
        self.mode_manager.change_mode(mode_name)
        self.mode = mode_name

        # 4. Перестройка интерфейса
        self._update_interface_for_mode()

        # 5. Восстанавливаем позицию окна
        target_pos = self.mode_positions.get(self.mode)
        if target_pos and self.isVisible():
            print(f"Восстановление позиции для режима '{self.mode}': {target_pos}")
            self.move(target_pos)

        # 6. Восстанавливаем фокус хоткея
        QTimer.singleShot(150, self._reset_hotkey_cursor_after_mode_change)

        end_time = time.time()
        print(f"--- Смена режима на {mode_name} ЗАВЕРШЕНА (в MainWindow) (заняло: {end_time - start_time:.4f} сек) ---")

    # Метод _update_interface_for_mode остается здесь
    # Метод _reset_hotkey_cursor_after_mode_change остается здесь

    # --- Управление Topmost ---
    # @property _is_win_topmost, set_topmost_winapi, toggle_topmost_winapi остаются здесь

    # --- Обработка сигналов хоткеев ---
    # _handle_move_cursor, _handle_toggle_selection, _handle_toggle_mode,
    # _handle_clear_all, _reset_hotkey_cursor_after_clear остаются здесь

    # --- Обработка сигналов распознавания ---
    # _on_recognition_complete, _on_recognition_error остаются здесь

    # --- Обновление UI ---
    # update_ui_after_logic_change, _update_selected_label, _update_counterpick_display,
    # _update_list_item_selection_states, _update_priority_labels остаются здесь

    # --- Обработчики событий UI ---
    # handle_selection_changed, show_priority_context_menu остаются здесь

    # --- Язык ---
    # switch_language остается здесь
    # <<< ВОССТАНОВЛЕН МЕТОД update_language >>>
    def update_language(self):
        """Обновляет тексты всех элементов интерфейса."""
        print("[LOG] update_language called")
        current_lang = self.logic.DEFAULT_LANGUAGE
        self.setWindowTitle(f"{get_text('title', language=current_lang)} v{self.app_version}")

        # Обновляем TopPanel
        if self.top_panel_instance:
            self.top_panel_instance.update_language()

        # Обновляем RightPanel (если она есть)
        if self.right_panel_instance:
            self.right_panel_instance.update_language()

        # Обновляем LeftPanel (result_label)
        # result_label теперь атрибут MainWindow, а не left_panel_instance
        if self.result_label and not self.logic.selected_heroes:
             self.result_label.setText(get_text('no_heroes_selected', language=current_lang))

        # Обновляем подсказки в QListWidget
        list_widget = self.right_list_widget # Используем атрибут MainWindow
        hero_items_dict = self.hero_items # Используем атрибут MainWindow
        if list_widget and list_widget.isVisible():
            focused_tooltip = None
            if 0 <= self.hotkey_cursor_index < list_widget.count():
                 try:
                     focused_item = list_widget.item(self.hotkey_cursor_index)
                     if focused_item: focused_tooltip = focused_item.toolTip()
                 except RuntimeError: pass

            for hero, item in hero_items_dict.items():
                 if item is None: continue
                 try:
                     # Обновляем текст элемента в зависимости от режима
                     item_text = hero if self.mode == "max" else ""
                     if item.text() != item_text: item.setText(item_text)
                     # Обновляем базовую подсказку
                     item.setToolTip(hero)
                 except RuntimeError: continue

            if focused_tooltip and ">>>" in focused_tooltip and 0 <= self.hotkey_cursor_index < list_widget.count():
                try:
                    current_focused_item = list_widget.item(self.hotkey_cursor_index)
                    if current_focused_item: current_focused_item.setToolTip(focused_tooltip)
                except RuntimeError: pass
    # <<< --------------------------------- >>>


    # --- Утилиты UI ---
    # _calculate_columns, _update_hotkey_highlight остаются здесь

    # --- Управление слушателем клавиатуры ---
    # start_keyboard_listener, stop_keyboard_listener, _keyboard_listener_loop остаются здесь

    # --- Копирование в буфер обмена ---
    # copy_to_clipboard остается здесь

    # --- Явно скопируем код _update_interface_for_mode и др. ---
    def _update_interface_for_mode(self):
        t0 = time.time()
        current_mode = self.mode
        print(f"[TIMING] _update_interface_for_mode: Start for mode '{current_mode}'")
        t1 = time.time()
        if self.inner_layout: self.mode_manager.clear_layout_recursive(self.inner_layout)
        else:
            if self.main_widget:
                 self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
                 self.inner_layout.setContentsMargins(0,0,0,0); self.inner_layout.setSpacing(0)
            else: print("[!] КРИТИЧЕСКАЯ ОШИБКА: main_widget не найден."); return
        t2 = time.time(); # print(f"[TIMING] -> Clear inner_layout: {t2-t1:.4f} s")
        self.left_panel_instance = None; self.canvas = None; self.result_frame = None; self.result_label = None
        self.right_panel_instance = None; self.right_frame = None; self.selected_heroes_label = None; self.right_list_widget = None
        self.hero_items.clear()
        t1 = time.time()
        try: self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(current_mode)
        except Exception as e: print(f"Критическая ошибка загрузки изображений для режима {current_mode}: {e}"); return
        t2 = time.time(); # print(f"[TIMING] -> Load/Get images: {t2-t1:.4f} s")
        t1 = time.time()
        # <<< ИЗМЕНЕНО: create_left_panel теперь импортирован и используется >>>
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.main_widget)
        self.left_frame = self.canvas.parentWidget() # Получаем QFrame контейнер
        self.left_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('left', 0))
        self.inner_layout.addWidget(self.left_frame, stretch=1)
        t2 = time.time(); # print(f"[TIMING] -> Create left panel: {t2-t1:.4f} s")
        t1 = time.time()
        if current_mode != "min":
            # <<< ИЗМЕНЕНО: Используем класс RightPanel напрямую >>>
            self.right_panel_instance = RightPanel(self, current_mode)
            self.right_frame = self.right_panel_instance.frame
            self.selected_heroes_label = self.right_panel_instance.selected_heroes_label
            self.right_list_widget = self.right_panel_instance.list_widget
            self.hero_items = self.right_panel_instance.hero_items
            self.right_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('right', 0))
            self.inner_layout.addWidget(self.right_frame, stretch=1)
            self.inner_layout.setStretch(0, 2); self.inner_layout.setStretch(1, 1)
        else: pass
        t2 = time.time(); # print(f"[TIMING] -> Create/Hide right panel: {t2-t1:.4f} s")
        t1 = time.time()
        top_h = self.top_frame.sizeHint().height() if self.top_frame else 40
        horiz_size = SIZES.get(current_mode, {}).get('horizontal')
        h_icon_h = horiz_size[1] if horiz_size else 30
        icons_h = h_icon_h + 12
        self.icons_scroll_area.setFixedHeight(icons_h)
        spacing = self.main_layout.spacing() if self.main_layout else 0
        base_h = top_h + icons_h + spacing
        self.setMinimumHeight(0); self.setMaximumHeight(16777215)
        is_min_mode = (current_mode == "min")
        current_flags = self.windowFlags()
        frameless_changed = False
        lang_label = self.top_frame.findChild(QLabel, "language_label")
        lang_combo = self.top_frame.findChild(QComboBox, "language_combo")
        version_label = self.top_frame.findChild(QLabel, "version_label")
        close_button = self.top_frame.findChild(QPushButton, "close_button")
        if is_min_mode:
            if not (current_flags & Qt.WindowType.FramelessWindowHint): self.setWindowFlags(current_flags | Qt.WindowType.FramelessWindowHint); frameless_changed = True
            if lang_label: lang_label.hide()
            if lang_combo: lang_combo.hide()
            if version_label: version_label.hide()
            if self.author_button: self.author_button.hide()
            if self.rating_button: self.rating_button.hide()
            if close_button: close_button.show()
            self.setWindowTitle("")
            calculated_fixed_min_height = base_h + 5
            self.setMinimumHeight(calculated_fixed_min_height); self.setMaximumHeight(calculated_fixed_min_height)
        else:
            if current_flags & Qt.WindowType.FramelessWindowHint: self.setWindowFlags(current_flags & ~Qt.WindowType.FramelessWindowHint); frameless_changed = True
            if lang_label: lang_label.show()
            if lang_combo: lang_combo.show()
            if version_label: version_label.show()
            if close_button: close_button.hide()
            self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
            if current_mode == "max":
                calculated_min_h = base_h + 300; self.setMinimumHeight(calculated_min_h)
                if self.author_button: self.author_button.show()
                if self.rating_button: self.rating_button.show()
            else: # middle
                calculated_min_h = base_h + 200; self.setMinimumHeight(calculated_min_h)
                if self.author_button: self.author_button.hide()
                if self.rating_button: self.rating_button.hide()
        if frameless_changed: print("[LOG] Frameless flag changed, calling window.show()"); self.show()
        t2 = time.time(); # print(f"[TIMING] -> Setup window flags/visibility: {t2-t1:.4f} s")
        t1 = time.time()
        self.update_language() # <<< ВЫЗОВ update_language ПЕРЕМЕЩЕН СЮДА >>>
        self.main_layout.activate()
        if self.inner_layout: self.inner_layout.activate()
        self.updateGeometry()
        t2 = time.time(); # print(f"[TIMING] -> Update language/layout/geometry: {t2-t1:.4f} s")
        t1 = time.time()
        target_size = MODE_DEFAULT_WINDOW_SIZES.get(current_mode, {'width': 800, 'height': 600})
        target_w = target_size['width']; target_h = target_size['height']
        min_w = self.minimumSizeHint().width(); actual_min_h = self.minimumHeight()
        if current_mode == 'min': final_w = max(target_w, min_w); final_h = self.minimumHeight(); self.resize(final_w, final_h)
        else: final_w = max(target_w, min_w); final_h = max(target_h, actual_min_h); self.resize(final_w, final_h)
        t2 = time.time(); # print(f"[TIMING] -> Resize window: {t2-t1:.4f} s")
        t1 = time.time()
        self.update_ui_after_logic_change()
        t2 = time.time(); # print(f"[TIMING] -> Restore UI state: {t2-t1:.4f} s")
        t_end = time.time()
        print(f"[TIMING] _update_interface_for_mode: Finished (Total: {t_end - t0:.4f} s)")

    # --- Остальные методы (без изменений) ---
    def _reset_hotkey_cursor_after_mode_change(self):
        print("[LOG] _reset_hotkey_cursor_after_mode_change called")
        list_widget = self.right_list_widget
        if list_widget and list_widget.isVisible() and self.mode != 'min':
            count = list_widget.count()
            if count > 0:
                self.hotkey_cursor_index = 0
                self._calculate_columns()
                self._update_hotkey_highlight(None)
                print(f"[Hotkey] Cursor reset to index 0 in mode {self.mode}")
            else: self.hotkey_cursor_index = -1; print(f"[Hotkey] List is empty, cursor set to -1 in mode {self.mode}")
        else:
            self.hotkey_cursor_index = -1
            list_visible_status = list_widget.isVisible() if list_widget else 'No list'
            print(f"[Hotkey] Cursor set to -1 (mode: {self.mode}, list visible: {list_visible_status})")

    @property
    def _is_win_topmost(self): return self.win_api_manager.is_win_topmost
    def set_topmost_winapi(self, enable: bool): self.win_api_manager.set_topmost_winapi(enable)
    def toggle_topmost_winapi(self): self.win_api_manager.set_topmost_winapi(not self.win_api_manager.is_win_topmost)

    @Slot(str)
    def _handle_move_cursor(self, direction):
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': return
        count = list_widget.count()
        if count == 0: return
        old_index = self.hotkey_cursor_index
        num_columns = self._calculate_columns()
        if self.hotkey_cursor_index < 0: new_index = 0
        else:
            current_row = self.hotkey_cursor_index // num_columns; current_col = self.hotkey_cursor_index % num_columns
            new_index = self.hotkey_cursor_index
            if direction == 'left':
                if current_col > 0: new_index -= 1
                elif current_row > 0: new_index = (current_row - 1) * num_columns + (num_columns - 1); new_index = min(new_index, count - 1)
                else: new_index = count - 1
            elif direction == 'right':
                if current_col < num_columns - 1: new_index += 1
                elif self.hotkey_cursor_index < count - 1: new_index = (current_row + 1) * num_columns
                else: new_index = 0
                new_index = min(new_index, count - 1)
            elif direction == 'up':
                new_index -= num_columns
                if new_index < 0:
                     last_row_start_index = (count - 1) - ((count - 1) % num_columns)
                     potential_index = last_row_start_index + current_col
                     new_index = min(potential_index, count - 1)
            elif direction == 'down':
                new_index += num_columns
                if new_index >= count:
                     new_index = current_col
                     if new_index >= count: new_index = 0
            new_index = max(0, min(count - 1, new_index))
        if old_index != new_index:
            self.hotkey_cursor_index = new_index
            self._update_hotkey_highlight(old_index)
        elif 0 <= self.hotkey_cursor_index < count:
             current_item = list_widget.item(self.hotkey_cursor_index)
             if current_item: list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)

    @Slot()
    def _handle_toggle_selection(self):
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': return
        if 0 <= self.hotkey_cursor_index < list_widget.count():
            item = list_widget.item(self.hotkey_cursor_index)
            if item:
                try: item.setSelected(not item.isSelected())
                except Exception as e: print(f"[ERROR] Error toggling selection: {e}")

    @Slot()
    def _handle_toggle_mode(self):
        print("[LOG] _handle_toggle_mode called")
        target_mode = "middle" if self.mode == "min" else "min"
        self.change_mode(target_mode)

    @Slot()
    def _handle_clear_all(self):
        print("[LOG] _handle_clear_all called")
        self.logic.clear_all()
        self.update_ui_after_logic_change()
        self._reset_hotkey_cursor_after_clear()

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes):
        print(f"[RESULT] Распознавание завершено в MainWindow. Распознанные герои: {recognized_heroes}")
        if recognized_heroes:
            self.logic.set_selection(set(recognized_heroes))
            self.update_ui_after_logic_change()
        else:
            print("[INFO] Герои не распознаны или список пуст.")
            QMessageBox.information(self, "Распознавание", get_text('recognition_failed', language=self.logic.DEFAULT_LANGUAGE))

    @Slot(str)
    def _on_recognition_error(self, error_message):
        print(f"[ERROR] Ошибка во время распознавания в MainWindow: {error_message}")
        QMessageBox.warning(self, get_text('error', language=self.logic.DEFAULT_LANGUAGE),
                            f"{get_text('recognition_error_prefix', language=self.logic.DEFAULT_LANGUAGE)}\n{error_message}")

    def update_ui_after_logic_change(self):
        print("[UI Update] Started after logic change.")
        start_time = time.time()
        self._update_selected_label()
        self._update_counterpick_display()
        update_horizontal_icon_list(self)
        self._update_list_item_selection_states()
        self._update_priority_labels()
        end_time = time.time()
        print(f"[UI Update] Finished in {end_time - start_time:.4f} sec.")

    def handle_selection_changed(self):
        if self.is_programmatically_updating_selection: return
        list_widget = self.right_list_widget
        if not list_widget: return
        print("[UI Event] Selection changed by user.")
        current_ui_selection_names = set()
        for item in list_widget.selectedItems():
            hero_name = item.data(HERO_NAME_ROLE);
            if hero_name: current_ui_selection_names.add(hero_name)
        if set(self.logic.selected_heroes) != current_ui_selection_names:
            self.logic.set_selection(current_ui_selection_names)
            self.update_ui_after_logic_change()

    def show_priority_context_menu(self, pos):
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible(): return
        item = list_widget.itemAt(pos)
        if not item: return
        hero_name = item.data(HERO_NAME_ROLE)
        if not hero_name: return
        global_pos = list_widget.viewport().mapToGlobal(pos)
        menu = QMenu(self)
        is_priority = hero_name in self.logic.priority_heroes
        is_selected = item.isSelected()
        action_text = get_text('remove_priority', language=self.logic.DEFAULT_LANGUAGE) if is_priority else get_text('set_priority', language=self.logic.DEFAULT_LANGUAGE)
        priority_action = menu.addAction(action_text)
        priority_action.setEnabled(is_selected)
        action = menu.exec(global_pos)
        if priority_action and action == priority_action:
            if hero_name in self.logic.selected_heroes:
                self.logic.set_priority(hero_name)
                self.update_ui_after_logic_change()
            else: print(f"Cannot change priority for '{hero_name}' as it's not selected.")

    def switch_language(self, lang_code: str):
        print(f"[Language] Attempting to switch to {lang_code}")
        if self.logic.DEFAULT_LANGUAGE != lang_code:
            set_language(lang_code)
            self.logic.DEFAULT_LANGUAGE = lang_code
            self.update_language()
            self.update_ui_after_logic_change()
            if self.hotkey_cursor_index != -1:
                QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))
        else:
            print(f"[Language] Already set to {lang_code}")

    def _calculate_columns(self):
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min':
            self._num_columns_cache = 1; return 1
        try:
            viewport = list_widget.viewport()
            if not viewport: return self._num_columns_cache
            vp_width = viewport.width()
            grid_w = list_widget.gridSize().width()
            spacing = list_widget.spacing()
            if grid_w <= 0: return self._num_columns_cache
            eff_grid_w = grid_w + spacing
            if eff_grid_w <= 0: return self._num_columns_cache
            cols = max(1, int(vp_width / eff_grid_w))
            self._num_columns_cache = cols; return cols
        except Exception as e: print(f"[ERROR] Calculating columns: {e}"); return self._num_columns_cache

    def _update_hotkey_highlight(self, old_index=None):
        list_widget = self.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': return
        count = list_widget.count()
        if count == 0: return
        needs_viewport_update = False
        new_index = self.hotkey_cursor_index
        if old_index is not None and old_index != new_index and 0 <= old_index < count:
            try:
                old_item = list_widget.item(old_index)
                if old_item:
                    hero_name = old_item.data(HERO_NAME_ROLE)
                    if hero_name and ">>>" in old_item.toolTip():
                        old_item.setToolTip(hero_name); needs_viewport_update = True
            except Exception as e: print(f"[ERROR] Restoring old tooltip (idx {old_index}): {e}")
        if 0 <= new_index < count:
            try:
                new_item = list_widget.item(new_index)
                if new_item:
                    hero_name = new_item.data(HERO_NAME_ROLE)
                    focus_tooltip = f">>> {hero_name} <<<"
                    if hero_name and new_item.toolTip() != focus_tooltip:
                        new_item.setToolTip(focus_tooltip); needs_viewport_update = True
                    list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
            except Exception as e: print(f"[ERROR] Setting new tooltip (idx {new_index}): {e}")
        if needs_viewport_update or old_index != new_index:
            list_widget.viewport().update()

    def start_keyboard_listener(self):
        if not keyboard: return
        if self._keyboard_listener_thread is None or not self._keyboard_listener_thread.is_alive():
            print("Starting keyboard listener thread...")
            self._stop_keyboard_listener_flag.clear()
            self._keyboard_listener_thread = threading.Thread(target=self._keyboard_listener_loop, daemon=True)
            self._keyboard_listener_thread.start()
        else: print("Keyboard listener already running.")

    def stop_keyboard_listener(self):
        if not keyboard: return
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
            print("Signalling keyboard listener to stop...")
            self._stop_keyboard_listener_flag.set()
        else: print("Keyboard listener not running or already stopped.")

    def _keyboard_listener_loop(self):
        print("Keyboard listener thread started.")
        def run_in_gui_thread(func, *args): QTimer.singleShot(0, lambda: func(*args))
        def run_if_topmost_gui(func, *args):
            is_topmost = self.win_api_manager.is_win_topmost if winapi_user32 else bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
            if is_topmost:
                try: run_in_gui_thread(func, *args)
                except Exception as e: print(f"[ERROR] Exception scheduling hotkey callback: {e}")
        hooks_registered = []
        try:
            print(f"Registering keyboard hooks...")
            keyboard.add_hotkey('tab+up', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'up'), suppress=True)
            keyboard.add_hotkey('tab+down', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'down'), suppress=True)
            keyboard.add_hotkey('tab+left', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'left'), suppress=True)
            keyboard.add_hotkey('tab+right', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'right'), suppress=True)
            hooks_registered.extend(['tab+up', 'tab+down', 'tab+left', 'tab+right'])
            try: keyboard.add_hotkey('tab+num 0', lambda: run_if_topmost_gui(self.toggle_selection_signal.emit), suppress=True); hooks_registered.append('tab+num 0')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+keypad 0', lambda: run_if_topmost_gui(self.toggle_selection_signal.emit), suppress=True); hooks_registered.append('tab+keypad 0')
            except ValueError: print("[WARN] Could not hook Tab + Num 0 / Keypad 0.")
            try: keyboard.add_hotkey('tab+delete', lambda: run_if_topmost_gui(self.toggle_mode_signal.emit), suppress=True); hooks_registered.append('tab+delete')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+del', lambda: run_if_topmost_gui(self.toggle_mode_signal.emit), suppress=True); hooks_registered.append('tab+del')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+.', lambda: run_if_topmost_gui(self.toggle_mode_signal.emit), suppress=True); hooks_registered.append('tab+.')
            except ValueError: print("[WARN] Could not hook Tab + Delete / Del / Numpad .")
            try: keyboard.add_hotkey('tab+num -', lambda: run_if_topmost_gui(self.clear_all_signal.emit), suppress=True); hooks_registered.append('tab+num -')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+keypad -', lambda: run_if_topmost_gui(self.clear_all_signal.emit), suppress=True); hooks_registered.append('tab+keypad -')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+-', lambda: run_if_topmost_gui(self.clear_all_signal.emit), suppress=True); hooks_registered.append('tab+-')
            except ValueError: print("[WARN] Could not hook Tab + Num - / Keypad - / -.")
            try: keyboard.add_hotkey('tab+num /', lambda: run_if_topmost_gui(self.recognize_heroes_signal.emit), suppress=True); hooks_registered.append('tab+num /')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+keypad /', lambda: run_if_topmost_gui(self.recognize_heroes_signal.emit), suppress=True); hooks_registered.append('tab+keypad /')
            except ValueError: print("[WARN] Could not hook Tab + Num / or Keypad /.")
            print(f"Hotkeys registered: {len(hooks_registered)}")
            self._stop_keyboard_listener_flag.wait()
            print("Keyboard listener stop signal received.")
        except ImportError: print("\n[ERROR] 'keyboard' library requires root/admin privileges.\n")
        except Exception as e: print(f"[ERROR] Error in keyboard listener setup: {e}")
        finally:
            print("Unhooking all keyboard hotkeys...")
            keyboard.unhook_all()
            print("Keyboard listener thread finished.")
