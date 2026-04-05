let bgWindow = overwolf.windows.getMainWindow();
let manualSelectedEnemies =[];

function getHeroImage(name) {
    let formatted = name.toLowerCase().replace(/[- ]/g, '_');
    return `../../resources/heroes_icons/${formatted}_1.png`;
}

function initData() {
    if (!bgWindow.marvelLogic || !bgWindow.marvelLogic.isReady) {
        setTimeout(initData, 500);
        return;
    }
    
    // Заполняем карты
    let mapSelects = [document.getElementById('cp-map-select'), document.getElementById('tl-map-select')];
    bgWindow.marvelLogic.availableMaps.forEach(map => {
        mapSelects.forEach(sel => {
            let opt = document.createElement('option');
            opt.value = map; opt.innerText = map;
            sel.appendChild(opt);
        });
    });

    document.getElementById('cp-heroes-count').innerText = `Всего героев в базе: ${bgWindow.marvelLogic.allHeroes.length}`;

    // Заполняем сетку ручного выбора
    let cpGrid = document.getElementById('cp-heroes-grid');
    bgWindow.marvelLogic.allHeroes.forEach(hero => {
        let btn = document.createElement('button');
        btn.className = 'grid-btn';
        btn.style.backgroundImage = `url('${getHeroImage(hero)}')`;
        btn.title = hero;
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

    // Обработчики карт
    document.getElementById('cp-map-select').addEventListener('change', updateManualCounterpicks);
    document.getElementById('tl-map-select').addEventListener('change', renderTierList);

    renderTierList();
    renderFavoritesGrid();
}

function updateManualCounterpicks() {
    let container = document.getElementById('cp-results');
    let map = document.getElementById('cp-map-select').value;
    document.getElementById('cp-selected-text').innerText = `Выбрано героев (${manualSelectedEnemies.length}/6): ${manualSelectedEnemies.join(', ')}`;
    
    if (manualSelectedEnemies.length === 0) {
        container.innerHTML = '<p style="color: gray; text-align: center;">Выберите героев справа</p>';
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
        text.innerHTML = `<strong>${index + 1}. ${hero}</strong>: ${score.toFixed(1)} очков`;
        
        row.appendChild(icon);
        row.appendChild(text);
        container.appendChild(row);
    });
}

function renderFavoritesGrid() {
    let grid = document.getElementById('favorites-grid');
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
        document.getElementById('logs-area').value = bgWindow.appLogs.join('\n');
    }
}

function openTab(tabId, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
    if (tabId === 'logs') refreshLogs();
}

document.addEventListener('DOMContentLoaded', () => {
    ['hide-allies', 'show-rating', 'priority-first', 'favorites-first'].forEach(id => {
        let cb = document.getElementById(`setting-${id}`);
        let key = id.replace(/-([a-z])/g, g => g[1].toUpperCase());
        cb.checked = localStorage.getItem(key) === 'true';
        cb.addEventListener('change', e => localStorage.setItem(key, e.target.checked));
    });

    document.getElementById('close-btn').addEventListener('click', () => {
        overwolf.windows.getCurrentWindow((res) => overwolf.windows.hide(res.window.id));
    });

    document.getElementById('header').addEventListener('mousedown', () => {
        overwolf.windows.getCurrentWindow((res) => overwolf.windows.dragMove(res.window.id));
    });

    initData();
});