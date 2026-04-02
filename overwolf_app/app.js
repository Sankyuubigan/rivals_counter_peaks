// МГНОВЕННЫЕ ОБНОВЛЕНИЯ + УМНЫЙ ПОЛЛИНГ (БЕЗ СПАМА В ЛОГАХ)
let ws = null;
let logQueue = [];

const REQUIRED_FEATURES =['match_info', 'game_info'];

let matchState = {
    rosters: {},
    map: null,
    gameType: "unknown",
    gameMode: "unknown"
};

function logToPython(msg) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type: "debug", data: msg}));
    } else {
        logQueue.push(msg);
    }
}

function flushLogQueue() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        while (logQueue.length > 0) {
            let msg = logQueue.shift();
            ws.send(JSON.stringify({type: "debug", data: msg}));
        }
    }
}

function connectWebSocket() {
    logToPython("DEBUG: connectWebSocket() called, attempting to connect to ws://localhost:8765");
    ws = new WebSocket('ws://localhost:8765');

    ws.onopen = () => {
        logToPython("INFO: WebSocket connection opened successfully");
        flushLogQueue();
        logToPython("=== CONNECTED TO PYTHON ===");
        init();
    };

    ws.onclose = (event) => {
        logToPython(`INFO: WebSocket connection closed (code: ${event.code}, reason: ${event.reason || 'none'})`);
        logToPython("DEBUG: Scheduling reconnect in 3000ms...");
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
        logToPython(`ERROR: WebSocket error occurred: ${JSON.stringify(error)}`);
    };
}

// Эта функция обновляет кэш и возвращает TRUE, только если что-то РЕАЛЬНО изменилось
function updateStateFromInfo(info) {
    if (!info) return false;
    let changed = false;
    
    logToPython(`DEBUG: updateStateFromInfo called with keys: ${Object.keys(info).join(', ')}`);
    
    if (info.match_info) {
        let mi = info.match_info;
        
        if (mi.map !== undefined && matchState.map !== mi.map) {
            logToPython(`DEBUG: Map changed from "${matchState.map}" to "${mi.map}"`);
            matchState.map = mi.map;
            changed = true;
        }
        if (mi.game_type !== undefined && matchState.gameType !== mi.game_type) {
            logToPython(`DEBUG: GameType changed from "${matchState.gameType}" to "${mi.game_type}"`);
            matchState.gameType = mi.game_type;
        }
        if (mi.game_mode !== undefined && matchState.gameMode !== mi.game_mode) {
            logToPython(`DEBUG: GameMode changed from "${matchState.gameMode}" to "${mi.game_mode}"`);
            matchState.gameMode = mi.game_mode;
        }
        
        for (let key in mi) {
            if (key.startsWith('roster_')) {
                let val = mi[key];
                if (val === null || val === "null" || val === "") {
                    if (matchState.rosters[key]) {
                        logToPython(`DEBUG: Roster "${key}" cleared (was: ${matchState.rosters[key].character_name || 'unknown'})`);
                        delete matchState.rosters[key];
                        changed = true;
                    }
                } else {
                    try {
                        let parsed = typeof val === 'string' ? JSON.parse(val) : val;
                        let oldHero = matchState.rosters[key] ? matchState.rosters[key].character_name : null;
                        let newHero = parsed.character_name;
                        
                        matchState.rosters[key] = parsed;
                        
                        if (oldHero !== newHero) {
                            logToPython(`DEBUG: Roster "${key}" hero changed from "${oldHero}" to "${newHero}"`);
                            changed = true;
                        }
                    } catch(e) {
                        logToPython(`ERROR: Failed to parse roster data for "${key}": ${e.message}. Raw value: ${val}`);
                    }
                }
            }
        }
    }
    
    logToPython(`DEBUG: updateStateFromInfo returning changed=${changed}, rosters count: ${Object.keys(matchState.rosters).length}`);
    return changed;
}

function sendDataToPython() {
    let enemyHeroes = [];
    let allyHeroes = [];
    let seenHeroes =[];
    
    for (let key in matchState.rosters) {
        let r = matchState.rosters[key];
        if (r.character_name) {
            seenHeroes.push({
                id: r.character_id || "unknown",
                name: r.character_name
            });
            
            if (r.is_teammate === false) {
                enemyHeroes.push(r.character_name);
            } else if (r.is_teammate === true) {
                allyHeroes.push(r.character_name);
            }
        }
    }

    logToPython(`DEBUG: sendDataToPython - map: ${matchState.map}, allies: ${allyHeroes.length}, enemies: ${enemyHeroes.length}, seen: ${seenHeroes.length}`);

    if (ws && ws.readyState === WebSocket.OPEN) {
        let payload = JSON.stringify({
            map: matchState.map,
            enemy_heroes: enemyHeroes,
            ally_heroes: allyHeroes,
            seen_heroes: seenHeroes
        });
        logToPython(`INFO: Sending data to Python (payload size: ${payload.length} bytes)`);
        ws.send(payload);
    } else {
        logToPython(`ERROR: Cannot send data - WebSocket not open (readyState: ${ws ? ws.readyState : 'null'})`);
    }
}

function init() {
    logToPython("INFO: === INIT STARTED ===");
    
    // 1. Сначала устанавливаем required features и ЖДЁМ успеха
    logToPython(`DEBUG: Calling setRequiredFeatures with: ${JSON.stringify(REQUIRED_FEATURES)}`);
    overwolf.games.events.setRequiredFeatures(REQUIRED_FEATURES, function(result) {
        logToPython("INFO: setRequiredFeatures callback received: " + JSON.stringify(result));
        
        if (!result || !result.success) {
            logToPython(`ERROR: setRequiredFeatures FAILED (result: ${JSON.stringify(result)}), retrying in 3s`);
            setTimeout(function() {
                init();
            }, 3000);
            return;
        }
        
        logToPython("INFO: setRequiredFeatures succeeded, proceeding to setup event listeners");
        // 2. Только после успеха подписываемся на события
        setupEventListeners();
        
        // 3. Первичный запрос при запуске
        logToPython("DEBUG: Requesting initial game info via getInfo()");
        overwolf.games.events.getInfo(function(info) {
            if (info && info.res) {
                logToPython(`DEBUG: getInfo() returned data with keys: ${Object.keys(info.res).join(', ')}`);
                updateStateFromInfo(info.res);
                logToPython(`INFO: === INITIAL STATE: Map: ${matchState.map}, GameType: ${matchState.gameType}, GameMode: ${matchState.gameMode}, Rosters: ${Object.keys(matchState.rosters).length} ===`);
                sendDataToPython();
            } else {
                logToPython(`ERROR: getInfo() returned empty or invalid result: ${JSON.stringify(info)}`);
            }
        });
    });
}

function setupEventListeners() {
    logToPython("DEBUG: setupEventListeners() called");
    
    // 1. Слушаем моментальные изменения (срабатывает сразу при смене героя)
    overwolf.games.events.onInfoUpdates2.addListener(function(info) {
        logToPython(`DEBUG: onInfoUpdates2 fired, info keys: ${info && info.info ? Object.keys(info.info).join(', ') : 'null'}`);
        if (info && info.info) {
            if (updateStateFromInfo(info.info)) {
                logToPython(`INFO: === INSTANT UPDATE: Map: ${matchState.map}, GameType: ${matchState.gameType}, GameMode: ${matchState.gameMode} ===`);
                sendDataToPython();
            } else {
                logToPython(`DEBUG: onInfoUpdates2 triggered but no state changes detected`);
            }
        } else {
            logToPython(`WARN: onInfoUpdates2 fired with empty info: ${JSON.stringify(info)}`);
        }
    });
    logToPython("INFO: Added onInfoUpdates2 listener");

    // 2. Умный поллинг каждые 5 секунд. Спасает, если мы пропустили старт матча.
    // Если данные не изменились - функция updateStateFromInfo вернет false и логов не будет!
    logToPython("INFO: Starting polling interval (every 5000ms)");
    setInterval(() => {
        overwolf.games.events.getInfo(function(info) {
            if (info && info.res) {
                if (updateStateFromInfo(info.res)) {
                    logToPython(`INFO: === POLLING UPDATE: Map: ${matchState.map}, GameType: ${matchState.gameType}, GameMode: ${matchState.gameMode} ===`);
                    sendDataToPython();
                }
            } else {
                logToPython(`WARN: Polling getInfo() returned empty result: ${JSON.stringify(info)}`);
            }
        });
    }, 5000);
}

connectWebSocket();