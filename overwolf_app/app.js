// Подключаемся к локальному серверу на Python (который мы создали в overwolf_server.py)
const ws = new WebSocket('ws://localhost:8765');
let currentMap = null;
let enemyHeroes = new Set();

ws.onopen = () => {
    console.log("Успешное подключение к Python приложению");
};

ws.onclose = () => {
    console.log("Соединение с Python закрыто. Программа выключена?");
};

function sendDataToPython() {
    if (ws.readyState === WebSocket.OPEN) {
        const payload = JSON.stringify({
            type: "update",
            map: currentMap,
            enemy_heroes: Array.from(enemyHeroes)
        });
        ws.send(payload);
        console.log("Отправлено в Python:", payload);
    }
}

// Указываем, какие данные из игры мы хотим получать
const g_interestedInFeatures = ['match_info', 'roster'];

// Запрашиваем у Overwolf подписку на эти события
overwolf.games.events.setRequiredFeatures(g_interestedInFeatures, function(info) {
    if (info.status === "error") {
        console.error("Не удалось запросить события игры: ", info.reason);
        return;
    }
    console.log("События успешно запрошены. Ожидание данных из игры...", info);
});

// Слушаем глобальные обновления состояния (например, когда мы только зашли в матч)
overwolf.games.events.onInfoUpdates2.addListener(function(info) {
    let changed = false;

    // 1. Обновление карты
    if (info.feature === "match_info" && info.info.match_info && info.info.match_info.map_name) {
        currentMap = info.info.match_info.map_name;
        changed = true;
    }

    // 2. Обновление списка игроков (roster)
    if (info.feature === "roster") {
        for (const key in info.info) {
            if (key.startsWith('roster_')) {
                const player = info.info[key];
                
                // Проверяем, враг ли это
                const isEnemy = player.is_teammate === "false" || player.is_teammate === false || player.team === "enemy";
                
                if (isEnemy && player.character_name) {
                    enemyHeroes.add(player.character_name);
                    changed = true;
                }
            }
        }
    }

    if (changed) {
        sendDataToPython();
    }
});

// Слушаем точечные события (например, когда враг сменил героя прямо посреди матча)
overwolf.games.events.onNewEvents.addListener(function(info) {
    let changed = false;
    
    info.events.forEach(event => {
        if (event.name === "roster_update") {
            try {
                let data = JSON.parse(event.data);
                const isEnemy = data.is_teammate === false || data.is_teammate === "false" || data.team === "enemy";
                
                if (isEnemy && data.character_name) {
                    enemyHeroes.add(data.character_name);
                    changed = true;
                }
            } catch(e) {
                console.error("Ошибка парсинга события roster_update", e);
            }
        }
    });

    if (changed) {
        sendDataToPython();
    }
});