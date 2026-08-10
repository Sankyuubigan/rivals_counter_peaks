let timeoutId;
let animationFrameId;
let bgWindow = null;
try { bgWindow = overwolf.windows.getMainWindow(); } catch (e) {}

// Мини-логгер уведомления: пишем в общий лог-стор (вкладка "Логи" в десктопе).
function notifLog(level, args) {
    let text = Array.from(args).map(a => {
        if (typeof a === 'object' && a !== null) {
            try { return JSON.stringify(a); } catch (e) { return String(a); }
        }
        return String(a);
    }).join(' ');
    try {
        if (bgWindow && bgWindow.appLogs) {
            bgWindow.appLogs.push(`[${new Date().toLocaleTimeString()}][${level}][NOTIFY] ${text}`);
            if (bgWindow.appLogs.length > 1000) bgWindow.appLogs.shift();
        }
    } catch (e) {}
    if (level === 'ERROR') console.error('[NOTIFY]', text);
    else console.log('[NOTIFY]', text);
}

window.addEventListener('error', function(ev) {
    notifLog('ERROR', ['JS_ERROR', `${ev.message} @ ${ev.filename}:${ev.lineno}:${ev.colno}`]);
});
window.addEventListener('unhandledrejection', function(ev) {
    let reason = ev.reason;
    let msg = (reason && reason.stack) ? reason.stack : (reason && reason.message ? reason.message : String(reason));
    notifLog('ERROR', ['PROMISE_REJECT', msg]);
});

function startAnimation(winId) {
    let progressBar = document.getElementById('progress-bar');
    let startTime = Date.now();
    let duration = 10000; 

    function update() {
        let elapsed = Date.now() - startTime;
        let progress = Math.max(0, 1 - (elapsed / duration));
        progressBar.style.transform = `scaleX(${progress})`;

        if (progress > 0) {
            animationFrameId = requestAnimationFrame(update);
        }
    }
    
    cancelAnimationFrame(animationFrameId);
    update();

    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
        overwolf.windows.hide(winId, (res) => {
            if (res && res.success === false) {
                notifLog('ERROR', ['hide уведомления:', res.error || JSON.stringify(res)]);
            }
        });
    }, duration);
}

function initWindow() {
    overwolf.windows.getCurrentWindow(res => {
        if (!res || !res.window) {
            notifLog('ERROR', ['getCurrentWindow: окно не получено']);
            return;
        }
        let winId = res.window.id;
        // Получаем информацию о мониторах, чтобы отцентрировать уведомление по вертикали слева
        overwolf.utils.getMonitorsList((monitors) => {
            let monitor = monitors.displays.find(m => m.is_primary) || monitors.displays[0];
            let y = Math.floor((monitor.height - 60) / 2);
            let x = 20; // Добавили отступ 20 пикселей от левого края
            overwolf.windows.changePosition(winId, x, y, (cr) => {
                if (cr && cr.success === false) {
                    notifLog('ERROR', ['changePosition уведомления:', cr.error || JSON.stringify(cr)]);
                }
            });
            startAnimation(winId);
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof applyTranslations === 'function') {
        applyTranslations();
    }
});

overwolf.windows.onStateChanged.addListener((state) => {
    overwolf.windows.getCurrentWindow(res => {
        if (state.window_name === res.window.name && state.window_state === "normal") {
            initWindow();
        }
    });
});

overwolf.windows.getCurrentWindow(res => {
    if (res.window.stateEx === "normal") {
        initWindow();
    }
});