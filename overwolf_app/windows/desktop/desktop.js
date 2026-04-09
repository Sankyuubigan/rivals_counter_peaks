let bgWindow = overwolf.windows.getMainWindow();
let manualSelectedEnemies =[];

const origDesktopLog = console.log;
console.log = function(...args) {
    origDesktopLog.apply(console, args);
    if (bgWindow && bgWindow.appLogs) {
        bgWindow.appLogs.push(`[${new Date().toLocaleTimeString()}][UI_LOG] ` + args.join(' '));
    }
};

function getHeroImage(name) {
    let formatted = name.toLowerCase().replace(/[- ]/g, '_');
    return `../../resources/heroes_icons/${formatted}_1.png`;
}

function updateMapsOptions() {
    let mapSelects = [document.getElementById('cp-map-select'), document.getElementById('tl-map-select')];
    let cpVal = mapSelects[0].value;
    let tlVal = mapSelects[1].value;
    
    mapSelects.forEach(sel => {
        sel.innerHTML = `<option value="">${getTranslation('no_map')}</option>`;
    });
    
    if (bgWindow.marvelLogic && bgWindow.marvelLogic.availableMaps) {
        bgWindow.marvelLogic.availableMaps.forEach(map => {
            mapSelects.forEach(sel => {
                let opt = document.createElement('option');
                opt.value = map; opt.innerText = map;
                sel.appendChild(opt);
            });
        });
    }
    
    mapSelects[0].value = cpVal;
    mapSelects[1].value = tlVal;
}

function initData() {
    if (!bgWindow.marvelLogic || !bgWindow.marvelLogic.isReady) {
        setTimeout(initData, 500);
        return;
    }
    
    updateMapsOptions();

    document.getElementById('cp-heroes-count').innerText = getTranslation('total_heroes', {count: bgWindow.marvelLogic.allHeroes.length});

    let cpGrid = document.getElementById('cp-heroes-grid');
    cpGrid.innerHTML = '';
    bgWindow.marvelLogic.allHeroes.forEach(hero => {
        let btn = document.createElement('button');
        btn.className = 'grid-btn';
        btn.style.backgroundImage = `url('${getHeroImage(hero)}')`;
        btn.title = hero;
        if (manualSelectedEnemies.includes(hero)) {
            btn.classList.add('selected');
        }
        btn.onclick = () => {
            if (manualSelectedEnemies.includes(hero)) {
                manualSelectedEnemies = manualSelectedEnemies.filter(h => h !== hero);
                btn.classList.remove('selected');
            } else {
                if (manualSelectedEnemies.length < 6) {
                    manualSelectedEnemies.push(hero);
                    btn.classList.add('selected');
                }
            }
            updateManualCounterpicks();
        };
        cpGrid.appendChild(btn);
    });

    document.getElementById('cp-map-select').addEventListener('change', updateManualCounterpicks);
    document.getElementById('tl-map-select').addEventListener('change', renderTierList);

    updateManualCounterpicks();
    renderTierList();
    renderFavoritesGrid();
    loadMdContent();
}

function loadMdContent() {
    let lang = localStorage.getItem('language') || 'ru';
    let infoFile = `../../resources/info/information_${lang}.md`;
    
    fetch(infoFile)
        .then(res => res.text())
        .then(text => {
            // Убираем заголовок # о программе (или # About Program)
            let content = text.replace(/^#\s*(о программе|About Program)\s*$/gim, '').trim();
            document.getElementById('about-md-content').innerHTML = content;
        })
        .catch(err => console.log('Failed to load info MD:', err));
}

function updateManualCounterpicks() {
    let container = document.getElementById('cp-results');
    let map = document.getElementById('cp-map-select').value;
    document.getElementById('cp-selected-text').innerText = getTranslation('selected_heroes', {count: manualSelectedEnemies.length, heroes: manualSelectedEnemies.join(', ')});
    
    if (manualSelectedEnemies.length === 0) {
        container.innerHTML = `<p style="color: gray; text-align: center;">${getTranslation('select_enemies')}</p>`;
        return;
    }

    let result = bgWindow.marvelLogic.calculateCounterScoresForTeam(manualSelectedEnemies, map);
    renderList(container, result.scores, result.optimalTeam);
}

function clearManualSelection() {
    manualSelectedEnemies =[];
    document.querySelectorAll('#cp-heroes-grid .grid-btn').forEach(b => b.classList.remove('selected'));
    updateManualCounterpicks();
}

function renderTierList() {
    let container = document.getElementById('tl-results');
    let map = document.getElementById('tl-map-select').value;
    let scores = bgWindow.marvelLogic.calculateTierListScoresWithMap(map);
    renderList(container, scores,[]);
}

function renderList(container, scores, effectiveTeam) {
    container.innerHTML = '';
    let sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
    
    sorted.forEach(([hero, score], index) => {
        let row = document.createElement('div');
        row.className = 'hero-row';
        if (effectiveTeam.includes(hero)) row.style.backgroundColor = '#45475a';
        
        let icon = document.createElement('div');
        icon.className = 'hero-icon';
        icon.style.backgroundImage = `url('${getHeroImage(hero)}')`;
        
        let text = document.createElement('div');
        text.innerHTML = `<strong>${index + 1}. ${hero}</strong>: ${score.toFixed(1)} ${getTranslation('points')}`;
        
        row.appendChild(icon);
        row.appendChild(text);
        container.appendChild(row);
    });
}

function renderFavoritesGrid() {
    let grid = document.getElementById('favorites-grid');
    grid.innerHTML = '';
    let savedFavorites = JSON.parse(localStorage.getItem('favoriteHeroes') || '[]');

    bgWindow.marvelLogic.allHeroes.forEach(hero => {
        let btn = document.createElement('button');
        btn.className = 'grid-btn';
        btn.style.backgroundImage = `url('${getHeroImage(hero)}')`;
        btn.title = hero;
        if (savedFavorites.includes(hero)) btn.classList.add('selected');

        btn.onclick = () => {
            btn.classList.toggle('selected');
            let currentFavs = JSON.parse(localStorage.getItem('favoriteHeroes') || '[]');
            if (btn.classList.contains('selected')) {
                if (!currentFavs.includes(hero)) currentFavs.push(hero);
            } else {
                currentFavs = currentFavs.filter(h => h !== hero);
            }
            localStorage.setItem('favoriteHeroes', JSON.stringify(currentFavs));
        };
        grid.appendChild(btn);
    });
}

function refreshLogs() {
    if (bgWindow && bgWindow.appLogs) {
        let ta = document.getElementById('logs-area');
        ta.value = bgWindow.appLogs.join('\n');
        ta.scrollTop = ta.scrollHeight;
    }
}

function copyLogs() {
    let logs = document.getElementById('logs-area').value;
    if (!logs) return;
    navigator.clipboard.writeText(logs).then(() => {
        let msg = document.getElementById('copy-log-msg');
        msg.style.display = 'inline';
        setTimeout(() => msg.style.display = 'none', 2000);
    });
}

function openTab(tabId, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
    if (tabId === 'logs') refreshLogs();
}

document.addEventListener('DOMContentLoaded', () => {['hide-allies', 'show-rating', 'priority-first', 'favorites-first', 'clear-tray'].forEach(id => {
        let cb = document.getElementById(`setting-${id}`);
        let key = id.replace(/-([a-z])/g, g => g[1].toUpperCase());
        cb.checked = localStorage.getItem(key) === 'true';
        cb.addEventListener('change', e => localStorage.setItem(key, e.target.checked));
    });

    let twSlider = document.getElementById('setting-tray-width');
    let twVal = document.getElementById('tray-width-val');
    twSlider.value = localStorage.getItem('trayWidth') || 800;
    twVal.innerText = twSlider.value;
    twSlider.addEventListener('input', e => twVal.innerText = e.target.value);
    twSlider.addEventListener('change', e => {
        localStorage.setItem('trayWidth', e.target.value);
        overwolf.windows.obtainDeclaredWindow("in_game", res => {
            overwolf.windows.changeSize(res.window.id, parseInt(e.target.value), 180);
        });
    });

    let langSelect = document.getElementById('setting-language');
    if (langSelect) {
        langSelect.value = localStorage.getItem('language') || 'ru';
        langSelect.addEventListener('change', (e) => {
            localStorage.setItem('language', e.target.value);
            applyTranslations();
            updateMapsOptions();
            updateManualCounterpicks();
            renderTierList();
            let countEl = document.getElementById('cp-heroes-count');
            if (countEl && bgWindow.marvelLogic) {
                countEl.innerText = getTranslation('total_heroes', {count: bgWindow.marvelLogic.allHeroes.length});
            }
        });
    }

    applyTranslations();

    // Проверка первого запуска для переключения на вкладку About
    let isFirstRunDesktop = !localStorage.getItem('firstRun_desktop');
    if (isFirstRunDesktop) {
        localStorage.setItem('firstRun_desktop', 'true');
        let aboutBtn = document.querySelector('.tab-btn[onclick*="about"]');
        if (aboutBtn) openTab('about', aboutBtn);
    }

    document.getElementById('close-btn').addEventListener('click', () => {
        overwolf.windows.getCurrentWindow((res) => overwolf.windows.hide(res.window.id));
    });

    document.getElementById('header').addEventListener('mousedown', () => {
        overwolf.windows.getCurrentWindow((res) => overwolf.windows.dragMove(res.window.id));
    });

    initData();
});