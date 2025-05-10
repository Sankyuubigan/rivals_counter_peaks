
# Определяем язык по умолчанию, с фолбэком на ru_RU
DEFAULT_LANGUAGE = 'ru_RU'
SUPPORTED_LANGUAGES = {'ru_RU': 'Русский', 'en_US': 'English'}

TRANSLATIONS = {
    'ru_RU': {
        'title': 'Подбор контрпиков',
        'select_heroes': 'Выберите героев, чтобы увидеть контрпики.',
        'no_heroes_selected': 'Выберите героев вражеской команды.',
        'selected': 'Выбрано', # Ключ 'selected' оставлен для обратной совместимости, если где-то используется
        'selected_none': 'Выбрано (0/{max_team_size})', # Новый ключ
        'selected_some': 'Выбрано', # Новый ключ
        'copy_rating': 'Копировать состав',
        'clear_all': 'Очистить всё',
        'about_author': 'Об авторе',
        'author_info': 'Автор: Nilden\nВерсия: {version}',
        'language': 'Язык',
        'strong_player': 'сильный игрок',
        'version': 'Версия: {version}', # Используется в author_info
        'counterpick_rating': 'Рейтинг контрпиков для вражеской команды:',
        'points': 'балл(ов)',
        'hero_rating': 'Рейтинг героев',
        'hero_rating_title': 'Рейтинг уязвимости героев', # Изменено название для ясности

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
        'info': 'Информация', # Добавлено
        'no_data_to_copy': 'Нет данных для копирования (команда не сформирована).',
        'enemy_selected_tooltip': 'Выбран врагом',
        'no_recommendations': 'Нет рекомендаций',
        'select_enemies_for_recommendations': 'Выберите врагов для рекомендаций', # Для горизонтального списка
        'recognition_error_prefix': 'Ошибка распознавания:',
        'recognition_no_screenshot': 'Не удалось сделать скриншот.',
        'recognition_no_templates': 'Шаблоны героев не загружены.',
        'recognition_failed': 'Не удалось распознать героев на скриншоте.',
        # <<< НОВЫЕ ПЕРЕВОДЫ (МЕНЮ, ЛОГИ, ХОТКЕИ) >>>
        'menu': 'Меню',
        'hotkeys_menu_item': 'Хоткеи',
        'logs_menu_item': 'Логи',
        'logs_window_title': 'Логи приложения',
        'copy_all_logs_button': 'Копировать все логи',
        'clear_log_window_button': 'Очистить окно',
        'log_copy_no_logs': 'Нет логов для копирования.',
        'log_copy_success': 'Логи скопированы в буфер обмена.',
        'log_copy_error': 'Ошибка копирования логов',
        'hotkeys_window_title': 'Горячие клавиши',
        'hotkeys_section_main': 'Основные:',
        'hotkeys_section_additional': 'Дополнительно:',
        'hotkey_desc_navigation': 'Перемещение по списку героев (Средний/Большой режим)',
        'hotkey_desc_select': 'Выбрать/Снять выбор героя (под курсором)',
        'hotkey_desc_toggle_mode': 'Переключить режим (Компактный/Средний)',
        'hotkey_desc_recognize': 'Распознать героев на экране',
        'hotkey_desc_clear': 'Очистить выбор',
        'hotkey_desc_copy_team': 'Копировать состав команды в буфер обмена',
        'hotkey_desc_toggle_topmost': 'Включить/Выключить "Поверх всех окон"',
        'hotkey_desc_toggle_mouse_ignore': 'Включить/Выключить игнорирование кликов мыши',
        'hotkey_desc_debug_screenshot': 'Сделать тестовый скриншот области распознавания',
        'hotkey_desc_lmb': 'ЛКМ по герою',
        'hotkey_desc_lmb_select': 'Выбрать/Снять выбор',
        'hotkey_desc_rmb': 'ПКМ по герою',
        'hotkey_desc_rmb_priority': 'Открыть меню приоритета (Средний/Большой режим)',
        'hotkey_desc_drag': 'Перетаскивание окна',
        'hotkey_desc_drag_window': 'За верхнюю панель (Компактный режим)',
        'hotkey_desc_slider': 'Слайдер прозрачности',
        'hotkey_desc_slider_transparency': 'В левом верхнем углу',
        # <<< --------------------------------------- >>>
    },
    'en_US': {
        'title': 'Counterpick Selection',
        'select_heroes': 'Select heroes to see counterpicks.',
        'no_heroes_selected': 'Select enemy team heroes.',
        'selected': 'Selected', # Kept for compatibility
        'selected_none': 'Selected (0/{max_team_size})', # New key
        'selected_some': 'Selected', # New key
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
        'hero_rating_title': 'Hero Vulnerability Rating', # Changed title for clarity

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
        'info': 'Information', # Added
        'no_data_to_copy': 'No data to copy (team not formed).',
        'enemy_selected_tooltip': 'Selected Enemy',
        'no_recommendations': 'No recommendations',
        'select_enemies_for_recommendations': 'Select enemies for recommendations',
        'recognition_error_prefix': 'Recognition Error:',
        'recognition_no_screenshot': 'Failed to capture screenshot.',
        'recognition_no_templates': 'Hero templates not loaded.',
        'recognition_failed': 'Could not recognize heroes in the screenshot.',
         # <<< НОВЫЕ ПЕРЕВОДЫ (МЕНЮ, ЛОГИ, ХОТКЕИ) >>>
        'menu': 'Menu',
        'hotkeys_menu_item': 'Hotkeys',
        'logs_menu_item': 'Logs',
        'logs_window_title': 'Application Logs',
        'copy_all_logs_button': 'Copy All Logs',
        'clear_log_window_button': 'Clear Window',
        'log_copy_no_logs': 'No logs to copy.',
        'log_copy_success': 'Logs copied to clipboard.',
        'log_copy_error': 'Error copying logs',
        'hotkeys_window_title': 'Hotkeys',
        'hotkeys_section_main': 'Main:',
        'hotkeys_section_additional': 'Additional:',
        'hotkey_desc_navigation': 'Navigate hero list (Middle/Large mode)',
        'hotkey_desc_select': 'Select/Deselect hero (under cursor)',
        'hotkey_desc_toggle_mode': 'Toggle mode (Compact/Middle)',
        'hotkey_desc_recognize': 'Recognize heroes on screen',
        'hotkey_desc_clear': 'Clear selection',
        'hotkey_desc_copy_team': 'Copy team composition to clipboard',
        'hotkey_desc_toggle_topmost': 'Toggle "Always on Top"',
        'hotkey_desc_toggle_mouse_ignore': 'Toggle mouse click-through',
        'hotkey_desc_debug_screenshot': 'Take test screenshot of recognition area',
        'hotkey_desc_lmb': 'LMB on hero',
        'hotkey_desc_lmb_select': 'Select/Deselect',
        'hotkey_desc_rmb': 'RMB on hero',
        'hotkey_desc_rmb_priority': 'Open priority menu (Middle/Large mode)',
        'hotkey_desc_drag': 'Drag window',
        'hotkey_desc_drag_window': 'By top panel (Compact mode)',
        'hotkey_desc_slider': 'Transparency slider',
        'hotkey_desc_slider_transparency': 'Top left corner',
        # <<< --------------------------------------- >>>
    }
}

# Кэш для форматированных строк
formatted_text_cache = {}


def _get_translation_table(language):
    """Получает таблицу переводов для указанного языка или таблицу для русского языка как запасной вариант."""
    return TRANSLATIONS.get(language, TRANSLATIONS['ru_RU'])


def _validate_key(key, translations_for_lang, default_text):
    """Проверяет наличие ключа в таблице переводов, возвращает перевод или текст по умолчанию."""
    base_text = translations_for_lang.get(key)
    if base_text is None:
        base_text = default_text if default_text is not None else f"_{key}_"  # Возвращаем ключ в _подчеркиваниях_
    return base_text


def get_text(key, default_text=None, language=None, **kwargs):
    """
    Получает переведенный текст по ключу, с возможностью форматирования.
    """
    current_language = language if language else DEFAULT_LANGUAGE

    cache_key_base = (current_language, key)
    cache_key_formatted = (current_language, key, tuple(sorted(kwargs.items())))

    if kwargs and cache_key_formatted in formatted_text_cache:
        return formatted_text_cache[cache_key_formatted]
    if not kwargs and cache_key_base in formatted_text_cache:
        return formatted_text_cache[cache_key_base]

    translations_for_lang = _get_translation_table(current_language)
    base_text = _validate_key(key, translations_for_lang, default_text)

    try:
        result_text = base_text.format(**kwargs) if kwargs else base_text
    except KeyError as e:
        print(f"[!] Warning: Missing key '{e}' for formatting text '{key}' in lang '{current_language}'")  # noqa
        result_text = base_text
    except ValueError as e:
        print(f"[!] Warning: Formatting error for text '{key}' in lang '{current_language}': {e}")  # noqa
        result_text = base_text

    cache_key = cache_key_formatted if kwargs else cache_key_base
    formatted_text_cache[cache_key] = result_text

    return result_text


def set_language(language):
    """Устанавливает глобальный язык по умолчанию и очищает кэш переводов."""
    global DEFAULT_LANGUAGE
    if language in SUPPORTED_LANGUAGES:
        if DEFAULT_LANGUAGE != language:
            DEFAULT_LANGUAGE = language
            formatted_text_cache.clear()  # Очищаем кэш при смене языка
            print(f"Global language set to: {language}")
        # else:
            # print(f"Global language is already {language}")
    else:
        print(f"Warning: Unsupported language '{language}'. Keeping '{DEFAULT_LANGUAGE}'.")
