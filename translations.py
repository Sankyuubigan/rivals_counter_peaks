import locale

DEFAULT_LANGUAGE = locale.getdefaultlocale()[0] if locale.getdefaultlocale()[0] else 'ru_RU'
SUPPORTED_LANGUAGES = {'ru_RU': 'Русский', 'en_US': 'English'}

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
        'hero_rating': 'Рейтинг героев',
        'hero_rating_title': 'Рейтинг наименее контрящихся персонажей',
        'donate_info': 'Купить мне кофе (помощь и благодарность за софт):\n'
                       'Тинькофф: 2200 7007 5813 1881\n'
                       'Ссылка для донатов из-за рубежа:\n'
                       'https://www.donationalerts.com/r/nildencorp\n\n'
                       'C идеями и предложениями можете обращаться:\n'
                       'https://t.me/dron_maredon'
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
        'hero_rating': 'Hero Rating',
        'hero_rating_title': 'Rating of Least Countered Characters',
        'donate_info': 'Buy me a coffee (support and thanks for the software):\n'
                       'Tinkoff: 2200 7007 5813 1881\n'
                       'Link for donations from abroad:\n'
                       'https://www.donationalerts.com/r/nildencorp\n\n'
                       'C идеями и предложениями можете обращаться:\n'
                       'https://t.me/dron_maredon'
    }
}

def get_text(key, language=None):
    current_language = language if language else DEFAULT_LANGUAGE
    return TRANSLATIONS.get(current_language, TRANSLATIONS['ru_RU']).get(key, key)

def set_language(language):
    global DEFAULT_LANGUAGE
    DEFAULT_LANGUAGE = language