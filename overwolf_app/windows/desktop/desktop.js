let bgWindow = overwolf.windows.getMainWindow();
let manualSelectedEnemies =[];

const origDesktopLog = console.log;
console.log = function(...args) {
    origDesktopLog.apply(console, args);
    if (bgWindow && bgWindow.appLogs) {
        bgWindow.appLogs.push(`[${new Date().toLocaleTimeString()}][UI_LOG] ` + args.join(' '));
    }
};

const imageCache = {};

function applyHeroImage(element, heroName) {
    if (!heroName) return;
    let formatted = heroName.toLowerCase().replace(/[- ]/g, '_');
    let localUrl = `../../resources/heroes_icons/${formatted}_1.png`;
    let githubUrl = `https://raw.githubusercontent.com/Sankyuubigan/rivals_counter_peaks/master/overwolf_app/resources/heroes_icons/${formatted}_1.png`;

    function setFallback() {
        element.style.backgroundImage = 'none';
        if (!element.querySelector('.hero-fallback-text')) {
            let span = document.createElement('span');
            span.className = 'hero-fallback-text';
            span.innerText = heroName.substring(0, 5).toUpperCase();
            element.appendChild(span);
        }
    }

    if (imageCache[heroName] === 'not_found') {
        setFallback();
        return;
    } else if (imageCache[heroName]) {
        element.style.backgroundImage = `url('${imageCache[heroName]}')`;
        return;
    }

    element.style.backgroundImage = `url('${localUrl}')`;
    let img = new Image();
    img.onload = () => { imageCache[heroName] = localUrl; };
    img.onerror = () => {
        let imgGit = new Image();
        imgGit.onload = () => { 
            imageCache[heroName] = githubUrl; 
            element.style.backgroundImage = `url('${githubUrl}')`; 
        };
        imgGit.onerror = () => { 
            imageCache[heroName] = 'not_found'; 
            setFallback(); 
        };
        imgGit.src = githubUrl;
    };
    img.src = localUrl;
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
        applyHeroImage(btn, hero);
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
    renderDbList();
}

function loadMdContent() {
    let lang = localStorage.getItem('language') || 'en';
    let infoFile = `../../resources/info/information_${lang}.md`;
    
    fetch(infoFile)
        .then(res => res.text())
        .then(text => {
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
        applyHeroImage(icon, hero);
        
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
        applyHeroImage(btn, hero);
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

// === СТАТУС ПОДКЛЮЧЕНИЯ К OVERWOLF ===
function updateOverwolfStatusUI() {
    try {
        let status = bgWindow.overwolfStatus;
        let dot = document.getElementById('overwolf-status-dot');
        let text = document.getElementById('overwolf-status-text');
        let errEl = document.getElementById('overwolf-status-error');
        let container = document.getElementById('overwolf-status');

        if (!dot || !text || !container) return;

        if (!status) {
            dot.style.background = '#f38ba8';
            text.innerText = getTranslation('overwolf_checking');
            if (errEl) errEl.style.display = 'none';
            return;
        }

        if (status.connected) {
            dot.style.background = '#a6e3a1';
            dot.style.boxShadow = '0 0 6px #a6e3a1';
            text.innerText = getTranslation('overwolf_connected');
            container.style.borderColor = '#a6e3a1';
            if (errEl) errEl.style.display = 'none';
        } else {
            dot.style.background = '#f38ba8';
            dot.style.boxShadow = '0 0 6px #f38ba8';
            text.innerText = getTranslation('overwolf_disconnected');
            container.style.borderColor = '#f38ba8';
            if (errEl) {
                errEl.style.display = 'inline';
                errEl.innerText = status.error || '';
            }
        }
    } catch (e) {
        console.error("Ошибка обновления статуса Overwolf:", e);
    }
}

setInterval(updateOverwolfStatusUI, 5000);

function openTab(tabId, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
    if (tabId === 'logs') refreshLogs();
    if (tabId === 'settings') updateOverwolfStatusUI();
}

// --- ЛОГИКА ОБНОВЛЕНИЯ БАЗ ДАННЫХ ---
const DB_GITHUB_API = "https://api.github.com/repos/Sankyuubigan/rivals_counter_peaks/contents/overwolf_app/database/stats?ref=master";

function renderDbList(githubFiles = []) {
    const container = document.getElementById('db-list-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    const activeDbName = localStorage.getItem('active_db_name') || 'local';
    const savedDbs = JSON.parse(localStorage.getItem('saved_dbs') || '{}');
    
    const builtInFileName = (bgWindow.marvelLogic && bgWindow.marvelLogic.gameEntities) 
        ? bgWindow.marvelLogic.gameEntities.default_db_file 
        : 'Встроенная база';

    container.appendChild(createDbRowItem(builtInFileName + " (Из коробки)", 'local', null, activeDbName === 'local', true));

    let allDbNames = new Set([...Object.keys(savedDbs), ...githubFiles.map(f => f.name)]);

    allDbNames.forEach(fileName => {
        if (fileName === 'local' || fileName === builtInFileName || !fileName.endsWith('.json')) return;
        
        let isDownloaded = !!savedDbs[fileName];
        let isActive = activeDbName === fileName;
        let gitFile = githubFiles.find(f => f.name === fileName);
        let downloadUrl = gitFile ? gitFile.download_url : null;

        container.appendChild(createDbRowItem(fileName, fileName, downloadUrl, isActive, isDownloaded));
    });
}

function createDbRowItem(displayName, fileName, downloadUrl, isActive, isDownloaded) {
    let row = document.createElement('div');
    row.style.cssText = `display: flex; justify-content: space-between; align-items: center; background: ${isActive ? '#45475a' : '#1e1e2e'}; padding: 5px 10px; border-radius: 3px; border: 1px solid ${isActive ? '#89dceb' : '#45475a'};`;

    let statusText = isActive ? getTranslation('db_status_active') : (isDownloaded ? getTranslation('db_status_downloaded') : getTranslation('db_status_available'));
    
    let infoDiv = document.createElement('div');
    infoDiv.innerHTML = `<span style="font-size: 13px; color: #cdd6f4;">${displayName}</span> <br>
                         <span style="font-size: 10px; color: ${isDownloaded ? '#a6e3a1' : '#f9e2af'};">${statusText}</span>`;
    
    let btnsDiv = document.createElement('div');
    btnsDiv.style.display = 'flex';
    btnsDiv.style.gap = '5px';

    if (!isActive) {
        let btnAct = document.createElement('button');
        btnAct.className = 'action-btn';
        btnAct.innerText = isDownloaded ? getTranslation('db_btn_activate') : getTranslation('db_btn_download');
        btnAct.onclick = async () => {
            let msgEl = document.getElementById('db-status-msg');
            if (fileName === 'local') {
                localStorage.setItem('active_db_name', 'local');
                reloadAppLogic("Встроенная база активирована!");
            } else if (isDownloaded) {
                localStorage.setItem('active_db_name', fileName);
                reloadAppLogic(`База ${fileName} активирована!`);
            } else if (downloadUrl) {
                msgEl.innerText = "Скачивание...";
                try {
                    let res = await fetch(downloadUrl + "?t=" + Date.now());
                    let data = await res.json();
                    
                    let savedDbs = JSON.parse(localStorage.getItem('saved_dbs') || '{}');
                    savedDbs[fileName] = data;
                    localStorage.setItem('saved_dbs', JSON.stringify(savedDbs));
                    localStorage.setItem('active_db_name', fileName);
                    
                    reloadAppLogic(`База скачана и активирована!`);
                } catch (e) {
                    msgEl.innerText = "Ошибка скачивания базы!";
                    console.error(e);
                }
            }
        };
        btnsDiv.appendChild(btnAct);
    }

    if (isDownloaded && fileName !== 'local') {
        let btnDel = document.createElement('button');
        btnDel.className = 'action-btn';
        btnDel.style.backgroundColor = '#f38ba8';
        btnDel.style.color = '#11111b';
        btnDel.innerText = getTranslation('db_btn_delete');
        btnDel.onclick = () => {
            let savedDbs = JSON.parse(localStorage.getItem('saved_dbs') || '{}');
            delete savedDbs[fileName];
            localStorage.setItem('saved_dbs', JSON.stringify(savedDbs));
            
            if (isActive) {
                localStorage.setItem('active_db_name', 'local');
                reloadAppLogic("Активная база удалена. Возврат на встроенную.");
            } else {
                renderDbList();
            }
        };
        btnsDiv.appendChild(btnDel);
    }

    row.appendChild(infoDiv);
    row.appendChild(btnsDiv);
    return row;
}

async function reloadAppLogic(msg) {
    let msgEl = document.getElementById('db-status-msg');
    if (msgEl) msgEl.innerText = msg;
    
    if (bgWindow && bgWindow.marvelLogic) {
        bgWindow.marvelLogic.isReady = false;
        await bgWindow.marvelLogic.init();
        renderDbList();
        initData();
    }
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
        langSelect.value = localStorage.getItem('language') || 'en';
        langSelect.addEventListener('change', (e) => {
            localStorage.setItem('language', e.target.value);
            applyTranslations();
            updateMapsOptions();
            updateManualCounterpicks();
            renderTierList();
            loadMdContent();
            renderDbList();
            let countEl = document.getElementById('cp-heroes-count');
            if (countEl && bgWindow.marvelLogic) {
                countEl.innerText = getTranslation('total_heroes', {count: bgWindow.marvelLogic.allHeroes.length});
            }
        });
    }

    applyTranslations();

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

    let btnCheckDb = document.getElementById('btn-check-db');
    if (btnCheckDb) {
        btnCheckDb.addEventListener('click', async () => {
            let msgEl = document.getElementById('db-status-msg');
            msgEl.innerText = "Ищем файлы в папке stats на GitHub...";
            try {
                let res = await fetch(DB_GITHUB_API + "&t=" + Date.now());
                if (!res.ok) throw new Error("GitHub API Error");
                let files = await res.json();
                
                let jsonFiles = files.filter(f => f.name.endsWith('.json'));
                
                msgEl.innerText = `Найдено баз: ${jsonFiles.length}`;
                setTimeout(() => { if(msgEl.innerText.includes("Найдено")) msgEl.innerText = ""; }, 3000);
                
                renderDbList(jsonFiles);
            } catch (e) {
                msgEl.innerText = "Ошибка. Возможно, превышен лимит запросов GitHub API (60 в час).";
                console.error(e);
            }
        });
    }

    initData();
});