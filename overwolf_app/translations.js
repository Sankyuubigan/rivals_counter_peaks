const TRANSLATIONS = {
    "ru": {
        "tab_counterpicks": "Контрпики",
        "tab_tier_list": "Тир-лист",
        "tab_favorites": "Избранные тимапы",
        "tab_settings": "Настройки",
        "tab_logs": "Логи",
        "tab_about": "О программе",
        "header_title": "Rivals Counter Picks (Alt+G скрыть/показать)",
        "select_enemies": "Выберите врагов справа",
        "no_map": "Без карты",
        "total_heroes": "Всего героев в базе: {count}",
        "selected_heroes": "Выбрано героев ({count}/6): {heroes}",
        "clear_all": "Очистить все",
        "tier_list_hint": "Мета героев для высоких рангов. Показывает, кто лучше всего контрит других.",
        "favorites_title": "Избранные тимапы",
        "favorites_hint": "Выберите тимапы, которые вы хотите видеть в трее. Кликните по маленькой иконке союзника, чтобы добавить тимап в избранное.",
        "settings_tray": "Настройки внутриигрового трея (TAB)",
        "setting_hide_allies": "Не показывать союзных героев в списке контрпиков",
        "setting_show_rating": "Показывать числовой рейтинг на иконках",
        "setting_priority_first": "Сначала приоритетные роли (!)",
        "setting_favorites_first": "Сначала избранные тимапы",
        "setting_fav_bonus": "Бонус избранного тимапа:",
        "points_short": "очк.",
        "setting_clear_tray": "Очищать трей после конца матча",
        "setting_language": "Язык / Language",
        "refresh_logs": "Обновить логи",
        "points": "очков",
        "tray_allies": "Союзники",
        "tray_enemies": "Враги",
        "tray_waiting": "Ожидание матча...",
        "map_not_found": "Карта не найдена",
        "notif_show_hide": "Показать/Скрыть",
        "db_update_title": "Обновление базы данных (Мета)",
        "db_check_github": "Проверить папку на GitHub",
        "db_status_active": "Активна",
        "db_status_downloaded": "Установлена",
        "db_status_available": "Доступна для скачивания",
        "db_btn_activate": "Активировать",
        "db_btn_download": "Скачать",
        "db_btn_delete": "Удалить",
        "overwolf_checking": "Проверка подключения к Overwolf...",
        "overwolf_connected": "Overwolf: подключен",
        "overwolf_disconnected": "Overwolf: отключен",
        "role_vanguard": "Авангарды",
        "role_duelist": "Дуэлисты",
        "role_strategist": "Стратегисты",
        "role_other": "Прочие ({count})"
    },
    "en": {
        "tab_counterpicks": "Counter Picks",
        "tab_tier_list": "Tier List",
        "tab_favorites": "Favorite Team-ups",
        "tab_settings": "Settings",
        "tab_logs": "Logs",
        "tab_about": "About",
        "header_title": "Rivals Counter Picks (Alt+G to show/hide)",
        "select_enemies": "Select enemies on the right",
        "no_map": "No map",
        "total_heroes": "Total heroes in database: {count}",
        "selected_heroes": "Selected heroes ({count}/6): {heroes}",
        "clear_all": "Clear All",
        "tier_list_hint": "Hero meta for high ranks. Shows who counters others best.",
        "favorites_title": "Favorite Team-ups",
        "favorites_hint": "Select team-ups you want to see in the tray. Click the small ally icon to add a team-up to favorites.",
        "settings_tray": "In-Game Tray Settings (TAB)",
        "setting_hide_allies": "Do not show ally heroes in the counter picks list",
        "setting_show_rating": "Show numerical rating on icons",
        "setting_priority_first": "Priority roles first (!)",
        "setting_favorites_first": "Favorite team-ups first",
        "setting_fav_bonus": "Favorite team-up bonus:",
        "points_short": "pts.",
        "setting_clear_tray": "Clear tray after match ends",
        "setting_language": "Language / Язык",
        "refresh_logs": "Refresh Logs",
        "points": "points",
        "tray_allies": "Allies",
        "tray_enemies": "Enemies",
        "tray_waiting": "Waiting for match...",
        "map_not_found": "Map not found",
        "notif_show_hide": "Show/Hide App",
        "db_update_title": "Database Update (Meta)",
        "db_check_github": "Check Folder on GitHub",
        "db_status_active": "Active",
        "db_status_downloaded": "Installed",
        "db_status_available": "Available for Download",
        "db_btn_activate": "Activate",
        "db_btn_download": "Download",
        "db_btn_delete": "Delete",
        "overwolf_checking": "Checking Overwolf connection...",
        "overwolf_connected": "Overwolf: connected",
        "overwolf_disconnected": "Overwolf: disconnected",
        "role_vanguard": "Vanguards",
        "role_duelist": "Duelists",
        "role_strategist": "Strategists",
        "role_other": "Other ({count})"
    }
};

function getTranslation(key, params = {}) {
    let lang = localStorage.getItem('language') || 'en';
    let text = TRANSLATIONS[lang] && TRANSLATIONS[lang][key] ? TRANSLATIONS[lang][key] : (TRANSLATIONS['en'][key] || key);
    for (let p in params) {
        text = text.replace(`{${p}}`, params[p]);
    }
    return text;
}

function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        let key = el.getAttribute('data-i18n');
        el.innerHTML = getTranslation(key).replace(/\n/g, '<br>');
    });
}