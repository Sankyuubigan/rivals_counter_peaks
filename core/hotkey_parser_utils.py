# File: core/hotkey_parser_utils.py
import logging
import re

def normalize_string_for_storage(hotkey_str: str) -> str:
    """
    Нормализует строку хоткея для консистентного хранения.
    """
    if not hotkey_str:
        return ""
        
    hk_lower = hotkey_str.lower().strip()
    
    num_symbol_map = {'.': 'decimal', '/': 'divide', '*': 'multiply', '-': 'subtract', '+': 'add'}
    
    def replace_num_symbol(match_obj):
        symbol_part = match_obj.group(1)
        actual_symbol = symbol_part.strip()
        return f"num_{num_symbol_map.get(actual_symbol, actual_symbol)}"

    hk_lower = re.sub(r'num\s*([0-9])', r'num_\1', hk_lower)
    hk_lower = re.sub(r'num\s*([\.\/\*\-\+])', replace_num_symbol, hk_lower)
    
    if "num_decimal" not in hk_lower:
         hk_lower = hk_lower.replace("decimal", "num_decimal")

    hk_lower = hk_lower.replace("del", "delete")
    hk_lower = hk_lower.replace("ins", "insert")
    hk_lower = hk_lower.replace("pgup", "page_up")
    hk_lower = hk_lower.replace("pgdn", "page_down")

    parts = [part.strip() for part in hk_lower.split('+')]
    normalized_storage_string = "+".join(filter(None, parts))

    logging.debug(f"[NormalizeStorage] Input: '{hotkey_str}', Output: '{normalized_storage_string}'")
    return normalized_storage_string