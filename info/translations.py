# File: info/translations.py
import os
import json
import logging
from typing import Dict, Any, Optional

# Поддерживаемые языки
SUPPORTED_LANGUAGES = {
    "ru_RU": "Русский",
    "en_US": "English"
}

# Язык по умолчанию
DEFAULT_LANGUAGE = "ru_RU"

# Текущий язык
_current_language = DEFAULT_LANGUAGE

# Загруженные переводы
_translations: Dict[str, Dict[str, str]] = {}

def load_translations():
    """Загружает переводы из файлов"""
    global _translations
    
    # Определяем путь к файлам переводов
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for lang_code in SUPPORTED_LANGUAGES:
        translation_file = os.path.join(current_dir, f"{lang_code}.json")
        if os.path.exists(translation_file):
            try:
                with open(translation_file, 'r', encoding='utf-8') as f:
                    _translations[lang_code] = json.load(f)
            except Exception as e:
                logging.error(f"Error loading translations for {lang_code}: {e}")
                _translations[lang_code] = {}

def set_language(lang_code: str):
    """Устанавливает текущий язык"""
    global _current_language
    if lang_code in SUPPORTED_LANGUAGES:
        _current_language = lang_code
    else:
        logging.warning(f"Unsupported language: {lang_code}. Using default: {DEFAULT_LANGUAGE}")
        _current_language = DEFAULT_LANGUAGE

def get_current_language() -> str:
    """Возвращает текущий язык"""
    return _current_language

def get_text(key: str, language: Optional[str] = None, default_text: Optional[str] = None, **kwargs) -> str:
    """
    Получает переведенный текст по ключу
    
    Args:
        key: Ключ перевода
        language: Язык (если не указан, используется текущий)
        default_text: Текст по умолчанию, если перевод не найден
        **kwargs: Параметры для форматирования строки
        
    Returns:
        Переведенный текст или текст по умолчанию
    """
    lang = language or _current_language
    
    # Если язык не поддерживается, используем язык по умолчанию
    if lang not in _translations:
        lang = DEFAULT_LANGUAGE
    
    # Получаем перевод
    translation = _translations.get(lang, {}).get(key)
    
    # Если перевод не найден, пытаемся использовать язык по умолчанию
    if translation is None and lang != DEFAULT_LANGUAGE:
        translation = _translations.get(DEFAULT_LANGUAGE, {}).get(key)
    
    # Если перевод все еще не найден, используем текст по умолчанию или ключ
    if translation is None:
        translation = default_text if default_text is not None else key
    
    # Форматируем строку, если есть параметры
    try:
        return translation.format(**kwargs)
    except (KeyError, ValueError):
        return translation

# Загружаем переводы при импорте модуля
load_translations()