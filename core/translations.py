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
        'selected': 'Выбрано', # Убрал двоеточие, будет в формате X/6
        'copy_rating': 'Копировать состав', # Изменено название кнопки
        'clear_all': 'Очистить всё',
        'about_author': 'Об авторе',
        'author_info': 'Автор: Nilden\nВерсия: {version}', # Версия будет подставляться
        'language': 'Язык',
        'strong_player': 'сильный игрок', # Ключ не используется?
        'version': 'Версия: {version}', # Ключ не используется?
        'counterpick_rating': 'Рейтинг контрпиков для вражеской команды:', # Изменено
        'points': 'балл(ов)',
        'hero_rating': 'Рейтинг героев',
        'hero_rating_title': 'Рейтинг неуязвимости героев', # Изменено
        'donate_info': 'Купить мне кофе (помощь и благодарность за софт):\n'
                       'Тинькофф: 2200 7007 5813 1881\n'
                       'Ссылка для донатов из-за рубежа:\n'
                       'https://www.donationalerts.com/r/nildencorp\n'
                       'Crypto USDT TRC20:\n'
                       'TQ4jTGfTpd3qMMHzBKrxmaCmaeJdjvEqky\n'
                       'Crypto USDT TON:\n'
                       'UQDKxUPol48B__NQvvTxKKFtr6PTwZH7i9BWWjVb9iFuNb7k\n'
                       '\n'
                       'C идеями и предложениями можете обращаться:\n'
                       'https://t.me/dron_maredon',
        'mode': 'Режим',
        'mode_min': 'Компактный',
        'mode_middle': 'Средний',
        'mode_max': 'Большой',
        'topmost_on': 'Поверх: Вкл',
        'topmost_off': 'Поверх: Выкл',
        'counters': 'контрит', # Для всплывающих подсказок
        'remove_priority': 'Снять приоритет',
        'set_priority': 'Назначить приоритет',
        'success': 'Успешно',
        'copied_to_clipboard': 'Состав команды скопирован.', # Изменено
        'error': 'Ошибка',
        'copy_error_detailed': 'Не удалось скопировать в буфер обмена:\n{e}',
        'copy_error': 'Не удалось скопировать в буфер обмена.',
        'warning': 'Внимание',
        'no_data_to_copy': 'Нет данных для копирования (команда не сформирована).',
        'enemy_selected_tooltip': 'Выбран врагом', # Подсказка для горизонтального списка
        'no_recommendations': 'Нет рекомендаций', # Если effective_team пуст
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
        'donate_info': 'Buy me a coffee (support and thanks for the software):\n'
                       'Tinkoff: 2200 7007 5813 1881\n'
                       'Link for donations from abroad:\n'
                       'https://www.donationalerts.com/r/nildencorp\n'
                       'Crypto USDT TRC20:\n'
                       'TQ4jTGfTpd3qMMHzBKrxmaCmaeJdjvEqky\n'
                       'Crypto USDT TON:\n'
                       'UQDKxUPol48B__NQvvTxKKFtr6PTwZH7i9BWWjVb9iFuNb7k\n'
                       '\n'
                       'For ideas and suggestions, contact:\n' # Переведено
                       'https://t.me/dron_maredon',
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

    # Генерируем ключ кэша
    cache_key = (current_language, key, tuple(sorted(kwargs.items())))

    if cache_key in formatted_text_cache:
        return formatted_text_cache[cache_key]

    # Получаем базовый перевод
    base_text = TRANSLATIONS.get(current_language, TRANSLATIONS['ru_RU']).get(key)

    # Если перевод не найден, используем default_text или сам ключ
    if base_text is None:
        base_text = default_text if default_text is not None else key

    # Выполняем форматирование, если переданы аргументы
    try:
        result_text = base_text.format(**kwargs) if kwargs else base_text
    except KeyError as e:
        print(f"[!] Warning: Missing key '{e}' for formatting text '{key}' in lang '{current_language}'")
        result_text = base_text # Возвращаем неформатированный текст при ошибке

    # Кэшируем результат
    formatted_text_cache[cache_key] = result_text
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