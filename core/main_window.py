# File: core/main_window.py
import sys
import time
import threading

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout,
                               QMessageBox, QApplication, QScrollArea)  # Добавлен QApplication для processEvents
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread
from PySide6.QtGui import QIcon, QMouseEvent

# Импорты из проекта (используем относительные пути внутри core)
from .translations import get_text, set_language
from .utils_gui import copy_to_clipboard
from .logic import CounterpickLogic, TEAM_SIZE # Импортируем TEAM_SIZE
# Менеджеры
from .mode_manager import ModeManager, change_mode, update_interface_for_mode # Импортируем функции управления режимом
from .win_api import WinApiManager, user32 as winapi_user32 # Импортируем user32 для проверки доступности
from .recognition import RecognitionManager, RecognitionWorker
# Загрузка ресурсов
from .images_load import load_hero_templates, load_original_images, get_images_for_mode, SIZES
# Элементы UI
from .top_panel import TopPanel # Используем класс TopPanel
from .left_panel import LeftPanel # Используем класс LeftPanel
from .right_panel import RightPanel # Используем класс RightPanel
from .horizontal_list import update_horizontal_icon_list # Функция обновления списка
from .display import generate_counterpick_display, generate_minimal_icon_list # Функции отрисовки
# Данные
from heroes_bd import heroes

# Библиотека hotkey
try:
    import keyboard
except ImportError:
    print("[ERROR] Библиотека 'keyboard' не найдена. Установите ее: pip install keyboard")
    keyboard = None # Помечаем, что библиотека недоступна


class MainWindow(QMainWindow):
    # Сигналы для межпоточного взаимодействия и UI
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()
    toggle_mode_signal = Signal()
    clear_all_signal = Signal()
    recognize_heroes_signal = Signal()
    recognition_complete_signal = Signal(list)

    def __init__(self, logic: CounterpickLogic, hero_templates: dict):
        """
        Инициализирует главное окно приложения.
        """
        super().__init__()
        print("[LOG] MainWindow.__init__ started")

        # --- Основные компоненты ---
        self.logic = logic
        self.hero_templates = hero_templates
        self.app_version = self.logic.APP_VERSION # Получаем версию из logic

        # --- Менеджеры ---
        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self) # Инициализируем менеджер режимов
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager) # Передаем self как main_window

        # --- Атрибуты состояния UI ---
        self.mode = "middle" # Начальный режим (будет установлен ModeManager)
        self.initial_pos = None
        self.mode_positions = {"max": None, "middle": None, "min": None}
        self.is_programmatically_updating_selection = False # Флаг для избежания рекурсии сигналов

        # --- Атрибуты UI (инициализируются как None, создаются в create_main_ui/update_interface) ---
        # Словари изображений для текущего режима
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        # Ссылки на основные виджеты/панели
        self.top_panel_widget: TopPanel | None = None # Экземпляр класса TopPanel
        self.left_panel_instance: LeftPanel | None = None # Экземпляр класса LeftPanel
        self.right_panel_instance: RightPanel | None = None # Экземпляр класса RightPanel
        # Ссылки на виджеты внутри панелей (для удобства доступа)
        self.icons_scroll_area = None
        self.icons_scroll_content = None
        self.icons_scroll_content_layout = None
        self.canvas = None # ScrollArea левой панели
        self.result_frame = None # Frame внутри левой ScrollArea
        self.result_label = None # Label внутри левой ScrollArea
        self.update_scrollregion = lambda: None # Функция обновления левой ScrollArea
        self.right_list_widget = None # QListWidget из правой панели
        self.selected_heroes_label = None # QLabel из правой панели
        self.hero_items = {} # Словарь {hero_name: QListWidgetItem}

        # --- Hotkeys ---
        self.hotkey_cursor_index = -1 # Индекс элемента под фокусом хоткея
        self._num_columns_cache = 1 # Кэш для расчета колонок
        self._keyboard_listener_thread = None
        self._stop_keyboard_listener_flag = threading.Event()

        # --- Распознавание ---
        self._recognition_thread = None
        self._recognition_worker = None

        # --- Настройка окна ---
        self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
        # Устанавливаем иконку (если есть заглушка)
        # icon_pixmap = load_default_pixmap((32,32)) # Создаем заглушку 32x32
        # if not icon_pixmap.isNull():
        #     self.setWindowIcon(QIcon(icon_pixmap))
        self.setGeometry(100, 100, 950, 350) # Начальный размер и позиция
        self.setMinimumSize(400, 100) # Минимальный размер окна

        # --- Создание UI ---
        self.create_main_ui()
        # Первоначальное обновление UI для текущего режима
        update_interface_for_mode(self)

        # --- Подключение сигналов ---
        self._connect_signals()

        # --- Запуск слушателя хоткеев ---
        if keyboard: # Запускаем только если библиотека keyboard доступна
             self.start_keyboard_listener()
        else:
             print("[WARN] Библиотека keyboard не найдена, горячие клавиши не будут работать.")

        print("[LOG] MainWindow.__init__ finished")

    # --- Создание и настройка UI ---
    def create_main_ui(self):
        """Создает основные виджеты и layout'ы окна."""
        print("[LOG] MainWindow.create_main_ui() started")
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        # --- Верхняя панель (TopPanel) ---
        # Создаем экземпляр TopPanel
        self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
        self.top_frame = self.top_panel_instance.top_frame # Получаем QFrame из экземпляра
        # Добавляем кнопки автора и рейтинга в атрибуты MainWindow для доступа из mode_manager
        self.author_button = self.top_panel_instance.author_button
        self.rating_button = self.top_panel_instance.rating_button
        self.main_layout.addWidget(self.top_frame)

        # --- Панель горизонтальных иконок (IconsScrollArea) ---
        # Этот виджет создается здесь, а не в Left/Right panel
        self._create_icons_scroll_area()
        self.main_layout.addWidget(self.icons_scroll_area)

        # --- Основная область с панелями (MainWidget + InnerLayout) ---
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
        self.inner_layout.setContentsMargins(0, 0, 0, 0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1) # Основная область растягивается

        # Левая и правая панели создаются/пересоздаются в update_interface_for_mode
        print("[LOG] MainWindow.create_main_ui() finished")

    def _create_icons_scroll_area(self):
        """Создает QScrollArea для горизонтального списка иконок."""
        self.icons_scroll_area = QScrollArea();
        self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f0f0f0; }") # Стиль фона

        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_scroll_content_layout.setObjectName("icons_scroll_content_layout")
        self.icons_scroll_content_layout.setContentsMargins(5, 2, 5, 2); self.icons_scroll_content_layout.setSpacing(4)
        self.icons_scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)

        # Высота будет установлена в update_interface_for_mode
        self.icons_scroll_area.setFixedHeight(40) # Начальная высота

    def _connect_signals(self):
        """Подключает все сигналы и слоты."""
        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)
        self.toggle_mode_signal.connect(self._handle_toggle_mode)
        self.clear_all_signal.connect(self._handle_clear_all)
        self.recognize_heroes_signal.connect(self.rec_manager._handle_recognize_heroes) # Сигнал к менеджеру распознавания
        self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete) # От менеджера к обработчику в окне
        self.rec_manager.error.connect(self._on_recognition_error) # Ошибки от менеджера
        # Сигнал изменения языка в TopPanel уже подключен при создании

    # --- Обработка событий окна ---
    def closeEvent(self, event):
        """Вызывается при закрытии окна."""
        print("Close event triggered.")
        self.stop_keyboard_listener() # Останавливаем хоткеи
        # Остановка потока распознавания (если он есть)
        if self._recognition_worker: self._recognition_worker.stop()
        if self._recognition_thread and self._recognition_thread.isRunning():
            print("Quitting recognition thread on close...")
            self._recognition_thread.quit()
            if not self._recognition_thread.wait(1000):
                 print("[WARN] Recognition thread did not quit gracefully on close.")
        # Ждем завершения потока хоткеев
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
             print("Waiting for keyboard listener thread to join...")
             self._keyboard_listener_thread.join(timeout=1.0)
             if self._keyboard_listener_thread.is_alive(): print("[WARN] Keyboard listener thread did not exit cleanly.")
             else: print("Keyboard listener thread joined successfully.")
        super().closeEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Обработка нажатия мыши (для перемещения в min режиме)."""
        # Используем self.mode напрямую
        if self.mode == "min" and self.top_frame and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_pressed = True
                self._old_pos = event.globalPosition().toPoint()
                event.accept()
                return # Прекращаем обработку здесь
        self._mouse_pressed = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка движения мыши (для перемещения в min режиме)."""
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Обработка отпускания мыши (для перемещения в min режиме)."""
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False
            self._old_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # --- Управление режимами окна ---
    def change_mode(self, mode_name: str):
        """Слот для изменения режима отображения."""
        # Используем функцию из mode_manager.py
        change_mode(self, mode_name)

    def _reset_hotkey_cursor_after_mode_change(self):
        """Восстанавливает фокус хоткея после смены режима."""
        # Этот метод вызывается из update_interface_for_mode в конце
        print("[LOG] _reset_hotkey_cursor_after_mode_change called")
        # Проверяем, что правая панель и список существуют и видимы
        if self.right_list_widget and self.right_list_widget.isVisible() and self.mode != 'min':
            count = self.right_list_widget.count()
            if count > 0:
                self.hotkey_cursor_index = 0 # Устанавливаем на первый элемент
                self._calculate_columns() # Пересчитываем колонки для нового режима
                self._update_hotkey_highlight(None) # Запрашиваем обновление для отрисовки рамки
                print(f"[Hotkey] Cursor reset to index 0 in mode {self.mode}")
            else:
                self.hotkey_cursor_index = -1
                print(f"[Hotkey] List is empty, cursor set to -1 in mode {self.mode}")
        else:
            self.hotkey_cursor_index = -1 # В min режиме или если списка нет - фокуса нет
            print(f"[Hotkey] Cursor set to -1 (mode: {self.mode}, list visible: {self.right_list_widget.isVisible() if self.right_list_widget else 'No list'})")
            # Если раньше был фокус, его рамка должна исчезнуть т.к. hotkey_cursor_index != row

    # --- Управление Topmost ---
    # Используем методы WinApiManager
    @property
    def _is_win_topmost(self):
        """Свойство для доступа к состоянию topmost."""
        return self.win_api_manager.is_win_topmost

    def set_topmost_winapi(self, enable: bool):
        """Устанавливает состояние topmost через WinAPI."""
        self.win_api_manager.set_topmost_winapi(enable)

    def toggle_topmost_winapi(self):
        """Переключает состояние topmost через WinAPI."""
        self.win_api_manager.set_topmost_winapi(not self.win_api_manager.is_win_topmost)

    # --- Обработка сигналов хоткеев ---
    @Slot(str)
    def _handle_move_cursor(self, direction):
        """Перемещение фокуса хоткея."""
        # Код перемещения остается здесь, так как он работает с UI элементами окна
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        list_widget = self.right_list_widget; count = list_widget.count()
        if count == 0: return

        old_index = self.hotkey_cursor_index
        num_columns = self._calculate_columns()

        if self.hotkey_cursor_index < 0: new_index = 0
        else:
            current_row = self.hotkey_cursor_index // num_columns; current_col = self.hotkey_cursor_index % num_columns
            new_index = self.hotkey_cursor_index

            # Логика перемещения (оставляем как было)
            if direction == 'left':
                if current_col > 0: new_index -= 1
                elif current_row > 0: # Переход в конец предыдущей строки
                    new_index = (current_row - 1) * num_columns + (num_columns - 1)
                    new_index = min(new_index, count - 1) # Убеждаемся, что индекс валидный
                else: # Переход в самый конец списка
                     new_index = count - 1
            elif direction == 'right':
                if current_col < num_columns - 1: new_index += 1
                elif self.hotkey_cursor_index < count - 1: # Переход в начало следующей строки
                     new_index = (current_row + 1) * num_columns
                else: # Переход в начало списка
                     new_index = 0
                new_index = min(new_index, count - 1) # Убеждаемся, что не вышли за пределы
            elif direction == 'up':
                new_index -= num_columns
                if new_index < 0: # Переход на последнюю строку
                     last_row_start_index = (count - 1) - ((count - 1) % num_columns)
                     potential_index = last_row_start_index + current_col
                     new_index = min(potential_index, count - 1)
            elif direction == 'down':
                new_index += num_columns
                if new_index >= count: # Переход на первую строку
                     new_index = current_col
                     if new_index >= count: new_index = 0 # Если в первой строке нет такого столбца

            new_index = max(0, min(count - 1, new_index))

        if old_index != new_index:
            self.hotkey_cursor_index = new_index
            self._update_hotkey_highlight(old_index) # Обновляем подсветку
        elif 0 <= self.hotkey_cursor_index < count: # Если индекс не изменился, просто прокручиваем
             current_item = list_widget.item(self.hotkey_cursor_index)
             if current_item: list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)


    @Slot()
    def _handle_toggle_selection(self):
        """Выбор/снятие выбора элемента под фокусом хоткея."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
            item = self.right_list_widget.item(self.hotkey_cursor_index)
            if item:
                try:
                    current_state = item.isSelected()
                    item.setSelected(not current_state)
                    # Сигнал itemSelectionChanged вызовет handle_selection_changed
                except Exception as e: print(f"[ERROR] Error toggling selection: {e}")

    @Slot()
    def _handle_toggle_mode(self):
        """Переключение режима min/middle."""
        print("[LOG] _handle_toggle_mode called")
        target_mode = "middle" if self.mode == "min" else "min"
        self.change_mode(target_mode)

    @Slot()
    def _handle_clear_all(self):
        """Очистка выбора."""
        print("[LOG] _handle_clear_all called")
        self.logic.clear_all()
        self.update_ui_after_logic_change()
        # Сброс фокуса хоткея на первый элемент (если он есть)
        self._reset_hotkey_cursor_after_clear()


    def _reset_hotkey_cursor_after_clear(self):
         """Сбрасывает фокус хоткея после очистки."""
         if self.right_list_widget and self.right_list_widget.isVisible() and self.mode != 'min':
            old_index = self.hotkey_cursor_index
            count = self.right_list_widget.count()
            self.hotkey_cursor_index = 0 if count > 0 else -1
            if self.hotkey_cursor_index != old_index or old_index != 0: # Обновляем если индекс изменился или был не 0
                self._update_hotkey_highlight(old_index)
         else:
            self.hotkey_cursor_index = -1

    # --- Обработка сигналов распознавания ---
    # Слот _handle_recognize_heroes теперь в RecognitionManager
    # Мы обрабатываем только результаты

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes):
        """Обрабатывает результат успешного распознавания."""
        print(f"[RESULT] Распознавание завершено в MainWindow. Распознанные герои: {recognized_heroes}")
        if recognized_heroes:
            self.logic.set_selection(set(recognized_heroes))
            self.update_ui_after_logic_change()
        else:
            print("[INFO] Герои не распознаны или список пуст.")
            QMessageBox.information(self, "Распознавание", get_text('recognition_failed', language=self.logic.DEFAULT_LANGUAGE))

    @Slot(str)
    def _on_recognition_error(self, error_message):
        """Обрабатывает ошибку во время распознавания."""
        print(f"[ERROR] Ошибка во время распознавания в MainWindow: {error_message}")
        QMessageBox.warning(self, get_text('error', language=self.logic.DEFAULT_LANGUAGE),
                            f"{get_text('recognition_error_prefix', language=self.logic.DEFAULT_LANGUAGE)}\n{error_message}")

    # --- Обновление UI ---
    # Основная логика обновления UI перенесена сюда из UiUpdateManager
    def update_ui_after_logic_change(self):
        """Обновляет все части UI, зависящие от выбора героев."""
        print("[UI Update] Started after logic change.")
        start_time = time.time()
        # Обновляем основные элементы
        self._update_selected_label()
        self._update_counterpick_display()
        update_horizontal_icon_list(self) # Обновляем горизонтальный список
        # Обновляем правую панель (состояния элементов)
        self._update_list_item_selection_states()
        self._update_priority_labels()
        end_time = time.time()
        print(f"[UI Update] Finished in {end_time - start_time:.4f} sec.")

    def _update_selected_label(self):
        """Обновляет метку с выбранными героями."""
        if self.selected_heroes_label:
             try: self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass # Игнорируем ошибку, если виджет удален
             except Exception as e: print(f"[ERROR] updating selected label: {e}")

    def _update_counterpick_display(self):
        """Обновляет левую панель (рейтинг или иконки)."""
        # Проверяем наличие необходимых виджетов
        if not self.result_frame or not self.canvas:
             print("[WARN] result_frame or canvas not found in _update_counterpick_display")
             return

        # print(f"[Display Update] Mode: {self.mode}") # Лог

        # Получаем/обновляем изображения, если нужно
        images_ok = bool(self.left_images)
        if self.mode != 'min': images_ok = images_ok and bool(self.small_images)

        if not images_ok:
            try:
                # print("[INFO] Reloading images for display update...")
                _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
            except Exception as e:
                print(f"[ERROR] reloading images for display: {e}")
                # Попытка продолжить без картинок или показать ошибку?
                # Пока просто выходим, чтобы избежать дальнейших ошибок
                return

        # Вызываем соответствующую функцию отрисовки
        try:
            if self.mode == "min":
                generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
            else:
                generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)

            # Обновляем геометрию и прокрутку после отрисовки
            # self.result_frame.adjustSize() # Это может быть не нужно, т.к. layout сам управляет
            if self.update_scrollregion:
                 QTimer.singleShot(0, self.update_scrollregion) # Обновляем ScrollArea

        except RuntimeError as e: print(f"[ERROR] RuntimeErr in display generation: {e}")
        except Exception as e: print(f"[ERROR] General Err in display generation: {e}")


    def _update_list_item_selection_states(self):
        """Обновляет состояние выбора элементов в QListWidget."""
        if not self.right_list_widget or not self.right_list_widget.isVisible(): return
        list_widget = self.right_list_widget
        self.is_programmatically_updating_selection = True
        try:
            list_widget.blockSignals(True)
            current_logic_selection = set(self.logic.selected_heroes)
            for hero, item in self.hero_items.items():
                if item is None: continue
                try:
                    is_now_selected = (hero in current_logic_selection)
                    if item.isSelected() != is_now_selected:
                        item.setSelected(is_now_selected)
                except RuntimeError: pass # Игнорируем ошибку, если виджет удален
                except Exception as e: print(f"[ERROR] updating selection state for {hero}: {e}")
            # Обновляем счетчик выбранных героев (на всякий случай)
            self._update_selected_label()
        finally:
            try:
                if self.right_list_widget: list_widget.blockSignals(False)
            except RuntimeError: pass
            self.is_programmatically_updating_selection = False


    def _update_priority_labels(self):
        """Обновляет фон для приоритетных героев."""
        # Эта логика пока убрана, т.к. фон мешал выделению.
        # Можно вернуть, если придумать, как комбинировать стили.
        pass # Пока не используем отдельный фон для приоритета

    # --- Обработчики событий UI ---
    def handle_selection_changed(self):
        """Обрабатывает сигнал itemSelectionChanged от QListWidget."""
        if self.is_programmatically_updating_selection: return
        if not self.right_list_widget: return

        print("[UI Event] Selection changed by user.")
        current_ui_selection_names = set()
        for item in self.right_list_widget.selectedItems():
            hero_name = item.data(HERO_NAME_ROLE);
            if hero_name: current_ui_selection_names.add(hero_name)

        # Обновляем логику только если выбор изменился
        if set(self.logic.selected_heroes) != current_ui_selection_names:
            self.logic.set_selection(current_ui_selection_names)
            self.update_ui_after_logic_change() # Полное обновление UI

    def show_priority_context_menu(self, pos):
        """Показывает контекстное меню для установки/снятия приоритета."""
        if not self.right_list_widget or not self.right_list_widget.isVisible(): return
        list_widget = self.right_list_widget
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
        priority_action.setEnabled(is_selected) # Доступно только для выбранных

        action = menu.exec(global_pos)
        if priority_action and action == priority_action:
            if hero_name in self.logic.selected_heroes: # Еще раз проверяем
                self.logic.set_priority(hero_name)
                self.update_ui_after_logic_change() # Обновляем UI
            else: print(f"Cannot change priority for '{hero_name}' as it's not selected.")

    # --- Язык ---
    def switch_language(self, lang_code: str):
        """Переключает язык интерфейса."""
        print(f"[Language] Attempting to switch to {lang_code}")
        if self.logic.DEFAULT_LANGUAGE != lang_code:
            set_language(lang_code) # Устанавливаем глобально
            self.logic.DEFAULT_LANGUAGE = lang_code # Обновляем в логике
            self.update_language() # Обновляем тексты в текущем UI
            self.update_ui_after_logic_change() # Пересчитываем и обновляем панели
            # Восстанавливаем фокус хоткея после обновления UI
            if self.hotkey_cursor_index != -1:
                QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))
        else:
            print(f"[Language] Already set to {lang_code}")

    def update_language(self):
        """Обновляет тексты всех элементов интерфейса."""
        print("[LOG] update_language called")
        self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
        # Обновляем TopPanel
        if self.top_panel_instance: self.top_panel_instance.update_language()
        # Обновляем RightPanel (если она есть)
        if self.right_panel_instance: self.right_panel_instance.update_language()
        # Обновляем LeftPanel (result_label)
        if self.result_label and not self.logic.selected_heroes:
             self.result_label.setText(get_text('no_heroes_selected', language=self.logic.DEFAULT_LANGUAGE))
        # Обновляем горизонтальный список (если он показывает текст)
        # update_horizontal_icon_list(self) # Вызывается из update_ui_after_logic_change

        # Обновляем подсказки в QListWidget (если он есть)
        if self.right_list_widget and self.right_list_widget.isVisible():
            # Сохраняем текущую фокусную подсказку
            focused_tooltip = None
            if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
                 try:
                     focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
                     if focused_item: focused_tooltip = focused_item.toolTip()
                 except RuntimeError: pass

            # Обновляем базовые подсказки
            for i in range(self.right_list_widget.count()):
                 try:
                    item = self.right_list_widget.item(i)
                    if item:
                        hero_name = item.data(HERO_NAME_ROLE)
                        if hero_name: item.setToolTip(hero_name)
                 except RuntimeError: continue

            # Восстанавливаем фокусную подсказку
            if focused_tooltip and ">>>" in focused_tooltip and 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
                try:
                    current_focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
                    if current_focused_item: current_focused_item.setToolTip(focused_tooltip)
                except RuntimeError: pass


    # --- Утилиты UI ---
    def _calculate_columns(self):
        """Вычисляет количество колонок для QListWidget."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min':
            self._num_columns_cache = 1; return 1
        try:
            # Используем viewport для более точных расчетов
            viewport = self.right_list_widget.viewport()
            if not viewport: return self._num_columns_cache

            vp_width = viewport.width()
            # Учитываем рамку и отступы самого QListWidget, если они есть
            # margins = self.right_list_widget.contentsMargins() # Не совсем то
            # border = self.right_list_widget.frameWidth() * 2 # Ширина рамки * 2
            # effective_width = vp_width - border

            grid_w = self.right_list_widget.gridSize().width()
            spacing = self.right_list_widget.spacing()

            if grid_w <= 0: return self._num_columns_cache
            # Ширина элемента = ширина сетки + расстояние между элементами
            # (spacing применяется между элементами, не вокруг)
            eff_grid_w = grid_w + spacing

            if eff_grid_w <= 0: return self._num_columns_cache
            # Рассчитываем количество колонок, помещающихся в ширину viewport'а
            cols = max(1, int(vp_width / eff_grid_w))

            # Отладка расчета колонок
            # print(f"[DEBUG] Cols calculation: vp_w={vp_width}, grid_w={grid_w}, spacing={spacing}, eff_grid_w={eff_grid_w}, cols={cols}")

            self._num_columns_cache = cols; return cols
        except Exception as e: print(f"[ERROR] Calculating columns: {e}"); return self._num_columns_cache


    def _update_hotkey_highlight(self, old_index=None):
        """Обновляет подсветку (рамку и подсказку) для фокуса хоткея."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        list_widget = self.right_list_widget; count = list_widget.count()
        if count == 0: return

        needs_viewport_update = False
        new_index = self.hotkey_cursor_index

        # --- Восстанавливаем старую подсказку ---
        if old_index is not None and old_index != new_index and 0 <= old_index < count:
            try:
                old_item = list_widget.item(old_index)
                if old_item:
                    hero_name = old_item.data(HERO_NAME_ROLE)
                    if hero_name and ">>>" in old_item.toolTip():
                        old_item.setToolTip(hero_name) # Убираем фокусную метку
                        needs_viewport_update = True # Нужно перерисовать, чтобы рамка исчезла
            except Exception as e: print(f"[ERROR] Restoring old tooltip (idx {old_index}): {e}")

        # --- Устанавливаем новую подсказку ---
        if 0 <= new_index < count:
            try:
                new_item = list_widget.item(new_index)
                if new_item:
                    hero_name = new_item.data(HERO_NAME_ROLE)
                    focus_tooltip = f">>> {hero_name} <<<"
                    if hero_name and new_item.toolTip() != focus_tooltip:
                        new_item.setToolTip(focus_tooltip)
                        needs_viewport_update = True
                    # Прокрутка к элементу
                    list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
            except Exception as e: print(f"[ERROR] Setting new tooltip (idx {new_index}): {e}")

        # --- Запрашиваем перерисовку viewport ---
        # Перерисовываем всегда при смене индекса или если меняли подсказку
        if needs_viewport_update or old_index != new_index:
            # print(f"[Viewport Update] Triggered. Old: {old_index}, New: {new_index}")
            list_widget.viewport().update()


    # --- Управление слушателем клавиатуры ---
    def start_keyboard_listener(self):
        """Запускает поток прослушивания клавиатуры."""
        if not keyboard: return # Не запускаем, если библиотека не импортирована
        if self._keyboard_listener_thread is None or not self._keyboard_listener_thread.is_alive():
            print("Starting keyboard listener thread...")
            self._stop_keyboard_listener_flag.clear()
            self._keyboard_listener_thread = threading.Thread(target=self._keyboard_listener_loop, daemon=True)
            self._keyboard_listener_thread.start()
        else: print("Keyboard listener already running.")

    def stop_keyboard_listener(self):
        """Останавливает поток прослушивания клавиатуры."""
        if not keyboard: return
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
            print("Signalling keyboard listener to stop...")
            self._stop_keyboard_listener_flag.set()
            # Пытаемся "разбудить" поток, если он ждет (зависит от keyboard.wait)
            # keyboard.press_and_release('esc') # Пример "пробуждения"
        else: print("Keyboard listener not running or already stopped.")

    def _keyboard_listener_loop(self):
        """Цикл прослушивания клавиатуры (выполняется в отдельном потоке)."""
        print("Keyboard listener thread started.")

        # --- Обертка для вызова слотов в GUI потоке ---
        def run_in_gui_thread(func, *args):
            # Вызываем функцию в основном потоке через QTimer
            # Это БЕЗОПАСНО для любых действий с UI
            QTimer.singleShot(0, lambda: func(*args))

        # --- Проверка условия Topmost + Вызов в GUI ---
        def run_if_topmost_gui(func, *args):
            # Проверяем флаг WinAPI, если доступен, иначе флаг Qt
            is_topmost = self.win_api_manager.is_win_topmost if winapi_user32 else bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
            if is_topmost:
                try:
                    run_in_gui_thread(func, *args) # Вызываем в потоке GUI
                except Exception as e:
                    print(f"[ERROR] Exception scheduling hotkey callback: {e}")
            # else: print("[Hotkey] Blocked (window not topmost)") # Отладка

        # --- Регистрация хуков ---
        hooks_registered = []
        try:
            print(f"Registering keyboard hooks...")
            # --- Навигация ---
            keyboard.add_hotkey('tab+up', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'up'), suppress=True)
            keyboard.add_hotkey('tab+down', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'down'), suppress=True)
            keyboard.add_hotkey('tab+left', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'left'), suppress=True)
            keyboard.add_hotkey('tab+right', lambda: run_if_topmost_gui(self.move_cursor_signal.emit, 'right'), suppress=True)
            hooks_registered.extend(['tab+up', 'tab+down', 'tab+left', 'tab+right'])

            # --- Выбор (Num 0 / Keypad 0) ---
            try: keyboard.add_hotkey('tab+num 0', lambda: run_if_topmost_gui(self.toggle_selection_signal.emit), suppress=True); hooks_registered.append('tab+num 0')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+keypad 0', lambda: run_if_topmost_gui(self.toggle_selection_signal.emit), suppress=True); hooks_registered.append('tab+keypad 0')
            except ValueError: print("[WARN] Could not hook Tab + Num 0 / Keypad 0.")

            # --- Смена режима (Delete / Del / Numpad .) ---
            try: keyboard.add_hotkey('tab+delete', lambda: run_if_topmost_gui(self.toggle_mode_signal.emit), suppress=True); hooks_registered.append('tab+delete')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+del', lambda: run_if_topmost_gui(self.toggle_mode_signal.emit), suppress=True); hooks_registered.append('tab+del')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+.', lambda: run_if_topmost_gui(self.toggle_mode_signal.emit), suppress=True); hooks_registered.append('tab+.')
            except ValueError: print("[WARN] Could not hook Tab + Delete / Del / Numpad .")

            # --- Очистка (Num - / Keypad - / -) ---
            try: keyboard.add_hotkey('tab+num -', lambda: run_if_topmost_gui(self.clear_all_signal.emit), suppress=True); hooks_registered.append('tab+num -')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+keypad -', lambda: run_if_topmost_gui(self.clear_all_signal.emit), suppress=True); hooks_registered.append('tab+keypad -')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+-', lambda: run_if_topmost_gui(self.clear_all_signal.emit), suppress=True); hooks_registered.append('tab+-')
            except ValueError: print("[WARN] Could not hook Tab + Num - / Keypad - / -.")

            # --- Распознавание (Num / / Keypad /) ---
            try: keyboard.add_hotkey('tab+num /', lambda: run_if_topmost_gui(self.recognize_heroes_signal.emit), suppress=True); hooks_registered.append('tab+num /')
            except ValueError: pass
            try: keyboard.add_hotkey('tab+keypad /', lambda: run_if_topmost_gui(self.recognize_heroes_signal.emit), suppress=True); hooks_registered.append('tab+keypad /')
            except ValueError: print("[WARN] Could not hook Tab + Num / or Keypad /.")

            print(f"Hotkeys registered: {len(hooks_registered)}")

            # --- Ожидание сигнала остановки ---
            self._stop_keyboard_listener_flag.wait() # Поток будет здесь, пока не установят флаг
            print("Keyboard listener stop signal received.")

        except ImportError: print("\n[ERROR] 'keyboard' library requires root/admin privileges.\n")
        except Exception as e: print(f"[ERROR] Error in keyboard listener setup: {e}")
        finally:
            print("Unhooking all keyboard hotkeys...")
            keyboard.unhook_all() # Удаляем все зарегистрированные хуки
            print("Keyboard listener thread finished.")
