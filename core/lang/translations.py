# File: core/lang/translations.py
import logging 

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
        'selected_heroes_label_format': '{selected_text} ({count}/{max_team_size}): {heroes_list}', 
        'none_selected_placeholder': 'нет выбранных', 
        'copy_rating': 'Копировать состав',
        'clear_all': 'Очистить всё',
        'about_program': 'О программе',
        'author_info_title': 'Об авторе', 
        'author_menu_item_text': 'Об авторе', 
        'language': 'Язык',
        'strong_player': 'сильный игрок',
        'version': 'Версия: {version}',
        'counterpick_rating': 'Рейтинг контрпиков для вражеской команды:',
        'points': 'балл(ов)',
        'hero_rating': 'Универсальные герои', 
        'hero_rating_title': 'Рейтинг универсальных героев', 
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
        'tray_mode_on': 'Трей: Вкл', 
        'tray_mode_off': 'Трей: Выкл', 
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
        'no_recommendations': 'Нет подходящих контрпиков', 
        'select_enemies_for_recommendations': 'Выберите врагов для отображения рекомендаций', 
        'recognition_error_prefix': 'Ошибка распознавания:',
        'recognition_no_screenshot': 'Не удалось сделать скриншот.',
        'recognition_no_templates': 'Шаблоны героев не загружены.',
        'recognition_failed': 'Не удалось распознать героев на скриншоте.',
        'screenshot_saved': 'Скриншот сохранен: {filepath}',
        'screenshot_save_failed': 'Не удалось сохранить скриншот: {error}',
        'menu': 'Меню',
        'hotkeys_menu_item': 'Горячие клавиши (Инфо)', 
        'hotkey_settings_menu_item': 'Настройки', 
        'logs_menu_item': 'Логи',
        'logs_window_title': 'Логи приложения',
        'copy_all_logs_button': 'Копировать все логи',
        'clear_log_window_button': 'Очистить окно',
        'log_copy_no_logs': 'Нет логов для копирования.',
        'log_copy_success': 'Логи скопированы в буфер обмена.',
        'log_copy_error': 'Ошибка копирования логов',
        'save_logs_to_file_button': "Сохранить логи в файл", 
        'log_save_no_logs': "Нет логов для сохранения.", 
        'log_save_dialog_title': "Сохранить логи как...", 
        'log_save_success': "Логи успешно сохранены в:\n{filepath}", 
        'log_save_error_detailed': "Не удалось сохранить логи в файл:\n{filepath}\n\nОшибка: {error_message}", 
        'hotkeys_window_title': 'Горячие клавиши', 
        'hotkey_settings_window_title': 'Настройка горячих клавиш', 
        'hotkeys_section_main': 'Основные действия:', 
        'hotkeys_section_interaction_title': 'Взаимодействие с интерфейсом:',
        'hotkeys_section_window_title': 'Управление окном:', 
        'hotkey_desc_navigation_up': 'Навигация: Вверх',
        'hotkey_desc_navigation_down': 'Навигация: Вниз',
        'hotkey_desc_navigation_left': 'Навигация: Влево',
        'hotkey_desc_navigation_right': 'Навигация: Вправо',
        'hotkey_desc_select': 'Выбор/снятие героя',
        'hotkey_desc_toggle_mode': 'Переключить режим окна',
        'hotkey_desc_recognize': 'Распознать героев',
        'hotkey_desc_clear': 'Очистить выбор врагов',
        'hotkey_desc_copy_team': 'Копировать состав',
        'hotkey_desc_toggle_tray': 'Режим "Трей" (Поверх + Игнор. мыши)',
        'hotkey_desc_debug_screenshot': 'Тестовый скриншот',
        'hotkey_desc_decrease_opacity': 'Уменьшить непрозрачность окна', 
        'hotkey_desc_increase_opacity': 'Увеличить непрозрачность окна', 
        'hotkey_desc_lmb': 'ЛКМ по герою',
        'hotkey_desc_lmb_select': 'Выбрать/Снять выбор',
        'hotkey_desc_rmb': 'ПКМ по герою',
        'hotkey_desc_rmb_priority': 'Меню приоритета',
        'hotkey_desc_drag': 'Перетаскивание окна',
        'hotkey_desc_drag_window': 'За верхнюю панель (Компактный режим)',
        'hotkey_desc_slider': 'Слайдер прозрачности',
        'hotkey_desc_slider_transparency': 'В левом верхнем углу',
        'hotkey_settings_change_btn': 'Изменить',
        'hotkey_settings_press_keys': 'Нажмите клавиши...', 
        'hotkey_settings_press_new_hotkey_for': 'Нажмите новую комбинацию для "{action}"',
        'hotkey_settings_capture_title': 'Ввод нового хоткея',
        'hotkey_settings_save': 'Сохранить', 
        'hotkey_settings_cancel': 'Отмена',
        'hotkey_settings_reset_defaults': 'Сбросить по умолчанию',
        'hotkey_settings_cancel_capture': 'Отменить ввод',
        'hotkey_not_set': 'Не назначен',
        'hotkey_none': 'Нет', 
        'hotkey_settings_defaults_reset_title': 'Сброс настроек', 
        'hotkey_settings_defaults_reset_msg': 'Настройки хоткеев сброшены к стандартным значениям.', 
        'hotkey_settings_duplicate_title': 'Дублирующиеся хоткеи',
        'hotkey_settings_duplicate_message': 'Обнаружены дублирующиеся горячие клавиши. Пожалуйста, исправьте:',
        'theme_menu_title': "Тема",
        'light_theme_action': "Светлая",
        'dark_theme_action': "Темная",
        'sw_general_tab_title': "Общие",
        'sw_hotkeys_tab_title': "Горячие клавиши",
        'sw_screenshots_tab_title': "Скриншоты", 
        'sw_save_less_than_6_label': "Сохранять скриншоты экрана, если распознано < 6 героев",
        'sw_save_path_label': "Папка для сохранения скриншотов:",
        'sw_default_path_text': "По умолчанию (рядом с программой)",
        'sw_default_path_tooltip': "Скриншоты будут сохраняться в папку, откуда запущена программа",
        'sw_browse_button_text': "Обзор...",
        'sw_select_dir_dialog_title': "Выберите папку для сохранения скриншотов",
        'sw_all_settings_reset_msg': "Все настройки сброшены к значениям по умолчанию.",
        'sw_apply_button': "Применить",
        'sw_settings_applied_title': "Настройки применены",
        'sw_settings_applied_msg': "Изменения успешно применены.",
        'sw_for_action_text': "для",
        'sw_and_text': "и",
        'version_tooltip_prefix': "Версия приложения", 
        'recognize_button_text': "Распознать", 
        'recognize_button_tooltip': "Распознать героев", 
        'recognition_models_loading_tooltip': "Модели распознавания загружаются...", 
        'recognition_models_not_ready': "Модели распознавания еще не загружены. Пожалуйста, подождите.", 
        'recognition_models_not_ready_tooltip': "Модели распознавания не готовы.", 
        'close_button_tooltip': "Закрыть приложение", 

    },
    'en_US': {
        'title': 'Counterpick Selection',
        'select_heroes': 'Select heroes to see counterpicks.',
        'no_heroes_selected': 'Select enemy team heroes.',
        'selected': 'Selected',
        'selected_none': 'Selected (0/{max_team_size})',
        'selected_some': 'Selected',
        'selected_heroes_label_format': '{selected_text} ({count}/{max_team_size}): {heroes_list}',
        'none_selected_placeholder': 'none selected',
        'copy_rating': 'Copy Team',
        'clear_all': 'Clear All',
        'about_program': 'About Program',
        'author_info_title': 'About Author', 
        'author_menu_item_text': 'About Author', 
        'language': 'Language',
        'strong_player': 'strong player',
        'version': 'Version: {version}',
        'counterpick_rating': 'Counterpick rating for the enemy team:',
        'points': 'points',
        'hero_rating': 'Universal Heroes', 
        'hero_rating_title': 'Universal Heroes Rating', 
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
        'no_recommendations': 'No suitable counterpicks',
        'select_enemies_for_recommendations': 'Select enemies to display recommendations',
        'recognition_error_prefix': 'Recognition Error:',
        'recognition_no_screenshot': 'Failed to capture screenshot.',
        'recognition_no_templates': 'Hero templates not loaded.',
        'recognition_failed': 'Could not recognize heroes in the screenshot.',
        'screenshot_saved': 'Screenshot saved: {filepath}',
        'screenshot_save_failed': 'Failed to save screenshot: {error}',
        'menu': 'Menu',
        'hotkeys_menu_item': 'Hotkeys (Info)',
        'hotkey_settings_menu_item': 'Settings', 
        'logs_menu_item': 'Logs',
        'logs_window_title': 'Application Logs',
        'copy_all_logs_button': 'Copy All Logs',
        'clear_log_window_button': 'Clear Window',
        'log_copy_no_logs': 'No logs to copy.',
        'log_copy_success': 'Logs copied to clipboard.',
        'log_copy_error': 'Error copying logs',
        'save_logs_to_file_button': "Save Logs to File", 
        'log_save_no_logs': "No logs to save.", 
        'log_save_dialog_title': "Save Logs As...", 
        'log_save_success': "Logs successfully saved to:\n{filepath}", 
        'log_save_error_detailed': "Could not save logs to file:\n{filepath}\n\nError: {error_message}", 
        'hotkeys_window_title': 'Hotkeys',
        'hotkey_settings_window_title': 'Hotkey Configuration',
        'hotkeys_section_main': 'Main Actions:',
        'hotkeys_section_interaction_title': 'Interface Interaction:',
        'hotkeys_section_window_title': 'Window Management:', 
        'hotkey_desc_navigation_up': 'Navigate: Up',
        'hotkey_desc_navigation_down': 'Navigate: Down',
        'hotkey_desc_navigation_left': 'Navigate: Left',
        'hotkey_desc_navigation_right': 'Navigate: Right',
        'hotkey_desc_select': 'Select/Deselect hero',
        'hotkey_desc_toggle_mode': 'Toggle window mode',
        'hotkey_desc_recognize': 'Recognize heroes',
        'hotkey_desc_clear': 'Clear enemy selection',
        'hotkey_desc_copy_team': 'Copy team composition',
        'hotkey_desc_toggle_tray': '"Tray" Mode (Always on Top + Mouse Ignore)',
        'hotkey_desc_debug_screenshot': 'Test screenshot',
        'hotkey_desc_decrease_opacity': 'Decrease window opacity', 
        'hotkey_desc_increase_opacity': 'Increase window opacity', 
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
        'hotkey_settings_defaults_reset_title': 'Reset Settings',
        'hotkey_settings_defaults_reset_msg': 'Hotkey settings have been reset to their default values.',
        'hotkey_settings_duplicate_title': 'Duplicate Hotkeys',
        'hotkey_settings_duplicate_message': 'Duplicate hotkeys found. Please correct them:',
        'theme_menu_title': "Theme",
        'light_theme_action': "Light",
        'dark_theme_action': "Dark",
        'sw_general_tab_title': "General",
        'sw_hotkeys_tab_title': "Hotkeys",
        'sw_screenshots_tab_title': "Screenshots",
        'sw_save_less_than_6_label': "Save screenshots if < 6 heroes are recognized",
        'sw_save_path_label': "Folder to save screenshots:",
        'sw_default_path_text': "Default (next to the program)",
        'sw_default_path_tooltip': "Screenshots will be saved in the program's launch directory",
        'sw_browse_button_text': "Browse...",
        'sw_select_dir_dialog_title': "Select folder to save screenshots",
        'sw_all_settings_reset_msg': "All settings have been reset to their default values.",
        'sw_apply_button': "Apply",
        'sw_settings_applied_title': "Settings Applied",
        'sw_settings_applied_msg': "Changes have been applied successfully.",
        'sw_for_action_text': "for",
        'sw_and_text': "and",
        'version_tooltip_prefix': "Application version",
        'recognize_button_text': "Recognize",
        'recognize_button_tooltip': "Recognize heroes",
        'recognition_models_loading_tooltip': "Recognition models are loading...",
        'recognition_models_not_ready': "Recognition models are not loaded yet. Please wait.",
        'recognition_models_not_ready_tooltip': "Recognition models are not ready.",
        'close_button_tooltip': "Close application",
    }
}

formatted_text_cache = {}
_current_lang_internal = DEFAULT_LANGUAGE


def _get_translation_table(language_code):
    return TRANSLATIONS.get(language_code, TRANSLATIONS[DEFAULT_LANGUAGE]) 


def _validate_key(key, translations_for_lang, default_text, language_code_for_fallback_search):
    base_text = translations_for_lang.get(key)
    if base_text is None:
        if language_code_for_fallback_search != 'en_US': 
            en_translations = TRANSLATIONS.get('en_US', {})
            base_text = en_translations.get(key)
        
        if base_text is None: 
             if default_text is None:
                 # Только логируем, не выбрасываем исключение
                 logging.warning(f"[Translations] Key '{key}' not found in translations for '{language_code_for_fallback_search}' or 'en_US', and no default_text provided.")
             # Возвращаем либо default_text, либо специальную строку, указывающую на отсутствующий ключ
             base_text = default_text if default_text is not None else f"_{key}_" 
    return base_text


def get_text(key, default_text=None, language=None, **kwargs):
    # Определяем язык для использования
    resolved_language = language if language else _current_lang_internal
    
    # Создаем ключ для кэша
    cache_key_base = (resolved_language, key)
    # Для форматированных строк включаем kwargs в ключ, отсортировав их для консистентности
    cache_key_formatted_tuple = tuple(sorted(kwargs.items())) if kwargs else tuple()
    cache_key_formatted = (resolved_language, key, cache_key_formatted_tuple)

    # Проверяем кэш
    if kwargs and cache_key_formatted in formatted_text_cache:
        return formatted_text_cache[cache_key_formatted]
    if not kwargs and cache_key_base in formatted_text_cache: # Если нет kwargs, используем базовый ключ
        return formatted_text_cache[cache_key_base]

    # Получаем таблицу переводов для выбранного языка
    translations_for_lang = _get_translation_table(resolved_language)
    # Получаем базовый текст, обрабатывая отсутствующие ключи
    base_text = _validate_key(key, translations_for_lang, default_text, resolved_language)

    result_text = base_text # По умолчанию результат - это базовый текст
    if kwargs: # Если есть аргументы для форматирования
        try:
            result_text = base_text.format(**kwargs)
        except KeyError as e: # Обработка ошибки, если ключ для форматирования отсутствует
            logging.warning(f"[Translations] Missing key '{e}' for formatting text_id '{key}' in lang '{resolved_language}'. Base text: '{base_text}'") 
            # Можно вернуть base_text как есть или специальную строку ошибки
        except ValueError as e: # Обработка других ошибок форматирования
            logging.warning(f"[Translations] Formatting ValueError for text_id '{key}' in lang '{resolved_language}': {e}. Base text: '{base_text}'")

    # Кэшируем результат
    cache_to_use_key = cache_key_formatted if kwargs else cache_key_base
    formatted_text_cache[cache_to_use_key] = result_text
    return result_text


def set_language(language_code):
    global _current_lang_internal # Указываем, что работаем с глобальной переменной
    if language_code in SUPPORTED_LANGUAGES:
        if _current_lang_internal != language_code: # Обновляем, только если язык действительно изменился
            _current_lang_internal = language_code
            formatted_text_cache.clear() # Очищаем кэш при смене языка
            logging.info(f"Global language set to: {language_code}. Translation cache cleared.")
    else:
        logging.warning(f"Warning: Unsupported language '{language_code}'. Keeping '{_current_lang_internal}'.")

# Устанавливаем язык по умолчанию при первом импорте модуля
set_language(DEFAULT_LANGUAGE)