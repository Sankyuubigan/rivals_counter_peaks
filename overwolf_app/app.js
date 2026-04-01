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
    ws = new WebSocket('ws://localhost:8765');
    ws.onopen = () => {
        flushLogQueue();
        logToPython("=== CONNECTED TO PYTHON ===");
        init();
    };
    ws.onclose = () => setTimeout(connectWebSocket, 3000);
}

// Эта функция обновляет кэш и возвращает TRUE, только если что-то РЕАЛЬНО изменилось
function updateStateFromInfo(info) {
    if (!info) return false;
    let changed = false;
    
    if (info.match_info) {
        let mi = info.match_info;
        
        if (mi.map !== undefined && matchState.map !== mi.map) {
            matchState.map = mi.map;
            changed = true;
        }
        if (mi.game_type !== undefined && matchState.gameType !== mi.game_type) {
            matchState.gameType = mi.game_type;
        }
        if (mi.game_mode !== undefined && matchState.gameMode !== mi.game_mode) {
            matchState.gameMode = mi.game_mode;
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
                        let parsed = typeof val === 'string' ? JSON.parse(val) : val;
                        let oldHero = matchState.rosters[key] ? matchState.rosters[key].character_name : null;
                        let newHero = parsed.character_name;
                        
                        matchState.rosters[key] = parsed;
                        
                        // Сравниваем старого и нового героя. Если изменился - фиксируем
                        if (oldHero !== newHero) {
                            changed = true;
                        }
                    } catch(e) {}
                }
            }
        }
    }
    return changed;
}

function sendDataToPython() {
    let enemyHeroes = [];
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
            }
        }
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            map: matchState.map,
            enemy_heroes: enemyHeroes,
            seen_heroes: seenHeroes
        }));
    }
}

function init() {
    overwolf.games.events.setRequiredFeatures(REQUIRED_FEATURES, function(result) {
        logToPython("=== setRequiredFeatures === " + JSON.stringify(result));
    });
    
    // 1. Слушаем моментальные изменения (срабатывает сразу при смене героя)
    overwolf.games.events.onInfoUpdates2.addListener(function(info) {
        if (info && info.info) {
            if (updateStateFromInfo(info.info)) {
                logToPython(`=== INSTANT UPDATE: Map: ${matchState.map} ===`);
                sendDataToPython();
            }
        }
    });

    // 2. Умный поллинг каждые 5 секунд. Спасает, если мы пропустили старт матча.
    // Если данные не изменились - функция updateStateFromInfo вернет false и логов не будет!
    setInterval(() => {
        overwolf.games.events.getInfo(function(info) {
            if (info && info.res) {
                if (updateStateFromInfo(info.res)) {
                    logToPython(`=== POLLING UPDATE: Map: ${matchState.map} ===`);
                    sendDataToPython();
                }
            }
        });
    }, 5000);

    // 3. Первичный запрос при запуске
    overwolf.games.events.getInfo(function(info) {
        if (info && info.res) {
            updateStateFromInfo(info.res);
            logToPython(`=== INITIAL STATE: Map: ${matchState.map} ===`);
            sendDataToPython();
        }
    });
}

connectWebSocket();