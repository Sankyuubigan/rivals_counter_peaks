let ws = null;
let currentMap = null;
let enemyRoster = {};
const GAME_CLASS_ID = 24890;
// Добавили 'roster' в список запрашиваемых фичей на всякий случай
const g_interestedInFeatures =['match_info', 'game_info', 'roster']; 

let logQueue =[];

function logToPython(msg) {
    console.log(msg);
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
        console.log("Connected to Python");
        flushLogQueue();
        logToPython("Overwolf JS script connected to Python!");
        sendDataToPython();
        checkGameRunningAndRegister();
    };

    ws.onclose = () => {
        setTimeout(connectWebSocket, 3000);
    };
    ws.onerror = (err) => {};
}

function checkGameRunningAndRegister() {
    overwolf.games.getRunningGameInfo(function(res) {
        if (res && (res.classId === GAME_CLASS_ID || Math.floor(res.classId / 10) === GAME_CLASS_ID)) {
            logToPython("Marvel Rivals is running. Registering features...");
            registerFeatures();
        }
    });
}

connectWebSocket();

function sendDataToPython() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: "update",
            map: currentMap,
            enemy_heroes: Object.values(enemyRoster)
        }));
    }
}

function processMatchInfo(matchInfo) {
    let changed = false;
    if (!matchInfo) return false;

    if (matchInfo.map !== undefined) {
        let newMap = matchInfo.map;
        if (currentMap !== newMap) {
            currentMap = newMap;
            changed = true;
        }
    }

    // 1. Сначала определяем, в какой команде находится сам игрок (local player)
    let localTeam = null;
    for (const key in matchInfo) {
        if (key.startsWith('roster_') && matchInfo[key] && matchInfo[key] !== "null") {
            try {
                let p = typeof matchInfo[key] === 'string' ? JSON.parse(matchInfo[key]) : matchInfo[key];
                if (p.is_local === true || p.is_local === "true") {
                    localTeam = p.team;
                }
            } catch(e) {}
        }
    }

    // 2. Теперь обрабатываем всех игроков
    for (const key in matchInfo) {
        if (key.startsWith('roster_')) {
            if (matchInfo[key] === null || matchInfo[key] === "null" || matchInfo[key] === "") {
                if (enemyRoster[key]) {
                    logToPython(`Player left or slot cleared: ${key}`);
                    delete enemyRoster[key];
                    changed = true;
                }
                continue;
            }

            try {
                let p = typeof matchInfo[key] === 'string' ? JSON.parse(matchInfo[key]) : matchInfo[key];
                
                if (p.character_name === undefined && p.is_teammate === undefined && p.team === undefined) {
                    continue;
                }

                // Логика определения врага: если номер команды отличается от нашего
                let isEnemy = false;
                if (localTeam !== null && p.team !== undefined) {
                    isEnemy = (String(p.team) !== String(localTeam));
                } else if (p.is_teammate !== undefined) {
                    isEnemy = (p.is_teammate === false || p.is_teammate === "false" || p.is_teammate === 0 || p.is_teammate === "0");
                } else {
                    isEnemy = enemyRoster[key] !== undefined;
                }
                
                let hero = p.character_name;
                if (hero && hero.includes('***')) {
                    hero = null;
                }
                
                // ДЕБАГ: Логируем каждого уникального игрока, чтобы видеть, что присылает игра
                if (!window._loggedPlayers) window._loggedPlayers = {};
                let logKey = key + "_" + hero + "_" + p.team + "_" + p.is_teammate;
                if (!window._loggedPlayers[logKey] && hero) {
                    logToPython(`[ROSTER DEBUG] Slot: ${key}, Hero: ${hero}, Team: ${p.team}, LocalTeam: ${localTeam}, is_teammate: ${p.is_teammate}, isEnemy_calc: ${isEnemy}`);
                    window._loggedPlayers[logKey] = true;
                }
                
                if (isEnemy && hero) {
                    if (enemyRoster[key] !== hero) {
                        logToPython(`Enemy detected in ${key}: ${hero}`);
                        enemyRoster[key] = hero;
                        changed = true;
                    }
                } else if (!isEnemy) {
                    if (enemyRoster[key]) {
                        delete enemyRoster[key];
                        changed = true;
                    }
                }
            } catch(e) {
                logToPython("Error parsing roster key " + key + ": " + e);
            }
        }
    }
    return changed;
}

let isFeaturesRegistered = false;
let pollingInterval = null;

function startPolling() {
    if (pollingInterval) return;
    logToPython("Starting getInfo polling fallback (every 5s)...");
    pollingInterval = setInterval(() => {
        if (isFeaturesRegistered) {
            overwolf.games.events.getInfo(function(infoData) {
                if (infoData && infoData.res && infoData.res.match_info) {
                    if (processMatchInfo(infoData.res.match_info)) {
                        sendDataToPython();
                    }
                }
            });
        }
    }, 5000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
        logToPython("Stopped getInfo polling.");
    }
}

function registerFeatures() {
    if (isFeaturesRegistered) return;
    
    overwolf.games.events.setRequiredFeatures(g_interestedInFeatures, function(info) {
        logToPython("setRequiredFeatures response: " + JSON.stringify(info));
        if (info.status === "success") {
            isFeaturesRegistered = true;
            startPolling(); 
            
            overwolf.games.events.getInfo(function(infoData) {
                logToPython("Initial getInfo response: " + JSON.stringify(infoData));
                if (infoData && infoData.res && infoData.res.match_info) {
                    if (processMatchInfo(infoData.res.match_info)) {
                        sendDataToPython();
                    }
                }
            });
        } else {
            logToPython("Failed to register features. Retrying in 2s...");
            setTimeout(registerFeatures, 2000);
        }
    });
}

overwolf.games.onGameInfoUpdated.addListener(function(res) {
    if (res && res.gameInfo && res.gameInfo.isRunning) {
        if (res.gameInfo.classId === GAME_CLASS_ID || Math.floor(res.gameInfo.classId / 10) === GAME_CLASS_ID) {
            if (!isFeaturesRegistered) {
                logToPython("Marvel Rivals started or updated.");
                registerFeatures();
            }
        }
    } else if (res && res.gameInfo && !res.gameInfo.isRunning) {
        if (res.gameInfo.classId === GAME_CLASS_ID || Math.floor(res.gameInfo.classId / 10) === GAME_CLASS_ID) {
            logToPython("Marvel Rivals closed.");
            isFeaturesRegistered = false;
            stopPolling();
            enemyRoster = {};
            currentMap = null;
            sendDataToPython();
        }
    }
});

overwolf.games.events.onInfoUpdates2.addListener(function(info) {
    if (info.feature === "match_info" && info.info && info.info.match_info) {
        if (processMatchInfo(info.info.match_info)) {
            sendDataToPython();
        }
    }
});

overwolf.games.events.onNewEvents.addListener(function(info) {
    if (info.events && info.events.length > 0) {
        for (let i = 0; i < info.events.length; i++) {
            let eventName = info.events[i].name;
            if (eventName === "match_start" || eventName === "round_start") {
                logToPython("Event " + eventName + " detected. Requesting full info...");
                overwolf.games.events.getInfo(function(infoData) {
                    if (infoData && infoData.res && infoData.res.match_info) {
                        if (processMatchInfo(infoData.res.match_info)) {
                            sendDataToPython();
                        }
                    }
                });
            }
        }
    }
});