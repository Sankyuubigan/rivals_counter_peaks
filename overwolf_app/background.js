// === КАСТОМНЫЙ ЛОГГЕР ДЛЯ ВКЛАДКИ "ЛОГИ" ===
window.appLogs =[];
const origLog = console.log;
const origWarn = console.warn;
const origError = console.error;

function formatLog(type, args) {
    let parsedArgs = Array.from(args).map(arg => {
        if (typeof arg === 'object') {
            try {
                return JSON.stringify(arg);
            } catch(e) {
                return String(arg);
            }
        }
        return String(arg);
    });
    let msg = `[${new Date().toLocaleTimeString()}] [${type}] ` + parsedArgs.join(' ');
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
    is_map_effective: false,
    enemy_heroes: [],
    ally_heroes: [],
    banned_heroes:[],
    counter_scores: {},
    effective_team:[]
};

let matchState = { 
    rosters: {}, 
    map: null, 
    bannedCharacters:[],
    lastRawBans: null,
    lastProcessedBans: null
};
let isTabHeld = false;
let isOurGameRunning = false;

window.marvelLogic.init().then(() => {
    console.log("База данных успешно загружена. Героев:", window.marvelLogic.allHeroes.length);
    overwolf.games.events.getInfo((info) => {
        if (info && info.res) updateStateFromInfo(info.res);
        processGameData();
    });
});

// Непробиваемый парсер для банов
function parseBannedCharacters(rawBans) {
    if (rawBans === undefined || rawBans === null || rawBans === "" || rawBans === "null" || rawBans === "[]") {
        return[];
    }
    
    let parsed = rawBans;
    let attempts = 0;
    
    // Пытаемся распарсить, если Overwolf прислал JSON внутри JSON'а
    while (typeof parsed === 'string' && attempts < 3) {
        try {
            let tmp = JSON.parse(parsed);
            if (typeof tmp === 'string' || typeof tmp === 'object') {
                parsed = tmp;
            } else {
                break;
            }
        } catch(e) {
            break;
        }
        attempts++;
    }

    if (Array.isArray(parsed)) {
        return parsed;
    } else if (typeof parsed === 'object' && parsed !== null) {
        // Если прислали один объект вместо массива
        if (parsed.character_id || parsed.character_name) {
            return [parsed];
        }
        return Object.values(parsed);
    } else if (typeof parsed === 'string') {
        // Если прислали просто строку через запятую
        return parsed.split(',').map(s => s.trim()).filter(s => s);
    }
    
    return[];
}

function updateStateFromInfo(info) {
    if (!info || !info.match_info) return false;
    
    let mi = info.match_info;
    let changed = false;

    if (mi.map !== undefined && matchState.map !== mi.map) {
        matchState.map = mi.map;
        changed = true;
        if (mi.map === null || mi.map === "null" || mi.map === "") {
            matchState.rosters = {};
            matchState.bannedCharacters =[];
            matchState.lastProcessedBans = null;
            console.log("[MATCH_STATE] Карта сброшена, очищаем ростеры и баны.");
        }
    }

    if (mi.hasOwnProperty('banned_characters')) {
        let rawBans = mi.banned_characters;
        
        // Логируем сырые данные только если они изменились, чтобы не спамить каждые 5 сек
        if (matchState.lastRawBans !== JSON.stringify(rawBans)) {
            console.log("[RAW_BANS] Изменение сырых данных banned_characters:", rawBans);
            matchState.lastRawBans = JSON.stringify(rawBans);
        }

        let parsed = parseBannedCharacters(rawBans);
        let newBansStr = JSON.stringify(parsed);
        let oldBansStr = JSON.stringify(matchState.bannedCharacters);
        
        if (newBansStr !== oldBansStr) {
            matchState.bannedCharacters = parsed;
            changed = true;
            console.log("[MATCH_STATE] Список банов успешно обновлен:", newBansStr);
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
                    let parsedVal = typeof val === 'string' ? JSON.parse(val) : val;
                    if (JSON.stringify(matchState.rosters[key]) !== JSON.stringify(parsedVal)) {
                        matchState.rosters[key] = parsedVal;
                        changed = true;
                    }
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
            if (typeof b === 'string') {
                bannedHeroes.push(window.marvelLogic.normalizeHeroName(b));
            } else if (typeof b === 'object' && b !== null) {
                if (b.character_name) {
                    bannedHeroes.push(window.marvelLogic.normalizeHeroName(b.character_name));
                } else if (b.character_id && window.marvelLogic.gameEntities && window.marvelLogic.gameEntities.heroes) {
                    // Если Overwolf прислал только ID без имени
                    let nameFromId = window.marvelLogic.gameEntities.heroes[b.character_id];
                    if (nameFromId) {
                        bannedHeroes.push(window.marvelLogic.normalizeHeroName(nameFromId));
                    }
                }
            }
        }

        // Убираем дубликаты и пустые значения
        bannedHeroes = [...new Set(bannedHeroes)].filter(h => h);

        // Логируем итоговый список банов при изменении
        if (JSON.stringify(matchState.lastProcessedBans) !== JSON.stringify(bannedHeroes)) {
            if (bannedHeroes.length > 0) {
                console.log("[LOGIC] Итоговые забаненные герои (нормализованные):", bannedHeroes);
            } else {
                console.log("[LOGIC] Забаненных героев нет (пустой список).");
            }
            matchState.lastProcessedBans = bannedHeroes;
        }

        let isMapEffective = false;
        let finalMapName = matchState.map;

        if (matchState.map) {
            let resolvedMap = window.marvelLogic.resolveMapName(matchState.map);
            let foundMap = window.marvelLogic.availableMaps.find(m => m.toLowerCase() === resolvedMap.toLowerCase());
            
            if (foundMap) {
                finalMapName = foundMap;
            } else {
                finalMapName = resolvedMap;
            }
            
            isMapEffective = window.marvelLogic.doesMapAffectScores(finalMapName);
        }

        let isMatchEmpty = (enemyHeroes.length === 0 && allyHeroes.length === 0);
        
        if (isMatchEmpty) {
            let clearTrayOnEnd = localStorage.getItem('clearTray') === 'true';
            
            if (clearTrayOnEnd) {
                window.latestData = {
                    map: null,
                    is_map_effective: false,
                    enemy_heroes: [],
                    ally_heroes: [],
                    banned_heroes:[],
                    counter_scores: {},
                    effective_team:[]
                };
            } else {
                let tierScores = window.marvelLogic.calculateTierListScoresWithMap(finalMapName);
                window.latestData = {
                    map: finalMapName,
                    is_map_effective: isMapEffective,
                    enemy_heroes: [],
                    ally_heroes:[],
                    banned_heroes: bannedHeroes,
                    counter_scores: tierScores,
                    effective_team:[]
                };
            }
            overwolf.windows.sendMessage("in_game", "update_data", window.latestData, () => {});
            return;
        }

        let activeEnemies = enemyHeroes.filter(h => !bannedHeroes.includes(h));
        
        let result;
        if (activeEnemies.length === 0) {
            let tierScores = window.marvelLogic.calculateTierListScoresWithMap(finalMapName);
            result = { 
                scores: tierScores, 
                optimalTeam: allyHeroes.length > 0 ? window.marvelLogic.getRecommendedHeroes(tierScores, allyHeroes, bannedHeroes) :[]
            };
        } else {
            result = window.marvelLogic.calculateCounterScoresForTeam(activeEnemies, finalMapName);
            result.optimalTeam = allyHeroes.length > 0 ? window.marvelLogic.getRecommendedHeroes(result.scores, allyHeroes, bannedHeroes) :[];
        }

        window.latestData = {
            map: finalMapName,
            is_map_effective: isMapEffective,
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

            if (state === "hidden" || state === "closed" || state === "minimized") {
                console.log(`[UI] Открываем ${targetWindowName}...`);
                overwolf.windows.restore(winId, () => {
                    overwolf.windows.bringToFront(winId, true, () => {
                        console.log(`[FOCUS] Мышь перехвачена.`);
                    });
                });
            } else {
                console.log(`[UI] Скрываем ${targetWindowName}...`);
                overwolf.windows.hide(winId);
            }
        });
    }
});

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
            if (info && info.info && info.info.match_info && info.info.match_info.hasOwnProperty('banned_characters')) {
                console.log("[EVENT] Обновление банов через onInfoUpdates2:", info.info.match_info.banned_characters);
            }
            if (updateStateFromInfo(info.info)) processGameData();
        });
        
        setInterval(() => {
            overwolf.games.events.getInfo((info) => {
                if (info && info.res && updateStateFromInfo(info.res)) processGameData();
            });
        }, 5000);
    }
});