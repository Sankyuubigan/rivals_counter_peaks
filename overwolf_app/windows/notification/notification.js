let timeoutId;
let animationFrameId;

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
        overwolf.windows.hide(winId);
    }, duration);
}

function initWindow() {
    overwolf.windows.getCurrentWindow(res => {
        let winId = res.window.id;
        // Получаем информацию о мониторах, чтобы отцентрировать уведомление по вертикали слева
        overwolf.utils.getMonitorsList((monitors) => {
            let monitor = monitors.displays.find(m => m.is_primary) || monitors.displays[0];
            let y = Math.floor((monitor.height - 60) / 2);
            let x = 20; // Добавили отступ 20 пикселей от левого края
            overwolf.windows.changePosition(winId, x, y);
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