# File: core/hotkey_manager.py
import json
import logging
import threading
from typing import Dict, Callable, Any
import time 
import os # <<< ИМПОРТ OS НА МЕСТЕ >>>

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
# Платформозависимая настройка для numpad точки
if os.name == 'nt': 
    DEFAULT_HOTKEYS["toggle_mode"] = "num ." # Для Windows
elif sys.platform == 'darwin': # Для macOS
    DEFAULT_HOTKEYS["toggle_mode"] = "keypad ." # Может потребоваться другая строка
else: # Для Linux и других
    DEFAULT_HOTKEYS["toggle_mode"] = "kp_decimal" # keyboard lib на Linux часто использует KP_ префиксы

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
        logging.debug("HotkeyManager.__init__ START")
        self.main_window = main_window
        self._current_hotkeys: Dict[str, str] = {} 
        self._hotkey_callbacks: Dict[str, Callable] = {} 
        self._listener_thread: threading.Thread | None = None
        self._stop_listener_flag = threading.Event()
        self.settings_file_path = get_settings_path()
        self._is_reregistering = False 
        self._active_hotkey_objects = {} # Храним объекты хуков, {hotkey_string: hook_object}

        self._prepare_callbacks()
        logging.debug("HotkeyManager.__init__ FINISHED")

    def _prepare_callbacks(self):
        for action_id in HOTKEY_ACTIONS_CONFIG.keys():
            self._hotkey_callbacks[action_id] = self._create_queued_callback(action_id)

    def _create_queued_callback(self, action_id: str):
        def _callback(): 
            logging.debug(f"[HotkeyManager Thread] Raw callback for action: {action_id}")
            try:
                QMetaObject.invokeMethod(self, "_emit_action_signal_slot", 
                                         Qt.ConnectionType.QueuedConnection, 
                                         Q_ARG(str, action_id))
            except Exception as e:
                logging.error(f"[HotkeyManager Thread] Error invoking _emit_action_signal_slot for {action_id}: {e}", exc_info=True)
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
        logging.info("HotkeyManager: load_hotkeys START")
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
        
        if self._listener_thread and self._listener_thread.is_alive():
            logging.info("HotkeyManager: Listener active after load, queueing reregistration.")
            QMetaObject.invokeMethod(self, "reregister_all_hotkeys_slot", Qt.ConnectionType.QueuedConnection)
        
        self.hotkeys_updated_signal.emit()
        logging.info("HotkeyManager: load_hotkeys FINISHED")


    def save_hotkeys(self, hotkeys_to_save: Dict[str, str] | None = None):
        logging.info(f"HotkeyManager: save_hotkeys START. hotkeys_to_save is None: {hotkeys_to_save is None}")
        data_to_save = hotkeys_to_save if hotkeys_to_save is not None else self._current_hotkeys
        try:
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            logging.info(f"Hotkeys saved to {self.settings_file_path}")
            self._current_hotkeys = data_to_save.copy() 
            
            if self._listener_thread and self._listener_thread.is_alive():
                logging.info("HotkeyManager: Listener active after save, queueing reregistration.")
                QMetaObject.invokeMethod(self, "reregister_all_hotkeys_slot", Qt.ConnectionType.QueuedConnection)
            else:
                 logging.info("HotkeyManager: Listener not active, hotkeys will be registered on next start_listening call.")
            self.hotkeys_updated_signal.emit()
        except IOError as e:
            logging.error(f"HotkeyManager: Error saving hotkeys to {self.settings_file_path}: {e}")
        logging.info("HotkeyManager: save_hotkeys FINISHED")

    @Slot() 
    def reregister_all_hotkeys_slot(self):
        logging.debug("HotkeyManager: reregister_all_hotkeys_slot called via QMetaObject.")
        self.reregister_all_hotkeys()

    def reregister_all_hotkeys(self):
        if self._is_reregistering:
            logging.warning("HotkeyManager: Reregistration already in progress, skipping.")
            return
        
        self._is_reregistering = True
        logging.info("HotkeyManager: reregister_all_hotkeys START")
        
        if not KEYBOARD_AVAILABLE or not keyboard:
            logging.warning("HotkeyManager: Cannot reregister, keyboard library not available.")
            self._is_reregistering = False
            return

        logging.debug(f"HotkeyManager: Unhooking {len(self._active_hotkey_objects)} previously registered hotkey objects.")
        unhook_success_count = 0
        unhook_fail_count = 0
        # Используем list(), чтобы создать копию ключей для итерации, так как словарь будет изменяться
        for hotkey_str, hook_obj in list(self._active_hotkey_objects.items()): 
            try:
                keyboard.remove_hotkey(hook_obj) 
                unhook_success_count +=1
                if hotkey_str in self._active_hotkey_objects: # Проверяем перед удалением
                    del self._active_hotkey_objects[hotkey_str]
                logging.debug(f"  Successfully unhooked: {hotkey_str}")
            except Exception as e_remove: # Ловим KeyError или другие возможные ошибки
                unhook_fail_count += 1
                logging.warning(f"  Failed to unhook {hotkey_str} (obj: {hook_obj}): {e_remove}")
        # self._active_hotkey_objects.clear() # Очищаем в любом случае после попытки
        logging.info(f"HotkeyManager: Unhooking finished. Success: {unhook_success_count}, Fail: {unhook_fail_count}. Remaining in _active_hotkey_objects: {len(self._active_hotkey_objects)}")

        time.sleep(0.1) 

        registered_count = 0
        logging.info(f"HotkeyManager: Registering new hotkeys based on current config: {self._current_hotkeys}")
        
        hotkeys_to_register = self._current_hotkeys.copy()

        for action_id, hotkey_str in hotkeys_to_register.items():
            callback = self._hotkey_callbacks.get(action_id)
            if hotkey_str and hotkey_str.lower() != 'none' and hotkey_str != get_text('hotkey_none') and hotkey_str != get_text('hotkey_not_set') and callback:
                try:
                    suppress_hotkey = 'tab+' in hotkey_str.lower() and hotkey_str.lower() != 'tab'
                    if hotkey_str.lower() == 'tab': suppress_hotkey = False

                    logging.debug(f"  Attempting to register '{hotkey_str}' for action '{action_id}'. Suppress: {suppress_hotkey}")
                    
                    hook_object = keyboard.add_hotkey(hotkey_str, callback, suppress=suppress_hotkey, trigger_on_release=False)
                    self._active_hotkey_objects[hotkey_str] = hook_object 
                    
                    registered_count += 1
                    logging.info(f"  Successfully registered '{hotkey_str}' for action '{action_id}'. Suppress: {suppress_hotkey}. Hook obj: {hook_object}")
                except ValueError as ve: 
                    logging.error(f"  Failed to register hotkey '{hotkey_str}' for '{action_id}' due to invalid format: {ve}")
                except Exception as e: 
                    logging.error(f"  Failed to register hotkey '{hotkey_str}' for '{action_id}': {e}", exc_info=True)
            elif not callback:
                 logging.warning(f"  No callback for action '{action_id}', cannot register hotkey '{hotkey_str}'.")
            else:
                 logging.debug(f"  Hotkey '{hotkey_str}' for action '{action_id}' is 'none' or not set, skipping registration.")

        logging.info(f"HotkeyManager: Reregistered {registered_count} hotkeys. Active hook objects: {len(self._active_hotkey_objects)}")
        if registered_count == 0 and any(hk.lower() != 'none' and hk != get_text('hotkey_none') and hk != get_text('hotkey_not_set') for hk in self._current_hotkeys.values()):
            logging.error("HotkeyManager: No hotkeys were re-registered successfully despite valid configurations!")
        
        self._is_reregistering = False
        logging.info("HotkeyManager: reregister_all_hotkeys FINISHED")


    def start_listening(self):
        logging.info("HotkeyManager: start_listening START")
        if not KEYBOARD_AVAILABLE or not keyboard:
            logging.warning("HotkeyManager: Cannot start listener, keyboard library not available.")
            return
        if self._listener_thread is None or not self._listener_thread.is_alive():
            logging.info("HotkeyManager: Keyboard listener thread is not running or not existent. Starting new one.")
            self._stop_listener_flag.clear()
            
            logging.debug("HotkeyManager: Queueing reregister_all_hotkeys before starting listener thread.")
            # Используем BlockingQueuedConnection чтобы убедиться, что хоткеи зарегистрированы до старта потока
            # Однако, если start_listening вызывается из конструктора, это может вызвать проблемы.
            # Проще вызвать reregister_all_hotkeys напрямую, если мы уверены, что start_listening вызывается из основного потока.
            # Для безопасности оставим QueuedConnection, но это может означать, что поток запустится ДО того, как хоткеи будут готовы.
            # QMetaObject.invokeMethod(self, "reregister_all_hotkeys_slot", Qt.ConnectionType.BlockingQueuedConnection)
            # Попробуем прямой вызов, т.к. start_listening обычно вызывается в конце инициализации MainWindow или в showEvent.
            self.reregister_all_hotkeys()
            
            self._listener_thread = threading.Thread(target=self._listener_loop, daemon=True, name="HotkeyListenerThread")
            self._listener_thread.start()
            logging.info(f"HotkeyManager: Listener thread '{self._listener_thread.name}' started with ID {self._listener_thread.ident}.")
        else:
            logging.info(f"HotkeyManager: Keyboard listener thread '{self._listener_thread.name}' (ID: {self._listener_thread.ident}) already running.")
        logging.info("HotkeyManager: start_listening FINISHED")

    def _listener_loop(self):
        if not KEYBOARD_AVAILABLE: return
        current_thread = threading.current_thread()
        logging.info(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) loop started.")
        try:
            while not self._stop_listener_flag.is_set():
                self._stop_listener_flag.wait(timeout=0.5) 
            logging.info(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) stop signal received.")
        except Exception as e:
            logging.error(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) Error in loop: {e}", exc_info=True)
        finally:
            logging.info(f"[HotkeyManager Listener Thread] '{current_thread.name}' (ID: {current_thread.ident}) loop finished.")


    def stop_listening(self):
        logging.info("HotkeyManager: stop_listening START")
        if not KEYBOARD_AVAILABLE: return

        current_thread_name = self._listener_thread.name if self._listener_thread else "N/A"
        current_thread_id = self._listener_thread.ident if self._listener_thread else "N/A"
        if self._listener_thread and self._listener_thread.is_alive():
            logging.info(f"HotkeyManager: Signalling our listener thread '{current_thread_name}' (ID: {current_thread_id}) to stop...")
            self._stop_listener_flag.set() 
            self._listener_thread.join(timeout=2.0) 
            if self._listener_thread.is_alive():
                logging.warning(f"HotkeyManager: Our listener thread '{current_thread_name}' (ID: {current_thread_id}) did not exit cleanly.")
            else:
                logging.info(f"HotkeyManager: Our listener thread '{current_thread_name}' (ID: {current_thread_id}) joined and finished.")
            self._listener_thread = None
        else:
            logging.info(f"HotkeyManager: Our listener thread '{current_thread_name}' (ID: {current_thread_id}) not running or already stopped.")
        
        if keyboard:
            logging.info("HotkeyManager: Attempting to unhook all active hotkey objects.")
            unhook_success_count = 0
            unhook_fail_count = 0
            for hotkey_str, hook_obj in list(self._active_hotkey_objects.items()):
                try:
                    keyboard.remove_hotkey(hook_obj)
                    unhook_success_count += 1
                    logging.debug(f"  Successfully unhooked (stop_listening): {hotkey_str}")
                except Exception as e_remove_stop:
                    unhook_fail_count += 1
                    logging.warning(f"  Failed to unhook (stop_listening) {hotkey_str}: {e_remove_stop}")
            self._active_hotkey_objects.clear()
            logging.info(f"HotkeyManager: Unhooking on stop finished. Success: {unhook_success_count}, Fail: {unhook_fail_count}")
            
            # Дополнительно, чтобы быть уверенным, если remove_hotkey(hook_obj) не сработал для всех
            try:
                logging.debug("HotkeyManager: Calling keyboard.unhook_all_hotkeys() as a final cleanup.")
                keyboard.unhook_all_hotkeys()
            except Exception as e_final_unhook:
                 logging.warning(f"HotkeyManager: Error during final keyboard.unhook_all_hotkeys(): {e_final_unhook}")

        logging.info("HotkeyManager: stop_listening FINISHED")

    def get_current_hotkeys(self) -> Dict[str, str]:
        return self._current_hotkeys.copy()

    def get_default_hotkeys(self) -> Dict[str, str]:
        return DEFAULT_HOTKEYS.copy()
    
    def get_actions_config(self) -> Dict[str, Any]:
        return HOTKEY_ACTIONS_CONFIG.copy()

    def get_hotkey_for_action(self, action_id: str) -> str | None:
        return self._current_hotkeys.get(action_id)

    def update_hotkey(self, action_id: str, new_hotkey_str: str): 
        if action_id in self._current_hotkeys: # Проверяем, что action_id существует в наших настройках
            # Этот метод вызывается из диалога HotkeySettingsDialog, когда пользователь меняет хоткей в UI,
            # но ДО нажатия кнопки "Сохранить". Поэтому здесь мы только обновляем _current_hotkeys,
            # чтобы диалог отображал актуальное значение. Фактическое сохранение в файл и перерегистрация
            # произойдут, когда пользователь нажмет "Сохранить" и вызовется self.save_hotkeys().
            logging.debug(f"HotkeyManager: Hotkey for action '{action_id}' (in-memory for dialog) changed from '{self._current_hotkeys[action_id]}' to '{new_hotkey_str}'.")
            # self._current_hotkeys[action_id] = new_hotkey_str # Это должно делаться в HotkeySettingsDialog в его копии current_hotkeys_copy
        else:
            logging.warning(f"HotkeyManager: Attempt to update hotkey for unknown action_id '{action_id}'.")
