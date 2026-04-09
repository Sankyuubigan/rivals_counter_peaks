const TRANSLATIONS = {
    "ru": {
        "tab_counterpicks": "Контрпики",
        "tab_tier_list": "Тир-лист",
        "tab_favorites": "Избранные герои",
        "tab_settings": "Настройки",
        "tab_logs": "Логи",
        "tab_about": "О программе",
        "tab_author": "Об авторе",
        "header_title": "Rivals Counter Picks (Alt+G скрыть/показать)",
        "select_enemies": "Выберите врагов справа",
        "no_map": "Без карты",
        "total_heroes": "Всего героев в базе: {count}",
        "selected_heroes": "Выбрано героев ({count}/6): {heroes}",
        "clear_all": "Очистить все",
        "tier_list_hint": "Мета героев для высоких рангов. Показывает, кто лучше всего контрит других.",
        "favorites_title": "Избранные герои",
        "favorites_hint": "Выберите героев, за которых вы любите играть. Они будут отображаться первыми в трее.",
        "settings_tray": "Настройки внутриигрового трея (TAB)",
        "setting_hide_allies": "Не показывать союзных героев в списке контрпиков",
        "setting_show_rating": "Показывать числовой рейтинг на иконках",
        "setting_priority_first": "Сначала приоритетные роли (!)",
        "setting_favorites_first": "Сначала избранные герои",
        "setting_clear_tray": "Очищать трей после конца матча",
        "setting_language": "Язык / Language",
        "refresh_logs": "Обновить логи",
        "about_title": "О программе",
        "about_text": "Добро пожаловать в Rivals Counter Picks!\n\nЭто оверлей для Marvel Rivals, который помогает подбирать контрпики в реальном времени.\n\n🎮 Как использовать в игре:\n• Удерживайте TAB, чтобы показать внутриигровой трей с рекомендациями.\n• Чтобы переместить трей, удерживайте TAB и нажимайте Стрелки (Влево/Вправо/Вверх/Вниз).\n• Нажмите Alt+G, чтобы открыть/скрыть это главное окно с настройками в любой момент.\n\nОверлей автоматически считывает вражескую команду и карту, чтобы предложить лучших героев для победы!",
        "author_title": "Об авторе",
        "author_text": "Создано Sankyuubigan.",
        "points": "очков",
        "tray_allies": "Союзники",
        "tray_enemies": "Враги",
        "tray_waiting": "Ожидание матча...",
        "map_not_found": "Карта не найдена"
    },
    "en": {
        "tab_counterpicks": "Counter Picks",
        "tab_tier_list": "Tier List",
        "tab_favorites": "Favorite Heroes",
        "tab_settings": "Settings",
        "tab_logs": "Logs",
        "tab_about": "About",
        "tab_author": "About Author",
        "header_title": "Rivals Counter Picks (Alt+G to show/hide)",
        "select_enemies": "Select enemies on the right",
        "no_map": "No map",
        "total_heroes": "Total heroes in database: {count}",
        "selected_heroes": "Selected heroes ({count}/6): {heroes}",
        "clear_all": "Clear All",
        "tier_list_hint": "Hero meta for high ranks. Shows who counters others best.",
        "favorites_title": "Favorite Heroes",
        "favorites_hint": "Select heroes you like to play. They will be shown first in the tray.",
        "settings_tray": "In-Game Tray Settings (TAB)",
        "setting_hide_allies": "Do not show ally heroes in the counter picks list",
        "setting_show_rating": "Show numerical rating on icons",
        "setting_priority_first": "Priority roles first (!)",
        "setting_favorites_first": "Favorite heroes first",
        "setting_clear_tray": "Clear tray after match ends",
        "setting_language": "Language / Язык",
        "refresh_logs": "Refresh Logs",
        "about_title": "About Program",
        "about_text": "Welcome to Rivals Counter Picks!\n\nThis is an overlay for Marvel Rivals that helps you pick counter heroes in real-time.\n\n🎮 How to use in-game:\n• Hold TAB to show the in-game tray with recommendations.\n• To move the tray, hold TAB and press the Arrow Keys (Left/Right/Up/Down).\n• Press Alt+G to show/hide this main window with settings at any time.\n\nThe overlay automatically reads the enemy team and map to suggest the best heroes for victory!",
        "author_title": "About Author",
        "author_text": "Created by Sankyuubigan.",
        "points": "points",
        "tray_allies": "Allies",
        "tray_enemies": "Enemies",
        "tray_waiting": "Waiting for match...",
        "map_not_found": "Map not found"
    }
};

function getTranslation(key, params = {}) {
    let lang = localStorage.getItem('language') || 'ru';
    let text = TRANSLATIONS[lang] && TRANSLATIONS[lang][key] ? TRANSLATIONS[lang][key] : (TRANSLATIONS['ru'][key] || key);
    for (let p in params) {
        text = text.replace(`{${p}}`, params[p]);
    }
    return text;
}

function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        let key = el.getAttribute('data-i18n');
        // Заменяем переносы строк на <br> для корректного отображения в HTML
        el.innerHTML = getTranslation(key).replace(/\n/g, '<br>');
    });
}