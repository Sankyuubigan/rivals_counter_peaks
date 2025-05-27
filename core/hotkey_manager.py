# File: core/hotkey_manager.py
import json
import logging
import threading
from typing import Dict, Callable, Any, Set
import time
import os
import sys
import re 

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QMetaObject, Q_ARG, Qt
from PySide6.QtGui import QGuiApplication 

from core.utils import get_settings_path
from core.lang.translations import get_text
# Импортируем утилиты парсинга
from core.hotkey_parser_utils import (
    parse_hotkey_string, 
    normalize_string_for_storage,
    normalize_key_object,
    get_key_object_id,
    get_pynput_key_to_string_map,
    PYNPUT_AVAILABLE_PARSER
)

try:
    from pynput import keyboard # pynput все еще нужен для Listener
    PYNPUT_AVAILABLE_LISTENER = True
except ImportError:
    PYNPUT_AVAILABLE_LISTENER = False
    keyboard = None 
    logging.error("HotkeyManager: 'pynput' library not found. Global hotkeys will be disabled.")

# PYNPUT_AVAILABLE теперь определяется на основе обоих
PYNPUT_AVAILABLE = PYNPUT_AVAILABLE_PARSER and PYNPUT_AVAILABLE_LISTENER


DEFAULT_HOTKEYS = { 
    "move_cursor_up": "tab+up",
    "move_cursor_down": "tab+down",
    "move_cursor_left": "tab+left",
    "move_cursor_right": "tab+right",
    "toggle_selection": "tab+num_0",
    "toggle_mode": "tab+decimal", 
    "recognize_heroes": "tab+num_divide",
    "clear_all": "tab+num_subtract",
    "copy_team": "tab+num_1",
    "toggle_tray_mode": "tab+num_7",
    "toggle_mouse_ignore_independent": "tab+num_9",
    "debug_capture": "tab+num_3",
}


HOTKEY_ACTIONS_CONFIG = {
    "move_cursor_up": {"desc_key": "hotkey_desc_navigation_up", "signal_name": "action_move_cursor_up", "suppress": True}, 
    "move_cursor_down": {"desc_key": "hotkey_desc_navigation_down", "signal_name": "action_move_cursor_down", "suppress": True},
    "move_cursor_left": {"desc_key": "hotkey_desc_navigation_left", "signal_name": "action_move_cursor_left", "suppress": True},
    "move_cursor_right": {"desc_key": "hotkey_desc_navigation_right", "signal_name": "action_move_cursor_right", "suppress": True},
    "toggle_selection": {"desc_key": "hotkey_desc_select", "signal_name": "action_toggle_selection", "suppress": True},
    "toggle_mode": {"desc_key": "hotkey_desc_toggle_mode", "signal_name": "action_toggle_mode", "suppress": True},
    "recognize_heroes": {"desc_key": "hotkey_desc_recognize", "signal_name": "action_recognize_heroes", "suppress": True},
    "clear_all": {"desc_key": "hotkey_desc_clear", "signal_name": "action_clear_all", "suppress": True},
    "copy_team": {"desc_key": "hotkey_desc_copy_team", "signal_name": "action_copy_team", "suppress": True},
    "toggle_tray_mode": {"desc_key": "hotkey_desc_toggle_tray", "signal_name": "action_toggle_tray_mode", "suppress": True},
    "toggle_mouse_ignore_independent": {"desc_key": "hotkey_desc_toggle_mouse_ignore", "signal_name": "action_toggle_mouse_ignore_independent", "suppress": True},
    "debug_capture": {"desc_key": "hotkey_desc_debug_screenshot", "signal_name": "action_debug_capture", "suppress": True},
}


class HotkeyManager(QObject):
    hotkeys_updated_signal = Signal()

    def __init__(self, main_window: QObject):
        super().__init__()
        self.main_window = main_window
        self._current_hotkeys: Dict[str, str] = {}
        self._parsed_hotkeys: Dict[str, Dict[str, Any]] = {}
        self._pynput_listener: Any = None # keyboard.Listener | None, но keyboard может быть None
        self.settings_file_path = get_settings_path()
        self._pressed_keys: Set[Any] = set() 
        self._lock = threading.Lock()

    # _normalize_key и _get_key_id теперь используются из hotkey_parser_utils
    # _parse_hotkey_string и _normalize_string_for_storage также оттуда

    def _get_key_str(self, key_obj) -> str: 
        if not PYNPUT_AVAILABLE or not keyboard: return ''
        normalized_key = normalize_key_object(key_obj) # Используем утилиту

        # Получаем маппинг из утилит
        pynput_key_to_string_map = get_pynput_key_to_string_map()

        if isinstance(normalized_key, keyboard.KeyCode):
            if sys.platform == "win32" and hasattr(normalized_key, 'vk') and normalized_key.vk is not None:
                vk_to_num_str = {
                    0x60: "num_0", 0x61: "num_1", 0x62: "num_2", 0x63: "num_3", 0x64: "num_4",
                    0x65: "num_5", 0x66: "num_6", 0x67: "num_7", 0x68: "num_8", 0x69: "num_9",
                    0x6A: "num_multiply", 0x6B: "num_add", 0x6D: "num_subtract",
                    0x6E: "num_decimal", 0x6F: "num_divide"
                }
                if normalized_key.vk in vk_to_num_str:
                    return vk_to_num_str[normalized_key.vk]
            char_attr = getattr(normalized_key, 'char', None)
            if char_attr is not None:
                return char_attr.lower()
            vk_attr = getattr(normalized_key, 'vk', 'None')
            return f"vk_{vk_attr}"
        elif isinstance(normalized_key, keyboard.Key):
            return pynput_key_to_string_map.get(normalized_key, normalized_key.name)
        return str(normalized_key) 

    def _update_parsed_hotkeys(self):
        if not PYNPUT_AVAILABLE: return
        with self._lock:
            self._parsed_hotkeys.clear()
            parsed_count = 0
            for action_id, hotkey_str in self._current_hotkeys.items():
                parsed = parse_hotkey_string(hotkey_str, get_text) # Передаем get_text
                if parsed:
                    config = HOTKEY_ACTIONS_CONFIG.get(action_id, {})
                    parsed['suppress_flag_from_config'] = config.get('suppress', False) 
                    parsed['action_id'] = action_id
                    self._parsed_hotkeys[action_id] = parsed
                    parsed_count +=1
                else:
                    logging.warning(f"Could not parse hotkey string '{hotkey_str}' for action '{action_id}'. It will be ignored.")
            logging.info(f"Parsed hotkeys updated: {parsed_count} active from {len(self._current_hotkeys)} configured.")

    def on_press(self, key):
        if not PYNPUT_AVAILABLE or not keyboard: return True
        try:
            with self._lock:
                normalized_key_obj = normalize_key_object(key) # Используем утилиту
                normalized_key_id = get_key_object_id(normalized_key_obj) # Используем утилиту
                self._pressed_keys.add(normalized_key_id)
                
                current_pressed_ids_repr = sorted([str(k_id) for k_id in self._pressed_keys])

                for action_id, parsed_combo in self._parsed_hotkeys.items():
                    if normalized_key_id == parsed_combo['main_key_id']:
                        if parsed_combo['keys_ids'].issubset(self._pressed_keys):
                            if self._pressed_keys == parsed_combo['keys_ids']: 
                                original_hotkey_str = self._current_hotkeys.get(action_id, "N/A")
                                logging.info(f"SUCCESS: Hotkey triggered: '{original_hotkey_str}' for action '{action_id}'")
                                try: # Оставляем try-except для QMetaObject, т.к. это межпоточный вызов
                                    QMetaObject.invokeMethod(self, "_emit_action_signal_slot",
                                                             Qt.ConnectionType.QueuedConnection,
                                                             Q_ARG(str, action_id))
                                except Exception as e_invoke:
                                    logging.error(f"Error invoking _emit_action_signal_slot for {action_id}: {e_invoke}")
            return True 
        except Exception as e_global_press: # Общий обработчик для неожиданных ошибок в колбэке
            logging.critical(f"CRITICAL ERROR in on_press: {e_global_press}", exc_info=True)
            return True 

    def on_release(self, key):
        if not PYNPUT_AVAILABLE or not keyboard: return True
        try:
            with self._lock:
                normalized_key_obj = normalize_key_object(key) # Используем утилиту
                normalized_key_id = get_key_object_id(normalized_key_obj) # Используем утилиту
                if normalized_key_id in self._pressed_keys:
                    self._pressed_keys.remove(normalized_key_id)
            return True
        except Exception as e_global_release: # Общий обработчик
            logging.critical(f"CRITICAL ERROR in on_release: {e_global_release}", exc_info=True)
            return True

    @Slot(str)
    def _emit_action_signal_slot(self, action_id: str):
        signal_config = HOTKEY_ACTIONS_CONFIG.get(action_id)
        if not signal_config: 
            logging.warning(f"No signal config for action_id {action_id}")
            return
        
        signal_name = signal_config.get("signal_name")
        if not signal_name:
            logging.warning(f"Signal name not found in config for action {action_id}")
            return
            
        if not hasattr(self.main_window, signal_name):
            logging.warning(f"Signal '{signal_name}' not found in main_window for action {action_id}")
            return
        
        signal_to_emit = getattr(self.main_window, signal_name)
        if not isinstance(signal_to_emit, Signal): # type: ignore
            logging.warning(f"Attribute '{signal_name}' is not a Signal for action {action_id}")
            return
        
        try: # Оставляем try-except для вызова emit, т.к. он может вызвать код в другом месте
            signal_to_emit.emit()
        except Exception as e:
            logging.error(f"Error emitting signal for {action_id}: {e}")


    def load_hotkeys(self):
        logging.info("HM: load_hotkeys")
        self._current_hotkeys = {k: normalize_string_for_storage(v) for k, v in DEFAULT_HOTKEYS.items()}
        
        if self.settings_file_path.exists():
            loaded_hotkeys = None
            try: # Оставляем try-except для чтения JSON
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    loaded_hotkeys = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading hotkeys from file: {e}. Using defaults.")
                loaded_hotkeys = None # Убедимся, что None, если ошибка

            if loaded_hotkeys is not None: # Проверяем, что загрузка удалась
                for action_id, hotkey_str in loaded_hotkeys.items():
                    if action_id in self._current_hotkeys:
                        if isinstance(hotkey_str, str):
                            normalized_str = normalize_string_for_storage(hotkey_str)
                            if hotkey_str.lower().strip() != normalized_str:
                                 logging.info(f"Normalized hotkey string from '{hotkey_str}' to '{normalized_str}' for {action_id} during load.")
                            self._current_hotkeys[action_id] = normalized_str
                        else: # hotkey_str не строка
                             logging.warning(f"Invalid type for hotkey '{action_id}' in settings: {type(hotkey_str)}. Using default.")
                    # else: # action_id не в DEFAULT_HOTKEYS (старое/неизвестное действие)
                        # logging.warning(f"Unknown action_id '{action_id}' in settings file. It will be ignored.")
        else:
            logging.info("Settings file not found. Using defaults (already normalized).")
        
        if PYNPUT_AVAILABLE:
            self._update_parsed_hotkeys()
        self.hotkeys_updated_signal.emit()

    def save_hotkeys(self, hotkeys_to_save: Dict[str, str] | None = None):
        logging.info(f"HM: save_hotkeys")
        data_to_save = {}
        source_hotkeys = hotkeys_to_save if hotkeys_to_save is not None else self._current_hotkeys
        
        for action_id, hotkey_str in source_hotkeys.items():
            data_to_save[action_id] = normalize_string_for_storage(hotkey_str)
        
        save_successful = False
        try: # Оставляем try-except для записи JSON
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            logging.info(f"Hotkeys saved to file.")
            save_successful = True
        except IOError as e:
            logging.error(f"Error saving hotkeys: {e}")

        if save_successful:
            self._current_hotkeys = data_to_save.copy() 
            if PYNPUT_AVAILABLE:
                self._update_parsed_hotkeys() 
                self.reregister_all_hotkeys() 
            self.hotkeys_updated_signal.emit()


    def reregister_all_hotkeys(self): 
        logging.info("HM: reregister_all_hotkeys (stops and starts listener)")
        if not PYNPUT_AVAILABLE:
            logging.warning("pynput lib not available. Cannot reregister hotkeys.")
            return
        self.stop_listening(is_internal_restart=True) 
        self.start_listening()
        # logging.info("HM: Listener restarted with new hotkey configurations.") # Это сообщение дублируется из start_listening

    def start_listening(self):
        logging.info("HM: start_listening method called.")
        if not PYNPUT_AVAILABLE or not keyboard:
            logging.warning("Pynput not available, cannot start listener.")
            return

        if self._pynput_listener is not None and self._pynput_listener.is_alive():
            logging.info("Listener is already running. Forcing stop and restart.")
            self.stop_listening(is_internal_restart=True) 
        self._actually_start_listener()

    def _actually_start_listener(self):
        logging.info("HM: _actually_start_listener executing.")
        self._pressed_keys.clear() 

        if not self._parsed_hotkeys and self._current_hotkeys and PYNPUT_AVAILABLE :
            logging.info("HM: _parsed_hotkeys is empty, calling _update_parsed_hotkeys before starting listener.")
            self._update_parsed_hotkeys()
        
        if not self._parsed_hotkeys and PYNPUT_AVAILABLE:
            logging.warning("HM: No hotkeys parsed. Listener will start but might not do anything.")

        # Проверка на keyboard здесь избыточна, т.к. PYNPUT_AVAILABLE уже это учитывает
        # Но для дополнительной безопасности можно оставить
        if not PYNPUT_AVAILABLE or not keyboard:
            logging.error("Cannot start listener, keyboard (pynput) is not available.")
            return

        try: # try-except для создания Listener
            self._pynput_listener = keyboard.Listener( 
                on_press=self.on_press,
                on_release=self.on_release,
                suppress=False
            )
            self._pynput_listener.daemon = True 
            self._pynput_listener.start() 
            time.sleep(0.05)
            if self._pynput_listener.is_alive():
                logging.info(f"Pynput listener started successfully.")
            else: 
                logging.error(f"Pynput listener FAILED to start.")
                self._pynput_listener = None
        except Exception as e:
            logging.error(f"Failed to create/start pynput listener: {e}", exc_info=True)
            self._pynput_listener = None
        logging.info("HM: start_listening / _actually_start_listener FINISHED")


    def stop_listening(self, is_internal_restart=False):
        logging.info(f"HM: stop_listening called (internal_restart={is_internal_restart})")
        if not PYNPUT_AVAILABLE: return

        listener_to_stop = self._pynput_listener
        if listener_to_stop is not None:
            if listener_to_stop.is_alive(): 
                logging.debug(f"Attempting to stop pynput listener. Is alive: {listener_to_stop.is_alive()}")
                try: # try-except для остановки Listener
                    listener_to_stop.stop() 
                    if hasattr(listener_to_stop, 'join') and callable(listener_to_stop.join):
                         logging.debug("Calling join on pynput listener thread...")
                         listener_to_stop.join(timeout=0.5)
                         if listener_to_stop.is_alive():
                             logging.warning("Pynput listener thread did not join after stop request.")
                         else:
                             logging.debug("Pynput listener thread joined successfully.")
                except Exception as e:
                    logging.warning(f"Exception while stopping/joining pynput listener: {e}", exc_info=True)
            else:
                logging.debug("Pynput listener was not alive when stop was called.")
            self._pynput_listener = None 
        else:
            logging.debug("No active pynput listener instance to stop.")
        
        with self._lock:
            self._pressed_keys.clear()
            
        if not is_internal_restart: 
            logging.info("HM: stop_listening FINISHED (full stop)")
        else:
            logging.info("HM: stop_listening FINISHED (internal restart step)")

    def get_current_hotkeys(self) -> Dict[str, str]: return self._current_hotkeys.copy()
    def get_default_hotkeys(self) -> Dict[str, str]: return DEFAULT_HOTKEYS.copy()
    def get_actions_config(self) -> Dict[str, Any]: return HOTKEY_ACTIONS_CONFIG.copy()
