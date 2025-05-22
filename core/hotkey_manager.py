# File: core/hotkey_manager.py
import json
import logging
import threading
from typing import Dict, Callable, Any

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QMetaObject, Q_ARG, Qt 

from core.utils import get_settings_path
from core.lang.translations import get_text 

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    keyboard = None
    logging.error("HotkeyManager: 'keyboard' library not found. Global hotkeys will be disabled.")


DEFAULT_HOTKEYS = {
    "move_cursor_up": "tab+up",
    "move_cursor_down": "tab+down",
    "move_cursor_left": "tab+left",
    "move_cursor_right": "tab+right",
    "toggle_selection": "tab+num 0",
    "toggle_mode": "tab+decimal",  
    "recognize_heroes": "tab+num /",
    "clear_all": "tab+num -",
    "copy_team": "tab+num 1",
    "toggle_tray_mode": "tab+num 7", 
    "toggle_mouse_ignore_independent": "tab+num 9", 
    "debug_capture": "tab+num 3",
}

HOTKEY_ACTIONS_CONFIG = {
    "move_cursor_up": {"desc_key": "hotkey_desc_navigation_up", "signal_name": "action_move_cursor_up"},
    "move_cursor_down": {"desc_key": "hotkey_desc_navigation_down", "signal_name": "action_move_cursor_down"},
    "move_cursor_left": {"desc_key": "hotkey_desc_navigation_left", "signal_name": "action_move_cursor_left"},
    "move_cursor_right": {"desc_key": "hotkey_desc_navigation_right", "signal_name": "action_move_cursor_right"},
    "toggle_selection": {"desc_key": "hotkey_desc_select", "signal_name": "action_toggle_selection"},
    "toggle_mode": {"desc_key": "hotkey_desc_toggle_mode", "signal_name": "action_toggle_mode"},
    "recognize_heroes": {"desc_key": "hotkey_desc_recognize", "signal_name": "action_recognize_heroes"},
    "clear_all": {"desc_key": "hotkey_desc_clear", "signal_name": "action_clear_all"},
    "copy_team": {"desc_key": "hotkey_desc_copy_team", "signal_name": "action_copy_team"},
    "toggle_tray_mode": {"desc_key": "hotkey_desc_toggle_tray", "signal_name": "action_toggle_tray_mode"},
    "toggle_mouse_ignore_independent": {"desc_key": "hotkey_desc_toggle_mouse_ignore", "signal_name": "action_toggle_mouse_ignore_independent"},
    "debug_capture": {"desc_key": "hotkey_desc_debug_screenshot", "signal_name": "action_debug_capture"},
}

class HotkeyManager(QObject):
    hotkeys_updated_signal = Signal()

    def __init__(self, main_window: QObject): 
        super().__init__()
        self.main_window = main_window
        self._current_hotkeys: Dict[str, str] = {} # {action_id: "hotkey_string"}
        self._hotkey_callbacks: Dict[str, Callable] = {} # {action_id: callback_function}
        self._listener_thread: threading.Thread | None = None
        self._stop_listener_flag = threading.Event()
        self.settings_file_path = get_settings_path()
        
        # Теперь будет хранить {hotkey_string: action_id} для активных хуков
        self._active_keyboard_hooks: Dict[str, str] = {}

        self._prepare_callbacks()

    def _prepare_callbacks(self):
        for action_id in HOTKEY_ACTIONS_CONFIG.keys():
            self._hotkey_callbacks[action_id] = self._create_queued_callback(action_id)

    def _create_queued_callback(self, action_id: str):
        def _callback():
            logging.debug(f"[HotkeyManager Thread] Action triggered: {action_id}. Queueing call to _emit_action_signal_slot via QMetaObject.")
            try:
                QMetaObject.invokeMethod(self, "_emit_action_signal_slot", 
                                         Qt.ConnectionType.QueuedConnection, 
                                         Q_ARG(str, action_id))
            except Exception as e:
                logging.error(f"[HotkeyManager Thread] Error invoking method for {action_id}: {e}", exc_info=True)
        return _callback

    @Slot(str) 
    def _emit_action_signal_slot(self, action_id: str):
        logging.info(f"[HotkeyManager MainThread] _emit_action_signal_slot received for action: {action_id}")
        signal_config = HOTKEY_ACTIONS_CONFIG.get(action_id)
        if not signal_config:
            logging.error(f"[HotkeyManager MainThread] No config found for action_id: {action_id}")
            return

        signal_name = signal_config.get("signal_name")
        if not signal_name:
            logging.error(f"[HotkeyManager MainThread] 'signal_name' not found in config for action_id: {action_id}")
            return
            
        if not hasattr(self.main_window, signal_name):
            logging.error(f"[HotkeyManager MainThread] Signal '{signal_name}' not found in MainWindow for action '{action_id}'. MainWindow type: {type(self.main_window)}")
            return
        
        signal_to_emit = getattr(self.main_window, signal_name)
        if not isinstance(signal_to_emit, Signal): 
            logging.error(f"[HotkeyManager MainThread] Attribute '{signal_name}' in MainWindow is not a Signal for action '{action_id}'. Type: {type(signal_to_emit)}")
            return

        try:
            logging.debug(f"[HotkeyManager MainThread] Attempting to emit signal for action {action_id} (Signal: {signal_name})")
            signal_to_emit.emit()
            logging.info(f"[HotkeyManager MainThread] Successfully emitted signal for action {action_id}")
        except Exception as e:
            logging.error(f"[HotkeyManager MainThread] Error emitting signal for action {action_id}: {e}", exc_info=True)


    def load_hotkeys(self):
        self._current_hotkeys = DEFAULT_HOTKEYS.copy() 
        if self.settings_file_path.exists():
            try:
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    loaded_hotkeys = json.load(f)
                for action_id, hotkey_str in loaded_hotkeys.items():
                    if action_id in self._current_hotkeys and isinstance(hotkey_str, str):
                        self._current_hotkeys[action_id] = hotkey_str
                    else:
                        logging.warning(f"HotkeyManager: Invalid or unknown action_id '{action_id}' or hotkey_str '{hotkey_str}' in settings file.")
                logging.info(f"Hotkeys loaded from {self.settings_file_path}")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"HotkeyManager: Error loading hotkeys from {self.settings_file_path}: {e}. Using defaults.")
                self._current_hotkeys = DEFAULT_HOTKEYS.copy() 
        else:
            logging.info("HotkeyManager: Settings file not found. Using default hotkeys.")
        self.hotkeys_updated_signal.emit()

    def save_hotkeys(self, hotkeys_to_save: Dict[str, str] | None = None):
        data_to_save = hotkeys_to_save if hotkeys_to_save is not None else self._current_hotkeys
        try:
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            logging.info(f"Hotkeys saved to {self.settings_file_path}")
            self._current_hotkeys = data_to_save.copy() 
            self.hotkeys_updated_signal.emit()
        except IOError as e:
            logging.error(f"HotkeyManager: Error saving hotkeys to {self.settings_file_path}: {e}")

    def get_current_hotkeys(self) -> Dict[str, str]:
        return self._current_hotkeys.copy()

    def get_default_hotkeys(self) -> Dict[str, str]:
        return DEFAULT_HOTKEYS.copy()
    
    def get_actions_config(self) -> Dict[str, Any]:
        return HOTKEY_ACTIONS_CONFIG.copy()

    def get_hotkey_for_action(self, action_id: str) -> str | None:
        return self._current_hotkeys.get(action_id)

    def update_hotkey(self, action_id: str, new_hotkey_str: str):
        # Этот метод вызывается из HotkeySettingsDialog, когда пользователь МЕНЯЕТ хоткей в диалоге,
        # но еще НЕ СОХРАНИЛ. Фактическое сохранение и перерегистрация происходят в HotkeySettingsDialog.save_and_close(),
        # который затем вызывает self.save_hotkeys() и self.reregister_all_hotkeys().
        if action_id in self._current_hotkeys:
            # Просто обновляем внутреннее состояние self._current_hotkeys, чтобы диалог отображал актуальные изменения
            # НЕ вызываем здесь save_hotkeys или reregister_all_hotkeys
            if self._current_hotkeys[action_id] != new_hotkey_str:
                logging.debug(f"HotkeyManager: Hotkey for action '{action_id}' internally updated (in dialog) from '{self._current_hotkeys[action_id]}' to '{new_hotkey_str}'.")
                self._current_hotkeys[action_id] = new_hotkey_str
        else:
            logging.warning(f"HotkeyManager: Attempt to update hotkey for unknown action_id '{action_id}'.")


    def reregister_all_hotkeys(self):
        if not KEYBOARD_AVAILABLE or not keyboard:
            logging.warning("HotkeyManager: Cannot reregister hotkeys, keyboard library not available.")
            return

        logging.info(f"HotkeyManager: Starting reregistration. Current active hooks (before removal): {list(self._active_keyboard_hooks.keys())}")
        
        # Удаляем все ранее зарегистрированные хуки
        # keyboard.remove_hotkey() принимает строку-комбинацию или объект хука
        # Безопаснее передавать строку, если мы ее храним.
        removed_count = 0
        hooks_to_remove_strings = list(self._active_keyboard_hooks.keys()) # Копируем ключи (строки хоткеев)
        for hotkey_str_to_remove in hooks_to_remove_strings:
            try:
                logging.debug(f"Attempting to remove hook for string: '{hotkey_str_to_remove}'")
                keyboard.remove_hotkey(hotkey_str_to_remove)
                if hotkey_str_to_remove in self._active_keyboard_hooks:
                    del self._active_keyboard_hooks[hotkey_str_to_remove]
                removed_count += 1
                logging.debug(f"Successfully removed hook for string: '{hotkey_str_to_remove}'")
            except Exception as e_remove:
                logging.warning(f"HotkeyManager: Error removing hook for string '{hotkey_str_to_remove}': {e_remove}. Continuing...")
        
        logging.info(f"HotkeyManager: Removed {removed_count}/{len(hooks_to_remove_strings)} old hotkey strings. Current active hooks: {list(self._active_keyboard_hooks.keys())}")

        # Регистрируем новые хоткеи
        registered_count = 0
        logging.info(f"HotkeyManager: Registering new hotkeys based on current config: {self._current_hotkeys}")
        for action_id, hotkey_str in self._current_hotkeys.items():
            callback = self._hotkey_callbacks.get(action_id)
            if hotkey_str and hotkey_str.lower() != 'none' and hotkey_str != get_text('hotkey_none') and hotkey_str != get_text('hotkey_not_set') and callback:
                try:
                    suppress_hotkey = 'tab+' in hotkey_str.lower() and hotkey_str.lower() != 'tab'
                    logging.debug(f"HotkeyManager: Attempting to register '{hotkey_str}' for action '{action_id}'. Suppress: {suppress_hotkey}")
                    
                    # add_hotkey возвращает функцию для удаления этого конкретного хука, но нам это не нужно,
                    # так как мы удаляем по строке.
                    keyboard.add_hotkey(hotkey_str, callback, suppress=suppress_hotkey, trigger_on_release=False)
                    
                    self._active_keyboard_hooks[hotkey_str] = action_id # Сохраняем строку и действие
                    registered_count += 1
                    logging.info(f"HotkeyManager: Successfully registered '{hotkey_str}' for action '{action_id}'. Suppress: {suppress_hotkey}.")
                except ValueError as ve: 
                    logging.error(f"HotkeyManager: Failed to register hotkey '{hotkey_str}' for '{action_id}' due to invalid format: {ve}")
                except Exception as e:
                    logging.error(f"HotkeyManager: Failed to register hotkey '{hotkey_str}' for '{action_id}': {e}", exc_info=True)
            elif not callback:
                 logging.warning(f"HotkeyManager: No callback for action '{action_id}', cannot register hotkey '{hotkey_str}'.")
            else:
                 logging.debug(f"HotkeyManager: Hotkey '{hotkey_str}' for action '{action_id}' is 'none' or not set, skipping registration.")

        logging.info(f"HotkeyManager: Reregistered {registered_count} hotkeys. Final active hooks: {list(self._active_keyboard_hooks.keys())}")
        if registered_count == 0 and any(hk.lower() != 'none' and hk != get_text('hotkey_none') and hk != get_text('hotkey_not_set') for hk in self._current_hotkeys.values()):
            logging.error("HotkeyManager: No hotkeys were re-registered successfully despite valid configurations!")


    def start_listening(self):
        if not KEYBOARD_AVAILABLE or not keyboard:
            logging.warning("HotkeyManager: Cannot start listener, keyboard library not available.")
            return
        if self._listener_thread is None or not self._listener_thread.is_alive():
            logging.info("HotkeyManager: Starting keyboard listener thread...")
            self._stop_listener_flag.clear()
            # Перерегистрация хоткеев перед запуском потока слушателя
            self.reregister_all_hotkeys() 
            
            self._listener_thread = threading.Thread(target=self._listener_loop, daemon=True, name="HotkeyListenerThread")
            self._listener_thread.start()
            logging.info(f"HotkeyManager: Listener thread '{self._listener_thread.name}' started with ID {self._listener_thread.ident}.")
        else:
            logging.info(f"HotkeyManager: Keyboard listener thread '{self._listener_thread.name}' (ID: {self._listener_thread.ident}) already running.")


    def _listener_loop(self):
        if not KEYBOARD_AVAILABLE: return
        current_thread = threading.current_thread()
        logging.info(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) started.")
        try:
            while not self._stop_listener_flag.is_set():
                self._stop_listener_flag.wait(timeout=0.5) 
            logging.info(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) stop signal received.")
        except Exception as e:
            logging.error(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) Error: {e}", exc_info=True)
        finally:
            logging.info(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) Finished.")


    def stop_listening(self):
        if not KEYBOARD_AVAILABLE: return
        current_thread_name = self._listener_thread.name if self._listener_thread else "N/A"
        current_thread_id = self._listener_thread.ident if self._listener_thread else "N/A"

        if self._listener_thread and self._listener_thread.is_alive():
            logging.info(f"HotkeyManager: Signalling keyboard listener thread '{current_thread_name}' (ID: {current_thread_id}) to stop...")
            self._stop_listener_flag.set() 
            self._listener_thread.join(timeout=2.0) 
            if self._listener_thread.is_alive():
                logging.warning(f"HotkeyManager: Listener thread '{current_thread_name}' (ID: {current_thread_id}) did not exit cleanly within timeout.")
            else:
                logging.info(f"HotkeyManager: Listener thread '{current_thread_name}' (ID: {current_thread_id}) joined and finished.")
            self._listener_thread = None
        else:
            logging.info(f"HotkeyManager: Keyboard listener thread '{current_thread_name}' (ID: {current_thread_id}) not running or already stopped.")
        
        if KEYBOARD_AVAILABLE and keyboard:
            try:
                logging.info("[HotkeyManager stop_listening] Final unhooking of all registered hotkeys...")
                hooks_to_remove_strings = list(self._active_keyboard_hooks.keys())
                removed_count = 0
                for i, hotkey_str_to_remove in enumerate(hooks_to_remove_strings):
                    try:
                        keyboard.remove_hotkey(hotkey_str_to_remove)
                        if hotkey_str_to_remove in self._active_keyboard_hooks:
                            del self._active_keyboard_hooks[hotkey_str_to_remove]
                        removed_count +=1
                        logging.debug(f"Successfully removed hook for string '{hotkey_str_to_remove}' ({i+1}/{len(hooks_to_remove_strings)}) during stop_listening.")
                    except Exception as e_remove:
                         logging.warning(f"Error removing hook for string '{hotkey_str_to_remove}' ({i+1}/{len(hooks_to_remove_strings)}) during stop_listening: {e_remove}")
                logging.info(f"HotkeyManager: Removed {removed_count}/{len(hooks_to_remove_strings)} hotkey strings during stop_listening. Remaining active hooks: {list(self._active_keyboard_hooks.keys())}")
            except Exception as e_unhook:
                logging.error(f"[HotkeyManager stop_listening] Error during final unhook_all attempt: {e_unhook}")