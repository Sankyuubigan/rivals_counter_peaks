// === DEBUG ONLY: заглушка Overwolf API для запуска UI без игры/клиента ===
// Подставляет window.overwolf, чтобы окна приложения работали в обычном браузере.
// НЕ используется в реальном Overwolf-приложении.

(function () {
    function noop() {}

    function makeWindowApi() {
        return {
            getMainWindow: function () {
                // В debug-режиме desktop-окно само выступает "background" окном,
                // поэтому bgWindow.marvelLogic / bgWindow.latestData берутся из window.
                return window;
            },
            getCurrentWindow: function (cb) {
                cb({ window: { id: 'debug', width: 1000, height: 950, left: 0, top: 0, stateEx: 'normal' } });
            },
            obtainDeclaredWindow: function (name, cb) {
                cb({ window: { id: 'debug_' + name, width: 1000, height: 950, left: 0, top: 0, stateEx: 'normal' } });
            },
            changeSize: noop,
            changePosition: noop,
            restore: noop,
            hide: noop,
            close: noop,
            minimize: noop,
            maximize: noop,
            dragMove: noop,
            dragResize: noop,
            bringToFront: noop,
            sendMessage: function (windowId, id, content, cb) {
                if (cb) cb({ success: true });
                // Имитируем получение сообщения внутри того же окна (для in_game-стиля)
                if (id === 'update_data' && typeof window.onDebugMessage === 'function') {
                    window.onDebugMessage(content);
                }
            },
            onMessageReceived: {
                addListener: noop
            }
        };
    }

    function makeHotkeysApi() {
        return {
            onHold: { addListener: noop },
            onPressed: { addListener: noop },
            get: noop,
            set: noop
        };
    }

    function makeGamesEventsApi() {
        return {
            setRequiredFeatures: function (features, cb) {
                if (cb) cb({ success: false, error: 'debug: overwolf not available' });
            },
            getInfo: function (cb) {
                if (cb) cb({ success: false, error: 'debug: overwolf not available' });
            },
            onInfoUpdates2: { addListener: noop },
            onNewEvents: { addListener: noop }
        };
    }

    function makeGamesApi() {
        return {
            events: makeGamesEventsApi(),
            onGameInfoUpdated: { addListener: noop },
            getRunningGameInfo: function (cb) {
                if (cb) cb({ success: false, isRunning: false });
            }
        };
    }

    window.overwolf = {
        windows: makeWindowApi(),
        settings: { hotkeys: makeHotkeysApi() },
        games: makeGamesApi(),
        log: noop
    };

    // === DEBUG: поправляем относительные fetch БД ===
    // logic.js делает fetch('database/...') относительно документа (/debug/),
    // а реальные файлы лежат на уровень выше (в overwolf_app/). Переписываем путь.
    const nativeFetch = window.fetch ? window.fetch.bind(window) : null;
    window.fetch = function (url, opts) {
        if (typeof url === 'string' && url.indexOf('database/') === 0) {
            url = '../' + url;
        }
        if (nativeFetch) return nativeFetch(url, opts);
        return Promise.reject(new Error('fetch not available'));
    };
})();
