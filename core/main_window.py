# File: core/main_window.py
import sys
import time
import threading

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout,
                               QMessageBox, QApplication, QScrollArea, QAbstractItemView, QMenu) # Добавлен QMenu
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QPoint, QModelIndex
from PySide6.QtGui import QIcon, QMouseEvent, QColor, QBrush

# Импорты из проекта
from translations import get_text, set_language, SUPPORTED_LANGUAGES
from utils_gui import copy_to_clipboard
from logic import CounterpickLogic, TEAM_SIZE
from mode_manager import ModeManager, change_mode as change_mode_func, update_interface_for_mode
from win_api import WinApiManager, user32 as winapi_user32
from recognition import RecognitionManager, RecognitionWorker
from images_load import load_original_images, get_images_for_mode, SIZES, load_default_pixmap
from top_panel import TopPanel
from left_panel import LeftPanel
from right_panel import RightPanel, HERO_NAME_ROLE
from horizontal_list import update_horizontal_icon_list
from display import generate_counterpick_display, generate_minimal_icon_list
# heroes_bd импортируется там, где нужен (в right_panel, logic)
# from heroes_bd import heroes # Убираем импорт heroes здесь

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
        self.app_version = self.logic.APP_VERSION

        # Менеджеры
        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)

        # Состояние UI
        self.mode = self.mode_manager.current_mode # Получаем начальный режим из менеджера
        self.initial_pos = self.pos()
        self.mode_positions = self.mode_manager.mode_positions # Используем словарь позиций из менеджера
        self.mode_positions["middle"] = self.initial_pos # Обновляем позицию для middle
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
        update_interface_for_mode(self)

        # Подключение сигналов
        self._connect_signals()

        # Запуск слушателя хоткеев
        if keyboard: self.start_keyboard_listener()
        else: print("[WARN] Библиотека keyboard не найдена, горячие клавиши не будут работать.")

        print("[LOG] MainWindow.__init__ finished")

    def _create_main_ui_layout(self):
        """Создает базовую структуру виджетов и layout'ов окна."""
        print("[LOG] MainWindow._create_main_ui_layout() started")
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        # Верхняя панель
        # <<< ИСПРАВЛЕНО: Передаем self.change_mode как callback >>>
        self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
        # <<< ---------------------------------------------- >>>
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

    def _create_icons_scroll_area(self):
        """Создает QScrollArea для горизонтального списка иконок."""
        self.icons_scroll_area = QScrollArea();
        self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f0f0f0; }")

        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_scroll_content_layout.setObjectName("icons_scroll_content_layout")
        self.icons_scroll_content_layout.setContentsMargins(5, 2, 5, 2); self.icons_scroll_content_layout.setSpacing(4)
        self.icons_scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)
        self.icons_scroll_area.setFixedHeight(40) # Начальная высота

    def _connect_signals(self):
        """Подключает все сигналы и слоты."""
        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)
        self.toggle_mode_signal.connect(self._handle_toggle_mode)
        self.clear_all_signal.connect(self._handle_clear_all)
        # Сигналы распознавания
        self.recognize_heroes_signal.connect(self.rec_manager._handle_recognize_heroes)
        self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
        self.rec_manager.error.connect(self._on_recognition_error)

    # --- Обработка событий окна ---
    # closeEvent, mousePress/Move/ReleaseEvent остаются без изменений

    # --- Управление режимами окна ---
    # <<< ДОБАВЛЕНО: Метод change_mode в MainWindow >>>
    def change_mode(self, mode_name: str):
        """Слот для изменения режима отображения (вызывается из TopPanel)."""
        # Делегируем вызов функции из модуля mode_manager
        change_mode_func(self, mode_name)
    # <<< -------------------------------------- >>>

    # _reset_hotkey_cursor_after_mode_change остается без изменений

    # --- Управление Topmost ---
    # Методы _is_win_topmost, set_topmost_winapi, toggle_topmost_winapi остаются без изменений

    # --- Обработка сигналов хоткеев ---
    # Методы _handle_move_cursor, _handle_toggle_selection, _handle_toggle_mode, _handle_clear_all,
    # _reset_hotkey_cursor_after_clear остаются без изменений

    # --- Обработка сигналов распознавания ---
    # Методы _on_recognition_complete, _on_recognition_error остаются без изменений

    # --- Обновление UI ---
    # Метод update_ui_after_logic_change остается без изменений
    # Метод _update_selected_label остается без изменений
    # Метод _update_counterpick_display остается без изменений
    # Метод _update_list_item_selection_states остается без изменений
    # Метод _update_priority_labels остается без изменений (пустой)

    # --- Обработчики событий UI ---
    # Метод handle_selection_changed остается без изменений
    # Метод show_priority_context_menu остается без изменений

    # --- Язык ---
    # Методы switch_language, update_language остаются без изменений

    # --- Утилиты UI ---
    # Методы _calculate_columns, _update_hotkey_highlight остаются без изменений

    # --- Управление слушателем клавиатуры ---
    # Методы start_keyboard_listener, stop_keyboard_listener, _keyboard_listener_loop остаются без изменений

    # --- Копирование в буфер обмена ---
    def copy_to_clipboard(self):
        """Слот для копирования рекомендуемой команды в буфер."""
        # Вызываем функцию из utils_gui, передавая текущую логику
        copy_to_clipboard(self.logic)

    # --- Переопределение стандартных методов (остаются без изменений) ---
    def closeEvent(self, event): super().closeEvent(event)
    def mousePressEvent(self, event: QMouseEvent): super().mousePressEvent(event)
    def mouseMoveEvent(self, event: QMouseEvent): super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event: QMouseEvent): super().mouseReleaseEvent(event)

    # --- Явно скопируем код оставшихся методов из предыдущего ответа для полноты ---
    def _create_icons_scroll_area(self):
        """Создает QScrollArea для горизонтального списка иконок."""
        self.icons_scroll_area = QScrollArea();
        self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f0f0f0; }")

        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_scroll_content_layout.setObjectName("icons_scroll_content_layout")
        self.icons_scroll_content_layout.setContentsMargins(5, 2, 5, 2); self.icons_scroll_content_layout.setSpacing(4)
        self.icons_scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)
        self.icons_scroll_area.setFixedHeight(40) # Начальная высота

    def closeEvent(self, event):
        """Вызывается при закрытии окна."""
        print("Close event triggered.")
        self.stop_keyboard_listener()
        if hasattr(self, '_recognition_worker') and self._recognition_worker: self._recognition_worker.stop()
        if hasattr(self, '_recognition_thread') and self._recognition_thread and self._recognition_thread.isRunning():
            print("Quitting recognition thread on close...")
            self._recognition_thread.quit()
            if not self._recognition_thread.wait(1000):
                 print("[WARN] Recognition thread did not quit gracefully on close.")
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
             print("Waiting for keyboard listener thread to join...")
             self._keyboard_listener_thread.join(timeout=1.0)
             if self._keyboard_listener_thread.is_alive(): print("[WARN] Keyboard listener thread did not exit cleanly.")
             else: print("Keyboard listener thread joined successfully.")
        super().closeEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self.mode == "min" and self.top_frame and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_pressed = True
                self._old_pos = event.globalPosition().toPoint()
                event.accept()
                return
        self._mouse_pressed = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False
            self._old_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _reset_hotkey_cursor_after_mode_change(self):
        print("[LOG] _reset_hotkey_cursor_after_mode_change called")
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
        if list_widget and list_widget.isVisible() and self.mode != 'min':
            count = list_widget.count()
            if count > 0:
                self.hotkey_cursor_index = 0
                self._calculate_columns()
                self._update_hotkey_highlight(None)
                print(f"[Hotkey] Cursor reset to index 0 in mode {self.mode}")
            else:
                self.hotkey_cursor_index = -1
                print(f"[Hotkey] List is empty, cursor set to -1 in mode {self.mode}")
        else:
            self.hotkey_cursor_index = -1
            list_visible_status = list_widget.isVisible() if list_widget else 'No list'
            print(f"[Hotkey] Cursor set to -1 (mode: {self.mode}, list visible: {list_visible_status})")

    # --- Управление Topmost ---
    @property
    def _is_win_topmost(self): return self.win_api_manager.is_win_topmost
    def set_topmost_winapi(self, enable: bool): self.win_api_manager.set_topmost_winapi(enable)
    def toggle_topmost_winapi(self): self.win_api_manager.set_topmost_winapi(not self.win_api_manager.is_win_topmost)

    # --- Обработка сигналов хоткеев ---
    @Slot(str)
    def _handle_move_cursor(self, direction):
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
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
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
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

    # --- Обработка сигналов распознавания ---
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

    # --- Обновление UI ---
    # _update_selected_label, _update_counterpick_display,
    # _update_list_item_selection_states, _update_priority_labels уже определены выше

    # --- Обработчики событий UI ---
    # handle_selection_changed, show_priority_context_menu уже определены выше

    # --- Язык ---
    # switch_language, update_language уже определены выше

    # --- Утилиты UI ---
    # _calculate_columns, _update_hotkey_highlight уже определены выше

    # --- Управление слушателем клавиатуры ---
    # start_keyboard_listener, stop_keyboard_listener, _keyboard_listener_loop уже определены выше

    def _reset_hotkey_cursor_after_clear(self):
         """Сбрасывает фокус хоткея после очистки."""
         list_widget = getattr(self.right_panel_instance, 'list_widget', None)
         if list_widget and list_widget.isVisible() and self.mode != 'min':
            old_index = self.hotkey_cursor_index
            count = list_widget.count()
            self.hotkey_cursor_index = 0 if count > 0 else -1
            if self.hotkey_cursor_index != old_index or old_index != 0:
                self._update_hotkey_highlight(old_index)
         else:
            self.hotkey_cursor_index = -1