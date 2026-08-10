// === КАСТОМНЫЙ ЛОГГЕР ДЛЯ ВКЛАДКИ "ЛОГИ" ===
window.appLogs =[];
window.__appLoggerInstalled = true;
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

window.addEventListener('error', function(ev) {
    formatLog('JS_ERROR', [`${ev.message} @ ${ev.filename}:${ev.lineno}:${ev.colno}`]);
});
window.addEventListener('unhandledrejection', function(ev) {
    let reason = ev.reason;
    let msg = (reason && reason.stack) ? reason.stack : (reason && reason.message ? reason.message : String(reason));
    formatLog('PROMISE_REJECT', [msg]);
});

// === СТАТУС ПОДКЛЮЧЕНИЯ К OVERWOLF ===
window.overwolfStatus = {
    connected: false,
    error: null,
    gameEventsSubscribed: false,
    lastCheckTime: null,
    lastErrorTime: null,
    errorCount: 0
};

function updateOverwolfStatus(connected, errorMsg) {
    let prevConnected = window.overwolfStatus.connected;
    window.overwolfStatus.connected = connected;
    window.overwolfStatus.error = errorMsg;
    window.overwolfStatus.lastCheckTime = new Date().toISOString();
    if (errorMsg) {
        window.overwolfStatus.lastErrorTime = new Date().toISOString();
        window.overwolfStatus.errorCount++;
    }
    // Логируем только при реальной смене состояния, чтобы не спамить.
    if (connected && !prevConnected) {
        console.log("[OVERWOLF_STATUS] Статус: ПОДКЛЮЧЕН");
    } else if (!connected && prevConnected) {
        console.error("[OVERWOLF_STATUS] Статус: ОТКЛЮЧЕН. Ошибка:", errorMsg);
    }
}

function checkOverwolfConnection() {
    try {
        if (typeof overwolf === 'undefined') {
            updateOverwolfStatus(false, "Overwolf API не найден (overwolf === undefined)");
            return;
        }
        if (!overwolf.games || !overwolf.games.events) {
            updateOverwolfStatus(false, "overwolf.games.events не доступен");
            return;
        }
        overwolf.games.events.getInfo(function(info) {
            if (info && info.success !== false) {
                if (!window.overwolfStatus.connected) {
                    console.log("[OVERWOLF_CHECK] getInfo успешен, соединение восстановлено");
                }
                updateOverwolfStatus(true, null);
            } else {
                let errMsg = info && info.error ? info.error : (info && info.status ? info.status : "getInfo вернул пустой результат");
                // "Not in a game" — нормальное состояние, когда игра не запущена.
                // Это НЕ обрыв связи с Overwolf, статус остаётся "подключён".
                if (String(errMsg).toLowerCase().indexOf('not in a game') !== -1) {
                    updateOverwolfStatus(true, null);
                    return;
                }
                updateOverwolfStatus(false, "getInfo: " + errMsg);
            }
        });
    } catch (e) {
        updateOverwolfStatus(false, "Исключение при проверке: " + (e.message || e));
    }
}

// === ОБЁРТКИ ОКОННЫХ API С ЛОГИРОВАНИЕМ ОШИБОК ===
// Раньше ошибки Overwolf API тихо проглатывались (пустые колбэки).
// Теперь любой сбой пишется в лог-стор вкладки "Логи".
function logApiError(context, res) {
    let err = res && (res.error || res.status)
        ? (res.error || res.status)
        : (res ? JSON.stringify(res) : "пустой ответ (res undefined)");
    console.error("[API_ERROR] " + context + ":", err);
}

function sendMessageLogged(windowId, messageId, content) {
    overwolf.windows.sendMessage(windowId, messageId, content, (res) => {
        if (!res || res.success === false) {
            logApiError(`sendMessage("${messageId}") в окно "${windowId}"`, res);
        }
    });
}

function obtainWindowLogged(windowName, cb) {
    overwolf.windows.obtainDeclaredWindow(windowName, (res) => {
        if (!res || !res.window) {
            logApiError(`obtainDeclaredWindow("${windowName}")`, res);
            return;
        }
        if (res.success === false) {
            logApiError(`obtainDeclaredWindow("${windowName}")`, res);
        }
        if (cb) cb(res);
    });
}

function winOpLogged(opName, windowId, ...args) {
    overwolf.windows[opName](windowId, ...args, (res) => {
        if (res && res.success === false) {
            logApiError(`${opName} окна "${windowId}"`, res);
        }
    });
}

// === ПОДПИСКА НА ИГРОВЫЕ СОБЫТИЯ ===
const REQUIRED_FEATURES =['match_info', 'game_info'];
let gameEventsSetupAttempts = 0;
const MAX_SETUP_ATTEMPTS = 30;
let gameEventsListenersReady = false;
let gameEventsSetupInProgress = false;
let gameEventsRetryTimer = null;
let infoPollInterval = null;
let lastPollError = null;

// Листенеры регистрируются ОДИН раз при старте приложения (так рекомендует
// Overwolf), а не в колбэке успешной подписки — иначе при повторных
// переподписках они дублируются.
function setupGameEventsListenersOnce() {
    if (gameEventsListenersReady) return;
    gameEventsListenersReady = true;

    // Главный диагностический канал ошибок провайдера игровых событий (GEP).
    overwolf.games.events.onError.addListener(function(error) {
        let reason = error && error.reason ? error.reason : (error && error.error ? error.error : JSON.stringify(error));
        console.error("[GEP_ERROR] Ошибка провайдера игровых событий:", reason);
    });

    overwolf.games.events.onInfoUpdates2.addListener(function(info) {
        if (info && info.info && info.info.match_info) {
            let mi = info.info.match_info;
            if (mi.hasOwnProperty('banned_characters')) {
                console.log("[EVENT] Обновление банов через onInfoUpdates2:", mi.banned_characters);
            }
        }
        if (updateStateFromInfo(info.info)) processGameData();
    });

    overwolf.games.events.onNewEvents.addListener(function(events) {
        if (!events || !events.events) return;
        for (let ev of events.events) {
            if (ev.name === 'match_start') {
                console.log("[EVENT] match_start получен.");
                // Если match_id ещё не пришёл — очищаем по самому факту старта матча.
                if (!matchState.matchId) {
                    clearTrayForNewMatch('match_start_' + Date.now());
                }
            }
        }
    });
}

// Периодический поллинг getInfo — создаётся один раз, активен только
// пока подписка жива. Ошибки логируются только при смене состояния (без спама).
function startInfoPolling() {
    if (infoPollInterval) return;
    infoPollInterval = setInterval(function() {
        if (!window.overwolfStatus.gameEventsSubscribed) return;
        overwolf.games.events.getInfo(function(info) {
            if (info && info.res && updateStateFromInfo(info.res)) processGameData();
            if (info && info.error) {
                let errStr = String(info.error);
                if (lastPollError !== errStr) {
                    lastPollError = errStr;
                    console.error("[OVERWOLF] Ошибка getInfo при поллинге:", errStr);
                }
            } else if (lastPollError !== null) {
                lastPollError = null;
                console.log("[OVERWOLF] getInfo при поллинге снова работает.");
            }
        });
    }, 5000);
}

function resetGameEventsSubscription() {
    gameEventsSetupAttempts = 0;
    window.overwolfStatus.gameEventsSubscribed = false;
    if (gameEventsRetryTimer) {
        clearTimeout(gameEventsRetryTimer);
        gameEventsRetryTimer = null;
    }
}

function setupGameEvents() {
    if (gameEventsSetupInProgress) return;
    gameEventsSetupInProgress = true;
    gameEventsSetupAttempts++;

    console.log("[OVERWOLF] Попытка #" + gameEventsSetupAttempts + " подписки на игровые события (setRequiredFeatures)...");
    overwolf.games.events.setRequiredFeatures(REQUIRED_FEATURES, function(result) {
        gameEventsSetupInProgress = false;
        if (result && result.success) {
            console.log("[OVERWOLF] Игровые события успешно подписаны! Попытка #" + gameEventsSetupAttempts +
                ". Поддерживаемые фичи: " + (result.supportedFeatures ? result.supportedFeatures.join(', ') : "не указаны"));
            window.overwolfStatus.gameEventsSubscribed = true;
            updateOverwolfStatus(true, null);
            gameEventsSetupAttempts = 0;
            startInfoPolling();
        } else {
            let errMsg = result && result.error ? result.error : "Неизвестная ошибка setRequiredFeatures";
            console.error("[OVERWOLF] ОШИБКА подписки на игровые события (попытка #" + gameEventsSetupAttempts + "):", errMsg);
            updateOverwolfStatus(false, "setRequiredFeatures: " + errMsg);

            // Игра не запущена — ретраи бессмысленны, подпишемся по событию запуска игры.
            if (String(errMsg).toLowerCase().indexOf('not in a game') !== -1) {
                console.log("[OVERWOLF] Игра не запущена (Not in a game) — ретраи остановлены, подпишемся при запуске игры.");
                resetGameEventsSubscription();
                return;
            }

            // Провайдер ещё инициализируется (Provider is not ready) — ретраим с бэкоффом.
            if (gameEventsSetupAttempts < MAX_SETUP_ATTEMPTS) {
                let delay = Math.min(3000 * gameEventsSetupAttempts, 15000);
                console.log("[OVERWOLF] Повторная попытка #" + (gameEventsSetupAttempts + 1) + " через " + delay + "ms (ошибка: " + errMsg + ")...");
                gameEventsRetryTimer = setTimeout(setupGameEvents, delay);
            } else {
                console.error("[OVERWOLF] Исчерпаны все попытки подписки на игровые события (" + MAX_SETUP_ATTEMPTS + "). Ждём следующего запуска игры.");
                resetGameEventsSubscription();
            }
        }
    });
}

window.marvelLogic = new CounterpickLogic();
window.latestData = {
    map: null,
    is_map_effective: false,
    enemy_heroes:[],
    ally_heroes: [],
    banned_heroes:[],
    counter_scores: {},
    effective_team:[]
};

let matchState = { 
    rosters: {}, 
    map: null, 
    matchId: null,
    bannedCharacters:[],
    lastRawBans: null,
    lastProcessedBans: null
};
// Гарантирует, что очистка трея происходит РОВНО 1 раз на каждый новый матч.
let trayClearedForMatchId = null;
let isTabHeld = false;
let isOurGameRunning = false;

window.marvelLogic.init().then(() => {
    console.log("База данных успешно загружена. Героев:", window.marvelLogic.allHeroes.length);
    overwolf.games.events.getInfo((info) => {
        if (info && info.res && info.res.match_info) {
            let mi = info.res.match_info;
        }
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
        if (parsed.character_id || parsed.character_name) {
            return [parsed];
        }
        return Object.values(parsed);
    } else if (typeof parsed === 'string') {
        return parsed.split(',').map(s => s.trim()).filter(s => s);
    }
    
    return[];
}

function updateStateFromInfo(info) {
    if (!info || !info.match_info) return false;
    
    let mi = info.match_info;
    let changed = false;

    // --- Обнаружение НОВОГО матча по match_id (надёжный триггер очистки) ---
    if (mi.match_id !== undefined) {
        let incomingMatchId = mi.match_id === "null" || mi.match_id === "" ? null : mi.match_id;
        if (incomingMatchId !== matchState.matchId) {
            console.log(`[MATCH] Смена match_id: '${matchState.matchId}' -> '${incomingMatchId}'`);
            if (incomingMatchId !== null) {
                // Новый матч начался — очищаем трей ровно 1 раз для этого match_id.
                clearTrayForNewMatch(incomingMatchId);
            }
            matchState.matchId = incomingMatchId;
            changed = true;
        }
    }

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
                // [DIAG] Overwolf прислал пустой roster. НЕ удаляем последний
                // достоверный состав, иначе союзники/враги частично исчезают из трея.
                // Сброс ростеров происходит только при смене карты/матча (match_id).
                console.log(`[DIAG] roster '${key}' пришёл пустым (null/""), оставляем старое значение. match_id=${matchState.matchId}`);
            } else {
                try {
                    let parsedVal = typeof val === 'string' ? JSON.parse(val) : val;
                    if (JSON.stringify(matchState.rosters[key]) !== JSON.stringify(parsedVal)) {
                        matchState.rosters[key] = parsedVal;
                        changed = true;
                        if (parsedVal && parsedVal.character_name) {
                            console.log(`[DIAG] roster '${key}' обновлён: ${parsedVal.character_name} (teammate=${parsedVal.is_teammate})`);
                        }
                    }
                } catch(e) {}
            }
        }
    }
    return changed;
}

function clearTrayForNewMatch(newMatchId) {
    if (trayClearedForMatchId === newMatchId) {
        console.log(`[MATCH] Очистка для match_id='${newMatchId}' уже выполнена, пропускаем (ровно 1 раз).`);
        return;
    }
    trayClearedForMatchId = newMatchId;

    console.log(`[MATCH] НАЧАЛО НОВОГО МАТЧА (${newMatchId}) — очищаем трей 1 раз.`);
    matchState.rosters = {};
    matchState.map = null;
    matchState.bannedCharacters = [];
    matchState.lastProcessedBans = null;
    matchState.lastRawBans = null;

    window.latestData = {
        map: null,
        is_map_effective: false,
        enemy_heroes: [],
        ally_heroes: [],
        banned_heroes: [],
        counter_scores: {},
        effective_team: []
    };
    sendMessageLogged("in_game", "update_data", window.latestData);
}

function processGameData() {
    try {
        if (!window.marvelLogic.isReady) return;

        let enemyHeroes = [], allyHeroes = [], bannedHeroes =[];
        
        for (let key in matchState.rosters) {
            let r = matchState.rosters[key];
            if (!r) continue;
            // Overwolf иногда шлёт character_name:null, но character_id заполнен (особенно у врагов в фазе лока).
            // Резолвим имя из ID через gameEntities.heroes, если имя пустое.
            let resolvedName = r.character_name;
            if ((!resolvedName || resolvedName === "UNKNOWN" || resolvedName === "null") && r.character_id != null) {
                let idKey = String(r.character_id);
                let byId = window.marvelLogic.gameEntities && window.marvelLogic.gameEntities.heroes
                    ? window.marvelLogic.gameEntities.heroes[idKey] : null;
                if (byId) resolvedName = byId;
            }
            if (resolvedName && resolvedName !== "UNKNOWN" && resolvedName !== "null") {
                let normName = window.marvelLogic.normalizeHeroName(resolvedName);
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
                    let nameFromId = window.marvelLogic.gameEntities.heroes[b.character_id];
                    if (nameFromId) {
                        bannedHeroes.push(window.marvelLogic.normalizeHeroName(nameFromId));
                    }
                }
            }
        }

        bannedHeroes = [...new Set(bannedHeroes)].filter(h => h);

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
            // Матч ещё не начался / нет данных о ростерах.
            // Очистка трея происходит РОВНО 1 раз в начале нового матча
            // (см. clearTrayForNewMatch по match_id / match_start), а не здесь.
            // Просто выходим, не трогая текущее состояние трея.
            console.log("[LOGIC] Ростеры пусты — пропускаем пересчёт (очистка уже была при старте матча).");
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

        sendMessageLogged("in_game", "update_data", window.latestData);
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
            obtainWindowLogged("in_game", (res) => {
                inGameWindowId = res.window.id;
                trayX = res.window.left;
                trayY = res.window.top;
                overwolf.windows.restore(inGameWindowId, () => {
                    sendMessageLogged(inGameWindowId, "update_data", window.latestData);
                });
            });
        } else {
            if (trayMoveInterval) {
                clearInterval(trayMoveInterval);
                trayMoveInterval = null;
            }
            if (inGameWindowId) winOpLogged("hide", inGameWindowId);
            else obtainWindowLogged("in_game", (res) => winOpLogged("hide", res.window.id));
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

        obtainWindowLogged(targetWindowName, (res) => {
            if (!res || !res.window) return;
            let winId = res.window.id;
            let state = res.window.stateEx;

            if (state === "hidden" || state === "closed" || state === "minimized") {
                console.log(`[UI] Открываем ${targetWindowName}...`);
                overwolf.windows.restore(winId, () => {
                    overwolf.windows.bringToFront(winId, true, (res2) => {
                        if (res2 && res2.success === false) logApiError(`bringToFront окна "${winId}"`, res2);
                        console.log(`[FOCUS] Мышь перехвачена.`);
                    });
                });
            } else {
                console.log(`[UI] Скрываем ${targetWindowName}...`);
                winOpLogged("hide", winId);
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
            console.log("[GAME] Игра запущена. Прячем десктопное окно и показываем уведомление.");
            console.log("[OVERWOLF] Игра запущена - переподписываемся на игровые события...");
            if (!window.overwolfStatus.gameEventsSubscribed) {
                console.log("[OVERWOLF] События не были подписаны ранее, вызываем setupGameEvents()...");
                setupGameEvents();
            }
            obtainWindowLogged("desktop", (res) => {
                if (res.window.stateEx !== "hidden" && res.window.stateEx !== "closed") {
                    winOpLogged("hide", res.window.id);
                }
            });
            obtainWindowLogged("notification", (res) => {
                winOpLogged("restore", res.window.id);
            });
        } else if (!gameRunning && isOurGameRunning) {
            isOurGameRunning = false;
            console.log("[GAME] Игра закрыта. Прячем in-game окно и уведомление.");
            // Провайдер игровых событий умирает вместе с игрой: сбрасываем
            // счётчик и флаг, чтобы следующий запуск игры начал подписку с нуля.
            resetGameEventsSubscription();
            console.log("[OVERWOLF] Подписка на игровые события сброшена, ждём следующего запуска игры.");
            obtainWindowLogged("desktop_in_game", (res) => {
                if (res.window.stateEx !== "hidden" && res.window.stateEx !== "closed") {
                    winOpLogged("hide", res.window.id);
                }
            });
            obtainWindowLogged("notification", (res) => {
                if (res.window.stateEx !== "hidden" && res.window.stateEx !== "closed") {
                    winOpLogged("hide", res.window.id);
                }
            });
            // Восстанавливаем десктопное окно, чтобы приложение оставалось доступным.
            obtainWindowLogged("desktop", (res) => {
                if (res.window.stateEx === "hidden" || res.window.stateEx === "closed") {
                    console.log("[UI] Игра закрыта — восстанавливаем десктопное окно.");
                    winOpLogged("restore", res.window.id);
                }
            });
        }
    }
});

overwolf.games.getRunningGameInfo((gameInfo) => {
    if (!gameInfo) {
        console.error("[API_ERROR] getRunningGameInfo: пустой ответ");
    }
    let gameRunning = (gameInfo && gameInfo.isRunning && gameInfo.classId === 24890);
    isOurGameRunning = gameRunning;
    
    if (gameRunning) {
        console.log("При старте приложения игра уже запущена. Показываем уведомление.");
        obtainWindowLogged("notification", (res) => {
            winOpLogged("restore", res.window.id);
        });
    } else {
        console.log("При старте приложения игра не запущена. Открываем десктоп.");
        obtainWindowLogged("desktop", (res) => {
            winOpLogged("restore", res.window.id);
        });
    }

    // После получения статуса игры запускаем подписку на события
    console.log("[OVERWOLF] Стартуем подписку на игровые события...");
    setupGameEvents();
});

// === ПЕРИОДИЧЕСКАЯ ПРОВЕРКА СТАТУСА OVERWOLF ===
setInterval(checkOverwolfConnection, 15000);
console.log("[OVERWOLF] Запущен периодический мониторинг соединения (интервал: 15с)");

// Регистрируем листенеры игровых событий ОДИН раз при старте приложения.
setupGameEventsListenersOnce();

// === ПЕРВАЯ ПРОВЕРКА ЧЕРЕЗ 3 СЕКУНДЫ ===
setTimeout(function() {
    console.log("[OVERWOLF] Первая плановая проверка соединения...");
    checkOverwolfConnection();
}, 3000);