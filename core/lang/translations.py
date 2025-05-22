
# Определяем язык по умолчанию, с фолбэком на ru_RU
DEFAULT_LANGUAGE = 'ru_RU'
SUPPORTED_LANGUAGES = {'ru_RU': 'Русский', 'en_US': 'English'}

TRANSLATIONS = {
    'ru_RU': {
        'title': 'Подбор контрпиков',
        'select_heroes': 'Выберите героев, чтобы увидеть контрпики.',
        'no_heroes_selected': 'Выберите героев вражеской команды.',
        'selected': 'Выбрано',
        'selected_none': 'Выбрано (0/{max_team_size})',
        'selected_some': 'Выбрано',
        'copy_rating': 'Копировать состав',
        'clear_all': 'Очистить всё',
        'about_program': 'О программе',
        'author_info': 'Автор: Nilden\nВерсия: {version}', # Может остаться в md файле
        'language': 'Язык',
        'strong_player': 'сильный игрок',
        'version': 'Версия: {version}',
        'counterpick_rating': 'Рейтинг контрпиков для вражеской команды:',
        'points': 'балл(ов)',
        'hero_rating': 'Рейтинг героев',
        'hero_rating_title': 'Рейтинг уязвимости героев',
        'donate_info_title': 'Купить мне кофе (помощь и благодарность за софт):',
        'donate_tinkoff_label': 'Тинькофф:',
        'donate_tinkoff_card': '2200 7007 5813 1881',
        'donate_donationalerts_label': 'Ссылка для донатов из-за рубежа:',
        'donate_donationalerts_url': 'https://www.donationalerts.com/r/nildencorp',
        'donate_usdt_trc20_label': 'Crypto USDT TRC20:',
        'donate_usdt_trc20': 'TQ4jTGfTpd3qMMHzBKrxmaCmaeJdjvEqky',
        'donate_usdt_ton_label': 'Crypto USDT TON:',
        'donate_usdt_ton': 'UQDKxUPol48B__NQvvTxKKFtr6PTwZH7i9BWWjVb9iFuNb7k',
        'contact_suggestions_label': 'C идеями и предложениями можете обращаться:',
        'contact_telegram': 'https://t.me/dron_maredon',
        'mode': 'Режим',
        'mode_min': 'Компактный',
        'mode_middle': 'Средний',
        'mode_max': 'Большой',
        'tray_mode_on': 'Трей: вкл',
        'tray_mode_off': 'Трей: выкл',
        'counters': 'контрит',
        'remove_priority': 'Снять приоритет',
        'set_priority': 'Назначить приоритет',
        'success': 'Успешно',
        'copied_to_clipboard': 'Состав команды скопирован.',
        'error': 'Ошибка',
        'copy_error_detailed': 'Не удалось скопировать в буфер обмена:\n{e}',
        'copy_error': 'Не удалось скопировать в буфер обмена.',
        'warning': 'Внимание',
        'info': 'Информация',
        'no_data_to_copy': 'Нет данных для копирования (команда не сформирована).',
        'enemy_selected_tooltip': 'Выбран врагом',
        'no_recommendations': 'Нет рекомендаций',
        'select_enemies_for_recommendations': 'Выберите врагов для рекомендаций',
        'recognition_error_prefix': 'Ошибка распознавания:',
        'recognition_no_screenshot': 'Не удалось сделать скриншот.',
        'recognition_no_templates': 'Шаблоны героев не загружены.',
        'recognition_failed': 'Не удалось распознать героев на скриншоте.',
        'menu': 'Меню',
        'hotkeys_menu_item': 'Горячие клавиши', # Для старого пункта меню
        'hotkey_settings_menu_item': 'Настройка хоткеев', # Новый пункт меню
        'logs_menu_item': 'Логи',
        'logs_window_title': 'Логи приложения',
        'copy_all_logs_button': 'Копировать все логи',
        'clear_log_window_button': 'Очистить окно',
        'log_copy_no_logs': 'Нет логов для копирования.',
        'log_copy_success': 'Логи скопированы в буфер обмена.',
        'log_copy_error': 'Ошибка копирования логов',
        'hotkeys_window_title': 'Горячие клавиши', # Заголовок окна отображения хоткеев
        'hotkey_settings_window_title': 'Настройка горячих клавиш', # Заголовок окна НАСТРОЙКИ
        'hotkeys_section_main': 'Основные действия:', # Для окна отображения и настройки
        'hotkeys_section_interaction_title': 'Взаимодействие с интерфейсом:', # Новый раздел для отображения
        'hotkey_desc_navigation': 'Навигация по списку героев',
        'hotkey_desc_select': 'Выбор/снятие героя (под курсором)',
        'hotkey_desc_toggle_mode': 'Переключить режим окна',
        'hotkey_desc_recognize': 'Распознать героев',
        'hotkey_desc_clear': 'Очистить выбор врагов',
        'hotkey_desc_copy_team': 'Копировать состав',
        'hotkey_desc_toggle_tray': 'Режим "Трей" (Поверх + Игнор. мыши)',
        'hotkey_desc_toggle_mouse_ignore': 'Игнорирование мыши (отдельно)',
        'hotkey_desc_debug_screenshot': 'Тестовый скриншот',
        'hotkey_desc_lmb': 'ЛКМ по герою',
        'hotkey_desc_lmb_select': 'Выбрать/Снять выбор',
        'hotkey_desc_rmb': 'ПКМ по герою',
        'hotkey_desc_rmb_priority': 'Меню приоритета',
        'hotkey_desc_drag': 'Перетаскивание окна',
        'hotkey_desc_drag_window': 'За верхнюю панель (Компактный режим)',
        'hotkey_desc_slider': 'Слайдер прозрачности',
        'hotkey_desc_slider_transparency': 'В левом верхнем углу',
        # Для окна настройки хоткеев
        'hotkey_settings_change_btn': 'Изменить',
        'hotkey_settings_press_keys': 'Нажмите клавиши...',
        'hotkey_settings_press_new_hotkey_for': 'Нажмите новую комбинацию для "{action}"',
        'hotkey_settings_capture_title': 'Ввод нового хоткея',
        'hotkey_settings_save': 'Сохранить',
        'hotkey_settings_cancel': 'Отмена',
        'hotkey_settings_reset_defaults': 'Сбросить по умолчанию',
        'hotkey_settings_cancel_capture': 'Отменить ввод',
        'hotkey_not_set': 'Не назначен',
        'hotkey_none': 'Нет', # Когда хоткей удален (не назначен)
        'hotkey_settings_defaults_reset_title': 'Сброс хоткеев',
        'hotkey_settings_defaults_reset_msg': 'Горячие клавиши сброшены к стандартным значениям.',
        'hotkey_settings_duplicate_title': 'Дублирующиеся хоткеи',
        'hotkey_settings_duplicate_message': 'Обнаружены дублирующиеся горячие клавиши. Пожалуйста, исправьте:',
    },
    'en_US': {
        'title': 'Counterpick Selection',
        'select_heroes': 'Select heroes to see counterpicks.',
        'no_heroes_selected': 'Select enemy team heroes.',
        'selected': 'Selected',
        'selected_none': 'Selected (0/{max_team_size})',
        'selected_some': 'Selected',
        'copy_rating': 'Copy Team',
        'clear_all': 'Clear All',
        'about_program': 'About Program',
        'author_info': 'Author: Nilden\nVersion: {version}',
        'language': 'Language',
        'strong_player': 'strong player',
        'version': 'Version: {version}',
        'counterpick_rating': 'Counterpick rating for the enemy team:',
        'points': 'points',
        'hero_rating': 'Hero Rating',
        'hero_rating_title': 'Hero Vulnerability Rating',
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
        'mode': 'Mode',
        'mode_min': 'Compact',
        'mode_middle': 'Middle',
        'mode_max': 'Large',
        'tray_mode_on': 'Tray: On',
        'tray_mode_off': 'Tray: Off',
        'counters': 'counters',
        'remove_priority': 'Remove Priority',
        'set_priority': 'Set Priority',
        'success': 'Success',
        'copied_to_clipboard': 'Team composition copied.',
        'error': 'Error',
        'copy_error_detailed': 'Could not copy to clipboard:\n{e}',
        'copy_error': 'Could not copy to clipboard.',
        'warning': 'Warning',
        'info': 'Information',
        'no_data_to_copy': 'No data to copy (team not formed).',
        'enemy_selected_tooltip': 'Selected Enemy',
        'no_recommendations': 'No recommendations',
        'select_enemies_for_recommendations': 'Select enemies for recommendations',
        'recognition_error_prefix': 'Recognition Error:',
        'recognition_no_screenshot': 'Failed to capture screenshot.',
        'recognition_no_templates': 'Hero templates not loaded.',
        'recognition_failed': 'Could not recognize heroes in the screenshot.',
        'menu': 'Menu',
        'hotkeys_menu_item': 'Hotkeys',
        'hotkey_settings_menu_item': 'Configure Hotkeys',
        'logs_menu_item': 'Logs',
        'logs_window_title': 'Application Logs',
        'copy_all_logs_button': 'Copy All Logs',
        'clear_log_window_button': 'Clear Window',
        'log_copy_no_logs': 'No logs to copy.',
        'log_copy_success': 'Logs copied to clipboard.',
        'log_copy_error': 'Error copying logs',
        'hotkeys_window_title': 'Hotkeys',
        'hotkey_settings_window_title': 'Hotkey Configuration',
        'hotkeys_section_main': 'Main Actions:',
        'hotkeys_section_interaction_title': 'Interface Interaction:',
        'hotkey_desc_navigation': 'Navigate hero list',
        'hotkey_desc_select': 'Select/Deselect hero (under cursor)',
        'hotkey_desc_toggle_mode': 'Toggle window mode',
        'hotkey_desc_recognize': 'Recognize heroes',
        'hotkey_desc_clear': 'Clear enemy selection',
        'hotkey_desc_copy_team': 'Copy team composition',
        'hotkey_desc_toggle_tray': '"Tray" Mode (Always on Top + Mouse Ignore)',
        'hotkey_desc_toggle_mouse_ignore': 'Mouse Click-through (Independent)',
        'hotkey_desc_debug_screenshot': 'Test screenshot',
        'hotkey_desc_lmb': 'LMB on hero',
        'hotkey_desc_lmb_select': 'Select/Deselect',
        'hotkey_desc_rmb': 'RMB on hero',
        'hotkey_desc_rmb_priority': 'Priority menu',
        'hotkey_desc_drag': 'Drag window',
        'hotkey_desc_drag_window': 'By top panel (Compact mode)',
        'hotkey_desc_slider': 'Transparency slider',
        'hotkey_desc_slider_transparency': 'Top left corner',
        'hotkey_settings_change_btn': 'Change',
        'hotkey_settings_press_keys': 'Press keys...',
        'hotkey_settings_press_new_hotkey_for': 'Press new combination for "{action}"',
        'hotkey_settings_capture_title': 'Enter New Hotkey',
        'hotkey_settings_save': 'Save',
        'hotkey_settings_cancel': 'Cancel',
        'hotkey_settings_reset_defaults': 'Reset to Defaults',
        'hotkey_settings_cancel_capture': 'Cancel Input',
        'hotkey_not_set': 'Not assigned',
        'hotkey_none': 'None',
        'hotkey_settings_defaults_reset_title': 'Reset Hotkeys',
        'hotkey_settings_defaults_reset_msg': 'Hotkeys have been reset to their default values.',
        'hotkey_settings_duplicate_title': 'Duplicate Hotkeys',
        'hotkey_settings_duplicate_message': 'Duplicate hotkeys found. Please correct them:',
    }
}

# Кэш для форматированных строк
formatted_text_cache = {}


def _get_translation_table(language):
    return TRANSLATIONS.get(language, TRANSLATIONS['ru_RU'])


def _validate_key(key, translations_for_lang, default_text):
    base_text = translations_for_lang.get(key)
    if base_text is None:
        base_text = default_text if default_text is not None else f"_{key}_"
    return base_text


def get_text(key, default_text=None, language=None, **kwargs):
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
        print(f"[!] Warning: Missing key '{e}' for formatting text '{key}' in lang '{current_language}'")
        result_text = base_text
    except ValueError as e:
        print(f"[!] Warning: Formatting error for text '{key}' in lang '{current_language}': {e}")
        result_text = base_text

    cache_key = cache_key_formatted if kwargs else cache_key_base
    formatted_text_cache[cache_key] = result_text
    return result_text


def set_language(language):
    global DEFAULT_LANGUAGE
    if language in SUPPORTED_LANGUAGES:
        if DEFAULT_LANGUAGE != language:
            DEFAULT_LANGUAGE = language
            formatted_text_cache.clear()
            print(f"Global language set to: {language}")
    else:
        print(f"Warning: Unsupported language '{language}'. Keeping '{DEFAULT_LANGUAGE}'.")
