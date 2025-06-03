# File: core/hotkey_parser_utils.py
import logging
import re
from typing import Dict, Any, Set

# PYNPUT_AVAILABLE_PARSER и связанные с pynput карты больше не нужны,
# так как мы переходим на библиотеку 'keyboard'.

# Оставляем только функцию normalize_string_for_storage,
# так как она определяет наш "внутренний" формат хранения хоткеев,
# который затем будет преобразовываться адаптером для конкретной библиотеки.

def normalize_string_for_storage(hotkey_str: str) -> str:
    """
    Нормализует строку хоткея для консистентного хранения.
    Приводит к нижнему регистру, удаляет лишние пробелы,
    обрабатывает numpad обозначения (например, 'num .', 'num /' -> 'num_decimal', 'num_divide').
    """
    if not hotkey_str:
        return ""
        
    hk_lower = hotkey_str.lower().strip()
    
    # Замена символов numpad на стандартные идентификаторы
    # num . -> num_decimal
    # num / -> num_divide
    # num * -> num_multiply
    # num - -> num_subtract
    # num + -> num_add
    num_symbol_map = {'.': 'decimal', '/': 'divide', '*': 'multiply', '-': 'subtract', '+': 'add'}
    
    def replace_num_symbol(match_obj):
        symbol_part = match_obj.group(1) # Это будет ' .', ' /' и т.д. или просто символ, если пробела нет
        # Удаляем возможный пробел перед символом и сам символ
        actual_symbol = symbol_part.strip()
        return f"num_{num_symbol_map.get(actual_symbol, actual_symbol)}"

    # Обрабатываем 'num <цифра>' -> 'num_<цифра>'
    hk_lower = re.sub(r'num\s*([0-9])', r'num_\1', hk_lower)
    # Обрабатываем 'num <символ>' -> 'num_<имя_символа>'
    hk_lower = re.sub(r'num\s*([\.\/\*\-\+])', replace_num_symbol, hk_lower)
    
    # Если после предыдущих замен "num_decimal" еще не сформировался (например, было просто "decimal")
    if "num_decimal" not in hk_lower:
         hk_lower = hk_lower.replace("decimal", "num_decimal") # numpad .

    # 'del' -> 'delete', 'ins' -> 'insert'
    # 'pgup' -> 'page_up', 'pgdn' -> 'page_down'
    # Эти нормализации важны, так как HotkeyCaptureLineEdit может генерировать такие строки
    hk_lower = hk_lower.replace("del", "delete")
    hk_lower = hk_lower.replace("ins", "insert")
    hk_lower = hk_lower.replace("pgup", "page_up")
    hk_lower = hk_lower.replace("pgdn", "page_down")
    # 'esc' также часто используется, оставляем его как 'esc' для внутреннего формата,
    # а адаптер преобразует в 'escape' для библиотеки 'keyboard'.

    # Удаляем лишние пробелы вокруг '+'
    parts = [part.strip() for part in hk_lower.split('+')]
    normalized_storage_string = "+".join(filter(None, parts)) # filter(None, ...) убирает пустые части, если были '++'

    logging.debug(f"[NormalizeStorage] Input: '{hotkey_str}', Output: '{normalized_storage_string}'")
    return normalized_storage_string
