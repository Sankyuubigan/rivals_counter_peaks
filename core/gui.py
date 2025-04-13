# File: gui.py
import time
import threading
import keyboard

# --- ИСПРАВЛЕНИЕ: Добавляем QComboBox ---
from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame,
                               QLabel, QPushButton, QApplication, QListWidget, QListWidgetItem, QMenu,
                               QAbstractItemView, QStyle, QComboBox)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QPoint, QModelIndex
from PySide6.QtGui import QColor, QPalette, QIcon, QBrush
from top_panel import create_top_panel
from right_panel import create_right_panel, HERO_NAME_ROLE
from left_panel import create_left_panel
from utils_gui import copy_to_clipboard
from build import version
from logic import CounterpickLogic, TEAM_SIZE # Используем исправленную логику
from images_load import get_images_for_mode, TOP_HORIZONTAL_ICON_SIZE
from translations import get_text, set_language, DEFAULT_LANGUAGE, TRANSLATIONS, SUPPORTED_LANGUAGES
from mode_manager import change_mode, update_interface_for_mode
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes
from display import generate_counterpick_display, generate_minimal_icon_list

# --- Класс MainWindow ---
class MainWindow(QMainWindow):
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()

    def __init__(self):
        super().__init__()
        self.logic = CounterpickLogic()
        self.mode = "middle"
        self.initial_pos = None
        self.mode_positions = {"max": None, "middle": None, "min": None}
        self.copy_to_clipboard = lambda: copy_to_clipboard(self.logic)

        # Атрибуты UI
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_horizontal_icon_size = TOP_HORIZONTAL_ICON_SIZE
        self.top_frame, self.author_button, self.rating_button = None, None, None
        self.main_widget, self.inner_layout, self.left_container = None, None, None
        self.icons_frame, self.icons_layout = None, None
        self.canvas, self.result_frame, self.result_label = None, None, None
        self.update_scrollregion = lambda: None
        self.right_frame, self.selected_heroes_label = None, None
        self.right_list_widget = None
        self.hero_items = {}
        self.is_programmatically_updating_selection = False

        # Hotkey related attributes
        self.hotkey_cursor_index = -1
        self._keyboard_listener_thread = None
        self._stop_keyboard_listener_flag = threading.Event()
        self._num_columns_cache = 1

        self.init_ui()
        self.start_keyboard_listener()

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{version}")
        self.setGeometry(100, 100, 950, 350)
        self.setMinimumSize(400, 100)
        self.initial_pos = self.pos()
        self.mode_positions["middle"] = self.pos()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        (self.top_frame, self.author_button, self.rating_button,
         self.switch_mode_cb) = create_top_panel(self, self.change_mode, self.logic)
        self.main_layout.addWidget(self.top_frame)

        self.icons_frame = QFrame(self)
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(5, 2, 5, 2)
        self.icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        icons_frame_height = self.top_horizontal_icon_size.height() + 8
        self.icons_frame.setFixedHeight(icons_frame_height)
        self.icons_frame.setStyleSheet("background-color: #f0f0f0;")
        self.main_layout.addWidget(self.icons_frame)

        self.main_widget = QWidget()
        self.inner_layout = QHBoxLayout(self.main_widget)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1)

        try:
            self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(self.mode)
        except Exception as e: print(f"Критическая ошибка загрузки изображений: {e}"); self.close(); return

        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.setSpacing(0)
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.left_container)
        left_layout.addWidget(self.canvas, stretch=1)
        self.inner_layout.addWidget(self.left_container, stretch=2)

        self.right_frame, self.selected_heroes_label = create_right_panel(self, self.mode)
        self.inner_layout.addWidget(self.right_frame, stretch=1)

        self.switch_language_callback = lambda lang: self.switch_language(lang)
        self.update_language()
        update_interface_for_mode(self)

        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)

        if self.right_list_widget and self.right_list_widget.count() > 0 and self.mode != 'min':
            self.hotkey_cursor_index = 0
            # Устанавливаем подсказку и запрашиваем обновление для начальной отрисовки
            QTimer.singleShot(100, lambda: self._update_hotkey_highlight(None))

    # --- HOTKEY RELATED METHODS ---

    def _calculate_columns(self):
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return 1
        try:
            vp_width = self.right_list_widget.viewport().width()
            grid_w = self.right_list_widget.gridSize().width()
            spacing = self.right_list_widget.spacing()
            if grid_w <= 0: return 1; eff_grid_w = grid_w + spacing
            if eff_grid_w <= 0: return 1; cols = max(1, int(vp_width / eff_grid_w))
            self._num_columns_cache = cols; return cols
        except Exception as e: print(f"[ERROR] Calculating columns: {e}"); return self._num_columns_cache

    def _update_hotkey_highlight(self, old_index=None):
        """
        Обновляет ПОДСКАЗКУ элемента и запрашивает обновление viewport'а.
        Не меняет свойства элемента напрямую.
        """
        # print(f"[LOG] _update_hotkey_highlight called: old={old_index}, new={self.hotkey_cursor_index}") # LOG
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min':
            # print("[LOG] _update_hotkey_highlight: skipped (widget hidden or mode=min)") # LOG
            return

        list_widget = self.right_list_widget
        count = list_widget.count()
        if count == 0: return

        needs_viewport_update = False # Флаг, чтобы вызвать update только один раз

        # --- Восстановление подсказки старого элемента ---
        if old_index is not None and 0 <= old_index < count:
            try:
                old_item = list_widget.item(old_index)
                if old_item:
                    hero_name = old_item.data(HERO_NAME_ROLE)
                    if hero_name and old_item.toolTip() != hero_name:
                        # print(f"[LOG] Restoring tooltip for index {old_index}") # LOG
                        old_item.setToolTip(hero_name)
                        needs_viewport_update = True # Обновляем, т.к. подсказка влияет на отображение? (на всякий случай)
            except Exception as e:
                print(f"[ERROR] processing old item index {old_index}: {e}")

        # --- Установка подсказки нового элемента ---
        new_index = self.hotkey_cursor_index
        if 0 <= new_index < count:
            try:
                new_item = list_widget.item(new_index)
                if new_item:
                    hero_name = new_item.data(HERO_NAME_ROLE)
                    focus_tooltip = f">>> {hero_name} <<<"
                    if hero_name and new_item.toolTip() != focus_tooltip:
                        # print(f"[LOG] Setting focus tooltip for index {new_index}") # LOG
                        new_item.setToolTip(focus_tooltip)
                        needs_viewport_update = True
                    list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
            except Exception as e:
                 print(f"[ERROR] processing new item index {new_index}: {e}")

        # --- Обновляем viewport ОДИН РАЗ, если что-то изменилось ---
        if needs_viewport_update:
            # print("[LOG] Calling list_widget.viewport().update()") # LOG
            list_widget.viewport().update() # Вызываем обновление видимой области


    @Slot(str)
    def _handle_move_cursor(self, direction):
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        list_widget = self.right_list_widget
        count = list_widget.count()
        if count == 0: return
        old_index = self.hotkey_cursor_index
        num_columns = self._calculate_columns()
        if self.hotkey_cursor_index < 0: new_index = 0
        else:
            current_row = self.hotkey_cursor_index // num_columns
            current_col = self.hotkey_cursor_index % num_columns
            new_index = self.hotkey_cursor_index
            if direction == 'left': new_index -= 1
            elif direction == 'right': new_index += 1
            elif direction == 'up': new_index -= num_columns
            elif direction == 'down': new_index += num_columns
            if new_index < 0:
                 if direction == 'up': last_row_start_index = (count - 1) // num_columns * num_columns; temp_index = last_row_start_index + current_col; new_index = min(temp_index, count - 1)
                 else: new_index = count - 1
            elif new_index >= count:
                 if direction == 'down': new_index = current_col;
                 if new_index >= count: new_index = 0
                 else: new_index = 0
            new_index = max(0, min(count - 1, new_index))

        if old_index != new_index:
            self.hotkey_cursor_index = new_index
            # Вызываем обновление подсказок и viewport'а
            self._update_hotkey_highlight(old_index)
        elif 0 <= self.hotkey_cursor_index < count:
             current_item = list_widget.item(self.hotkey_cursor_index)
             if current_item: list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)


    @Slot()
    def _handle_toggle_selection(self):
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
            item = self.right_list_widget.item(self.hotkey_cursor_index)
            if item:
                try: item.setSelected(not item.isSelected())
                except Exception as e: print(f"Error toggling selection: {e}")


    # --- Keyboard Listener Loop and Start/Stop/Close ---
    def _keyboard_listener_loop(self):
        print("Keyboard listener thread started.")
        hooks = []
        try:
            hooks.append(keyboard.add_hotkey('up', lambda: self.move_cursor_signal.emit('up'), suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('down', lambda: self.move_cursor_signal.emit('down'), suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('left', lambda: self.move_cursor_signal.emit('left'), suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('right', lambda: self.move_cursor_signal.emit('right'), suppress=True, trigger_on_release=False))
            try: hooks.append(keyboard.add_hotkey('num 0', lambda: self.toggle_selection_signal.emit(), suppress=True, trigger_on_release=False))
            except ValueError:
                try: hooks.append(keyboard.add_hotkey('keypad 0', lambda: self.toggle_selection_signal.emit(), suppress=True, trigger_on_release=False))
                except ValueError: print("Warning: Could not hook Numpad 0.")
            print("Hotkeys registered.")
            self._stop_keyboard_listener_flag.wait()
            print("Keyboard listener stop signal received.")
        except ImportError: print("\nERROR: 'keyboard' library requires root/admin privileges.\n")
        except Exception as e: print(f"Error setting up keyboard hooks: {e}")
        finally:
            print("Unhooking keyboard...")
            for hook in hooks:
                try: keyboard.remove_hotkey(hook)
                except Exception as e: print(f"Error removing hook: {e}")
            print("Keyboard listener thread finished.")

    def start_keyboard_listener(self):
        if self._keyboard_listener_thread is None or not self._keyboard_listener_thread.is_alive():
            self._stop_keyboard_listener_flag.clear()
            self._keyboard_listener_thread = threading.Thread(target=self._keyboard_listener_loop, daemon=True)
            self._keyboard_listener_thread.start()
        else: print("Keyboard listener already running.")

    def stop_keyboard_listener(self):
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
            print("Signalling keyboard listener to stop...")
            self._stop_keyboard_listener_flag.set()
        else: print("Keyboard listener not running or already stopped.")

    def closeEvent(self, event):
        print("Close event triggered.")
        self.stop_keyboard_listener()
        if self._keyboard_listener_thread:
             print("Waiting for keyboard listener thread to join...")
             self._keyboard_listener_thread.join(timeout=1.0)
             if self._keyboard_listener_thread.is_alive(): print("Warning: Keyboard listener thread did not exit cleanly.")
             else: print("Keyboard listener thread joined successfully.")
        super().closeEvent(event)
    # --- END HOTKEY METHODS ---

    # --- Existing Methods ---

    def update_list_item_selection_states(self):
        """Обновляет состояние выбора элементов в QListWidget в соответствии с logic.selected_heroes."""
        if not self.hero_items or not self.right_list_widget: return
        list_widget = self.right_list_widget
        self.is_programmatically_updating_selection = True
        try:
            list_widget.blockSignals(True)
            current_logic_selection = set(self.logic.selected_heroes)
            for hero, item in self.hero_items.items():
                if item is None: continue
                try:
                    is_now_selected = (hero in current_logic_selection)
                    if item.isSelected() != is_now_selected: item.setSelected(is_now_selected)
                except RuntimeError: pass
                except Exception as e: print(f"[ERROR] updating selection state for {hero}: {e}")
        finally:
            try:
                if self.right_list_widget: list_widget.blockSignals(False)
            except RuntimeError: pass
            except Exception as e: print(f"[ERROR] unblocking signals: {e}")
            self.is_programmatically_updating_selection = False

    def update_priority_labels(self):
        """Обновляет фон для приоритетных героев."""
        if not self.hero_items or not self.right_list_widget: return
        list_widget = self.right_list_widget
        priority_color = QColor("lightcoral")
        default_brush = QBrush(Qt.GlobalColor.transparent)
        focused_index = self.hotkey_cursor_index # Получаем текущий индекс фокуса
        for hero, item in self.hero_items.items():
             if item is None: continue
             try:
                 item_index = list_widget.row(item)
                 is_priority = hero in self.logic.priority_heroes
                 # Проверяем, что ЭТОТ элемент НЕ имеет фокус
                 is_hotkey_focused = (item_index == focused_index)
                 target_brush = QBrush(priority_color) if is_priority else default_brush
                 if is_priority and not item.isSelected() and not is_hotkey_focused: # Только если приоритет, не выделен и не фокус
                     if item.background() != target_brush: item.setBackground(target_brush)
                 elif item.background() == QBrush(priority_color): # Убираем фон, если он был, но условия не выполнены
                     item.setBackground(default_brush)
             except RuntimeError: pass
             except Exception as e: print(f"[ERROR] updating priority label for {hero}: {e}")

    def update_selected_label(self):
        if self.selected_heroes_label:
             try: self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass
             except Exception as e: print(f"[ERROR] updating selected label: {e}")

    def update_counterpick_display(self):
        """Обновляет левую панель с рейтингом контрпиков."""
        if not self.result_frame or not self.result_label: return
        try:
            layout = self.result_frame.layout(); need_add_label = False
            if not layout: layout = QVBoxLayout(self.result_frame); layout.setAlignment(Qt.AlignmentFlag.AlignTop); self.result_frame.setLayout(layout); need_add_label = True
            while layout.count():
                 item = layout.takeAt(0)
                 if item:
                     widget = item.widget()
                     if widget and widget != self.result_label: widget.deleteLater()
                     elif item.layout():
                         while item.layout().count(): sub_item = item.layout().takeAt(0)
                         if sub_item and sub_item.widget(): sub_item.widget().deleteLater()
                         layout.removeItem(item)
                     elif item.spacerItem(): layout.removeItem(item)
            if not self.logic.selected_heroes:
                if self.result_label:
                    self.result_label.setText(get_text('no_heroes_selected')); self.result_label.show()
                    if need_add_label or layout.indexOf(self.result_label) == -1: layout.addWidget(self.result_label)
                if layout.count() == 0 or not layout.itemAt(layout.count() - 1).spacerItem(): layout.addStretch(1)
            else:
                if self.result_label: self.result_label.hide()
                if not self.left_images or (self.mode != 'min' and not self.small_images):
                     try: _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
                     except Exception as e: print(f"[ERROR] reloading images: {e}"); return
                if self.mode == "min": generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
                else: generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)
            layout.activate(); self.result_frame.adjustSize()
            if self.canvas:
                self.canvas.updateGeometry(); QTimer.singleShot(0, self.update_scrollregion); self.canvas.verticalScrollBar().setValue(0); self.canvas.update()
        except RuntimeError as e: print(f"[ERROR] RuntimeErr(upd_cnt): {e}")
        except Exception as e: print(f"[ERROR] General Err(upd_cnt): {e}")


    def update_ui_after_logic_change(self):
        # print("[LOG] Updating UI after logic change") # LOG
        self.update_selected_label(); self.update_counterpick_display(); update_horizontal_icon_list(self)
        self.update_list_item_selection_states(); self.update_priority_labels()

    def handle_selection_changed(self):
        # Вызывается при изменении ВЫДЕЛЕНИЯ (мышью или через setSelected)
        if self.is_programmatically_updating_selection: return
        if not self.right_list_widget: return
        list_widget = self.right_list_widget; current_ui_selection_names = set()
        for item in list_widget.selectedItems():
            hero_name = item.data(HERO_NAME_ROLE);
            if hero_name: current_ui_selection_names.add(hero_name)
        # print(f"[LOG] handle_selection_changed: UI selection = {current_ui_selection_names}") # LOG
        self.logic.set_selection(current_ui_selection_names)
        self.update_ui_after_logic_change()

    def show_priority_context_menu(self, pos):
        """Показывает контекстное меню для установки/снятия приоритета."""
        if not self.right_list_widget: return
        list_widget = self.right_list_widget
        global_pos = list_widget.viewport().mapToGlobal(pos)
        item = list_widget.itemAt(pos)
        if not item: return
        hero_name = item.data(HERO_NAME_ROLE)
        if not hero_name: return
        menu = QMenu(self)
        is_priority = hero_name in self.logic.priority_heroes
        is_selected = item.isSelected()
        action_text = get_text('remove_priority') if is_priority else get_text('set_priority')
        priority_action = menu.addAction(action_text)
        priority_action.setEnabled(is_selected)
        if not menu.isEmpty():
            action = menu.exec(global_pos)
            if priority_action and action == priority_action:
                 if hero_name in self.logic.selected_heroes:
                     self.logic.set_priority(hero_name)
                     self.update_ui_after_logic_change()
                 else: print(f"Cannot change priority for '{hero_name}' as it's not selected.")


    def change_mode(self, mode):
        """Изменяет режим и сбрасывает фокус."""
        print(f"[LOG] Attempting to change mode to: {mode}") # LOG
        if self.mode == mode: print("[LOG] Mode is already set."); return
        # Сбрасываем фокус на старом элементе перед сменой режима
        old_index = self.hotkey_cursor_index
        if old_index >= 0 and self.right_list_widget:
            try:
                old_item = self.right_list_widget.item(old_index)
                if old_item and old_item.data(Qt.UserRole + 10) == True:
                    # print(f"[LOG] Resetting focus property for old index {old_index} before mode change") # LOG
                    old_item.setData(Qt.UserRole + 10, False)
            except Exception as e: print(f"[ERROR] resetting old focus property before mode change: {e}")
        self.hotkey_cursor_index = -1 # Сбрасываем индекс
        change_mode(self, mode) # Перестраивает UI
        # Отложенный вызов для установки фокуса ПОСЛЕ перестройки
        QTimer.singleShot(250, self._reset_hotkey_cursor_after_mode_change)

    def _reset_hotkey_cursor_after_mode_change(self):
        """Восстанавливает фокус после смены режима."""
        print("[LOG] _reset_hotkey_cursor_after_mode_change called") # LOG
        if self.right_list_widget and self.right_list_widget.isVisible() and self.mode != 'min':
            count = self.right_list_widget.count()
            if count > 0:
                self.hotkey_cursor_index = 0
                self._calculate_columns()
                # print("[LOG] --> Calling _update_hotkey_highlight(None) to set initial focus") # LOG
                self._update_hotkey_highlight(None)
            else: self.hotkey_cursor_index = -1
        else: self.hotkey_cursor_index = -1


    # --- Остальные методы ---
    def restore_hero_selections(self):
        # print("[LOG] restore_hero_selections called") # LOG
        self.update_ui_after_logic_change()
        # Восстанавливаем подсветку фокуса
        if self.hotkey_cursor_index != -1:
             # print("[LOG] --> Scheduling focus highlight update after restore") # LOG
             QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))


    def switch_language(self, lang):
        # print(f"[LOG] Switching language to {lang}") # LOG
        set_language(lang); self.update_language(); self.update_ui_after_logic_change()
        # Восстанавливаем подсветку фокуса
        if self.hotkey_cursor_index != -1:
            # print("[LOG] --> Scheduling focus highlight update after language switch") # LOG
            QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))


    def update_language(self):
        """Обновляет тексты интерфейса и подсказки элементов списка."""
        # print("[LOG] update_language called") # LOG
        self.setWindowTitle(f"{get_text('title')} v{version}")
        if self.selected_heroes_label: self.update_selected_label()
        if self.result_label and not self.logic.selected_heroes: self.result_label.setText(get_text('no_heroes_selected'))
        if self.author_button: self.author_button.setText(get_text('about_author'))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating'))
        if self.top_frame: self._update_top_panel_lang()
        if self.right_frame: self._update_right_panel_lang()
        if self.right_list_widget:
            focused_hero_tooltip = None
            focused_item = None
            if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
                 focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
            if focused_item: focused_hero_tooltip = focused_item.toolTip()
            for i in range(self.right_list_widget.count()):
                item = self.right_list_widget.item(i)
                if item:
                    hero_name = item.data(HERO_NAME_ROLE)
                    if hero_name:
                        item_text = hero_name if self.mode == "max" else ""
                        if item.text() != item_text: item.setText(item_text)
                        item.setToolTip(hero_name)
            current_focused_item = None
            if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
                current_focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
            if focused_hero_tooltip and current_focused_item == focused_item:
                 current_focused_item.setToolTip(focused_hero_tooltip)

    def _update_top_panel_lang(self):
        # --- ИСПРАВЛЕНИЕ ОШИБКИ ИМПОРТА ---
        try:
            # Находим элементы более надежно по имени объекта, если возможно
            # Или используем старый метод поиска по тексту
            lang_label = self.top_frame.findChild(QLabel, "language_label") or self._find_object_by_text_keys(QLabel, ['language'])
            mode_label = self.top_frame.findChild(QLabel, "mode_label") or self._find_object_by_text_keys(QLabel, ['mode'])
            if lang_label: lang_label.setText(get_text('language')); lang_label.setObjectName("language_label") # Добавляем имя объекта для будущего поиска
            if mode_label: mode_label.setText(get_text('mode')); mode_label.setObjectName("mode_label")

            min_button = self.top_frame.findChild(QPushButton, "min_button") or self._find_object_by_text_keys(QPushButton,['mode_min'])
            middle_button = self.top_frame.findChild(QPushButton, "middle_button") or self._find_object_by_text_keys(QPushButton,['mode_middle'])
            max_button = self.top_frame.findChild(QPushButton, "max_button") or self._find_object_by_text_keys(QPushButton,['mode_max'])
            topmost_button = self.top_frame.findChild(QPushButton, "topmost_button") or self._find_object_by_text_keys(QPushButton,['topmost_on', 'topmost_off'])
            if min_button: min_button.setText(get_text('mode_min')); min_button.setObjectName("min_button")
            if middle_button: middle_button.setText(get_text('mode_middle')); middle_button.setObjectName("middle_button")
            if max_button: max_button.setText(get_text('mode_max')); max_button.setObjectName("max_button")
            if topmost_button:
                is_topmost = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
                topmost_button.setText(get_text('topmost_on') if is_topmost else get_text('topmost_off'))
                topmost_button.setObjectName("topmost_button")

            if self.author_button: self.author_button.setText(get_text('about_author'))
            if self.rating_button: self.rating_button.setText(get_text('hero_rating'))

            # Обработка QComboBox
            lang_combo = self.top_frame.findChild(QComboBox) # Используем QComboBox напрямую
            if lang_combo:
                current_lang_text = lang_combo.currentText()
                current_lang_code = DEFAULT_LANGUAGE # По умолчанию
                for code, name in SUPPORTED_LANGUAGES.items():
                    if name == current_lang_text:
                        current_lang_code = code
                        break
                lang_combo.blockSignals(True)
                lang_combo.clear()
                lang_combo.addItems(SUPPORTED_LANGUAGES.values())
                lang_combo.setCurrentText(SUPPORTED_LANGUAGES[current_lang_code])
                lang_combo.blockSignals(False)
            else:
                print("[WARN] QComboBox for language not found in top panel.")

        except Exception as e: print(f"[ERROR] updating top panel language: {e}")

    def _find_object_by_text_keys(self, obj_type, keys, parent_widget=None):
        """Вспомогательная функция для поиска виджета по тексту."""
        parent = parent_widget if parent_widget else self.top_frame
        if not parent: return None
        for widget in parent.findChildren(obj_type):
            current_text = ""
            widget_text_func = getattr(widget, "text", None)
            if callable(widget_text_func): current_text = widget_text_func()
            if not current_text: continue
            for key in keys:
                possible_texts = [get_text(key, lang=l) for l in SUPPORTED_LANGUAGES]
                if current_text in possible_texts: return widget
        return None

    def _update_right_panel_lang(self):
         if not self.right_frame: return
         try:
             copy_button = self.right_frame.findChild(QPushButton, "copy_button") or self._find_object_by_text_keys(QPushButton, ['copy_rating'], self.right_frame)
             clear_button = self.right_frame.findChild(QPushButton, "clear_button") or self._find_object_by_text_keys(QPushButton, ['clear_all'], self.right_frame)
             if copy_button: copy_button.setText(get_text('copy_rating')); copy_button.setObjectName("copy_button")
             if clear_button: clear_button.setText(get_text('clear_all')); clear_button.setObjectName("clear_button")
             self.update_selected_label()
         except Exception as e: print(f"[ERROR] updating right panel language: {e}")


# --- Глобальные функции ---
def create_gui():
    return MainWindow()