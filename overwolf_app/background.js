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
const REQUIRED_FEATURES = ['match_info', 'game_info'];

window.marvelLogic = new CounterpickLogic();
window.latestData = {
    map: null,
    enemy_heroes: [],
    ally_heroes: [],
    banned_heroes:[],
    counter_scores: {},
    effective_team:[]
};

let matchState = { rosters: {}, map: null, bannedCharacters:[] };
let isTabHeld = false;
let isOurGameRunning = false;

window.marvelLogic.init().then(() => {
    console.log("База данных успешно загружена. Героев:", window.marvelLogic.allHeroes.length);
    overwolf.games.events.getInfo((info) => {
        if (info && info.res) updateStateFromInfo(info.res);
        processGameData();
    });
});

function updateStateFromInfo(info) {
    if (!info || !info.match_info) return false;
    let mi = info.match_info;
    let changed = false;

    if (mi.map !== undefined && matchState.map !== mi.map) {
        matchState.map = mi.map;
        changed = true;
    }

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

        let enemyHeroes =[], allyHeroes = [], bannedHeroes =[];
        
        for (let key in matchState.rosters) {
            let r = matchState.rosters[key];
            if (r && r.character_name) {
                let normName = window.marvelLogic.normalizeHeroName(r.character_name);
                if (r.is_teammate === false) enemyHeroes.push(normName);
                else if (r.is_teammate === true) allyHeroes.push(normName);
            }
        }
        
        let safeBanned = Array.isArray(matchState.bannedCharacters) ? matchState.bannedCharacters :[];
        for (let b of safeBanned) {
            if (b && b.character_name) {
                bannedHeroes.push(window.marvelLogic.normalizeHeroName(b.character_name));
            }
        }

        // --- ЛОГИКА ОЧИСТКИ ТРЕЯ ВНЕ МАТЧА ---
        let isMatchEmpty = (enemyHeroes.length === 0 && allyHeroes.length === 0);
        
        if (isMatchEmpty) {
            let clearTrayOnEnd = localStorage.getItem('clearTray') === 'true';
            
            if (clearTrayOnEnd) {
                // Полностью очищаем трей, если включена настройка
                window.latestData = {
                    map: null,
                    enemy_heroes: [],
                    ally_heroes: [],
                    banned_heroes: [],
                    counter_scores: {}, // Пустой список внизу
                    effective_team: []
                };
                overwolf.windows.sendMessage("in_game", "update_data", window.latestData, () => {});
            } else {
                // Если настройка выключена - оставляем данные прошлого матча.
                // Исключение: если приложение только запустили и данных еще нет, покажем Тир-лист
                if (Object.keys(window.latestData.counter_scores).length === 0) {
                    let tierScores = window.marvelLogic.calculateTierListScoresWithMap(matchState.map);
                    window.latestData = {
                        map: matchState.map,
                        enemy_heroes: [],
                        ally_heroes: [],
                        banned_heroes: [],
                        counter_scores: tierScores,
                        effective_team: window.marvelLogic.getRecommendedHeroes(tierScores, [])
                    };
                    overwolf.windows.sendMessage("in_game", "update_data", window.latestData, () => {});
                }
            }
            return; // Прерываем дальнейшие расчеты, пока не начнется новый матч
        }
        // ------------------------------------

        let activeEnemies = enemyHeroes.filter(h => !bannedHeroes.includes(h));
        
        let result;
        if (activeEnemies.length === 0) {
            let tierScores = window.marvelLogic.calculateTierListScoresWithMap(matchState.map);
            result = { 
                scores: tierScores, 
                optimalTeam: window.marvelLogic.getRecommendedHeroes(tierScores, allyHeroes) 
            };
        } else {
            result = window.marvelLogic.calculateCounterScoresForTeam(activeEnemies, matchState.map);
            result.optimalTeam = window.marvelLogic.getRecommendedHeroes(result.scores, allyHeroes);
        }

        window.latestData = {
            map: matchState.map,
            enemy_heroes: enemyHeroes,
            ally_heroes: allyHeroes,
            banned_heroes: bannedHeroes,
            counter_scores: result.scores,
            effective_team: result.optimalTeam
        };

        overwolf.windows.sendMessage("in_game", "update_data", window.latestData, () => {});
    } catch (e) {
        console.error("Критическая ошибка в processGameData:", e);
    }
}

// === ХОТКЕИ И ПЕРЕМЕЩЕНИЕ ТРЕЯ ===
let trayMoveInterval = null;
let inGameWindowId = null;
let trayX = 0;
let trayY = 0;

overwolf.settings.hotkeys.onHold.addListener((event) => {
    if (event.name === "show_tray") {
        isTabHeld = (event.state === "down");
        if (isTabHeld) {
            overwolf.windows.obtainDeclaredWindow("in_game", (res) => {
                inGameWindowId = res.window.id;
                trayX = res.window.left;
                trayY = res.window.top;
                overwolf.windows.restore(inGameWindowId, () => {
                    overwolf.windows.sendMessage(inGameWindowId, "update_data", window.latestData, () => {});
                });
            });
        } else {
            if (trayMoveInterval) {
                clearInterval(trayMoveInterval);
                trayMoveInterval = null;
            }
            if (inGameWindowId) overwolf.windows.hide(inGameWindowId);
            else overwolf.windows.obtainDeclaredWindow("in_game", (res) => overwolf.windows.hide(res.window.id));
        }
        return;
    }

    const moveMap = {
        "move_tray_left":  { dx: -20, dy: 0 },
        "move_tray_up":    { dx: 0, dy: -20 },
        "move_tray_right": { dx: 20, dy: 0 },
        "move_tray_down":  { dx: 0, dy: 20 },
    };

    const move = moveMap[event.name];
    if (!move) return;
    if (!isTabHeld) return;

    if (event.state === "down") {
        if (trayMoveInterval) clearInterval(trayMoveInterval);
        trayMoveInterval = setInterval(() => {
            if (inGameWindowId !== null) {
                trayX += move.dx;
                trayY += move.dy;
                overwolf.windows.changePosition(inGameWindowId, trayX, trayY);
            }
        }, 50);
    } else if (event.state === "up") {
        if (trayMoveInterval) {
            clearInterval(trayMoveInterval);
            trayMoveInterval = null;
        }
    }
});

// Управление окном Desktop
overwolf.settings.hotkeys.onPressed.addListener((event) => {
    if (event.name === "toggle_desktop") {
        let targetWindowName = isOurGameRunning ? "desktop_in_game" : "desktop";
        console.log(`[HOTKEY] Вызван ${event.name}. Целевое окно: ${targetWindowName}`);

        overwolf.windows.obtainDeclaredWindow(targetWindowName, (res) => {
            if (!res || !res.window) return;
            let winId = res.window.id;
            let state = res.window.stateEx;

            // Если окно скрыто - восстанавливаем и забираем мышку
            if (state === "hidden" || state === "closed" || state === "minimized") {
                console.log(`[UI] Открываем ${targetWindowName}...`);
                overwolf.windows.restore(winId, () => {
                    overwolf.windows.bringToFront(winId, true, () => {
                        console.log(`[FOCUS] Мышь перехвачена.`);
                    });
                });
            } else {
                // Если окно уже отображается - скрываем его (мышь автоматически вернется в игру)
                console.log(`[UI] Скрываем ${targetWindowName}...`);
                overwolf.windows.hide(winId);
            }
        });
    }
});

// Слушаем старт и закрытие игры для закрытия неактуальных окон
overwolf.games.onGameInfoUpdated.addListener((event) => {
    if (event && event.runningChanged) {
        let gameRunning = event.gameInfo && event.gameInfo.isRunning;
        let classId = event.gameInfo ? event.gameInfo.classId : 0;
        
        if (gameRunning && classId === 24890) {
            isOurGameRunning = true;
            console.log("[GAME] Игра запущена. Прячем десктопное окно.");
            overwolf.windows.obtainDeclaredWindow("desktop", (res) => {
                if (res && res.window && res.window.stateEx !== "hidden" && res.window.stateEx !== "closed") {
                    overwolf.windows.hide(res.window.id);
                }
            });
        } else if (!gameRunning && isOurGameRunning) {
            isOurGameRunning = false;
            console.log("[GAME] Игра закрыта. Прячем in-game окно.");
            overwolf.windows.obtainDeclaredWindow("desktop_in_game", (res) => {
                if (res && res.window && res.window.stateEx !== "hidden" && res.window.stateEx !== "closed") {
                    overwolf.windows.hide(res.window.id);
                }
            });
        }
    }
});

// Запуск
overwolf.games.getRunningGameInfo((gameInfo) => {
    if (gameInfo && gameInfo.isRunning && gameInfo.classId === 24890) {
        isOurGameRunning = true;
        console.log("При старте приложения игра уже запущена.");
    } else {
        isOurGameRunning = false;
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