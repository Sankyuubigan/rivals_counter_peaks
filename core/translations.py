# File: translations.py
import locale

# Определяем язык по умолчанию, с фолбэком на ru_RU
DEFAULT_LANGUAGE = locale.getdefaultlocale()[0] if locale.getdefaultlocale() and locale.getdefaultlocale()[0] in ['ru_RU', 'en_US'] else 'ru_RU'
SUPPORTED_LANGUAGES = {'ru_RU': 'Русский', 'en_US': 'English'}

TRANSLATIONS = {
    'ru_RU': {
        'title': 'Подбор контрпиков',
        'select_heroes': 'Выберите героев, чтобы увидеть контрпики.',
        'no_heroes_selected': 'Выберите героев вражеской команды.',
        'selected': 'Выбрано',
        'copy_rating': 'Копировать состав',
        'clear_all': 'Очистить всё',
        'about_author': 'Об авторе',
        'author_info': 'Автор: Nilden\nВерсия: {version}',
        'language': 'Язык',
        'strong_player': 'сильный игрок',
        'version': 'Версия: {version}',
        'counterpick_rating': 'Рейтинг контрпиков для вражеской команды:',
        'points': 'балл(ов)',
        'hero_rating': 'Рейтинг героев',
        'hero_rating_title': 'Рейтинг неуязвимости героев',

        # --- Donate/Contact Info ---
        'donate_info_title': 'Купить мне кофе (помощь и благодарность за софт):',
        'donate_tinkoff_label': 'Тинькофф:',
        'donate_tinkoff_card': '2200 7007 5813 1881', # Карта как отдельный ключ
        'donate_donationalerts_label': 'Ссылка для донатов из-за рубежа:',
        'donate_donationalerts_url': 'https://www.donationalerts.com/r/nildencorp', # URL как ключ
        'donate_usdt_trc20_label': 'Crypto USDT TRC20:',
        'donate_usdt_trc20': 'TQ4jTGfTpd3qMMHzBKrxmaCmaeJdjvEqky', # Адрес как ключ
        'donate_usdt_ton_label': 'Crypto USDT TON:',
        'donate_usdt_ton': 'UQDKxUPol48B__NQvvTxKKFtr6PTwZH7i9BWWjVb9iFuNb7k', # Адрес как ключ
        'contact_suggestions_label': 'C идеями и предложениями можете обращаться:',
        'contact_telegram': 'https://t.me/dron_maredon', # Контакт как ключ
        # --- End Donate/Contact ---

        'mode': 'Режим',
        'mode_min': 'Компактный',
        'mode_middle': 'Средний',
        'mode_max': 'Большой',
        'topmost_on': 'Поверх: Вкл',
        'topmost_off': 'Поверх: Выкл',
        'counters': 'контрит',
        'remove_priority': 'Снять приоритет',
        'set_priority': 'Назначить приоритет',
        'success': 'Успешно',
        'copied_to_clipboard': 'Состав команды скопирован.',
        'error': 'Ошибка',
        'copy_error_detailed': 'Не удалось скопировать в буфер обмена:\n{e}',
        'copy_error': 'Не удалось скопировать в буфер обмена.',
        'warning': 'Внимание',
        'no_data_to_copy': 'Нет данных для копирования (команда не сформирована).',
        'enemy_selected_tooltip': 'Выбран врагом',
        'no_recommendations': 'Нет рекомендаций',
        'select_enemies_for_recommendations': 'Выберите врагов для рекомендаций', # Для горизонтального списка
    },
    'en_US': {
        'title': 'Counterpick Selection',
        'select_heroes': 'Select heroes to see counterpicks.',
        'no_heroes_selected': 'Select enemy team heroes.',
        'selected': 'Selected',
        'copy_rating': 'Copy Team',
        'clear_all': 'Clear All',
        'about_author': 'About Author',
        'author_info': 'Author: Nilden\nVersion: {version}',
        'language': 'Language',
        'strong_player': 'strong player',
        'version': 'Version: {version}',
        'counterpick_rating': 'Counterpick rating for the enemy team:',
        'points': 'points',
        'hero_rating': 'Hero Rating',
        'hero_rating_title': 'Hero Invulnerability Rating',

        # --- Donate/Contact Info ---
        'donate_info_title': 'Buy me a coffee (support and thanks for the software):',
        'donate_tinkoff_label': 'Tinkoff:',
        'donate_tinkoff_card': '2200 7007 5813 1881',
        'donate_donationalerts_label': 'Link for donations from abroad:',
        'donate_donationalerts_url': 'https://www.donationalerts.com/r/nildencorp',
        'donate_usdt_trc20_label': 'Crypto USDT TRC20:',
        'donate_usdt_trc20': 'TQ4jTGfTpd3qMMHzBKrxmaCmaeJdjvEqky',
        'donate_usdt_ton_label': 'Crypto USDT TON:',
        'donate_usdt_ton': 'UQDKxUPol48B__NQvvTxKKFtr6PTwZH7i9BWWjVb9iFuNb7k',
        'contact_suggestions_label': 'For ideas and suggestions, contact:',
        'contact_telegram': 'https://t.me/dron_maredon',
        # --- End Donate/Contact ---

        'mode': 'Mode',
        'mode_min': 'Compact',
        'mode_middle': 'Middle',
        'mode_max': 'Large',
        'topmost_on': 'Top: On',
        'topmost_off': 'Top: Off',
        'counters': 'counters',
        'remove_priority': 'Remove Priority',
        'set_priority': 'Set Priority',
        'success': 'Success',
        'copied_to_clipboard': 'Team composition copied.',
        'error': 'Error',
        'copy_error_detailed': 'Could not copy to clipboard:\n{e}',
        'copy_error': 'Could not copy to clipboard.',
        'warning': 'Warning',
        'no_data_to_copy': 'No data to copy (team not formed).',
        'enemy_selected_tooltip': 'Selected Enemy',
        'no_recommendations': 'No recommendations',
        'select_enemies_for_recommendations': 'Select enemies for recommendations',
    }
}

# Кэш для форматированных строк
formatted_text_cache = {}

def get_text(key, default_text=None, language=None, **kwargs):
    """
    Получает перевод по ключу для указанного или текущего языка.
    Поддерживает форматирование строки с помощью kwargs.
    Использует кэш для форматированных строк.
    """
    global DEFAULT_LANGUAGE
    current_language = language if language else DEFAULT_LANGUAGE

    cache_key_base = (current_language, key)
    cache_key_formatted = (current_language, key, tuple(sorted(kwargs.items())))

    # Сначала проверяем кэш для форматированной строки
    if kwargs and cache_key_formatted in formatted_text_cache:
        return formatted_text_cache[cache_key_formatted]
    # Затем проверяем кэш для неформатированной строки (если нет kwargs)
    if not kwargs and cache_key_base in formatted_text_cache:
        return formatted_text_cache[cache_key_base]

    # Получаем базовый перевод
    translations_for_lang = TRANSLATIONS.get(current_language, TRANSLATIONS['ru_RU'])
    base_text = translations_for_lang.get(key)

    if base_text is None:
        base_text = default_text if default_text is not None else key

    # Выполняем форматирование, если переданы аргументы
    try:
        result_text = base_text.format(**kwargs) if kwargs else base_text
    except KeyError as e:
        print(f"[!] Warning: Missing key '{e}' for formatting text '{key}' in lang '{current_language}'")
        result_text = base_text # Возвращаем неформатированный текст при ошибке
    except ValueError as e: # Обработка ошибок форматирования (например, неверные спецификаторы)
        print(f"[!] Warning: Formatting error for text '{key}' in lang '{current_language}': {e}")
        result_text = base_text

    # Кэшируем результат
    if kwargs:
        formatted_text_cache[cache_key_formatted] = result_text
    else:
        formatted_text_cache[cache_key_base] = result_text

    return result_text


def set_language(language):
    """Устанавливает текущий язык и очищает кэш переводов."""
    global DEFAULT_LANGUAGE
    if language in SUPPORTED_LANGUAGES:
        DEFAULT_LANGUAGE = language
        formatted_text_cache.clear() # Очищаем кэш при смене языка
        print(f"Language set to: {language}")
    else:
        print(f"Warning: Unsupported language '{language}'. Keeping '{DEFAULT_LANGUAGE}'.")