import locale

# Определяем язык по умолчанию на основе системы
DEFAULT_LANGUAGE = locale.getdefaultlocale()[0] if locale.getdefaultlocale()[0] else 'ru_RU'
SUPPORTED_LANGUAGES = {'ru_RU': 'Русский', 'en_US': 'English'}

# Словари переводов
TRANSLATIONS = {
    'ru_RU': {
        'title': 'Подбор контрпиков',
        'select_heroes': 'Выберите героев, чтобы увидеть контрпики.',
        'no_heroes_selected': 'Выберите героев вражеской команды, чтобы увидеть контрпики.',
        'selected': 'Выбрано: ',
        'copy_rating': 'Копировать рейтинг',
        'clear_all': 'Очистить всё',
        'about_author': 'Об авторе',
        'author_info': 'Автор: Nilden\nВерсия: 1.01',
        'language': 'Язык',
        'strong_player': 'сильный игрок',
        'version': 'Версия: 1.01',
        'counterpick_rating': 'Рейтинг контрпиков для выбранной вражеской команды:',
        'points': 'балл(ов)',
    },
    'en_US': {
        'title': 'Counterpick Selection',
        'select_heroes': 'Select heroes to see counterpicks.',
        'no_heroes_selected': 'Select enemy team heroes to see counterpicks.',
        'selected': 'Selected: ',
        'copy_rating': 'Copy Rating',
        'clear_all': 'Clear All',
        'about_author': 'About Author',
        'author_info': 'Author: Nilden\nVersion: 1.01',
        'language': 'Language',
        'strong_player': 'strong player',
        'version': 'Version: 1.01',
        'counterpick_rating': 'Counterpick rating for a given enemy team\'s lineup:',
        'points': 'points',
    }
}

# Функция для получения текущего текста
def get_text(key, language=None):
    current_language = language if language else DEFAULT_LANGUAGE
    return TRANSLATIONS.get(current_language, TRANSLATIONS['ru_RU']).get(key, key)

# Функция переключения языка
def set_language(language):
    global DEFAULT_LANGUAGE
    DEFAULT_LANGUAGE = language