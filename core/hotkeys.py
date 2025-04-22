# File: core/hotkeys.py
import threading
from PySide6.QtCore import QTimer, Signal, Slot, QObject, Qt
import keyboard
from core.win_api import is_window_topmost

class HotkeyManager(QObject):
    move_cursor_signal = Signal(str)
    toggle_selection_signal = Signal()
    toggle_mode_signal = Signal()
    clear_all_signal = Signal()

    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self._keyboard_listener_thread = None
        self._stop_keyboard_listener_flag = threading.Event()

    def run_if_topmost_gui(self, func):
        def wrapper(*args, **kwargs):
            if is_window_topmost(self.parent_window):
                QTimer.singleShot(0, lambda: func(*args, **kwargs))
        return wrapper

    
    def _handle_move_cursor(self, direction):
        if not self.parent_window.right_list_widget or not self.parent_window.right_list_widget.isVisible() or self.parent_window.mode == 'min': return
        list_widget = self.parent_window.right_list_widget; count = list_widget.count()
        if count == 0: return

        old_index = self.parent_window.hotkey_cursor_index
        num_columns = self.parent_window._calculate_columns()
        if self.parent_window.hotkey_cursor_index < 0: new_index = 0
        else:
            current_row = self.parent_window.hotkey_cursor_index // num_columns; current_col = self.parent_window.hotkey_cursor_index % num_columns
            new_index = self.parent_window.hotkey_cursor_index

            if direction == 'left':
                if current_col > 0: new_index -= 1
                elif current_row > 0:
                    new_index = (current_row - 1) * num_columns + (num_columns - 1)
                    new_index = min(new_index, count - 1)
                else:
                    new_index = count - 1

            elif direction == 'right':
                if current_col < num_columns - 1: new_index += 1
                elif self.parent_window.hotkey_cursor_index < count - 1:
                    new_index = (current_row + 1) * num_columns
                else:
                    new_index = 0
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
                    new_index = current_col
                    if new_index >= count: new_index = 0

            new_index = max(0, min(count - 1, new_index))
        if old_index != new_index:
            self.parent_window.hotkey_cursor_index = new_index
            self.parent_window._update_hotkey_highlight(old_index)
        elif 0 <= self.parent_window.hotkey_cursor_index < count:            
            current_item = list_widget.item(self.parent_window.hotkey_cursor_index)
            if current_item: list_widget.scrollToItem(current_item, QObject.ScrollHint.EnsureVisible)

    @Slot()
    def _handle_toggle_selection(self):
        if not self.parent_window.right_list_widget or not self.parent_window.right_list_widget.isVisible() or self.parent_window.mode == 'min': return
        
        if 0 <= self.parent_window.hotkey_cursor_index < self.parent_window.right_list_widget.count():
            try:
                item = self.parent_window.right_list_widget.item(self.parent_window.hotkey_cursor_index)
                if item:
                    item.setSelected(not item.isSelected())
            except RuntimeError: pass
            except Exception as e: print(f"Error toggling selection: {e}")

    @Slot()
    def _handle_toggle_mode(self):
        print("[LOG] _handle_toggle_mode called")
        if self.parent_window.mode == "min":
            print("[LOG] --> Switching to middle mode")
            self.parent_window.change_mode("middle")
        else:
            print("[LOG] --> Switching to min mode")
            self.parent_window.change_mode("min")

    @Slot()
    def _handle_clear_all(self):
        print("[LOG] _handle_clear_all called")
        self.parent_window.logic.clear_all()
        self.parent_window.update_ui_after_logic_change()
        if self.parent_window.right_list_widget and self.parent_window.right_list_widget.isVisible() and self.parent_window.mode != 'min':
            old_index = self.parent_window.hotkey_cursor_index
            count = self.parent_window.right_list_widget.count()
            self.parent_window.hotkey_cursor_index = 0 if count > 0 else -1
            if self.parent_window.hotkey_cursor_index != old_index or old_index == -1:
                self.parent_window._update_hotkey_highlight(old_index)
        else:
            self.parent_window.hotkey_cursor_index = -1

    def _keyboard_listener_loop(self):
        print("Keyboard listener thread started.")

        run_if_topmost_gui = self.run_if_topmost_gui

        @run_if_topmost_gui
        def _emit_move(direction): self.move_cursor_signal.emit(direction)
        @run_if_topmost_gui
        def _emit_toggle_select(): self.toggle_selection_signal.emit()
        @run_if_topmost_gui
        def _emit_toggle_mode(): self.toggle_mode_signal.emit()
        @run_if_topmost_gui
        def _emit_clear(): self.clear_all_signal.emit()
        @run_if_topmost_gui
        def _emit_recognize(): self.parent_window.recognize_heroes_signal.emit()

        self._register_topmost_hotkey(_emit_move, hooks=[])
        self._register_recognition_hotkey(_emit_recognize, hooks=[])
        self._register_change_mode_hotkey(_emit_toggle_mode, _emit_clear, _emit_toggle_select, hooks=[])

        print("Hotkeys registered successfully.")
        self._stop_keyboard_listener_flag.wait()
        print("Keyboard listener stop signal received.")

    def _register_topmost_hotkey(self, _emit_move, hooks):
        print(f"Регистрация хуков клавиатуры...")
        hooks.append(keyboard.add_hotkey('tab+up', lambda: _emit_move('up'), suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+down', lambda: _emit_move('down'), suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+left', lambda: _emit_move('left'), suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+right', lambda: _emit_move('right'), suppress=True, trigger_on_release=False))

    def _register_recognition_hotkey(self, _emit_recognize, hooks):
        
        
        hooks.append(keyboard.add_hotkey('tab+num /', _emit_recognize, suppress=True, trigger_on_release=False))
        print("[INFO] Hooked Tab + Num /")

        
        hooks.append(keyboard.add_hotkey('tab+keypad /', _emit_recognize, suppress=True, trigger_on_release=False))
        print("[INFO] Hooked Tab + Keypad /")

        hooks.append(keyboard.add_hotkey('tab+/', _emit_recognize, suppress=True, trigger_on_release=False))
        print("[INFO] Hooked Tab + /")
        
        print("[WARN] Could not hook Tab + Num / or Keypad / or /.")


    def _register_change_mode_hotkey(self, _emit_toggle_mode, _emit_clear, _emit_toggle_select, hooks):
        
        hooks.append(keyboard.add_hotkey('tab+num 0', _emit_toggle_select, suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+keypad 0', _emit_toggle_select, suppress=True, trigger_on_release=False))
        print("[WARN] Could not hook Tab + Numpad 0 / Keypad 0.")

        hooks.append(keyboard.add_hotkey('tab+delete', _emit_toggle_mode, suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+del', _emit_toggle_mode, suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+.', _emit_toggle_mode, suppress=True, trigger_on_release=False))
        print("[WARN] Could not hook Tab + Delete / Del / Numpad .")

        hooks.append(keyboard.add_hotkey('tab+num -', _emit_clear, suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+keypad -', _emit_clear, suppress=True, trigger_on_release=False))
        hooks.append(keyboard.add_hotkey('tab+-', _emit_clear, suppress=True, trigger_on_release=False))
        print("[WARN] Could not hook Tab + Num - / Keypad - / -.")

        print("\n[ERROR] 'keyboard' library requires root/admin privileges.\n")

        print("Unhooking keyboard...")
        keyboard.unhook_all()
        print("Keyboard listener thread finished.")

    def start_keyboard_listener(self):
        if self._keyboard_listener_thread is None or not self._keyboard_listener_thread.is_alive():
            print("Starting keyboard listener thread...")
            self._stop_keyboard_listener_flag.clear()
            self._keyboard_listener_thread = threading.Thread(target=self._keyboard_listener_loop, daemon=True)
            self._keyboard_listener_thread.start() 
        else: print("Keyboard listener already running.")

    def stop_keyboard_listener(self):
        if self._keyboard_listener_thread and self._keyboard_listener_thread.is_alive():
            print("Signalling keyboard listener to stop...")
            self._stop_keyboard_listener_flag.set()            
            if self.parent_window._recognition_worker:
                self.parent_window._recognition_worker.stop()
            if self.parent_window._recognition_thread and self.parent_window._recognition_thread.isRunning():
                print("Quitting recognition thread...")
                self.parent_window._recognition_thread.quit()
                if not self.parent_window._recognition_thread.wait(1000):
                    print("[WARN] Recognition thread did not quit gracefully.")                   
        else:
             if self.parent_window._recognition_worker: self.parent_window._recognition_worker.stop()
             if self.parent_window._recognition_thread and self.parent_window._recognition_thread.isRunning():
                print("Quitting orphan recognition thread...")               
                self.parent_window._recognition_thread.quit()
                self.parent_window._recognition_thread.wait(500)
                