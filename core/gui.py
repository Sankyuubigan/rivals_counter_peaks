# File: gui.py
import time
import threading
import keyboard

from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame,
                               QLabel, QPushButton, QApplication, QListWidget, QListWidgetItem, QMenu,
                               QAbstractItemView, QStyle, QComboBox, QScrollArea)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QPoint, QModelIndex, QEvent
from PySide6.QtGui import QColor, QPalette, QIcon, QBrush, QMouseEvent
from top_panel import create_top_panel
from right_panel import create_right_panel, HERO_NAME_ROLE # Убедимся, что right_panel импортирует делегат
from left_panel import create_left_panel
from utils_gui import copy_to_clipboard
from build import version
from logic import CounterpickLogic, TEAM_SIZE
from images_load import get_images_for_mode, SIZES
from translations import get_text, set_language, DEFAULT_LANGUAGE, TRANSLATIONS, SUPPORTED_LANGUAGES
from mode_manager import change_mode, update_interface_for_mode
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes
from display import generate_counterpick_display, generate_minimal_icon_list

# --- Класс MainWindow ---
class MainWindow(QMainWindow):
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()
    toggle_mode_signal = Signal()
    clear_all_signal = Signal()

    def __init__(self):
        super().__init__()
        self.logic = CounterpickLogic()
        self.mode = "middle"
        self.initial_pos = None
        self.mode_positions = {"max": None, "middle": None, "min": None}
        self.copy_to_clipboard = lambda: copy_to_clipboard(self.logic)

        # Атрибуты UI
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_frame, self.author_button, self.rating_button = None, None, None
        self.main_widget, self.inner_layout, self.left_container = None, None, None
        self.icons_scroll_area = None
        self.icons_scroll_content = None
        self.icons_scroll_content_layout = None
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

        # Для перемещения окна
        self._mouse_pressed = False
        self._old_pos = None

        self.init_ui()
        self.start_keyboard_listener()

    # --- Перемещение окна без рамки ---
    def mousePressEvent(self, event: QMouseEvent):
        if self.mode == "min" and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_pressed = True; self._old_pos = event.globalPosition().toPoint(); event.accept()
        else: self._mouse_pressed = False; super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos; self.move(self.pos() + delta); self._old_pos = event.globalPosition().toPoint(); event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False; self._old_pos = None; event.accept()
        else: super().mouseReleaseEvent(event)
    # ------------------------------------

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{version}")
        self.setGeometry(100, 100, 950, 350); self.setMinimumSize(400, 100)
        self.initial_pos = self.pos(); self.mode_positions["middle"] = self.pos()

        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        (self.top_frame, self.author_button, self.rating_button, self.switch_mode_cb) = create_top_panel(self, self.change_mode, self.logic)
        self.main_layout.addWidget(self.top_frame)

        # Создаем QScrollArea для иконок
        self.icons_scroll_area = QScrollArea(); self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f0f0f0; }")
        self.icons_scroll_content = QWidget(); self.icons_scroll_content_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_scroll_content_layout.setContentsMargins(5, 2, 5, 2); self.icons_scroll_content_layout.setSpacing(4); self.icons_scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)

        # Расчет высоты icons_scroll_area
        try:
            self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(self.mode)
            h_icon_h = SIZES[self.mode]['horizontal'][1] if self.mode in SIZES and 'horizontal' in SIZES[self.mode] else 30
            icons_frame_height = h_icon_h + 12
        except Exception as e: print(f"[ERROR] Ошибка загрузки изображений в init_ui: {e}"); icons_frame_height = 42; self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.icons_scroll_area.setFixedHeight(icons_frame_height); self.main_layout.addWidget(self.icons_scroll_area)

        self.main_widget = QWidget(); self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setContentsMargins(0, 0, 0, 0); self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1)

        # Изображения уже загружены

        self.left_container = QWidget(); left_layout = QVBoxLayout(self.left_container); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(0)
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.left_container)
        left_layout.addWidget(self.canvas, stretch=1); self.inner_layout.addWidget(self.left_container, stretch=2)

        self.right_frame, self.selected_heroes_label = create_right_panel(self, self.mode) # Делегат устанавливается внутри
        self.inner_layout.addWidget(self.right_frame, stretch=1)

        self.switch_language_callback = lambda lang: self.switch_language(lang)
        self.update_language()
        update_interface_for_mode(self)

        self.move_cursor_signal.connect(self._handle_move_cursor)
        self.toggle_selection_signal.connect(self._handle_toggle_selection)
        self.toggle_mode_signal.connect(self._handle_toggle_mode)
        self.clear_all_signal.connect(self._handle_clear_all)

        if self.right_list_widget and self.right_list_widget.count() > 0 and self.mode != 'min':
            self.hotkey_cursor_index = 0
            QTimer.singleShot(100, lambda: self._update_hotkey_highlight(None))

    # --- HOTKEY RELATED METHODS ---

    def _calculate_columns(self):
        """Вычисляет количество колонок."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min':
            self._num_columns_cache = 1; return 1
        try:
            vp_width = self.right_list_widget.viewport().width(); grid_w = self.right_list_widget.gridSize().width(); spacing = self.right_list_widget.spacing();
            if grid_w <= 0: return self._num_columns_cache
            # <<< ИСПРАВЛЕНИЕ: eff_grid_w должно быть присвоено здесь >>>
            eff_grid_w = grid_w + spacing
            if eff_grid_w <= 0: return self._num_columns_cache
            cols = max(1, int(vp_width / eff_grid_w))
            self._num_columns_cache = cols; return cols
        except Exception as e: print(f"[ERROR] Calculating columns: {e}"); return self._num_columns_cache


    def _update_hotkey_highlight(self, old_index=None):
        """
        Обновляет ПОДСКАЗКУ элемента и запрашивает обновление viewport'а,
        чтобы делегат перерисовал рамку.
        """
        # print(f"[LOG] _update_hotkey_highlight called: old={old_index}, new={self.hotkey_cursor_index}") # LOG
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        list_widget = self.right_list_widget; count = list_widget.count()
        if count == 0: return

        needs_viewport_update = False

        # Восстановление подсказки старого элемента
        if old_index is not None and 0 <= old_index < count:
            try:
                old_item = list_widget.item(old_index)
                if old_item:
                    hero_name = old_item.data(HERO_NAME_ROLE)
                    if hero_name and old_item.toolTip() != hero_name: old_item.setToolTip(hero_name); needs_viewport_update = True
            except Exception as e: print(f"[ERROR] processing old item index {old_index}: {e}")

        # Установка подсказки нового элемента
        new_index = self.hotkey_cursor_index
        if 0 <= new_index < count:
            try:
                new_item = list_widget.item(new_index)
                if new_item:
                    hero_name = new_item.data(HERO_NAME_ROLE)
                    focus_tooltip = f">>> {hero_name} <<<"
                    if hero_name and new_item.toolTip() != focus_tooltip: new_item.setToolTip(focus_tooltip); needs_viewport_update = True
                    list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
            except Exception as e: print(f"[ERROR] processing new item index {new_index}: {e}")

        # --- Обновляем viewport ОДИН РАЗ, если нужно ---
        # Обновляем всегда при смене индекса для перерисовки рамки делегатом
        if needs_viewport_update or old_index != new_index:
             # print("[LOG] Calling list_widget.viewport().update()") # LOG
             list_widget.viewport().update() # Вызываем обновление видимой области


    @Slot(str)
    def _handle_move_cursor(self, direction):
        """Обрабатывает перемещение фокуса горячими клавишами."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        list_widget = self.right_list_widget; count = list_widget.count()
        if count == 0: return

        old_index = self.hotkey_cursor_index
        num_columns = self._calculate_columns() # Получаем АКТУАЛЬНОЕ число колонок
        # print(f"[LOG] _handle_move_cursor: direction={direction}, old_index={old_index}, num_columns={num_columns}") # LOG

        if self.hotkey_cursor_index < 0: new_index = 0
        else:
            current_row = self.hotkey_cursor_index // num_columns; current_col = self.hotkey_cursor_index % num_columns
            new_index = self.hotkey_cursor_index

            # --- ЛОГИКА ПЕРЕМЕЩЕНИЯ ---
            if direction == 'left':
                if current_col > 0: new_index -= 1
                else: new_index += (num_columns - 1); new_index = min(new_index, count - 1)
            elif direction == 'right':
                if current_col < num_columns - 1: new_index += 1
                else: new_index -= (num_columns - 1)
                new_index = min(new_index, count - 1)
            elif direction == 'up':
                new_index -= num_columns
                if new_index < 0:
                    last_row_index = (count - 1) // num_columns
                    potential_index = last_row_index * num_columns + current_col
                    new_index = potential_index if potential_index < count else count - 1
            elif direction == 'down':
                new_index += num_columns
                if new_index >= count:
                    new_index = current_col
                    if new_index >= count: new_index = 0
            new_index = max(0, min(count - 1, new_index))
        # print(f"[LOG] --> new_index={new_index}") # LOG
        if old_index != new_index:
            self.hotkey_cursor_index = new_index
            self._update_hotkey_highlight(old_index)
        elif 0 <= self.hotkey_cursor_index < count:
             current_item = list_widget.item(self.hotkey_cursor_index)
             if current_item: list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)


    @Slot()
    def _handle_toggle_selection(self):
        """Обрабатывает выбор/снятие выбора горячей клавишей."""
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode == 'min': return
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
            item = self.right_list_widget.item(self.hotkey_cursor_index)
            if item:
                try: item.setSelected(not item.isSelected())
                except Exception as e: print(f"Error toggling selection: {e}")

    @Slot()
    def _handle_toggle_mode(self):
        """Переключает режим между min и middle по горячей клавише."""
        print("[LOG] _handle_toggle_mode called") # LOG
        if self.mode == "min":
            print("[LOG] --> Switching to middle mode") # LOG
            self.change_mode("middle")
        else: # Включая middle и max
            print("[LOG] --> Switching to min mode") # LOG
            self.change_mode("min")

    # <<< СЛОТ для очистки >>>
    @Slot()
    def _handle_clear_all(self):
        """Обрабатывает сигнал очистки от горячей клавиши."""
        print("[LOG] _handle_clear_all called") # LOG
        self.logic.clear_all()
        self.update_ui_after_logic_change()
        # Сброс фокуса хоткея
        if self.right_list_widget and self.mode != 'min':
            old_index = self.hotkey_cursor_index
            self.hotkey_cursor_index = 0 if self.right_list_widget.count() > 0 else -1
            if self.hotkey_cursor_index != old_index:
                 self._update_hotkey_highlight(old_index)
            elif self.hotkey_cursor_index != -1:
                 self._update_hotkey_highlight(None)
        else:
            self.hotkey_cursor_index = -1

    # --- Keyboard Listener Loop and Start/Stop/Close ---
    def _keyboard_listener_loop(self):
        print("Keyboard listener thread started.")
        def run_if_topmost(func):
            def wrapper(*args, **kwargs):
                is_topmost = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
                if is_topmost:
                    try: func(*args, **kwargs)
                    except Exception as e: print(f"[ERROR] Exception in hotkey callback: {e}")
            return wrapper

        @run_if_topmost
        def on_up(): self.move_cursor_signal.emit('up')
        @run_if_topmost
        def on_down(): self.move_cursor_signal.emit('down')
        @run_if_topmost
        def on_left(): self.move_cursor_signal.emit('left')
        @run_if_topmost
        def on_right(): self.move_cursor_signal.emit('right')
        @run_if_topmost
        def on_select(): self.toggle_selection_signal.emit()
        @run_if_topmost
        def on_toggle_mode(): self.toggle_mode_signal.emit()
        @run_if_topmost
        def on_clear(): self.clear_all_signal.emit()

        hooks = []
        try:
            # Горячие клавиши с Tab
            hooks.append(keyboard.add_hotkey('tab+up', on_up, suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('tab+down', on_down, suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('tab+left', on_left, suppress=True, trigger_on_release=False))
            hooks.append(keyboard.add_hotkey('tab+right', on_right, suppress=True, trigger_on_release=False))
            try: hooks.append(keyboard.add_hotkey('tab+num 0', on_select, suppress=True, trigger_on_release=False))
            except ValueError:
                try: hooks.append(keyboard.add_hotkey('tab+keypad 0', on_select, suppress=True, trigger_on_release=False))
                except ValueError: print("[WARN] Could not hook Tab + Numpad 0.")
            try: hooks.append(keyboard.add_hotkey('tab+delete', on_toggle_mode, suppress=True, trigger_on_release=False))
            except ValueError:
                 try: hooks.append(keyboard.add_hotkey('tab+del', on_toggle_mode, suppress=True, trigger_on_release=False))
                 except ValueError:
                     try: hooks.append(keyboard.add_hotkey('tab+.', on_toggle_mode, suppress=True, trigger_on_release=False)) # Numpad .
                     except ValueError: print("[WARN] Could not hook Tab + Delete/Numpad .")
            # Горячая клавиша очистки
            try: hooks.append(keyboard.add_hotkey('tab+num -', on_clear, suppress=True, trigger_on_release=False))
            except ValueError:
                try: hooks.append(keyboard.add_hotkey('tab+keypad -', on_clear, suppress=True, trigger_on_release=False))
                except ValueError:
                    try: hooks.append(keyboard.add_hotkey('tab+-', on_clear, suppress=True, trigger_on_release=False))
                    except ValueError: print("[WARN] Could not hook Tab + Numpad - / Keypad - / -.")

            print("Hotkeys registered.")
            self._stop_keyboard_listener_flag.wait()
            print("Keyboard listener stop signal received.")
        except ImportError: print("\n[ERROR] 'keyboard' library requires root/admin privileges.\n")
        except Exception as e: print(f"[ERROR] setting up keyboard hooks: {e}")
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
        focused_index = self.hotkey_cursor_index
        for hero, item in self.hero_items.items():
             if item is None: continue
             try:
                 item_index = list_widget.row(item)
                 is_priority = hero in self.logic.priority_heroes
                 is_hotkey_focused = (item_index == focused_index)
                 target_brush = QBrush(priority_color) if is_priority else default_brush
                 if is_priority and not item.isSelected() and not is_hotkey_focused:
                     if item.background() != target_brush: item.setBackground(target_brush)
                 elif item.background() == QBrush(priority_color):
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
        if not self.result_frame or not self.result_label: print("[WARN] No result_frame or result_label"); return
        try:
            layout = self.result_frame.layout(); need_add_label = False
            if not layout: layout = QVBoxLayout(self.result_frame); layout.setAlignment(Qt.AlignmentFlag.AlignTop); self.result_frame.setLayout(layout); need_add_label = True
            # Очистка layout'а
            while layout.count(): item = layout.takeAt(0)
            if item:
                widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem()
                if widget and widget != self.result_label: widget.deleteLater()
                elif layout_item: layout.removeItem(item)
                elif spacer: layout.removeItem(item)
            # Заполнение layout'а
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
                # print(f"[LOG] Generating display for mode: {self.mode}") # LOG
                if self.mode == "min": generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
                else: generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)

            layout.activate(); self.result_frame.adjustSize()
            if self.canvas:
                self.canvas.updateGeometry(); QTimer.singleShot(0, self.update_scrollregion); self.canvas.verticalScrollBar().setValue(0); self.canvas.update()
        except RuntimeError as e: print(f"[ERROR] RuntimeErr(upd_cnt): {e}")
        except Exception as e: print(f"[ERROR] General Err(upd_cnt): {e}")


    def update_ui_after_logic_change(self):
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
        self.hotkey_cursor_index = -1 # Сбрасываем индекс ДО перестройки
        change_mode(self, mode) # Перестраивает UI
        QTimer.singleShot(250, self._reset_hotkey_cursor_after_mode_change)

    def _reset_hotkey_cursor_after_mode_change(self):
        """Восстанавливает фокус после смены режима."""
        print("[LOG] _reset_hotkey_cursor_after_mode_change called") # LOG
        if self.right_list_widget and self.right_list_widget.isVisible() and self.mode != 'min':
            count = self.right_list_widget.count()
            if count > 0:
                self.hotkey_cursor_index = 0
                self._calculate_columns() # Пересчитываем колонки для нового режима
                self._update_hotkey_highlight(None) # Запрашиваем обновление для отрисовки рамки
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
        try:
            lang_label = self.top_frame.findChild(QLabel, "language_label") or self._find_object_by_text_keys(QLabel, ['language'])
            mode_label = self.top_frame.findChild(QLabel, "mode_label") or self._find_object_by_text_keys(QLabel, ['mode'])
            if lang_label: lang_label.setText(get_text('language')); lang_label.setObjectName("language_label")
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
            lang_combo = self.top_frame.findChild(QComboBox)
            if lang_combo:
                current_lang_text = lang_combo.currentText(); current_lang_code = DEFAULT_LANGUAGE
                for code, name in SUPPORTED_LANGUAGES.items():
                    if name == current_lang_text: current_lang_code = code; break
                lang_combo.blockSignals(True); lang_combo.clear(); lang_combo.addItems(SUPPORTED_LANGUAGES.values()); lang_combo.setCurrentText(SUPPORTED_LANGUAGES[current_lang_code]); lang_combo.blockSignals(False)
        except Exception as e: print(f"[ERROR] updating top panel language: {e}")

    def _find_object_by_text_keys(self, obj_type, keys, parent_widget=None):
        """Вспомогательная функция для поиска виджета по тексту."""
        parent = parent_widget if parent_widget else self.top_frame
        if not parent: return None
        for widget in parent.findChildren(obj_type):
            current_text = ""; widget_text_func = getattr(widget, "text", None)
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