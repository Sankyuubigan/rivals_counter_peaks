// === КАСТОМНЫЙ ЛОГГЕР ДЛЯ ВКЛАДКИ "ЛОГИ" ===
window.appLogs =[];
const origLog = console.log;
const origWarn = console.warn;
const origError = console.error;

function formatLog(type, args) {
    let msg = `[${new Date().toLocaleTimeString()}] [${type}] ` + Array.from(args).join(' ');
    window.appLogs.push(msg);
    if (window.appLogs.length > 1000) window.appLogs.shift();
}

console.log = function() { formatLog('INFO', arguments); origLog.apply(console, arguments); };
console.warn = function() { formatLog('WARN', arguments); origWarn.apply(console, arguments); };
console.error = function() { formatLog('ERROR', arguments); origError.apply(console, arguments); };

// === ОСНОВНАЯ ЛОГИКА ===
const REQUIRED_FEATURES =['match_info', 'game_info'];

window.marvelLogic = new CounterpickLogic();
window.latestData = {
    map: null,
    enemy_heroes: [],
    ally_heroes:[],
    banned_heroes: [],
    counter_scores: {},
    effective_team:[]
};

let matchState = { rosters: {}, map: null, bannedCharacters:[] };
let isTabHeld = false;

window.marvelLogic.init().then(() => {
    console.log("База данных успешно загружена. Героев:", window.marvelLogic.allHeroes.length);
});

function updateStateFromInfo(info) {
    if (!info || !info.match_info) return false;
    let mi = info.match_info;
    let changed = false;

    if (mi.map !== undefined && matchState.map !== mi.map) {
        matchState.map = mi.map;
        changed = true;
    }

    // ИСПРАВЛЕНИЕ БАГА С БАНАМИ (Защита от null и строк)
    if (mi.banned_characters !== undefined) {
        if (!mi.banned_characters || mi.banned_characters === "null") {
            matchState.bannedCharacters =[];
            changed = true;
        } else {
            try {
                let bannedData = typeof mi.banned_characters === 'string' ? JSON.parse(mi.banned_characters) : mi.banned_characters;
                matchState.bannedCharacters = Array.isArray(bannedData) ? bannedData :[];
                changed = true;
            } catch(e) {
                console.error("Ошибка парсинга банов:", e);
                matchState.bannedCharacters =[];
            }
        }
    }

    for (let key in mi) {
        if (key.startsWith('roster_')) {
            let val = mi[key];
            if (val === null || val === "null" || val === "") {
                if (matchState.rosters[key]) {
                    delete matchState.rosters[key];
                    changed = true;
                }
            } else {
                try {
                    matchState.rosters[key] = typeof val === 'string' ? JSON.parse(val) : val;
                    changed = true;
                } catch(e) {}
            }
        }
    }
    return changed;
}

function processGameData() {
    try {
        if (!window.marvelLogic.isReady) return;

        let enemyHeroes = [], allyHeroes = [], bannedHeroes =[];
        
        for (let key in matchState.rosters) {
            let r = matchState.rosters[key];
            if (r && r.character_name) {
                let normName = window.marvelLogic.normalizeHeroName(r.character_name);
                if (r.is_teammate === false) enemyHeroes.push(normName);
                else if (r.is_teammate === true) allyHeroes.push(normName);
            }
        }
        
        // Жесткая проверка, что баны - это массив
        let safeBanned = Array.isArray(matchState.bannedCharacters) ? matchState.bannedCharacters :[];
        for (let b of safeBanned) {
            if (b && b.character_name) {
                bannedHeroes.push(window.marvelLogic.normalizeHeroName(b.character_name));
            }
        }

        let activeEnemies = enemyHeroes.filter(h => !bannedHeroes.includes(h));
        
        let result;
        // Если врагов нет, показываем Тир-лист
        if (activeEnemies.length === 0) {
            let tierScores = window.marvelLogic.calculateTierListScoresWithMap(matchState.map);
            result = { scores: tierScores, optimalTeam:[] };
        } else {
            result = window.marvelLogic.calculateCounterScoresForTeam(activeEnemies, matchState.map);
        }

        window.latestData = {
            map: matchState.map,
            enemy_heroes: enemyHeroes,
            ally_heroes: allyHeroes,
            banned_heroes: bannedHeroes,
            counter_scores: result.scores,
            effective_team: result.optimalTeam
        };

        // Отправляем данные в трей
        overwolf.windows.sendMessage("in_game", "update_data", window.latestData, () => {});
    } catch (e) {
        console.error("Критическая ошибка в processGameData:", e);
    }
}

// === ХОТКЕИ И ПЕРЕМЕЩЕНИЕ ТРЕЯ ===
overwolf.settings.hotkeys.onHold.addListener((event) => {
    if (event.name === "show_tray") {
        isTabHeld = (event.state === "down");
        if (isTabHeld) {
            overwolf.windows.obtainDeclaredWindow("in_game", (res) => {
                overwolf.windows.restore(res.window.id);
            });
        } else {
            overwolf.windows.obtainDeclaredWindow("in_game", (res) => {
                overwolf.windows.hide(res.window.id);
            });
        }
    }
});

// Перемещение трея стрелочками при зажатом TAB
overwolf.games.inputTracking.onKeyDown.addListener((event) => {
    if (isTabHeld) {
        // 37=Влево, 38=Вверх, 39=Вправо, 40=Вниз
        const step = 50;
        if ([37, 38, 39, 40].includes(event.virtualKeycode)) {
            overwolf.windows.obtainDeclaredWindow("in_game", (res) => {
                let x = res.window.left;
                let y = res.window.top;
                if (event.virtualKeycode === 37) x -= step;
                if (event.virtualKeycode === 38) y -= step;
                if (event.virtualKeycode === 39) x += step;
                if (event.virtualKeycode === 40) y += step;
                overwolf.windows.changePosition(res.window.id, x, y);
            });
        }
    }
});

overwolf.settings.hotkeys.onPressed.addListener((event) => {
    if (event.name === "toggle_desktop") {
        overwolf.windows.obtainDeclaredWindow("desktop", (res) => {
            if (res.window.stateEx === "hidden" || res.window.stateEx === "closed") {
                overwolf.windows.restore(res.window.id);
            } else {
                overwolf.windows.hide(res.window.id);
            }
        });
    }
});

// Запуск
overwolf.games.getRunningGameInfo((gameInfo) => {
    if (gameInfo && gameInfo.isRunning && gameInfo.classId === 24890) {
        console.log("Игра запущена, работаем в фоне.");
    } else {
        overwolf.windows.obtainDeclaredWindow("desktop", (res) => {
            overwolf.windows.restore(res.window.id);
        });
    }
});

overwolf.games.events.setRequiredFeatures(REQUIRED_FEATURES, (result) => {
    if (result.success) {
        overwolf.games.events.onInfoUpdates2.addListener((info) => {
            if (updateStateFromInfo(info.info)) processGameData();
        });
        setInterval(() => {
            overwolf.games.events.getInfo((info) => {
                if (info && info.res && updateStateFromInfo(info.res)) processGameData();
            });
        }, 5000);
    }
});