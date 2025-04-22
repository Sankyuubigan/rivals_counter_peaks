# File: core/main_window.py
import sys
import time
import threading
import os # <<< ДОБАВЛЕН os для APP_VERSION

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout,
                               QMessageBox, QApplication, QScrollArea, QAbstractItemView, QMenu, QLabel, QPushButton, QComboBox) # <<< ДОБАВЛЕНЫ QLabel, QPushButton, QComboBox
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QPoint, QModelIndex
from PySide6.QtGui import QIcon, QMouseEvent, QColor, QBrush

# Импорты из проекта
from translations import get_text, set_language, SUPPORTED_LANGUAGES
from utils_gui import copy_to_clipboard
from logic import CounterpickLogic, TEAM_SIZE
# Менеджеры и связанные функции
from mode_manager import ModeManager, PANEL_MIN_WIDTHS, MODE_DEFAULT_WINDOW_SIZES # <<< УБРАН change_mode, update_interface_for_mode
from win_api import WinApiManager, user32 as winapi_user32
from recognition import RecognitionManager, RecognitionWorker
# Загрузка ресурсов
from images_load import load_original_images, get_images_for_mode, SIZES, load_default_pixmap
# Элементы UI
from top_panel import TopPanel
from left_panel import LeftPanel, create_left_panel # <<< ДОБАВЛЕН create_left_panel
from right_panel import RightPanel, HERO_NAME_ROLE # <<< ДОБАВЛЕН create_right_panel
from horizontal_list import update_horizontal_icon_list
from display import generate_counterpick_display, generate_minimal_icon_list
# Данные
# from heroes_bd import heroes # Импортируется там где нужно

# Библиотека hotkey
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

    def __init__(self, logic: CounterpickLogic, hero_templates: dict):
        super().__init__()
        print("[LOG] MainWindow.__init__ started")

        # Основные компоненты
        self.logic = logic
        self.hero_templates = hero_templates
        # <<< ИСПРАВЛЕНО: Получаем версию из environment, как в logic >>>
        self.app_version = os.environ.get("APP_VERSION", "N/A")
        # self.app_version = self.logic.APP_VERSION # Убираем зависимость от logic здесь
        # <<< ------------------------------------------------------- >>>

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

        # Атрибуты UI (инициализируем None)
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
        self._create_main_ui_layout()
        self._update_interface_for_mode() # <<< ИЗМЕНЕНО: Вызываем внутренний метод

        # Подключение сигналов
        self._connect_signals()

        # Запуск слушателя хоткеев
        if keyboard: self.start_keyboard_listener()
        else: print("[WARN] Библиотека keyboard не найдена, горячие клавиши не будут работать.")

        print("[LOG] MainWindow.__init__ finished")

    # --- Создание и настройка UI ---
    # _create_main_ui_layout остается как есть
    # _create_icons_scroll_area остается как есть
    # _connect_signals остается как есть

    # --- Обработка событий окна ---
    # closeEvent, mousePress/Move/ReleaseEvent остаются без изменений

    # --- Управление режимами окна ---
    # <<< ИЗМЕНЕНО: change_mode теперь внутри MainWindow >>>
    def change_mode(self, mode_name: str):
        """Инициирует смену режима отображения."""
        print(f"--- Попытка смены режима на: {mode_name} ---")
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
        self.mode_manager.change_mode(mode_name) # Обновляем режим в менеджере
        self.mode = mode_name # Обновляем режим в окне

        # 4. Перестройка интерфейса
        self._update_interface_for_mode() # Вызываем внутренний метод

        # 5. Восстанавливаем позицию окна
        target_pos = self.mode_positions.get(self.mode)
        if target_pos and self.isVisible():
            print(f"Восстановление позиции для режима '{self.mode}': {target_pos}")
            self.move(target_pos)

        # 6. Восстанавливаем фокус хоткея
        QTimer.singleShot(150, self._reset_hotkey_cursor_after_mode_change)

        end_time = time.time()
        print(f"--- Смена режима на {mode_name} ЗАВЕРШЕНА (заняло: {end_time - start_time:.4f} сек) ---")
    # <<< ------------------------------------------ >>>


    # <<< ДОБАВЛЕНО: Метод _update_interface_for_mode перенесен сюда из mode_manager.py >>>
    def _update_interface_for_mode(self):
        """Перестраивает интерфейс для текущего режима (`self.mode`)."""
        t0 = time.time()
        current_mode = self.mode # Используем режим из self
        print(f"[TIMING] _update_interface_for_mode: Start for mode '{current_mode}'")

        # --- 1. Очистка inner_layout ---
        t1 = time.time()
        if self.inner_layout: self.mode_manager.clear_layout_recursive(self.inner_layout)
        else:
            if self.main_widget:
                 self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
                 self.inner_layout.setContentsMargins(0,0,0,0); self.inner_layout.setSpacing(0)
            else: print("[!] КРИТИЧЕСКАЯ ОШИБКА: main_widget не найден."); return
        t2 = time.time(); # print(f"[TIMING] -> Clear inner_layout: {t2-t1:.4f} s")

        # --- 2. Сброс ссылок ---
        self.left_panel_instance = None; self.canvas = None; self.result_frame = None; self.result_label = None
        self.right_panel_instance = None; self.right_frame = None; self.selected_heroes_label = None; self.right_list_widget = None
        self.hero_items.clear()

        # --- 3. Загрузка изображений ---
        t1 = time.time()
        try: self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(current_mode)
        except Exception as e: print(f"Критическая ошибка загрузки изображений для режима {current_mode}: {e}"); return
        t2 = time.time(); # print(f"[TIMING] -> Load/Get images: {t2-t1:.4f} s")

        # --- 4. Пересоздание левой панели ---
        t1 = time.time()
        # Используем функцию create_left_panel, которая создает экземпляр LeftPanel
        # и возвращает нужные виджеты
        # ВАЖНО: create_left_panel ожидает родительский виджет, передаем self.main_widget
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.main_widget)
        # Контейнер left_frame теперь внутри create_left_panel, получаем ссылку на него, если нужно
        self.left_frame = self.canvas.parentWidget() # Получаем QFrame контейнер
        self.left_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('left', 0))
        self.inner_layout.addWidget(self.left_frame, stretch=1)
        t2 = time.time(); # print(f"[TIMING] -> Create left panel: {t2-t1:.4f} s")

        # --- 5. Пересоздание/Скрытие правой панели ---
        t1 = time.time()
        if current_mode != "min":
            # Используем функцию create_right_panel
            # ВАЖНО: Передаем self (MainWindow) и режим
            self.right_panel_instance = RightPanel(self, current_mode) # Создаем экземпляр
            self.right_frame = self.right_panel_instance.frame # Получаем QFrame
            # Получаем ссылки на виджеты из экземпляра right_panel_instance
            self.selected_heroes_label = self.right_panel_instance.selected_heroes_label
            self.right_list_widget = self.right_panel_instance.list_widget
            self.hero_items = self.right_panel_instance.hero_items
            # Настраиваем и добавляем
            self.right_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('right', 0))
            self.inner_layout.addWidget(self.right_frame, stretch=1)
            self.inner_layout.setStretch(0, 2); self.inner_layout.setStretch(1, 1)
        else: pass # Ссылки уже None
        t2 = time.time(); # print(f"[TIMING] -> Create/Hide right panel: {t2-t1:.4f} s")

        # --- 6. Настройка окна и TopPanel ---
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
            if not (current_flags & Qt.WindowType.FramelessWindowHint):
                self.setWindowFlags(current_flags | Qt.WindowType.FramelessWindowHint); frameless_changed = True
            if lang_label: lang_label.hide()
            if lang_combo: lang_combo.hide()
            if version_label: version_label.hide()
            if self.author_button: self.author_button.hide()
            if self.rating_button: self.rating_button.hide()
            if close_button: close_button.show()
            self.setWindowTitle("")
            calculated_fixed_min_height = base_h + 5
            self.setMinimumHeight(calculated_fixed_min_height)
            self.setMaximumHeight(calculated_fixed_min_height)
        else:
            if current_flags & Qt.WindowType.FramelessWindowHint:
                self.setWindowFlags(current_flags & ~Qt.WindowType.FramelessWindowHint); frameless_changed = True
            if lang_label: lang_label.show()
            if lang_combo: lang_combo.show()
            if version_label: version_label.show()
            if close_button: close_button.hide()
            self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
            if current_mode == "max":
                calculated_min_h = base_h + 300
                self.setMinimumHeight(calculated_min_h)
                if self.author_button: self.author_button.show()
                if self.rating_button: self.rating_button.show()
            else: # middle
                calculated_min_h = base_h + 200
                self.setMinimumHeight(calculated_min_h)
                if self.author_button: self.author_button.hide()
                if self.rating_button: self.rating_button.hide()

        if frameless_changed:
            print("[LOG] Frameless flag changed, calling window.show()")
            self.show()
        t2 = time.time(); # print(f"[TIMING] -> Setup window flags/visibility: {t2-t1:.4f} s")

        # --- 7. Обновление языка и геометрии ---
        t1 = time.time()
        self.update_language() # <<< ВЫЗЫВАЕМ МЕТОД self.update_language() >>>
        self.main_layout.activate()
        if self.inner_layout: self.inner_layout.activate()
        self.updateGeometry()
        t2 = time.time(); # print(f"[TIMING] -> Update language/layout/geometry: {t2-t1:.4f} s")

        # --- 8. Установка размера окна ---
        t1 = time.time()
        target_size = MODE_DEFAULT_WINDOW_SIZES.get(current_mode, {'width': 800, 'height': 600})
        target_w = target_size['width']; target_h = target_size['height']
        min_w = self.minimumSizeHint().width(); actual_min_h = self.minimumHeight()

        if current_mode == 'min':
            final_w = max(target_w, min_w); final_h = self.minimumHeight()
            self.resize(final_w, final_h)
        else:
            final_w = max(target_w, min_w); final_h = max(target_h, actual_min_h)
            self.resize(final_w, final_h)
        t2 = time.time(); # print(f"[TIMING] -> Resize window: {t2-t1:.4f} s")

        # --- 9. Восстановление состояния UI ---
        t1 = time.time()
        self.update_ui_after_logic_change()
        t2 = time.time(); # print(f"[TIMING] -> Restore UI state: {t2-t1:.4f} s")

        t_end = time.time()
        print(f"[TIMING] _update_interface_for_mode: Finished (Total: {t_end - t0:.4f} s)")
    # <<< КОНЕЦ ПЕРЕНЕСЕННОГО МЕТОДА >>>

    # Остальные методы остаются как были (без изменений)
    # _reset_hotkey_cursor_after_mode_change, _is_win_topmost, set_topmost_winapi, toggle_topmost_winapi,
    # _handle_move_cursor, _handle_toggle_selection, _handle_toggle_mode, _handle_clear_all,
    # _reset_hotkey_cursor_after_clear, _on_recognition_complete, _on_recognition_error,
    # update_ui_after_logic_change, _update_selected_label, _update_counterpick_display,
    # _update_list_item_selection_states, _update_priority_labels, handle_selection_changed,
    # show_priority_context_menu, switch_language, update_language, _calculate_columns,
    # _update_hotkey_highlight, start_keyboard_listener, stop_keyboard_listener,
    # _keyboard_listener_loop, copy_to_clipboard

    # <<< ДОБАВЛЕНО: Явная реализация методов, которые были в UiUpdateManager >>>
    def update_ui(self):
        """Обновляет основные элементы UI (вызывается, если нужно обновить все сразу)."""
        self.update_ui_after_logic_change() # Используем существующий метод
        # Дополнительно можно обновить элементы, не зависящие от логики, если нужно

    # <<< Явная реализация update_language, если она нужна >>>
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
        result_label = getattr(self.left_panel_instance, 'result_label', None)
        if result_label and not self.logic.selected_heroes:
             result_label.setText(get_text('no_heroes_selected', language=current_lang))

        # Обновляем подсказки в QListWidget
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
        hero_items_dict = getattr(self.right_panel_instance, 'hero_items', {})
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

    # --- Остальные методы MainWindow... ---
    # _create_icons_scroll_area, closeEvent, mouseEvents, _reset_hotkey_cursor_after_mode_change,
    # _is_win_topmost, set_topmost_winapi, toggle_topmost_winapi, _handle_move_cursor, _handle_toggle_selection,
    # _handle_toggle_mode, _handle_clear_all, _reset_hotkey_cursor_after_clear,
    # _on_recognition_complete, _on_recognition_error, update_ui_after_logic_change,
    # _update_selected_label, _update_counterpick_display, _update_list_item_selection_states,
    # _update_priority_labels, handle_selection_changed, show_priority_context_menu,
    # switch_language, _calculate_columns, _update_hotkey_highlight,
    # start_keyboard_listener, stop_keyboard_listener, _keyboard_listener_loop, copy_to_clipboard
