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

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    keyboard = None 
    logging.error("HotkeyManager: 'pynput' library not found. Global hotkeys will be disabled.")


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

PYNPUT_KEY_TO_STRING_MAP = {}
STRING_TO_PYNPUT_KEY_MAP = {}
NORMALIZED_MODIFIERS_PYNPUT = {}

if PYNPUT_AVAILABLE and keyboard:
    PYNPUT_KEY_TO_STRING_MAP = {
        keyboard.Key.alt: 'alt', keyboard.Key.alt_l: 'alt', keyboard.Key.alt_r: 'alt',
        keyboard.Key.ctrl: 'ctrl', keyboard.Key.ctrl_l: 'ctrl', keyboard.Key.ctrl_r: 'ctrl',
        keyboard.Key.shift: 'shift', keyboard.Key.shift_l: 'shift', keyboard.Key.shift_r: 'shift',
        keyboard.Key.cmd: 'win', keyboard.Key.cmd_l: 'win', keyboard.Key.cmd_r: 'win', # 'win' or 'cmd' for mac
        keyboard.Key.tab: 'tab',
        keyboard.Key.space: 'space', keyboard.Key.enter: 'enter', keyboard.Key.esc: 'esc',
        keyboard.Key.up: 'up', keyboard.Key.down: 'down', keyboard.Key.left: 'left', keyboard.Key.right: 'right',
        keyboard.Key.f1: 'f1', keyboard.Key.f2: 'f2', keyboard.Key.f3: 'f3', keyboard.Key.f4: 'f4',
        keyboard.Key.f5: 'f5', keyboard.Key.f6: 'f6', keyboard.Key.f7: 'f7', keyboard.Key.f8: 'f8',
        keyboard.Key.f9: 'f9', keyboard.Key.f10: 'f10', keyboard.Key.f11: 'f11', keyboard.Key.f12: 'f12',
        keyboard.Key.insert: 'insert', keyboard.Key.delete: 'delete', keyboard.Key.home: 'home', keyboard.Key.end: 'end',
        keyboard.Key.page_up: 'page_up', keyboard.Key.page_down: 'page_down',
        keyboard.Key.backspace: 'backspace',
        # Numpad keys using KeyCode (VK codes are for Windows)
        # These might need to be platform-specific or handled by char if not special
    }
    STRING_TO_PYNPUT_KEY_MAP = {v: k for k, v in PYNPUT_KEY_TO_STRING_MAP.items()}
    
    # Add numpad keys. For cross-platform, KeyCode.from_vk might not be ideal.
    # pynput often represents numpad numbers as regular numbers when NumLock is on,
    # and special keys (like arrows) when NumLock is off.
    # The string "num_0" etc. is a convention for this app.
    # If using VK codes, it's Windows-specific.
    if sys.platform == "win32":
        STRING_TO_PYNPUT_KEY_MAP.update({
            "num_0": keyboard.KeyCode.from_vk(0x60), "num_1": keyboard.KeyCode.from_vk(0x61),
            "num_2": keyboard.KeyCode.from_vk(0x62), "num_3": keyboard.KeyCode.from_vk(0x63),
            "num_4": keyboard.KeyCode.from_vk(0x64), "num_5": keyboard.KeyCode.from_vk(0x65),
            "num_6": keyboard.KeyCode.from_vk(0x66), "num_7": keyboard.KeyCode.from_vk(0x67),
            "num_8": keyboard.KeyCode.from_vk(0x68), "num_9": keyboard.KeyCode.from_vk(0x69),
            "num_multiply": keyboard.KeyCode.from_vk(0x6A), 
            "num_*": keyboard.KeyCode.from_vk(0x6A), # Alias
            "num_add": keyboard.KeyCode.from_vk(0x6B),
            "num_+": keyboard.KeyCode.from_vk(0x6B), # Alias
            "num_subtract": keyboard.KeyCode.from_vk(0x6D),
            "num_-": keyboard.KeyCode.from_vk(0x6D), # Alias
            "num_decimal": keyboard.KeyCode.from_vk(0x6E), # Numpad .
            "num_.": keyboard.KeyCode.from_vk(0x6E), # Alias
            "decimal": keyboard.KeyCode.from_vk(0x6E), # Alias for "tab+decimal"
            "num_divide": keyboard.KeyCode.from_vk(0x6F),
            "num_/": keyboard.KeyCode.from_vk(0x6F), # Alias
        })
    else: # Fallback for non-Windows (less reliable for numpad symbolic names)
        logging.warning("Numpad symbolic hotkeys (e.g., 'num_multiply') might not work reliably on non-Windows OS for pynput.")
        # One could try to map numpad characters if pynput provides them as char
        # e.g. STRING_TO_PYNPUT_KEY_MAP['*'] = keyboard.KeyCode.from_char('*') if that's how numpad * appears


    NORMALIZED_MODIFIERS_PYNPUT = {
        keyboard.Key.alt_l: keyboard.Key.alt, keyboard.Key.alt_r: keyboard.Key.alt,
        keyboard.Key.ctrl_l: keyboard.Key.ctrl, keyboard.Key.ctrl_r: keyboard.Key.ctrl,
        keyboard.Key.shift_l: keyboard.Key.shift, keyboard.Key.shift_r: keyboard.Key.shift,
        keyboard.Key.cmd_l: keyboard.Key.cmd, keyboard.Key.cmd_r: keyboard.Key.cmd,
    }


class HotkeyManager(QObject):
    hotkeys_updated_signal = Signal()

    def __init__(self, main_window: QObject):
        super().__init__()
        self.main_window = main_window
        self._current_hotkeys: Dict[str, str] = {}
        self._parsed_hotkeys: Dict[str, Dict[str, Any]] = {}
        self._pynput_listener: keyboard.Listener | None = None # type: ignore
        self.settings_file_path = get_settings_path()
        self._pressed_keys: Set[Any] = set() 
        self._lock = threading.Lock()

    def _normalize_key(self, key):
        if not PYNPUT_AVAILABLE: return key
        return NORMALIZED_MODIFIERS_PYNPUT.get(key, key)

    def _get_key_id(self, key_obj):
        if not PYNPUT_AVAILABLE or not keyboard: return str(key_obj)
        normalized_key_obj = self._normalize_key(key_obj)

        if isinstance(normalized_key_obj, keyboard.Key):
            return ("Key", normalized_key_obj.name) 
        elif isinstance(normalized_key_obj, keyboard.KeyCode):
            # For numpad keys from VK codes on Windows, their char might be None or numbers
            # We need a consistent way to ID them based on how _parse_hotkey_string will ID them from strings like "num_0"
            if sys.platform == "win32":
                vk = getattr(normalized_key_obj, 'vk', None)
                if vk is not None:
                    # Check if it's one of our conventionally named numpad VKs
                    # This mapping should align with STRING_TO_PYNPUT_KEY_MAP's numpad keys
                    vk_to_num_str_map = {
                        0x60: "num_0", 0x61: "num_1", 0x62: "num_2", 0x63: "num_3", 0x64: "num_4",
                        0x65: "num_5", 0x66: "num_6", 0x67: "num_7", 0x68: "num_8", 0x69: "num_9",
                        0x6A: "num_multiply", 0x6B: "num_add", 0x6D: "num_subtract",
                        0x6E: "num_decimal", 0x6F: "num_divide"
                    }
                    if vk in vk_to_num_str_map:
                        return ("KeyCode_ConventionalNum", vk_to_num_str_map[vk])
            
            # Fallback for other KeyCodes or non-Windows
            char = getattr(normalized_key_obj, 'char', None)
            if char is not None:
                return ("KeyCode_char", char.lower())
            # If no char (e.g. some special keys on non-Windows), use vk if available
            vk = getattr(normalized_key_obj, 'vk', None)
            if vk is not None:
                return ("KeyCode_vk_only", vk)
            return ("KeyCode_unknown", str(normalized_key_obj)) # Should not happen often
        return ("Unknown", str(normalized_key_obj))


    def _get_key_str(self, key) -> str: 
        if not PYNPUT_AVAILABLE or not keyboard: return ''
        normalized_key = self._normalize_key(key)

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
            # Fallback or non-Windows
            return normalized_key.char.lower() if hasattr(normalized_key, 'char') and normalized_key.char else f"vk_{getattr(normalized_key, 'vk', 'None')}"
        elif isinstance(normalized_key, keyboard.Key):
            return PYNPUT_KEY_TO_STRING_MAP.get(normalized_key, normalized_key.name)
        return str(normalized_key) 

    def _parse_hotkey_string(self, hotkey_str: str) -> Dict[str, Any] | None:
        if not PYNPUT_AVAILABLE or not keyboard: return None
        
        hk_str_lower = hotkey_str.lower().strip()
        if not hk_str_lower or hk_str_lower == 'none' or hk_str_lower == get_text('hotkey_none').lower() or hk_str_lower == get_text('hotkey_not_set').lower():
            return None

        # Normalize "num <symbol>" to "num_<word>" e.g. "num ." -> "num_decimal"
        num_symbol_map = {'.': 'decimal', '/': 'divide', '*': 'multiply', '-': 'subtract', '+': 'add'}
        def replace_num_symbol(match_obj):
            symbol = match_obj.group(1)
            return f"num_{num_symbol_map.get(symbol, symbol)}" 

        # Handle "num <digit>" and "num <symbol>"
        hk_str_lower = re.sub(r'num\s*([0-9])', r'num_\1', hk_str_lower) 
        # Ensure "num_decimal" (from "num .") is processed before "decimal" (if it's alone)
        hk_str_lower = re.sub(r'num\s*([\.\/\*\-\+])', replace_num_symbol, hk_str_lower)
        # Handle standalone "decimal" if it's not part of "num_decimal" already
        if "num_decimal" not in hk_str_lower:
             hk_str_lower = hk_str_lower.replace("decimal", "num_decimal") # Treat standalone "decimal" as "num_decimal"
        
        parts = hk_str_lower.split('+')
        if not parts: return None

        modifier_key_ids_set = set() 
        main_key_obj = None 
        potential_main_key_str = parts[-1]

        for part_str in parts[:-1]:
            pynput_mod_key_obj = STRING_TO_PYNPUT_KEY_MAP.get(part_str)
            # Tab is a modifier here
            if pynput_mod_key_obj and isinstance(pynput_mod_key_obj, keyboard.Key) and \
               pynput_mod_key_obj in [keyboard.Key.alt, keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.cmd, keyboard.Key.tab]:
                modifier_key_ids_set.add(self._get_key_id(pynput_mod_key_obj)) 
            else:
                logging.warning(f"Invalid or non-modifier part '{part_str}' used as modifier in hotkey string '{hotkey_str}'")
                return None

        if potential_main_key_str in STRING_TO_PYNPUT_KEY_MAP:
            main_key_obj = STRING_TO_PYNPUT_KEY_MAP[potential_main_key_str]
        elif len(potential_main_key_str) == 1: 
            try: # For simple characters a-z, 0-9 (not numpad), symbols
                main_key_obj = keyboard.KeyCode.from_char(potential_main_key_str)
            except ValueError: # Should not happen if HotkeyCaptureLineEdit generates valid chars
                 logging.warning(f"Cannot parse main key char '{potential_main_key_str}' in '{hotkey_str}'")
                 return None
        else:
            logging.warning(f"Unknown main key part '{potential_main_key_str}' in hotkey string '{hotkey_str}' (normalized: {hk_str_lower})")
            return None

        if main_key_obj is None: # Should be caught by "Unknown main key part" already
            logging.error(f"Failed to parse main key for '{hotkey_str}' (normalized: {hk_str_lower})")
            return None

        main_key_id = self._get_key_id(main_key_obj) 
        all_keys_for_combo_ids = modifier_key_ids_set.copy()
        all_keys_for_combo_ids.add(main_key_id)

        return {
            'keys_ids': all_keys_for_combo_ids, 
            'main_key_id': main_key_id,    
            'modifier_ids': modifier_key_ids_set   
        }

    def _update_parsed_hotkeys(self):
        if not PYNPUT_AVAILABLE: return
        with self._lock:
            self._parsed_hotkeys.clear()
            parsed_count = 0
            # logging.debug("--- Updating Parsed Hotkeys ---") 
            for action_id, hotkey_str in self._current_hotkeys.items():
                # logging.debug(f"  Parsing for action '{action_id}', string: '{hotkey_str}'") 
                parsed = self._parse_hotkey_string(hotkey_str)
                # logging.debug(f"    Parsed result: {parsed}") 
                if parsed:
                    config = HOTKEY_ACTIONS_CONFIG.get(action_id, {})
                    parsed['suppress_flag_from_config'] = config.get('suppress', False) 
                    parsed['action_id'] = action_id
                    self._parsed_hotkeys[action_id] = parsed
                    parsed_count +=1
                else:
                    logging.warning(f"Could not parse hotkey string '{hotkey_str}' for action '{action_id}'. It will be ignored.")
            logging.info(f"Parsed hotkeys updated: {parsed_count} active from {len(self._current_hotkeys)} configured.")
            # logging.debug("--- Finished Updating Parsed Hotkeys ---")

    def on_press(self, key):
        if not PYNPUT_AVAILABLE or not keyboard: return True
        try:
            with self._lock:
                normalized_key_obj = self._normalize_key(key)
                normalized_key_id = self._get_key_id(normalized_key_obj)
                self._pressed_keys.add(normalized_key_id)
                
                current_pressed_ids_repr = sorted([str(k_id) for k_id in self._pressed_keys])
                # logging.debug(f"Press Event: KeyID='{normalized_key_id}' (Raw: {key}). PynputSetIDs: {current_pressed_ids_repr}")

                for action_id, parsed_combo in self._parsed_hotkeys.items():
                    # parsed_keys_ids_repr = sorted([str(k_id) for k_id in parsed_combo['keys_ids']])
                    # logging.debug(f"  Comparing '{action_id}': main_id='{parsed_combo['main_key_id']}', combo_ids={parsed_keys_ids_repr} ||| current_pressed_ids={current_pressed_ids_repr}, current_normalized_key_id='{normalized_key_id}'")
                    
                    # Check if the pressed key is the main key of this combo
                    if normalized_key_id == parsed_combo['main_key_id']:
                        # logging.debug(f"    Main key ID MATCH for '{action_id}' (Pressed: '{normalized_key_id}', Expected: '{parsed_combo['main_key_id']}')")
                        # Check if all required modifiers for this combo are currently pressed
                        # self._pressed_keys should contain all keys needed for parsed_combo['keys_ids']
                        if parsed_combo['keys_ids'].issubset(self._pressed_keys):
                            # To avoid triggering "ctrl+a" when "ctrl+shift+a" is pressed,
                            # ensure the set of pressed keys is EXACTLY what the combo expects.
                            if self._pressed_keys == parsed_combo['keys_ids']: 
                                original_hotkey_str = self._current_hotkeys.get(action_id, "N/A")
                                logging.info(f"SUCCESS: Hotkey triggered: '{original_hotkey_str}' for action '{action_id}'")
                                try:
                                    QMetaObject.invokeMethod(self, "_emit_action_signal_slot",
                                                             Qt.ConnectionType.QueuedConnection,
                                                             Q_ARG(str, action_id))
                                except Exception as e_invoke:
                                    logging.error(f"Error invoking _emit_action_signal_slot for {action_id}: {e_invoke}")
                                # No break here, allow other potential matches if complex setups exist
                                # (though typically one combo per action)
                            # else:
                                # logging.debug(f"      Exact set IDs MISMATCH for '{action_id}': current_set_ids={current_pressed_ids_repr} vs combo_ids={parsed_keys_ids_repr}")
                        # else:
                            # required_combo_ids_repr = sorted([str(k_id) for k_id in parsed_combo['keys_ids']])
                            # logging.debug(f"      Required combo IDs NOT SUBSET of pressed for '{action_id}': Required_Set_IDs: {required_combo_ids_repr}, Pressed_Set_IDs: {current_pressed_ids_repr}")
            return True 
        except Exception as e_global_press:
            logging.critical(f"CRITICAL ERROR in on_press: {e_global_press}", exc_info=True)
            return True 

    def on_release(self, key):
        if not PYNPUT_AVAILABLE or not keyboard: return True
        try:
            with self._lock:
                normalized_key_obj = self._normalize_key(key)
                normalized_key_id = self._get_key_id(normalized_key_obj)
                if normalized_key_id in self._pressed_keys:
                    self._pressed_keys.remove(normalized_key_id)
                # current_pressed_ids_repr = sorted([str(k_id) for k_id in self._pressed_keys])
                # logging.debug(f"Release Event: KeyID='{normalized_key_id}'. PynputSetIDs: {current_pressed_ids_repr}")
            return True
        except Exception as e_global_release:
            logging.critical(f"CRITICAL ERROR in on_release: {e_global_release}", exc_info=True)
            return True

    @Slot(str)
    def _emit_action_signal_slot(self, action_id: str):
        signal_config = HOTKEY_ACTIONS_CONFIG.get(action_id)
        if not signal_config: logging.warning(f"No signal config for action_id {action_id}"); return
        signal_name = signal_config.get("signal_name")
        if not signal_name or not hasattr(self.main_window, signal_name):
            logging.warning(f"Signal name '{signal_name}' not found in main_window for action {action_id}"); return
        
        signal_to_emit = getattr(self.main_window, signal_name)
        if not isinstance(signal_to_emit, Signal): # type: ignore
            logging.warning(f"Attribute '{signal_name}' is not a Signal for action {action_id}"); return
        try:
            signal_to_emit.emit()
        except Exception as e:
            logging.error(f"Error emitting signal for {action_id}: {e}")

    def _normalize_string_for_storage(self, hotkey_str: str) -> str:
        hk_lower = hotkey_str.lower().strip()
        
        num_symbol_map = {'.': 'decimal', '/': 'divide', '*': 'multiply', '-': 'subtract', '+': 'add'}
        def replace_num_symbol(match_obj):
            symbol = match_obj.group(1)
            return f"num_{num_symbol_map.get(symbol, symbol)}"
        
        hk_lower = re.sub(r'num\s*([0-9])', r'num_\1', hk_lower)
        hk_lower = re.sub(r'num\s*([\.\/\*\-\+])', replace_num_symbol, hk_lower)
        # Ensure standalone "decimal" becomes "num_decimal" for consistency if not already part of "num_decimal"
        if "num_decimal" not in hk_lower:
             hk_lower = hk_lower.replace("decimal", "num_decimal")
        return hk_lower

    def load_hotkeys(self):
        logging.info("HM: load_hotkeys")
        self._current_hotkeys = {k: self._normalize_string_for_storage(v) for k, v in DEFAULT_HOTKEYS.items()}
        
        if self.settings_file_path.exists():
            try:
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    loaded_hotkeys = json.load(f)
                for action_id, hotkey_str in loaded_hotkeys.items():
                    if action_id in self._current_hotkeys and isinstance(hotkey_str, str):
                        normalized_str = self._normalize_string_for_storage(hotkey_str)
                        if hotkey_str.lower().strip() != normalized_str: # Log if normalization changed it
                             logging.info(f"Normalized hotkey string from '{hotkey_str}' to '{normalized_str}' for {action_id} during load.")
                        self._current_hotkeys[action_id] = normalized_str
                    elif action_id in self._current_hotkeys: # Action ID is valid, but hotkey_str is not string
                         logging.warning(f"Invalid type for hotkey '{action_id}' in settings: {hotkey_str}. Using default.")
            except Exception as e:
                logging.error(f"Error loading hotkeys: {e}. Defaults already set and normalized.")
        else:
            logging.info("Settings file not found. Using defaults (already normalized).")
        
        if PYNPUT_AVAILABLE:
            self._update_parsed_hotkeys()
        self.hotkeys_updated_signal.emit()

    def save_hotkeys(self, hotkeys_to_save: Dict[str, str] | None = None):
        logging.info(f"HM: save_hotkeys")
        # logging.debug(f"HM: save_hotkeys received: {hotkeys_to_save}") 
        data_to_save = {}
        source_hotkeys = hotkeys_to_save if hotkeys_to_save is not None else self._current_hotkeys
        
        for action_id, hotkey_str in source_hotkeys.items():
            data_to_save[action_id] = self._normalize_string_for_storage(hotkey_str)
        
        # logging.debug(f"HM: data_to_save after normalization for file: {data_to_save}")

        try:
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            logging.info(f"Hotkeys saved to file.")
            
            self._current_hotkeys = data_to_save.copy() 
            # logging.debug(f"HM: self._current_hotkeys updated to: {self._current_hotkeys}")
            
            if PYNPUT_AVAILABLE:
                self._update_parsed_hotkeys() 
                self.reregister_all_hotkeys() 
            self.hotkeys_updated_signal.emit()
        except IOError as e:
            logging.error(f"Error saving hotkeys: {e}")

    def reregister_all_hotkeys(self): 
        logging.info("HM: reregister_all_hotkeys (stops and starts listener)")
        if not PYNPUT_AVAILABLE:
            logging.warning("pynput lib not available. Cannot reregister hotkeys.")
            return
        self.stop_listening(is_internal_restart=True) 
        self.start_listening()
        logging.info("HM: Listener restarted with new hotkey configurations.")

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

        try:
            self._pynput_listener = keyboard.Listener( 
                on_press=self.on_press,
                on_release=self.on_release,
                suppress=False # We don't suppress globally; individual actions might signal suppression needs
            )
            self._pynput_listener.daemon = True 
            self._pynput_listener.start() 
            time.sleep(0.05) # Give listener thread a moment to start
            if self._pynput_listener.is_alive():
                logging.info(f"Pynput listener started successfully.")
            else: # pragma: no cover
                logging.error(f"Pynput listener FAILED to start.")
                self._pynput_listener = None # Ensure it's None if not started
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
                try:
                    listener_to_stop.stop() 
                    if hasattr(listener_to_stop, 'join') and callable(listener_to_stop.join):
                         logging.debug("Calling join on pynput listener thread...")
                         listener_to_stop.join(timeout=0.5) # Reduced timeout
                         if listener_to_stop.is_alive(): # pragma: no cover
                             logging.warning("Pynput listener thread did not join after stop request.")
                         else:
                             logging.debug("Pynput listener thread joined successfully.")
                    # else: # No join, pynput listener might stop asynchronously
                         # time.sleep(0.1) # Shorter sleep
                except Exception as e: # pragma: no cover
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