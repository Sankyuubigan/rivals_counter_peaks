# File: core/hotkey_parser_utils.py
import logging
import re
import sys
from typing import Dict, Any, Set

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE_PARSER = True
except ImportError:
    PYNPUT_AVAILABLE_PARSER = False
    keyboard = None

# Карты для преобразования строк в объекты pynput и обратно
# Инициализируются только если pynput доступен
PYNPUT_KEY_TO_STRING_MAP_PARSER: Dict[Any, str] = {}
STRING_TO_PYNPUT_KEY_MAP_PARSER: Dict[str, Any] = {}
NORMALIZED_MODIFIERS_PYNPUT_PARSER: Dict[Any, Any] = {}

if PYNPUT_AVAILABLE_PARSER and keyboard:
    PYNPUT_KEY_TO_STRING_MAP_PARSER = {
        keyboard.Key.alt: 'alt', keyboard.Key.alt_l: 'alt', keyboard.Key.alt_r: 'alt',
        keyboard.Key.ctrl: 'ctrl', keyboard.Key.ctrl_l: 'ctrl', keyboard.Key.ctrl_r: 'ctrl',
        keyboard.Key.shift: 'shift', keyboard.Key.shift_l: 'shift', keyboard.Key.shift_r: 'shift',
        keyboard.Key.cmd: 'win', keyboard.Key.cmd_l: 'win', keyboard.Key.cmd_r: 'win',
        keyboard.Key.tab: 'tab',
        keyboard.Key.space: 'space', keyboard.Key.enter: 'enter', keyboard.Key.esc: 'esc',
        keyboard.Key.up: 'up', keyboard.Key.down: 'down', keyboard.Key.left: 'left', keyboard.Key.right: 'right',
        keyboard.Key.f1: 'f1', keyboard.Key.f2: 'f2', keyboard.Key.f3: 'f3', keyboard.Key.f4: 'f4',
        keyboard.Key.f5: 'f5', keyboard.Key.f6: 'f6', keyboard.Key.f7: 'f7', keyboard.Key.f8: 'f8',
        keyboard.Key.f9: 'f9', keyboard.Key.f10: 'f10', keyboard.Key.f11: 'f11', keyboard.Key.f12: 'f12',
        keyboard.Key.insert: 'insert', keyboard.Key.delete: 'delete', keyboard.Key.home: 'home', keyboard.Key.end: 'end',
        keyboard.Key.page_up: 'page_up', keyboard.Key.page_down: 'page_down',
        keyboard.Key.backspace: 'backspace',
    }
    STRING_TO_PYNPUT_KEY_MAP_PARSER = {v: k for k, v in PYNPUT_KEY_TO_STRING_MAP_PARSER.items()}

    if sys.platform == "win32":
        STRING_TO_PYNPUT_KEY_MAP_PARSER.update({
            "num_0": keyboard.KeyCode.from_vk(0x60), "num_1": keyboard.KeyCode.from_vk(0x61),
            "num_2": keyboard.KeyCode.from_vk(0x62), "num_3": keyboard.KeyCode.from_vk(0x63),
            "num_4": keyboard.KeyCode.from_vk(0x64), "num_5": keyboard.KeyCode.from_vk(0x65),
            "num_6": keyboard.KeyCode.from_vk(0x66), "num_7": keyboard.KeyCode.from_vk(0x67),
            "num_8": keyboard.KeyCode.from_vk(0x68), "num_9": keyboard.KeyCode.from_vk(0x69),
            "num_multiply": keyboard.KeyCode.from_vk(0x6A), "num_*": keyboard.KeyCode.from_vk(0x6A),
            "num_add": keyboard.KeyCode.from_vk(0x6B), "num_+": keyboard.KeyCode.from_vk(0x6B),
            "num_subtract": keyboard.KeyCode.from_vk(0x6D), "num_-": keyboard.KeyCode.from_vk(0x6D),
            "num_decimal": keyboard.KeyCode.from_vk(0x6E), "num_.": keyboard.KeyCode.from_vk(0x6E),
            "decimal": keyboard.KeyCode.from_vk(0x6E), # Alias for "tab+decimal"
            "num_divide": keyboard.KeyCode.from_vk(0x6F), "num_/": keyboard.KeyCode.from_vk(0x6F),
        })
    else:
        logging.warning("[HotkeyParser] Numpad symbolic hotkeys (e.g., 'num_multiply') might not work reliably on non-Windows OS for pynput.")

    NORMALIZED_MODIFIERS_PYNPUT_PARSER = {
        keyboard.Key.alt_l: keyboard.Key.alt, keyboard.Key.alt_r: keyboard.Key.alt,
        keyboard.Key.ctrl_l: keyboard.Key.ctrl, keyboard.Key.ctrl_r: keyboard.Key.ctrl,
        keyboard.Key.shift_l: keyboard.Key.shift, keyboard.Key.shift_r: keyboard.Key.shift,
        keyboard.Key.cmd_l: keyboard.Key.cmd, keyboard.Key.cmd_r: keyboard.Key.cmd,
    }

def normalize_key_object(key_obj: Any) -> Any:
    if not PYNPUT_AVAILABLE_PARSER: return key_obj
    return NORMALIZED_MODIFIERS_PYNPUT_PARSER.get(key_obj, key_obj)

def get_key_object_id(key_obj: Any) -> tuple:
    if not PYNPUT_AVAILABLE_PARSER or not keyboard: return ("UnknownType", str(key_obj))
    
    normalized_key_obj = normalize_key_object(key_obj)

    if isinstance(normalized_key_obj, keyboard.Key):
        return ("Key", normalized_key_obj.name)
    elif isinstance(normalized_key_obj, keyboard.KeyCode):
        if sys.platform == "win32":
            vk = getattr(normalized_key_obj, 'vk', None)
            if vk is not None:
                vk_to_num_str_map = {
                    0x60: "num_0", 0x61: "num_1", 0x62: "num_2", 0x63: "num_3", 0x64: "num_4",
                    0x65: "num_5", 0x66: "num_6", 0x67: "num_7", 0x68: "num_8", 0x69: "num_9",
                    0x6A: "num_multiply", 0x6B: "num_add", 0x6D: "num_subtract",
                    0x6E: "num_decimal", 0x6F: "num_divide"
                }
                if vk in vk_to_num_str_map:
                    return ("KeyCode_ConventionalNum", vk_to_num_str_map[vk])
        
        char_attr = getattr(normalized_key_obj, 'char', None)
        if char_attr is not None:
            return ("KeyCode_char", char_attr.lower())
        
        vk_attr = getattr(normalized_key_obj, 'vk', None)
        if vk_attr is not None:
            return ("KeyCode_vk_only", vk_attr)
        return ("KeyCode_unknown", str(normalized_key_obj))
    return ("Unknown", str(normalized_key_obj))


def parse_hotkey_string(hotkey_str: str, lang_get_text_func: callable) -> Dict[str, Any] | None:
    if not PYNPUT_AVAILABLE_PARSER or not keyboard: return None
    
    hk_str_lower = hotkey_str.lower().strip()
    if not hk_str_lower or hk_str_lower == 'none' or \
       hk_str_lower == lang_get_text_func('hotkey_none').lower() or \
       hk_str_lower == lang_get_text_func('hotkey_not_set').lower():
        return None

    num_symbol_map = {'.': 'decimal', '/': 'divide', '*': 'multiply', '-': 'subtract', '+': 'add'}
    def replace_num_symbol(match_obj):
        symbol = match_obj.group(1)
        return f"num_{num_symbol_map.get(symbol, symbol)}" 

    hk_str_lower = re.sub(r'num\s*([0-9])', r'num_\1', hk_str_lower)
    hk_str_lower = re.sub(r'num\s*([\.\/\*\-\+])', replace_num_symbol, hk_str_lower)
    if "num_decimal" not in hk_str_lower:
         hk_str_lower = hk_str_lower.replace("decimal", "num_decimal")
    
    parts = hk_str_lower.split('+')
    if not parts: return None

    modifier_key_ids_set: Set[tuple] = set()
    main_key_obj = None 
    potential_main_key_str = parts[-1]

    for part_str in parts[:-1]:
        pynput_mod_key_obj = STRING_TO_PYNPUT_KEY_MAP_PARSER.get(part_str)
        if pynput_mod_key_obj and isinstance(pynput_mod_key_obj, keyboard.Key) and \
           pynput_mod_key_obj in [keyboard.Key.alt, keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.cmd, keyboard.Key.tab]:
            modifier_key_ids_set.add(get_key_object_id(pynput_mod_key_obj))
        else:
            logging.warning(f"[HotkeyParser] Invalid or non-modifier part '{part_str}' used as modifier in hotkey string '{hotkey_str}'")
            return None

    if potential_main_key_str in STRING_TO_PYNPUT_KEY_MAP_PARSER:
        main_key_obj = STRING_TO_PYNPUT_KEY_MAP_PARSER[potential_main_key_str]
    elif len(potential_main_key_str) == 1:
        main_key_obj = keyboard.KeyCode.from_char(potential_main_key_str)
    else:
        logging.warning(f"[HotkeyParser] Unknown main key part '{potential_main_key_str}' in hotkey string '{hotkey_str}' (normalized: {hk_str_lower})")
        return None

    if main_key_obj is None:
        logging.error(f"[HotkeyParser] Failed to parse main key for '{hotkey_str}' (normalized: {hk_str_lower})")
        return None

    main_key_id = get_key_object_id(main_key_obj)
    all_keys_for_combo_ids = modifier_key_ids_set.copy()
    all_keys_for_combo_ids.add(main_key_id)

    return {
        'keys_ids': all_keys_for_combo_ids,
        'main_key_id': main_key_id,
        'modifier_ids': modifier_key_ids_set
    }

def normalize_string_for_storage(hotkey_str: str) -> str:
    hk_lower = hotkey_str.lower().strip()
    
    num_symbol_map = {'.': 'decimal', '/': 'divide', '*': 'multiply', '-': 'subtract', '+': 'add'}
    def replace_num_symbol(match_obj):
        symbol = match_obj.group(1)
        return f"num_{num_symbol_map.get(symbol, symbol)}"
    
    hk_lower = re.sub(r'num\s*([0-9])', r'num_\1', hk_lower)
    hk_lower = re.sub(r'num\s*([\.\/\*\-\+])', replace_num_symbol, hk_lower)
    if "num_decimal" not in hk_lower:
         hk_lower = hk_lower.replace("decimal", "num_decimal")
    return hk_lower

def get_pynput_key_to_string_map() -> Dict[Any, str]:
    return PYNPUT_KEY_TO_STRING_MAP_PARSER.copy()
