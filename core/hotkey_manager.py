# File: core/hotkey_manager.py
import json
import logging
import threading
from typing import Dict, Callable, Any

from PySide6.QtCore import QObject, Signal, QTimer # Добавлен QTimer

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
        self._current_hotkeys: Dict[str, str] = {}
        self._hotkey_callbacks: Dict[str, Callable] = {} 
        self._listener_thread: threading.Thread | None = None
        self._stop_listener_flag = threading.Event()
        self.settings_file_path = get_settings_path()
        self._registered_keyboard_hooks = [] 

        self._prepare_callbacks()

    def _prepare_callbacks(self):
        for action_id, config in HOTKEY_ACTIONS_CONFIG.items():
            signal_name = config.get("signal_name")
            if signal_name and hasattr(self.main_window, signal_name):
                signal_instance = getattr(self.main_window, signal_name)
                if isinstance(signal_instance, Signal):
                    # Обертка для вызова в главном потоке
                    self._hotkey_callbacks[action_id] = self._create_queued_callback(signal_instance, action_id)
                else:
                    logging.warning(f"HotkeyManager: Attribute '{signal_name}' in MainWindow is not a Signal for action '{action_id}'.")
            else:
                logging.warning(f"HotkeyManager: Signal '{signal_name}' not found in MainWindow for action '{action_id}'.")

    def _create_queued_callback(self, signal_instance, action_id):
        # Эта функция создает замыкание, которое будет вызвано библиотекой keyboard
        def _callback():
            logging.info(f"[HotkeyManager Thread] Action triggered: {action_id}. Queueing signal emission.")
            # Используем QTimer.singleShot для вызова _emit_action_signal в главном потоке
            QTimer.singleShot(0, lambda s=signal_instance, aid=action_id: self._emit_action_signal(s, aid))
        return _callback

    def _emit_action_signal(self, signal_to_emit: Signal, action_id: str):
        # Этот метод теперь вызывается из главного потока благодаря QTimer
        logging.info(f"[HotkeyManager MainThread] Emitting signal for action: {action_id}")
        try:
            signal_to_emit.emit()
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
        # Этот метод вызывается из HotkeySettingsDialog.save_and_close()
        # когда пользователь сохраняет изменения.
        # HotkeySettingsDialog сам вызовет reregister_all_hotkeys() после успешного сохранения.
        if action_id in self._current_hotkeys:
            if self._current_hotkeys[action_id] != new_hotkey_str:
                logging.info(f"Hotkey for action '{action_id}' updated internally (pending save/reregister) from '{self._current_hotkeys[action_id]}' to '{new_hotkey_str}'.")
                self._current_hotkeys[action_id] = new_hotkey_str
                # Перерегистрация теперь происходит централизованно после сохранения всех изменений
        else:
            logging.warning(f"HotkeyManager: Attempt to update hotkey for unknown action_id '{action_id}'.")


    def reregister_all_hotkeys(self):
        if not KEYBOARD_AVAILABLE or not keyboard:
            logging.warning("HotkeyManager: Cannot reregister hotkeys, keyboard library not available.")
            return

        logging.info("HotkeyManager: Reregistering all hotkeys...")
        try:
            for hook in self._registered_keyboard_hooks:
                keyboard.remove_hotkey(hook)
            self._registered_keyboard_hooks.clear()
        except Exception as e:
            logging.error(f"HotkeyManager: Error unhooking hotkeys: {e}", exc_info=True)

        registered_count = 0
        for action_id, hotkey_str in self._current_hotkeys.items():
            callback = self._hotkey_callbacks.get(action_id)
            if hotkey_str and hotkey_str.lower() != 'none' and hotkey_str != get_text('hotkey_none') and hotkey_str != get_text('hotkey_not_set') and callback:
                try:
                    # Возвращаем оригинальную логику для suppress
                    suppress_hotkey = 'tab+' in hotkey_str.lower() 
                    
                    hook = keyboard.add_hotkey(hotkey_str, callback, suppress=suppress_hotkey, trigger_on_release=False)
                    self._registered_keyboard_hooks.append(hook)
                    
                    registered_count += 1
                    logging.debug(f"HotkeyManager: Registered '{hotkey_str}' for action '{action_id}'. Suppress: {suppress_hotkey}")
                except ValueError as ve: # keyboard может выбросить ValueError для некорректных строк
                    logging.error(f"HotkeyManager: Failed to register hotkey '{hotkey_str}' for '{action_id}' due to invalid format: {ve}")
                except Exception as e:
                    logging.error(f"HotkeyManager: Failed to register hotkey '{hotkey_str}' for '{action_id}': {e}", exc_info=True)
            elif not callback:
                 logging.warning(f"HotkeyManager: No callback for action '{action_id}', cannot register hotkey '{hotkey_str}'.")

        logging.info(f"HotkeyManager: Reregistered {registered_count}/{len(self._current_hotkeys)} hotkeys.")
        if registered_count == 0 and any(hk.lower() != 'none' and hk != get_text('hotkey_none') and hk != get_text('hotkey_not_set') for hk in self._current_hotkeys.values()):
            logging.error("HotkeyManager: No hotkeys were re-registered successfully!")


    def start_listening(self):
        if not KEYBOARD_AVAILABLE or not keyboard:
            logging.warning("HotkeyManager: Cannot start listener, keyboard library not available.")
            return
        if self._listener_thread is None or not self._listener_thread.is_alive():
            logging.info("HotkeyManager: Starting keyboard listener thread...")
            self._stop_listener_flag.clear()
            self.reregister_all_hotkeys()
            
            self._listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
            self._listener_thread.start()
        else:
            logging.info("HotkeyManager: Keyboard listener already running.")

    def _listener_loop(self):
        if not KEYBOARD_AVAILABLE: return
        logging.info("[HotkeyManager Listener Thread] Started.")
        try:
            while not self._stop_listener_flag.is_set():
                self._stop_listener_flag.wait(timeout=0.5) 
            logging.info("[HotkeyManager Listener Thread] Stop signal received.")
        except Exception as e:
            logging.error(f"[HotkeyManager Listener Thread] Error: {e}", exc_info=True)
        finally:
            if KEYBOARD_AVAILABLE and keyboard:
                try:
                    logging.info("[HotkeyManager Listener Thread] Unhooking all registered hotkeys...")
                    for hook in self._registered_keyboard_hooks:
                        try: # Добавляем try-except для каждого remove_hotkey
                            keyboard.remove_hotkey(hook)
                        except Exception as e_remove:
                            logging.error(f"Error removing hook {hook}: {e_remove}")
                    self._registered_keyboard_hooks.clear()
                except Exception as e_unhook:
                    logging.error(f"[HotkeyManager Listener Thread] Error during unhook_all attempt: {e_unhook}")
            logging.info("[HotkeyManager Listener Thread] Finished.")


    def stop_listening(self):
        if not KEYBOARD_AVAILABLE: return
        if self._listener_thread and self._listener_thread.is_alive():
            logging.info("HotkeyManager: Signalling keyboard listener to stop...")
            self._stop_listener_flag.set() 
            self._listener_thread.join(timeout=1.5) 
            if self._listener_thread.is_alive():
                logging.warning("HotkeyManager: Listener thread did not exit cleanly within timeout.")
            else:
                logging.info("HotkeyManager: Listener thread joined and finished.")
            self._listener_thread = None
        else:
            logging.info("HotkeyManager: Keyboard listener not running or already stopped.")