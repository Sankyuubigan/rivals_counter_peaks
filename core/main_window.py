# File: core/main_window.py
import sys
import time
import threading

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout,
                               QMessageBox, QApplication, QScrollArea, QAbstractItemView) # Добавлены QAbstractItemView, QScrollArea
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QPoint, QModelIndex # Добавлены QPoint, QModelIndex
from PySide6.QtGui import QIcon, QMouseEvent, QColor, QBrush # Добавлены QColor, QBrush

# Импорты из проекта (используем относительные пути внутри core)
from translations import get_text, set_language, SUPPORTED_LANGUAGES # Добавлен SUPPORTED_LANGUAGES
from utils_gui import copy_to_clipboard
from logic import CounterpickLogic, TEAM_SIZE
# Менеджеры
from mode_manager import ModeManager, change_mode, update_interface_for_mode
from win_api import WinApiManager, user32 as winapi_user32
from recognition import RecognitionManager, RecognitionWorker
# Загрузка ресурсов
from images_load import load_original_images, get_images_for_mode, SIZES, load_default_pixmap # Добавлен load_default_pixmap
# Элементы UI
from top_panel import TopPanel
from left_panel import LeftPanel
from right_panel import RightPanel, HERO_NAME_ROLE # Добавлен HERO_NAME_ROLE
from horizontal_list import update_horizontal_icon_list
from display import generate_counterpick_display, generate_minimal_icon_list
# Данные
from heroes_bd import heroes # Выходим на уровень выше для импорта heroes_bd

# Библиотека hotkey
try:
    import keyboard
except ImportError:
    print("[ERROR] Библиотека 'keyboard' не найдена. Установите ее: pip install keyboard")
    keyboard = None

# Класс MainWindow остается практически тем же, но убедимся, что все методы корректно работают с новыми панелями
class MainWindow(QMainWindow):
    # --- Сигналы ---
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()
    toggle_mode_signal = Signal()
    clear_all_signal = Signal()
    recognize_heroes_signal = Signal()
    recognition_complete_signal = Signal(list)

    def __init__(self, logic: CounterpickLogic, hero_templates: dict):
        super().__init__()
        print("[LOG] MainWindow.__init__ started")

        # --- Основные компоненты ---
        self.logic = logic
        self.hero_templates = hero_templates
        self.app_version = self.logic.APP_VERSION

        # --- Менеджеры ---
        self.win_api_manager = WinApiManager(self)
        self.mode_manager = ModeManager(self)
        self.rec_manager = RecognitionManager(self, self.logic, self.win_api_manager)

        # --- Состояние UI ---
        self.mode = "middle"
        self.initial_pos = self.pos() # Сохраняем начальную позицию
        self.mode_positions = {"max": None, "middle": self.initial_pos, "min": None}
        self.is_programmatically_updating_selection = False

        # --- Атрибуты UI (инициализируем None) ---
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_panel_instance: TopPanel | None = None
        self.left_panel_instance: LeftPanel | None = None
        self.right_panel_instance: RightPanel | None = None
        self.top_frame = None # QFrame верхней панели
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

        # --- Hotkeys ---
        self.hotkey_cursor_index = -1
        self._num_columns_cache = 1
        self._keyboard_listener_thread = None
        self._stop_keyboard_listener_flag = threading.Event()

        # --- Распознавание ---
        self._recognition_thread = None
        self._recognition_worker = None

        # --- Настройка окна ---
        self.setWindowTitle(f"{get_text('title', language=self.logic.DEFAULT_LANGUAGE)} v{self.app_version}")
        icon_pixmap = load_default_pixmap((32,32)) # Заглушка для иконки
        if not icon_pixmap.isNull(): self.setWindowIcon(QIcon(icon_pixmap))
        self.setGeometry(100, 100, 950, 350)
        self.setMinimumSize(400, 100)

        # --- Создание UI ---
        self._create_main_ui_layout() # Создаем базовую структуру
        update_interface_for_mode(self) # Создаем панели для начального режима

        # --- Подключение сигналов ---
        self._connect_signals()

        # --- Запуск слушателя хоткеев ---
        if keyboard: self.start_keyboard_listener()
        else: print("[WARN] Библиотека keyboard не найдена, горячие клавиши не будут работать.")

        print("[LOG] MainWindow.__init__ finished")

    def _create_main_ui_layout(self):
        """Создает базовую структуру виджетов и layout'ов окна."""
        print("[LOG] MainWindow._create_main_ui_layout() started")
        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        # Верхняя панель (создается здесь)
        self.top_panel_instance = TopPanel(self, self.change_mode, self.logic, self.app_version)
        self.top_frame = self.top_panel_instance.top_frame
        self.author_button = self.top_panel_instance.author_button
        self.rating_button = self.top_panel_instance.rating_button
        self.main_layout.addWidget(self.top_frame)

        # Горизонтальный список иконок (создается здесь)
        self._create_icons_scroll_area()
        self.main_layout.addWidget(self.icons_scroll_area)

        # Контейнер для левой и правой панелей
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
        self.inner_layout.setContentsMargins(0, 0, 0, 0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1)
        print("[LOG] MainWindow._create_main_ui_layout() finished")

    # _create_icons_scroll_area остается как в предыдущем ответе

    def _connect_signals(self):
        """Подключает все сигналы и слоты."""
        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)
        self.toggle_mode_signal.connect(self._handle_toggle_mode)
        self.clear_all_signal.connect(self._handle_clear_all)
        # Подключаем сигнал распознавания к менеджеру
        self.recognize_heroes_signal.connect(self.rec_manager._handle_recognize_heroes)
        # Подключаем сигналы от менеджера к слотам окна
        self.rec_manager.recognition_complete_signal.connect(self._on_recognition_complete)
        self.rec_manager.error.connect(self._on_recognition_error)


    # --- Обновление UI ---
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
        # Используем ссылку на label из RightPanel, если она есть
        label_to_update = getattr(self.right_panel_instance, 'selected_heroes_label', None)
        if label_to_update:
             try: label_to_update.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass
             except Exception as e: print(f"[ERROR] updating selected label: {e}")

    # _update_counterpick_display остается как в предыдущем ответе

    def _update_list_item_selection_states(self):
        """Обновляет состояние выбора элементов в QListWidget."""
        # Используем ссылку на list_widget из RightPanel
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
        hero_items_dict = getattr(self.right_panel_instance, 'hero_items', {})
        if not list_widget or not list_widget.isVisible(): return

        self.is_programmatically_updating_selection = True
        try:
            list_widget.blockSignals(True)
            current_logic_selection = set(self.logic.selected_heroes)
            for hero, item in hero_items_dict.items(): # Используем словарь из RightPanel
                if item is None: continue
                try:
                    is_now_selected = (hero in current_logic_selection)
                    if item.isSelected() != is_now_selected:
                        item.setSelected(is_now_selected)
                except RuntimeError: pass
                except Exception as e: print(f"[ERROR] updating selection state for {hero}: {e}")
            # Обновляем счетчик после изменения состояний
            self._update_selected_label()
        finally:
            try:
                if list_widget: list_widget.blockSignals(False)
            except RuntimeError: pass
            self.is_programmatically_updating_selection = False

    # _update_priority_labels остается как в предыдущем ответе (пустой)

    # --- Обработчики событий UI ---
    def handle_selection_changed(self):
        """Обрабатывает сигнал itemSelectionChanged от QListWidget."""
        if self.is_programmatically_updating_selection: return
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
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
        """Показывает контекстное меню для приоритета."""
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
        if not list_widget or not list_widget.isVisible(): return
        # Остальная логика остается прежней, использует list_widget
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

    # --- Язык ---
    def switch_language(self, lang_code: str):
        """Переключает язык интерфейса."""
        print(f"[Language] Attempting to switch to {lang_code}")
        if self.logic.DEFAULT_LANGUAGE != lang_code:
            set_language(lang_code) # Устанавливаем глобально
            self.logic.DEFAULT_LANGUAGE = lang_code # Обновляем в логике
            self.update_language() # Обновляем тексты в текущем UI
            # Пересчитываем и обновляем панели, зависящие от языка (если нужно)
            self.update_ui_after_logic_change()
            # Восстанавливаем фокус хоткея
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
        # Проверяем наличие result_label перед доступом
        result_label = getattr(self.left_panel_instance, 'result_label', None)
        if result_label and not self.logic.selected_heroes:
             result_label.setText(get_text('no_heroes_selected', language=self.logic.DEFAULT_LANGUAGE))

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

            for hero, item in hero_items_dict.items(): # Используем словарь из RightPanel
                 if item is None: continue
                 try: item.setToolTip(hero) # Устанавливаем базовую подсказку
                 except RuntimeError: pass

            if focused_tooltip and ">>>" in focused_tooltip and 0 <= self.hotkey_cursor_index < list_widget.count():
                try:
                    current_focused_item = list_widget.item(self.hotkey_cursor_index)
                    if current_focused_item: current_focused_item.setToolTip(focused_tooltip)
                except RuntimeError: pass

    # Остальные методы (_calculate_columns, _update_hotkey_highlight, слушатель клавиатуры и т.д.)
    # остаются в основном без изменений, но используют ссылки на виджеты,
    # полученные из экземпляров панелей (например, self.right_list_widget)

    # --- Место для остальных методов ---
    # _create_icons_scroll_area, closeEvent, mouseEvents, change_mode,
    # _reset_hotkey_cursor_after_mode_change, _is_win_topmost, set_topmost_winapi,
    # toggle_topmost_winapi, _handle_move_cursor, _handle_toggle_selection,
    # _handle_toggle_mode, _handle_clear_all, _reset_hotkey_cursor_after_clear,
    # _on_recognition_complete, _on_recognition_error, start_keyboard_listener,
    # stop_keyboard_listener, _keyboard_listener_loop, _calculate_columns,
    # _update_hotkey_highlight

    # --- Утилиты UI (скопированы из предыдущей версии для полноты) ---
    def _calculate_columns(self):
        """Вычисляет количество колонок для QListWidget."""
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
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
        """Обновляет подсветку (рамку и подсказку) для фокуса хоткея."""
        list_widget = getattr(self.right_panel_instance, 'list_widget', None)
        if not list_widget or not list_widget.isVisible() or self.mode == 'min': return
        count = list_widget.count()
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
                        old_item.setToolTip(hero_name)
                        needs_viewport_update = True
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
                    list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
            except Exception as e: print(f"[ERROR] Setting new tooltip (idx {new_index}): {e}")

        # --- Запрашиваем перерисовку viewport ---
        if needs_viewport_update or old_index != new_index:
            list_widget.viewport().update()

    # --- Управление слушателем клавиатуры ---
    def start_keyboard_listener(self):
        """Запускает поток прослушивания клавиатуры."""
        if not keyboard: return
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
        else: print("Keyboard listener not running or already stopped.")

    def _keyboard_listener_loop(self):
        """Цикл прослушивания клавиатуры (выполняется в отдельном потоке)."""
        print("Keyboard listener thread started.")
        def run_in_gui_thread(func, *args):
            QTimer.singleShot(0, lambda: func(*args))
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
            