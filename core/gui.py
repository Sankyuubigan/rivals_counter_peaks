# File: gui.py
import time
import threading
import keyboard
import sys

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame,
                               QLabel, QPushButton, QApplication, QListWidget, QListWidgetItem, QMenu,
                               QAbstractItemView, QStyle, QComboBox, QScrollArea, QMessageBox) # Добавлен QMessageBox
from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QPoint, QModelIndex, QEvent, QThread, QObject
from PySide6.QtGui import QColor, QPalette, QIcon, QBrush, QMouseEvent
from top_panel import create_top_panel
from right_panel import create_right_panel, HERO_NAME_ROLE
from left_panel import create_left_panel
from utils_gui import copy_to_clipboard
# from build import version # Версия теперь берется из logic или os.environ
from logic import CounterpickLogic, TEAM_SIZE
from images_load import get_images_for_mode, SIZES, load_hero_templates
from translations import get_text, set_language, DEFAULT_LANGUAGE, TRANSLATIONS, SUPPORTED_LANGUAGES
from mode_manager import change_mode, update_interface_for_mode
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes
from display import generate_counterpick_display, generate_minimal_icon_list
# <<< ДОБАВЛЕНО: Импорты для распознавания >>>
from utils import capture_screen_area, RECOGNITION_AREA, RECOGNITION_THRESHOLD
# <<< ------------------------------------ >>>
import os # Для получения версии из окружения

# <<< ДОБАВЛЕНО: Импорты для Win32 API >>>
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    # Константы для SetWindowPos
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    # Загружаем user32.dll
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        # Определяем прототип функции SetWindowPos
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, # hWnd
            wintypes.HWND, # hWndInsertAfter
            wintypes.INT,  # X
            wintypes.INT,  # Y
            wintypes.INT,  # cx
            wintypes.INT,  # cy
            wintypes.UINT  # uFlags
        ]
    except Exception as e:
        print(f"[WARN] Не удалось загрузить user32.dll или SetWindowPos: {e}")
        user32 = None # Помечаем, что API недоступно
else:
    user32 = None # Не Windows
# <<< КОНЕЦ ДОБАВЛЕННОГО >>>

# <<< ДОБАВЛЕНО: Worker для распознавания в отдельном потоке >>>
class RecognitionWorker(QObject):
    finished = Signal(list) # Сигнал завершения, передает список распознанных героев
    error = Signal(str)     # Сигнал ошибки

    def __init__(self, logic, area, threshold, hero_templates):
        super().__init__()
        self.logic = logic
        self.area = area
        self.threshold = threshold
        self.hero_templates = hero_templates
        self._is_running = True

    @Slot() # Добавляем декоратор Slot
    def run(self): # Меняем название для ясности
        print("[THREAD] Recognition worker started.")
        recognized_heroes = []
        try:
            if not self._is_running: return # Проверка перед началом работы

            screenshot_cv2 = capture_screen_area(self.area)
            if screenshot_cv2 is None:
                # Используем язык из logic
                raise ValueError(get_text('recognition_no_screenshot', language=self.logic.DEFAULT_LANGUAGE))

            if not self.hero_templates:
                 # Используем язык из logic
                 raise ValueError(get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))

            if not self._is_running: return # Проверка перед распознаванием

            recognized_heroes = self.logic.recognize_heroes_from_image(
                screenshot_cv2,
                self.hero_templates,
                self.threshold
            )

            if self._is_running: # Финальная проверка перед отправкой сигнала
                self.finished.emit(recognized_heroes)

        except Exception as e:
            print(f"[THREAD ERROR] Ошибка в потоке распознавания: {e}")
            if self._is_running:
                self.error.emit(str(e))
        finally:
             print(f"[THREAD] Recognition worker finished. Found: {recognized_heroes}")

    def stop(self):
        print("[THREAD] Stopping recognition worker...")
        self._is_running = False
# <<< КОНЕЦ WORKER >>>

# --- Класс MainWindow ---
class MainWindow(QMainWindow):
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()
    toggle_mode_signal = Signal()
    clear_all_signal = Signal()
    # <<< ДОБАВЛЕНО: Сигнал для распознавания >>>
    recognize_heroes_signal = Signal()
    # <<< ------------------------------------ >>>
    # <<< ДОБАВЛЕНО: Сигнал для обновления UI после распознавания >>>
    recognition_complete_signal = Signal(list)
    # <<< -------------------------------------------------------- >>>


    def __init__(self):
        super().__init__()
        # Получаем версию из переменной окружения, установленной в build.py
        self.app_version = os.environ.get("APP_VERSION", "N/A")
        self.logic = CounterpickLogic()
        # Передаем версию в logic
        self.logic.APP_VERSION = self.app_version

        self.mode = "middle" # Начальный режим
        self.initial_pos = None # Начальная позиция окна
        self.mode_positions = {"max": None, "middle": None, "min": None} # Позиции для каждого режима
        self.copy_to_clipboard = lambda: copy_to_clipboard(self.logic)
        self._is_win_topmost = False # Флаг для WinAPI Topmost

        # Атрибуты UI (инициализируем как None)
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_frame, self.author_button, self.rating_button = None, None, None
        self.main_widget, self.inner_layout, self.left_container = None, None, None
        self.icons_scroll_area = None
        self.icons_scroll_content = None
        self.icons_scroll_content_layout = None
        self.canvas, self.result_frame, self.result_label = None, None, None
        self.update_scrollregion = lambda: None # Placeholder
        self.right_frame, self.selected_heroes_label = None, None
        self.right_list_widget = None
        self.hero_items = {} # Словарь для хранения QListWidgetItem'ов
        self.is_programmatically_updating_selection = False # Флаг для предотвращения рекурсии

        # Атрибуты для горячих клавиш
        self.hotkey_cursor_index = -1 # Индекс элемента под фокусом хоткея (-1 = нет фокуса)
        self._keyboard_listener_thread = None # Поток для листенера keyboard
        self._stop_keyboard_listener_flag = threading.Event() # Флаг для остановки листенера
        self._num_columns_cache = 1 # Кэш количества колонок в QListWidget

        # <<< ДОБАВЛЕНО: Атрибуты для распознавания >>>
        self.hero_templates = {} # Загруженные шаблоны
        self._recognition_thread = None # Поток для распознавания
        self._recognition_worker = None # Объект Worker'а
        # <<< ------------------------------------ >>>

        # Атрибуты для перемещения окна без рамки
        self._mouse_pressed = False
        self._old_pos = None

        # <<< ДОБАВЛЕНО: Загрузка шаблонов при инициализации >>>
        self.load_templates()
        # <<< ---------------------------------------------- >>>

        # Инициализация UI и запуск листенера
        self.init_ui()
        self.start_keyboard_listener()

    # --- Перемещение окна без рамки ---
    def mousePressEvent(self, event: QMouseEvent):
        # Разрешаем перемещение только в min режиме и только если зажали top_frame
        if self.mode == "min" and self.top_frame and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_pressed = True
                self._old_pos = event.globalPosition().toPoint() # Запоминаем глобальную позицию
                event.accept() # Говорим, что обработали событие
                return # Выходим, чтобы не передавать дальше
        self._mouse_pressed = False # Сбрасываем флаг в остальных случаях
        super().mousePressEvent(event) # Вызываем стандартный обработчик

    def mouseMoveEvent(self, event: QMouseEvent):
        # Перемещаем окно, только если зажата кнопка в min режиме
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint() # Обновляем позицию
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        # Сбрасываем флаги при отпускании левой кнопки
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False
            self._old_pos = None
            event.accept()
            return
        super().mouseReleaseEvent(event)
    # ------------------------------------

    # --- Управление Topmost через WinAPI ---
    def set_topmost_winapi(self, enable: bool):
        """Устанавливает или снимает состояние HWND_TOPMOST с помощью WinAPI."""
        if not user32: # Если API недоступно (не Windows или ошибка загрузки)
            print("[INFO] WinAPI недоступно. Используется стандартный флаг Qt.")
            # Возвращаемся к стандартному поведению Qt как запасной вариант
            current_flags = self.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            if enable != flag_set:
                self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                self._is_win_topmost = enable
                # Показываем окно, чтобы флаг применился, но делаем это безопасно
                try:
                    if self.isVisible(): self.show()
                except RuntimeError: pass # Игнорируем ошибку, если виджет уже удален
            # Обновляем кнопку в любом случае
            self._update_topmost_button_visuals()
            return # Выходим, т.к. WinAPI не используется

        # Используем WinAPI
        hwnd = self.winId()
        # Ждем HWND, если его нет сразу (окно может еще не быть полностью создано)
        wait_count = 0
        while not hwnd and wait_count < 10: # Ждем до 1 секунды (10 * 100мс)
            print("[WARN] HWND не получен, ожидание...")
            QApplication.processEvents() # Обрабатываем события
            time.sleep(0.1)
            hwnd = self.winId()
            wait_count += 1

        if not hwnd:
            print("[ERROR] Не удалось получить HWND окна для SetWindowPos после ожидания.")
            # Пытаемся использовать Qt как fallback
            current_flags = self.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            if enable != flag_set:
                self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                self._is_win_topmost = enable
                try:
                     if self.isVisible(): self.show()
                except RuntimeError: pass
            self._update_topmost_button_visuals()
            return

        # Определяем параметры для SetWindowPos
        insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
        flags = SWP_NOMOVE | SWP_NOSIZE # Не меняем позицию и размер

        print(f"[API] Вызов SetWindowPos: HWND={hwnd}, InsertAfter={'TOPMOST' if enable else 'NOTOPMOST'}, Flags={flags}")
        success = user32.SetWindowPos(int(hwnd), insert_after, 0, 0, 0, 0, flags)

        if success:
            print(f"[API] SetWindowPos успешно: Topmost {'включен' if enable else 'выключен'}.")
            self._is_win_topmost = enable
            # Убедимся, что флаг Qt соответствует (для консистентности, хотя API главнее)
            # if self.windowFlags() & Qt.WindowStaysOnTopHint != enable:
            #     self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
            #     try:
            #          if self.isVisible(): self.show()
            #     except RuntimeError: pass
        else:
            error_code = ctypes.get_last_error()
            print(f"[API ERROR] SetWindowPos не удался: Код ошибки {error_code}")
            # Пытаемся использовать стандартный флаг Qt как fallback
            print("[API ERROR] Попытка использовать Qt.WindowStaysOnTopHint как fallback.")
            current_flags = self.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            if enable != flag_set:
                self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                self._is_win_topmost = enable
                try:
                    if self.isVisible(): self.show()
                except RuntimeError: pass
            else: # Если флаг уже был в нужном состоянии
                 self._is_win_topmost = enable # Устанавливаем флаг в соответствии с попыткой

        # Обновляем кнопку в top_panel после изменения состояния
        self._update_topmost_button_visuals()

    def _update_topmost_button_visuals(self):
        """Обновляет вид кнопки topmost."""
        try:
            if self.top_frame:
                topmost_button = self.top_frame.findChild(QPushButton, "topmost_button")
                if topmost_button:
                    # Вызываем метод обновления, сохраненный в кнопке
                    update_func = getattr(topmost_button, '_update_visual_state', None)
                    if callable(update_func):
                        update_func()
        except Exception as e:
            print(f"[WARN] Не удалось обновить вид кнопки topmost: {e}")


    def toggle_topmost_winapi(self):
        """Переключает состояние Topmost с помощью WinAPI."""
        self.set_topmost_winapi(not self._is_win_topmost)
    # --- Конец Управление Topmost ---

    # <<< ДОБАВЛЕНО: Метод загрузки шаблонов >>>
    def load_templates(self):
        print("Загрузка шаблонов героев для распознавания...")
        try:
            # Функция из images_load.py использует кэш
            self.hero_templates = load_hero_templates()
            if not self.hero_templates:
                print("[WARN] Шаблоны героев не найдены или не удалось загрузить.")
            else:
                print(f"Загружено шаблонов для {len(self.hero_templates)} героев.")
        except Exception as e:
            print(f"[ERROR] Критическая ошибка при загрузке шаблонов: {e}")
            self.hero_templates = {} # Очищаем на случай ошибки
    # <<< ----------------------------------- >>>

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{self.app_version}") # Используем версию из атрибута
        self.setGeometry(100, 100, 950, 350); self.setMinimumSize(400, 100)
        self.initial_pos = self.pos(); self.mode_positions["middle"] = self.pos() # Сохраняем начальную позицию для среднего режима

        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        # Создаем верхнюю панель
        (self.top_frame, self.author_button, self.rating_button, _) = create_top_panel(self, self.change_mode, self.logic)
        self.main_layout.addWidget(self.top_frame)

        # Создаем панель для горизонтального списка иконок
        self.icons_scroll_area = QScrollArea(); self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f0f0f0; }") # Стиль панели
        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_scroll_content_layout.setObjectName("icons_scroll_content_layout")
        self.icons_scroll_content_layout.setContentsMargins(5, 2, 5, 2); self.icons_scroll_content_layout.setSpacing(4); self.icons_scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)

        # Расчет высоты панели иконок
        try:
            if not self.horizontal_images: # Загружаем, если еще не загружены
                 _, _, _, self.horizontal_images = get_images_for_mode(self.mode)
            h_icon_h = SIZES[self.mode]['horizontal'][1] if self.mode in SIZES and 'horizontal' in SIZES[self.mode] else 30
            icons_frame_height = h_icon_h + 12 # Добавляем отступы (5+5 + 2 для содержимого)
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки/расчета изображений в init_ui: {e}")
            icons_frame_height = 42 # Fallback
            self.horizontal_images = {} # Сбрасываем, если ошибка
        self.icons_scroll_area.setFixedHeight(icons_frame_height) # Устанавливаем фиксированную высоту
        self.main_layout.addWidget(self.icons_scroll_area) # Добавляем панель иконок под верхнюю панель

        # Основной виджет для левой и правой панелей
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
        self.inner_layout.setContentsMargins(0, 0, 0, 0); self.inner_layout.setSpacing(0) # Без отступов и расстояний
        self.main_layout.addWidget(self.main_widget, stretch=1) # Этот виджет будет растягиваться

        # Создание левой и правой панелей происходит в update_interface_for_mode
        # Мы вызываем ее в конце init_ui

        # Callback для смены языка (сохраняем в атрибуте)
        self.switch_language_callback = lambda lang: self.switch_language(lang)
        # Первоначальная настройка интерфейса под текущий режим
        update_interface_for_mode(self)

        # --- Подключение сигналов ---
        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)
        self.toggle_mode_signal.connect(self._handle_toggle_mode)
        self.clear_all_signal.connect(self._handle_clear_all)
        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        self.recognition_complete_signal.connect(self._on_recognition_complete)
        # --- Конец подключения сигналов ---

        # Установка начального фокуса хоткея, если нужно
        if self.right_list_widget and self.right_list_widget.count() > 0 and self.mode != 'min':
            self.hotkey_cursor_index = 0
            # Обновляем подсветку с небольшой задержкой, чтобы UI успел отрисоваться
            QTimer.singleShot(100, lambda: self._update_hotkey_highlight(None))

    # --- HOTKEY RELATED METHODS ---

    def _calculate_columns(self):
        """Вычисляет количество колонок в QListWidget."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min':
            self._num_columns_cache = 1; return 1
        try:
            vp_width = self.right_list_widget.viewport().width()
            grid_w = self.right_list_widget.gridSize().width()
            spacing = self.right_list_widget.spacing()
            # Учитываем внутренние отступы viewport'а
            margins = self.right_list_widget.viewportMargins()
            effective_width = vp_width - margins.left() - margins.right() - 5 # Небольшой запас

            if grid_w <= 0: return self._num_columns_cache # Защита от деления на ноль
            # Эффективная ширина элемента сетки = ширина + расстояние между элементами
            eff_grid_w = grid_w + spacing
            if eff_grid_w <= 0: return self._num_columns_cache # Защита от деления на ноль

            cols = max(1, int(effective_width / eff_grid_w))
            # print(f"[DEBUG] Cols calculation: vp_w={vp_width}, eff_w={effective_width}, grid_w={grid_w}, spacing={spacing}, eff_grid_w={eff_grid_w}, cols={cols}")
            self._num_columns_cache = cols; return cols
        except Exception as e: print(f"[ERROR] Calculating columns: {e}"); return self._num_columns_cache


    def _update_hotkey_highlight(self, old_index=None):
        """Обновляет подсветку (через делегата) и тултип элемента под фокусом хоткея."""
        # print(f"[LOG] _update_hotkey_highlight called: old={old_index}, new={self.hotkey_cursor_index}") # DEBUG LOG
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min':
            # Если виджета нет или режим min, убедимся, что старый фокус снят
            if old_index is not None and self.right_list_widget and 0 <= old_index < self.right_list_widget.count():
                try:
                     old_item = self.right_list_widget.item(old_index)
                     if old_item:
                         hero_name = old_item.data(HERO_NAME_ROLE)
                         if hero_name and ">>>" in old_item.toolTip():
                             old_item.setToolTip(hero_name)
                             self.right_list_widget.viewport().update() # Запросить перерисовку для удаления рамки
                except Exception as e: print(f"[ERROR] processing old item index {old_index} on clear: {e}")
            return

        list_widget = self.right_list_widget; count = list_widget.count()
        if count == 0: return

        needs_viewport_update = False
        new_index = self.hotkey_cursor_index # Используем текущий индекс

        # Восстановление подсказки старого элемента (если он не новый фокус)
        if old_index is not None and old_index != new_index and 0 <= old_index < count:
            try:
                old_item = list_widget.item(old_index)
                if old_item:
                    hero_name = old_item.data(HERO_NAME_ROLE)
                    if hero_name and ">>>" in old_item.toolTip(): # Если была фокусная подсказка
                        old_item.setToolTip(hero_name) # Восстанавливаем базовую
                        needs_viewport_update = True
            except RuntimeError: pass # Виджет мог быть удален
            except Exception as e: print(f"[ERROR] processing old item index {old_index}: {e}")

        # Установка подсказки нового элемента
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
            except RuntimeError: pass # Виджет мог быть удален
            except Exception as e: print(f"[ERROR] processing new item index {new_index}: {e}")

        # Обновляем viewport, если изменился тултип или индекс
        # Это заставит делегата перерисовать рамки
        if needs_viewport_update or old_index != new_index:
             # print("[LOG] Calling list_widget.viewport().update()") # DEBUG LOG
             try:
                 list_widget.viewport().update() # Вызываем обновление видимой области
             except RuntimeError: pass # Игнорируем, если виджет удален


    @Slot(str)
    def _handle_move_cursor(self, direction):
        """Обрабатывает перемещение фокуса горячими клавишами."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        list_widget = self.right_list_widget; count = list_widget.count()
        if count == 0: return

        old_index = self.hotkey_cursor_index
        num_columns = self._calculate_columns() # Получаем АКТУАЛЬНОЕ число колонок
        # print(f"[LOG] _handle_move_cursor: direction={direction}, old_index={old_index}, num_columns={num_columns}") # LOG

        if self.hotkey_cursor_index < 0: new_index = 0 # Если фокуса нет, начинаем с первого
        else:
            current_row = self.hotkey_cursor_index // num_columns; current_col = self.hotkey_cursor_index % num_columns
            new_index = self.hotkey_cursor_index

            # --- ЛОГИКА ПЕРЕМЕЩЕНИЯ ---
            if direction == 'left':
                if current_col > 0: new_index -= 1
                # Переход на правый край предыдущей строки (или последней строки)
                elif current_row > 0: # Если не первая строка
                    new_index = (current_row - 1) * num_columns + (num_columns - 1)
                    new_index = min(new_index, count - 1) # Убедимся, что не вышли за последнюю строку
                else: # Первая строка, переход на конец последней
                    new_index = count - 1

            elif direction == 'right':
                if current_col < num_columns - 1: new_index += 1
                 # Переход на левый край следующей строки (или первой)
                elif self.hotkey_cursor_index < count - 1: # Если не последний элемент
                    new_index = (current_row + 1) * num_columns
                else: # Последний элемент, переход на первый
                    new_index = 0
                new_index = min(new_index, count - 1) # Убеждаемся, что не вышли за пределы

            elif direction == 'up':
                new_index -= num_columns
                # Переход на последнюю строку, если ушли вверх с первой
                if new_index < 0:
                     # Вычисляем индекс в последней строке с тем же столбцом (или правее, если там нет элемента)
                     last_row_index = (count - 1) // num_columns
                     potential_index = last_row_index * num_columns + current_col
                     new_index = min(potential_index, count - 1) # Берем либо рассчитанный, либо последний элемент

            elif direction == 'down':
                new_index += num_columns
                # Переход на первую строку, если ушли вниз с последней
                if new_index >= count:
                    new_index = current_col # Индекс в первой строке с тем же столбцом
                    # Если в первой строке нет такого столбца (она короче), берем первый элемент
                    if new_index >= count: new_index = 0

            # Общая проверка на выход за границы
            new_index = max(0, min(count - 1, new_index))
        # print(f"[LOG] --> new_index={new_index}") # LOG
        if old_index != new_index:
            self.hotkey_cursor_index = new_index
            self._update_hotkey_highlight(old_index) # Обновляем подсветку
        # Если индекс не изменился, но элемент мог быть за пределами видимости
        elif 0 <= self.hotkey_cursor_index < count:
             try:
                current_item = list_widget.item(self.hotkey_cursor_index)
                if current_item: list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)
             except RuntimeError: pass


    @Slot()
    def _handle_toggle_selection(self):
        """Обрабатывает выбор/снятие выбора горячей клавишей."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
            try:
                item = self.right_list_widget.item(self.hotkey_cursor_index)
                if item:
                     # Инвертируем состояние выделения
                     item.setSelected(not item.isSelected())
                     # handle_selection_changed вызовется автоматически сигналом itemSelectionChanged
            except RuntimeError: pass # Окно/виджет могли быть удалены
            except Exception as e: print(f"Error toggling selection: {e}")

    @Slot()
    def _handle_toggle_mode(self):
        """Переключает режим между min и middle/max по горячей клавише."""
        print("[LOG] _handle_toggle_mode called") # LOG
        if self.mode == "min":
            print("[LOG] --> Switching to middle mode") # LOG
            self.change_mode("middle")
        else: # Включая middle и max
            print("[LOG] --> Switching to min mode") # LOG
            self.change_mode("min")

    @Slot()
    def _handle_clear_all(self):
        """Обрабатывает сигнал очистки от горячей клавиши."""
        print("[LOG] _handle_clear_all called") # LOG
        self.logic.clear_all()
        self.update_ui_after_logic_change()
        # Сброс фокуса хоткея на первый элемент (или -1, если список пуст)
        if self.right_list_widget and self.right_list_widget.isVisible() and self.mode != 'min':
            old_index = self.hotkey_cursor_index
            count = self.right_list_widget.count()
            self.hotkey_cursor_index = 0 if count > 0 else -1
            # Обновляем подсветку только если индекс изменился или был сброшен
            if self.hotkey_cursor_index != old_index or old_index == -1:
                 self._update_hotkey_highlight(old_index)
        else:
            self.hotkey_cursor_index = -1

    # <<< ДОБАВЛЕНО: Слот для запуска распознавания >>>
    @Slot()
    def _handle_recognize_heroes(self):
        """Запускает процесс распознавания героев в отдельном потоке."""
        print("[ACTION] Запрос на распознавание героев...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            print("[WARN] Процесс распознавания уже запущен.")
            QMessageBox.information(self, "Распознавание", "Процесс распознавания уже выполняется.")
            return

        if not self.hero_templates:
             print("[ERROR] Шаблоны героев не загружены. Распознавание невозможно.")
             QMessageBox.warning(self, get_text('error'), get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))
             return

        # Создаем и запускаем поток
        self._recognition_worker = RecognitionWorker(
            self.logic,
            RECOGNITION_AREA,
            RECOGNITION_THRESHOLD,
            self.hero_templates
        )
        self._recognition_thread = QThread(self) # Указываем родителя для управления жизненным циклом
        self._recognition_worker.moveToThread(self._recognition_thread)

        # Подключаем сигналы потока и воркера
        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self.recognition_complete_signal.emit) # Перенаправляем сигнал в основной поток
        self._recognition_worker.error.connect(self._on_recognition_error) # Обработка ошибок в основном потоке

        # Очистка после завершения потока (важно для избежания утечек)
        self._recognition_worker.finished.connect(self._recognition_thread.quit)
        self._recognition_worker.finished.connect(self._recognition_worker.deleteLater) # Удаляем воркер
        self._recognition_thread.finished.connect(self._recognition_thread.deleteLater) # Удаляем поток
        self._recognition_thread.finished.connect(self._reset_recognition_thread) # Сбрасываем ссылки

        self._recognition_thread.start()
        print("[INFO] Поток распознавания запущен.")

    @Slot()
    def _reset_recognition_thread(self):
        """Сбрасывает ссылки на поток и воркер после завершения."""
        print("[INFO] Сброс ссылок на поток распознавания.")
        self._recognition_thread = None
        self._recognition_worker = None

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes):
        """Обрабатывает результат успешного распознавания."""
        print(f"[RESULT] Распознавание завершено. Распознанные герои: {recognized_heroes}")
        if recognized_heroes:
            # Устанавливаем выбор в логике (полностью заменяем текущий выбор врагов)
            self.logic.set_selection(set(recognized_heroes))
            # Обновляем UI
            self.update_ui_after_logic_change()
            # Показываем сообщение об успехе (опционально)
            # QMessageBox.information(self, "Распознавание", f"Распознанные герои: {', '.join(recognized_heroes)}")
        else:
            print("[INFO] Герои не распознаны или список пуст.")
            # Показываем сообщение пользователю
            QMessageBox.information(self, "Распознавание", get_text('recognition_failed', language=self.logic.DEFAULT_LANGUAGE))

    @Slot(str)
    def _on_recognition_error(self, error_message):
        """Обрабатывает ошибку во время распознавания."""
        print(f"[ERROR] Ошибка во время распознавания: {error_message}")
        # Показываем ошибку пользователю
        QMessageBox.warning(self, get_text('error', language=self.logic.DEFAULT_LANGUAGE), f"{get_text('recognition_error_prefix', language=self.logic.DEFAULT_LANGUAGE)}\n{error_message}")
    # <<< КОНЕЦ Слотов распознавания >>>

    # --- Keyboard Listener Loop and Start/Stop/Close ---
    def _keyboard_listener_loop(self):
        """Цикл прослушивания клавиатуры в отдельном потоке."""
        print("Keyboard listener thread started.")

        # Декоратор для проверки topmost и вызова в GUI потоке
        def run_if_topmost_gui(func):
            def wrapper(*args, **kwargs):
                # Проверяем флаг WinAPI, если доступен, иначе флаг Qt
                is_topmost = self._is_win_topmost if user32 else bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
                if is_topmost:
                    try:
                        # Выполняем действие в основном потоке GUI через QTimer.singleShot
                        QTimer.singleShot(0, lambda: func(*args, **kwargs))
                    except Exception as e:
                        print(f"[ERROR] Exception scheduling hotkey callback: {e}")
            return wrapper

        # Функции-обертки для emit сигналов (они будут выполнены в основном потоке)
        @run_if_topmost_gui
        def _emit_move(direction): self.move_cursor_signal.emit(direction)
        @run_if_topmost_gui
        def _emit_toggle_select(): self.toggle_selection_signal.emit()
        @run_if_topmost_gui
        def _emit_toggle_mode(): self.toggle_mode_signal.emit()
        @run_if_topmost_gui
        def _emit_clear(): self.clear_all_signal.emit()
        @run_if_topmost_gui
        def _emit_recognize(): self.recognize_heroes_signal.emit()

        hooks = []
        print(f"Регистрация хуков клавиатуры...")
        try:
            # Горячие клавиши навигации/выбора/режима/очистки
            hooks.append(keyboard.add_hotkey('tab+up', lambda: _emit_move('up'), suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('tab+down', lambda: _emit_move('down'), suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('tab+left', lambda: _emit_move('left'), suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('tab+right', lambda: _emit_move('right'), suppress=True, trigger_on_release=False))
            try: hooks.append(keyboard.add_hotkey('tab+num 0', _emit_toggle_select, suppress=True, trigger_on_release=False))
            except ValueError:
                try: hooks.append(keyboard.add_hotkey('tab+keypad 0', _emit_toggle_select, suppress=True, trigger_on_release=False))
                except ValueError: print("[WARN] Could not hook Tab + Numpad 0 / Keypad 0.")
            try: hooks.append(keyboard.add_hotkey('tab+delete', _emit_toggle_mode, suppress=True, trigger_on_release=False))
            except ValueError:
                 try: hooks.append(keyboard.add_hotkey('tab+del', _emit_toggle_mode, suppress=True, trigger_on_release=False))
                 except ValueError:
                     try: hooks.append(keyboard.add_hotkey('tab+.', _emit_toggle_mode, suppress=True, trigger_on_release=False)) # Numpad .
                     except ValueError: print("[WARN] Could not hook Tab + Delete / Del / Numpad .")
            try: hooks.append(keyboard.add_hotkey('tab+num -', _emit_clear, suppress=True, trigger_on_release=False))
            except ValueError:
                try: hooks.append(keyboard.add_hotkey('tab+keypad -', _emit_clear, suppress=True, trigger_on_release=False))
                except ValueError:
                    try: hooks.append(keyboard.add_hotkey('tab+-', _emit_clear, suppress=True, trigger_on_release=False))
                    except ValueError: print("[WARN] Could not hook Tab + Num - / Keypad - / -.")

            # Горячая клавиша распознавания
            try:
                hooks.append(keyboard.add_hotkey('tab+num /', _emit_recognize, suppress=True, trigger_on_release=False))
                print("[INFO] Hooked Tab + Num /")
            except ValueError:
                try:
                    hooks.append(keyboard.add_hotkey('tab+keypad /', _emit_recognize, suppress=True, trigger_on_release=False))
                    print("[INFO] Hooked Tab + Keypad /")
                except ValueError:
                    try: # Добавляем обычный '/' как fallback
                         hooks.append(keyboard.add_hotkey('tab+/', _emit_recognize, suppress=True, trigger_on_release=False))
                         print("[INFO] Hooked Tab + /")
                    except ValueError:
                         print("[WARN] Could not hook Tab + Num / or Keypad / or /.")

            print("Hotkeys registered successfully.")
            # Ждем сигнала остановки потока
            self._stop_keyboard_listener_flag.wait()
            print("Keyboard listener stop signal received.")

        except ImportError: print("\n[ERROR] 'keyboard' library requires root/admin privileges.\n")
        except Exception as e: print(f"[ERROR] setting up keyboard hooks: {e}")
        finally:
            print("Unhooking keyboard...")
            keyboard.unhook_all() # Самый надежный способ удалить все хуки этой библиотеки
            print("Keyboard listener thread finished.")

    def start_keyboard_listener(self):
        """Запускает поток прослушивания клавиатуры, если он еще не запущен."""
        if self._keyboard_listener_thread is None or not self._keyboard_listener_thread.is_alive():
            print("Starting keyboard listener thread...")
            self._stop_keyboard_listener_flag.clear() # Сбрасываем флаг остановки
            # Создаем поток как daemon, чтобы он автоматически завершился при выходе основного потока
            self._keyboard_listener_thread = threading.Thread(target=self._keyboard_listener_loop, daemon=True)
            self._keyboard_listener_thread.start()
        else: print("Keyboard listener already running.")

    def stop_keyboard_listener(self):
        """Останавливает поток прослушивания клавиатуры и поток распознавания."""
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
            print("Signalling keyboard listener to stop...")
            self._stop_keyboard_listener_flag.set() # Сигнал для основного цикла листенера

            # Остановка потока распознавания, если он работает
            if self._recognition_worker:
                self._recognition_worker.stop() # Устанавливаем флаг остановки в воркере
            if self._recognition_thread and self._recognition_thread.isRunning():
                print("Quitting recognition thread...")
                self._recognition_thread.quit() # Просим поток завершиться
                if not self._recognition_thread.wait(1000): # Ждем до 1 секунды
                     print("[WARN] Recognition thread did not quit gracefully.")
        else:
             # Если поток листенера не запущен, все равно проверим поток распознавания
             if self._recognition_worker: self._recognition_worker.stop()
             if self._recognition_thread and self._recognition_thread.isRunning():
                print("Quitting orphan recognition thread...")
                self._recognition_thread.quit()
                self._recognition_thread.wait(500)
             # print("Keyboard listener not running or already stopped.")

    def closeEvent(self, event):
        """Перехватывает событие закрытия окна."""
        print("Close event triggered.")
        self.stop_keyboard_listener() # Останавливаем листенер и поток распознавания
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
             print("Waiting for keyboard listener thread to join...")
             self._keyboard_listener_thread.join(timeout=0.5) # Даем полсекунды на завершение
             if self._keyboard_listener_thread.is_alive(): print("[WARN] Keyboard listener thread did not exit cleanly.")
             else: print("Keyboard listener thread joined successfully.")
        super().closeEvent(event) # Вызываем стандартный обработчик закрытия
    # --- END HOTKEY METHODS ---

    # --- Existing Methods ---

    def update_list_item_selection_states(self):
        """Обновляет состояние выбора элементов в QListWidget в соответствии с logic.selected_heroes."""
        if not self.hero_items or not self.right_list_widget or not self.right_list_widget.isVisible(): return # Добавлена проверка видимости
        list_widget = self.right_list_widget
        self.is_programmatically_updating_selection = True # Ставим флаг
        try:
            list_widget.blockSignals(True) # Блокируем сигналы, чтобы избежать рекурсии
            current_logic_selection = set(self.logic.selected_heroes)
            # Обновляем состояние выбора для каждого элемента
            for hero, item in self.hero_items.items():
                if item is None: continue
                try:
                    is_now_selected = (hero in current_logic_selection)
                    if item.isSelected() != is_now_selected:
                        item.setSelected(is_now_selected)
                except RuntimeError: continue # Игнорируем ошибку, если виджет удален
                except Exception as e: print(f"[ERROR] updating selection state for {hero}: {e}")

            # Обновляем счетчик выбранных героев
            self.update_selected_label()

        finally:
            try:
                if self.right_list_widget: list_widget.blockSignals(False) # Разблокируем сигналы
            except RuntimeError: pass
            except Exception as e: print(f"[ERROR] unblocking signals: {e}")
            self.is_programmatically_updating_selection = False # Снимаем флаг

    def update_priority_labels(self):
        """Обновляет фон для приоритетных героев."""
        if not self.hero_items or not self.right_list_widget or not self.right_list_widget.isVisible(): return # Добавлена проверка видимости
        list_widget = self.right_list_widget
        priority_color = QColor("lightcoral")
        default_brush = QBrush(Qt.GlobalColor.transparent)
        focused_index = self.hotkey_cursor_index
        for hero, item in self.hero_items.items():
             if item is None: continue
             try:
                 item_index = list_widget.row(item)
                 is_priority = hero in self.logic.priority_heroes
                 is_hotkey_focused = (item_index == focused_index and self.mode != 'min') # Учитываем режим
                 is_selected = item.isSelected()

                 target_brush = default_brush # По умолчанию прозрачный фон
                 # Применяем красный фон, только если герой приоритетный, не выделен и не под фокусом хоткея
                 if is_priority and not is_selected and not is_hotkey_focused:
                      target_brush = QBrush(priority_color)

                 # Применяем фон, если он отличается от текущего
                 if item.background() != target_brush:
                      item.setBackground(target_brush)

             except RuntimeError: continue # Игнорируем ошибку, если виджет удален
             except Exception as e: print(f"[ERROR] updating priority label for {hero}: {e}")

    def update_selected_label(self):
        """Обновляет текст метки с количеством выбранных героев."""
        if self.selected_heroes_label:
             try: self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass # Игнорируем ошибку, если виджет удален
             except Exception as e: print(f"[ERROR] updating selected label: {e}")

    def update_counterpick_display(self):
        """Обновляет левую панель (result_frame) с рейтингом или иконками контрпиков."""
        if not self.result_frame:
             # print("[WARN] No result_frame found in update_counterpick_display")
             return
        # Находим result_label безопасным способом
        result_label_found = self.findChild(QLabel, "result_label") # Ищем во всем окне

        try:
            layout = self.result_frame.layout()
            # Если layout еще не создан (маловероятно, т.к. создается в left_panel), создаем его
            if not layout:
                 layout = QVBoxLayout(self.result_frame); layout.setObjectName("result_layout")
                 layout.setAlignment(Qt.AlignmentFlag.AlignTop); layout.setContentsMargins(2,2,2,2); layout.setSpacing(1)
                 self.result_frame.setLayout(layout)

            # Не очищаем layout здесь, это делается внутри generate_* функций

            # Определяем, какие картинки нужны
            images_ok = bool(self.left_images)
            if self.mode != 'min': images_ok = images_ok and bool(self.small_images)

            # Перезагружаем картинки, если их нет
            if not images_ok:
                 try:
                     print("[INFO] Перезагрузка изображений для display...")
                     _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
                 except Exception as e: print(f"[ERROR] reloading images for display: {e}"); return

            # Вызываем нужную функцию для генерации контента
            if self.mode == "min":
                generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
            else:
                generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)

            # Обновление геометрии и прокрутки ScrollArea
            # layout.activate() # activate() может быть не нужен
            self.result_frame.adjustSize() # Подгоняем размер result_frame под контент
            if self.canvas: # self.canvas - это ScrollArea из left_panel
                self.canvas.updateGeometry() # Обновляем геометрию ScrollArea
                # Вызываем update_scrollregion после небольшой задержки
                QTimer.singleShot(10, self.update_scrollregion);
                # self.canvas.verticalScrollBar().setValue(0); # Прокрутка в начало не всегда желательна
                self.canvas.update() # Принудительная перерисовка ScrollArea

        except RuntimeError as e: print(f"[ERROR] RuntimeErr(upd_cnt): {e}")
        except Exception as e: print(f"[ERROR] General Err(upd_cnt): {e}")


    def update_ui_after_logic_change(self):
        """Обновляет все части UI, зависящие от выбора героев."""
        # print("[UI Update] Started after logic change.")
        start_time = time.time()
        # Обновляем основные элементы
        self.update_selected_label() # Метка "Выбрано: ..."
        self.update_counterpick_display() # Левая панель
        update_horizontal_icon_list(self) # Горизонтальный список иконок
        # Обновляем правую панель (состояния элементов)
        self.update_list_item_selection_states() # Выделение элементов
        self.update_priority_labels() # Фон приоритетных
        end_time = time.time()
        # print(f"[UI Update] Finished in {end_time - start_time:.4f} sec.")


    def handle_selection_changed(self):
        """Слот, вызываемый при изменении выделения в QListWidget."""
        # Игнорируем, если изменение вызвано программно (из update_list_item_selection_states)
        if self.is_programmatically_updating_selection: return
        if not self.right_list_widget: return

        print("[UI Event] Selection changed by user/hotkey.")
        list_widget = self.right_list_widget; current_ui_selection_names = set()
        # Собираем имена всех выделенных героев
        for item in list_widget.selectedItems():
            hero_name = item.data(HERO_NAME_ROLE);
            if hero_name: current_ui_selection_names.add(hero_name)

        # Обновляем логику только если реальный выбор отличается от того, что в logic
        if set(self.logic.selected_heroes) != current_ui_selection_names:
            self.logic.set_selection(current_ui_selection_names)
            self.update_ui_after_logic_change() # Полное обновление UI
        else:
             print("[UI Event] Selection unchanged in logic, skipping full UI update.")
             # Обновляем только приоритеты, так как set_selection не вызывался
             self.update_priority_labels()


    def show_priority_context_menu(self, pos):
        """Показывает контекстное меню для установки/снятия приоритета."""
        if not self.right_list_widget or not self.right_list_widget.isVisible(): return
        list_widget = self.right_list_widget
        # Получаем элемент под курсором
        item = list_widget.itemAt(pos)
        if not item: return
        hero_name = item.data(HERO_NAME_ROLE)
        if not hero_name: return

        # Получаем глобальные координаты для показа меню
        global_pos = list_widget.viewport().mapToGlobal(pos)

        menu = QMenu(self)
        is_priority = hero_name in self.logic.priority_heroes
        is_selected = item.isSelected()

        # Создаем действие в меню
        action_text = get_text('remove_priority', language=self.logic.DEFAULT_LANGUAGE) if is_priority else get_text('set_priority', language=self.logic.DEFAULT_LANGUAGE)
        priority_action = menu.addAction(action_text)
        # Действие доступно только если герой выбран
        priority_action.setEnabled(is_selected)

        # Показываем меню и обрабатываем выбор
        action = menu.exec(global_pos)
        if action == priority_action:
             # Проверяем еще раз, что герой выбран (на всякий случай)
             if hero_name in self.logic.selected_heroes:
                 self.logic.set_priority(hero_name)
                 self.update_ui_after_logic_change() # Обновляем UI
             else: print(f"Cannot change priority for '{hero_name}' as it's not selected.")


    def change_mode(self, mode):
        """Инициирует смену режима отображения."""
        print(f"[MODE] Attempting to change mode to: {mode}")
        if self.mode == mode: print("[MODE] Mode is already set."); return

        # Сбрасываем индекс фокуса хоткея ДО перестройки UI
        old_cursor_index = self.hotkey_cursor_index
        self.hotkey_cursor_index = -1
        # Запрашиваем перерисовку для старого индекса, чтобы убрать рамку
        if self.right_list_widget and self.right_list_widget.isVisible() and old_cursor_index >= 0:
            # Вызываем обновление через QTimer, чтобы оно произошло после текущего события
            QTimer.singleShot(0, lambda idx=old_cursor_index: self._update_hotkey_highlight(idx))

        # Вызываем функцию смены режима, которая перестраивает UI
        change_mode(self, mode) # Эта функция установит self.mode = mode

        # Восстанавливаем фокус хоткея после небольшой задержки
        QTimer.singleShot(150, self._reset_hotkey_cursor_after_mode_change) # Уменьшил задержку

    def _reset_hotkey_cursor_after_mode_change(self):
        """Восстанавливает фокус хоткея после смены режима."""
        print("[MODE] Resetting hotkey cursor after mode change.")
        # Проверяем, что правая панель существует, видима и режим не минимальный
        if self.right_list_widget and self.right_list_widget.isVisible() and self.mode != 'min':
            count = self.right_list_widget.count()
            if count > 0:
                self.hotkey_cursor_index = 0 # Устанавливаем на первый элемент
                self._calculate_columns() # Пересчитываем колонки
                self._update_hotkey_highlight(None) # Запрашиваем отрисовку рамки для нового индекса
            else: self.hotkey_cursor_index = -1 # Список пуст
        else:
             self.hotkey_cursor_index = -1 # В min режиме или если списка нет
             # Убедимся, что рамка точно убрана (если она была)
             self._update_hotkey_highlight(None)


    # --- Остальные методы ---
    def restore_hero_selections(self):
        """Восстанавливает UI в соответствии с текущим состоянием logic."""
        # print("[UI Restore] Restoring hero selections and UI state.")
        # Эта функция теперь вызывается из update_interface_for_mode ПОСЛЕ создания панелей
        # Основная логика обновления UI теперь в update_ui_after_logic_change
        self.update_ui_after_logic_change()
        # Восстанавливаем подсветку фокуса хоткея, если он был установлен
        if self.hotkey_cursor_index != -1:
             # print("[UI Restore] Scheduling focus highlight update.")
             # Используем QTimer для вызова после завершения текущего цикла событий
             QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))


    def switch_language(self, lang):
        """Переключает язык интерфейса."""
        print(f"[LANG] Attempting to switch language to {lang}")
        current_lang = self.logic.DEFAULT_LANGUAGE # Получаем текущий язык из logic
        if current_lang != lang and lang in SUPPORTED_LANGUAGES:
            set_language(lang) # Устанавливаем новый язык в translations.py
            self.logic.DEFAULT_LANGUAGE = lang # Обновляем язык в logic
            self.update_language() # Обновляем тексты в UI немедленно
            self.update_ui_after_logic_change() # Пересчитываем и перерисовываем все зависимые части
            # Восстанавливаем подсветку фокуса хоткея
            if self.hotkey_cursor_index != -1:
                # print("[LANG] Scheduling focus highlight update after language switch.")
                QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))
        elif current_lang == lang:
            print(f"[LANG] Language already set to {lang}")
        else:
             print(f"[WARN] Unsupported language: {lang}")


    def update_language(self):
        """Обновляет тексты интерфейса и подсказки элементов списка."""
        print("[LANG] Updating UI language texts...")
        self.setWindowTitle(f"{get_text('title')} v{self.app_version}")
        # Обновление текстов в дочерних виджетах (если они существуют)
        if self.selected_heroes_label: self.update_selected_label()
        if self.author_button: self.author_button.setText(get_text('about_author'))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating'))
        # Обновляем панели (они найдут свои элементы и обновят текст)
        if self.top_frame: self._update_top_panel_lang()
        if self.right_frame: self._update_right_panel_lang()
        # Обновление подсказок и текстов в QListWidget (если он существует и видим)
        if self.right_list_widget and self.right_list_widget.isVisible():
            self._update_list_widget_language()
        # Обновление текста в result_label (если герои не выбраны)
        if self.result_label and not self.logic.selected_heroes:
             self.result_label.setText(get_text('no_heroes_selected', language=self.logic.DEFAULT_LANGUAGE))

    def _update_list_widget_language(self):
        """Обновляет тексты и тултипы элементов в QListWidget."""
        if not self.right_list_widget: return
        focused_hero_tooltip = None
        focused_item = None
        # Сохраняем текущую фокусную подсказку, если она есть
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
             try:
                 focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
                 if focused_item: focused_hero_tooltip = focused_item.toolTip()
             except RuntimeError: pass # Игнорируем, если виджет уже удален

        # Обновляем тексты и базовые подсказки
        for i in range(self.right_list_widget.count()):
             try:
                item = self.right_list_widget.item(i)
                if item:
                    hero_name = item.data(HERO_NAME_ROLE)
                    if hero_name:
                        # Обновляем текст элемента (имя в max, пусто в middle)
                        item_text = hero_name if self.mode == "max" else ""
                        if item.text() != item_text: item.setText(item_text)
                        # Обновляем базовую подсказку
                        item.setToolTip(get_text(hero_name, default_text=hero_name, language=self.logic.DEFAULT_LANGUAGE))
             except RuntimeError: continue # Пропускаем, если виджет удален

        # Восстанавливаем фокусный тултип, если элемент тот же и тултип был фокусным
        current_focused_item = None
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
             try:
                current_focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
             except RuntimeError: pass
        if focused_hero_tooltip and current_focused_item == focused_item and ">>>" in focused_hero_tooltip:
             # Восстанавливаем фокусную подсказку (>>> Имя <<<)
             hero_name = current_focused_item.data(HERO_NAME_ROLE)
             if hero_name:
                 focus_tooltip = f">>> {get_text(hero_name, default_text=hero_name, language=self.logic.DEFAULT_LANGUAGE)} <<<"
                 current_focused_item.setToolTip(focus_tooltip)


    def _update_top_panel_lang(self):
        """Обновляет язык элементов верхней панели."""
        if not self.top_frame: return
        print("[LANG] Updating top panel language...")
        try:
            # Находим элементы по имени объекта (предпочтительнее)
            lang_label = self.top_frame.findChild(QLabel, "language_label")
            mode_label = self.top_frame.findChild(QLabel, "mode_label")
            min_button = self.top_frame.findChild(QPushButton, "min_button")
            middle_button = self.top_frame.findChild(QPushButton, "middle_button")
            max_button = self.top_frame.findChild(QPushButton, "max_button")
            topmost_button = self.top_frame.findChild(QPushButton, "topmost_button")
            lang_combo = self.top_frame.findChild(QComboBox, "language_combo")
            version_label = self.top_frame.findChild(QLabel, "version_label") # Находим лейбл версии

            # Обновляем тексты найденных элементов
            if lang_label: lang_label.setText(get_text('language', language=self.logic.DEFAULT_LANGUAGE))
            if mode_label: mode_label.setText(get_text('mode', language=self.logic.DEFAULT_LANGUAGE))
            if min_button: min_button.setText(get_text('mode_min', language=self.logic.DEFAULT_LANGUAGE))
            if middle_button: middle_button.setText(get_text('mode_middle', language=self.logic.DEFAULT_LANGUAGE))
            if max_button: max_button.setText(get_text('mode_max', language=self.logic.DEFAULT_LANGUAGE))
            if topmost_button: self._update_topmost_button_visuals() # Обновляем текст и стиль кнопки Topmost
            if version_label: version_label.setText(f"v{self.app_version}") # Обновляем текст версии
            if self.author_button: self.author_button.setText(get_text('about_author', language=self.logic.DEFAULT_LANGUAGE))
            if self.rating_button: self.rating_button.setText(get_text('hero_rating', language=self.logic.DEFAULT_LANGUAGE))

            # Обновление комбо-бокса языка
            if lang_combo:
                current_lang_code = self.logic.DEFAULT_LANGUAGE # Берем язык из logic
                lang_combo.blockSignals(True) # Блокируем сигналы
                # Находим индекс текущего языка по коду
                index_to_set = -1
                current_items = [lang_combo.itemText(i) for i in range(lang_combo.count())]
                expected_items = list(SUPPORTED_LANGUAGES.values())

                # Перезаполняем, если список отличается
                if current_items != expected_items:
                    lang_combo.clear()
                    lang_combo.addItems(expected_items)

                # Находим индекс для установки
                for index, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
                    if code == current_lang_code:
                        index_to_set = index
                        break
                # Устанавливаем текущий элемент по индексу
                if index_to_set != -1:
                    lang_combo.setCurrentIndex(index_to_set)
                lang_combo.blockSignals(False) # Разблокируем сигналы

        except Exception as e: print(f"[ERROR] updating top panel language: {e}")


    def _update_right_panel_lang(self):
         """Обновляет язык элементов правой панели."""
         if not self.right_frame: return
         print("[LANG] Updating right panel language...")
         try:
             # Находим кнопки по имени объекта
             copy_button = self.right_frame.findChild(QPushButton, "copy_button")
             clear_button = self.right_frame.findChild(QPushButton, "clear_button")
             # Обновляем текст кнопок
             if copy_button: copy_button.setText(get_text('copy_rating', language=self.logic.DEFAULT_LANGUAGE))
             if clear_button: clear_button.setText(get_text('clear_all', language=self.logic.DEFAULT_LANGUAGE))
             # Обновляем метку выбранных героев (она тоже на правой панели)
             self.update_selected_label()
         except Exception as e: print(f"[ERROR] updating right panel language: {e}")


# --- Глобальные функции ---
def create_gui():
    """Создает и возвращает экземпляр MainWindow."""
    return MainWindow()
