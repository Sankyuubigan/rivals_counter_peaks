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
        "setting_language": "Язык / Language",
        "refresh_logs": "Обновить логи",
        "copy_logs": "Копировать логи",
        "logs_copied": "Логи скопированы!",
        "about_title": "О программе",
        "about_text": "Rivals Counter Peaks — это оверлей для Marvel Rivals, который помогает подбирать контрпики в реальном времени.",
        "author_title": "Об авторе",
        "author_text": "Создано Sankyuubigan.",
        "points": "очков",
        "tray_allies": "Союзники",
        "tray_enemies": "Враги",
        "tray_waiting": "Ожидание матча..."
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
        "setting_language": "Language / Язык",
        "refresh_logs": "Refresh Logs",
        "copy_logs": "Copy Logs",
        "logs_copied": "Logs copied!",
        "about_title": "About Program",
        "about_text": "Rivals Counter Peaks is an overlay for Marvel Rivals that helps you pick counter heroes in real-time.",
        "author_title": "About Author",
        "author_text": "Created by Sankyuubigan.",
        "points": "points",
        "tray_allies": "Allies",
        "tray_enemies": "Enemies",
        "tray_waiting": "Waiting for match..."
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
        el.innerText = getTranslation(key);
    });
}