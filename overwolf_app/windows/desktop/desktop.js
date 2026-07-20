let bgWindow = overwolf.windows.getMainWindow();
let manualSelectedEnemies =[];

function getLogStore() {
    if (!window.appLogs) window.appLogs = [];
    // В debug-режиме bgWindow === window, поэтому синхронизируем явно,
    // чтобы логгер (desktop-debug.html) и refreshLogs смотрели в один массив.
    if (bgWindow && bgWindow !== window && !bgWindow.appLogs) {
        try { bgWindow.appLogs = window.appLogs; } catch (_) {}
    }
    if (bgWindow && bgWindow.appLogs && bgWindow.appLogs !== window.appLogs) {
        // отдаём тот же массив, что наполняет логгер
        window.appLogs = bgWindow.appLogs;
    }
    return window.appLogs;
}

// Устанавливаем перехват console только если он ещё не установлен
// (в debug-режиме логгер уже поднят в desktop-debug.html до logic.js).
if (!window.__appLoggerInstalled) {
    window.__appLoggerInstalled = true;

    const origDesktopLog = console.log.bind(console);
    const origDesktopWarn = console.warn.bind(console);
    const origDesktopError = console.error.bind(console);

    const writeToLogStore = function(level, args) {
        const text = Array.from(args).map(a => {
            if (typeof a === 'object' && a !== null) {
                try { return JSON.stringify(a); } catch (_) { return String(a); }
            }
            return String(a);
        }).join(' ');
        const store = getLogStore();
        store.push(`[${new Date().toLocaleTimeString()}][${level}] ${text}`);
        if (store.length > 1000) store.shift();
    };

    console.log = function(...args) { origDesktopLog(...args); writeToLogStore('UI_LOG', args); };
    console.warn = function(...args) { origDesktopWarn(...args); writeToLogStore('UI_WARN', args); };
    console.error = function(...args) { origDesktopError(...args); writeToLogStore('UI_ERROR', args); };

    window.addEventListener('error', function(ev) {
        writeToLogStore('JS_ERROR', [`${ev.message} @ ${ev.filename}:${ev.lineno}:${ev.colno}`]);
    });
    window.addEventListener('unhandledrejection', function(ev) {
        let reason = ev.reason;
        let msg = (reason && reason.stack) ? reason.stack : (reason && reason.message ? reason.message : String(reason));
        writeToLogStore('PROMISE_REJECT', [msg]);
    });
}

const imageCache = {};

function applyHeroImage(element, heroName) {
    if (!heroName) return;
    let formatted = (bgWindow && bgWindow.marvelLogic ? bgWindow.marvelLogic.heroIconName(heroName) : heroName.toLowerCase().trim().replace(/\s*\&\s*/g, ' ').replace(/\(([^)]+)\)/g, ' $1').replace(/[^\w-]+/g, ' ').trim().replace(/[\s-]+/g, '_'));
    let localUrl = `../../resources/heroes_icons/${formatted}.png`;
    let githubUrl = `https://raw.githubusercontent.com/Sankyuubigan/rivals_counter_peaks/master/overwolf_app/resources/heroes_icons/${formatted}.png`;

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
    renderList(container, result.scores, result.optimalTeam, []);
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
    renderList(container, scores, [], []);
}

function renderList(container, scores, effectiveTeam, allyHeroes = []) {
    container.innerHTML = '';

    let favoriteTeamups = JSON.parse(localStorage.getItem('favoriteTeamups') || '[]');
    let favoritesFirst = localStorage.getItem('favoritesFirst') === 'true';
    if (favoritesFirst && bgWindow.marvelLogic && bgWindow.marvelLogic.applyFavoriteTeamupBonus) {
        scores = bgWindow.marvelLogic.applyFavoriteTeamupBonus(scores, allyHeroes, favoriteTeamups);
    }

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

function heroKeyNorm(s) {
    // приводим имена к сравнимому виду: убираем &, пробелы, дефисы, подчёркивания,
    // скобки и прочие не-буквы -> остаются только буквы в lower-case.
    // "Cloak & Dagger" -> "cloakdagger", "cloak-dagger" -> "cloakdagger" (совпадает)
    return String(s).toLowerCase().replace(/[^a-zа-яё0-9]/g, '');
}

function getHeroRoleSafe(heroName) {
    if (!heroName || !bgWindow.marvelLogic) return null;
    let logic = bgWindow.marvelLogic;
    let n = heroKeyNorm(heroName);

    // 1. по heroRoles (имена с пробелами/скобками)
    let roles = logic.heroRoles;
    if (roles) {
        for (let role in roles) {
            if ((roles[role] || []).some(h => heroKeyNorm(h) === n)) return role;
        }
    }
    // 2. напрямую по statsData (ключи совпадают с именами heroRoles)
    let stats = logic.statsData;
    if (stats) {
        if (stats[heroName] && stats[heroName].role) return stats[heroName].role;
        for (let h in stats) {
            if (heroKeyNorm(h) === n && stats[h] && stats[h].role) return stats[h].role;
        }
    }
    return null;
}

function renderFavoritesGrid() {
    let grid = document.getElementById('favorites-grid');
    grid.innerHTML = '';
    if (!bgWindow.marvelLogic || !bgWindow.marvelLogic.teamupsData) return;

    let savedFavorites = JSON.parse(localStorage.getItem('favoriteTeamups') || '[]');

    let tierOrder = { 'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4 };
    let roleColumns = [
        { role: 'Vanguard', title: getTranslation('role_vanguard') },
        { role: 'Duelist', title: getTranslation('role_duelist') },
        { role: 'Strategist', title: getTranslation('role_strategist') }
    ];
    let knownRoles = roleColumns.map(c => c.role);

    let teamups = bgWindow.marvelLogic.teamupsData;

    // группируем тимапы по герою-получателю (heroes[0])
    let byHero = {};
    teamups.forEach(tu => {
        let receiver = tu.heroes && tu.heroes[0];
        if (!receiver) return;
        if (!byHero[receiver]) byHero[receiver] = [];
        byHero[receiver].push(tu);
    });

    let receivers = Object.keys(byHero);

    receivers.sort((a, b) => {
        // внутри роли: по максимальному тиру тимапов (S вверху)
        let bestA = Math.min(...byHero[a].map(t => tierOrder[t.tier] ?? 99));
        let bestB = Math.min(...byHero[b].map(t => tierOrder[t.tier] ?? 99));
        if (bestA !== bestB) return bestA - bestB;
        return a.localeCompare(b);
    });

    function makeCard(hero) {
        let card = document.createElement('div');
        card.className = 'teamup-card';

        let main = document.createElement('div');
        main.className = 'teamup-main';
        applyHeroImage(main, hero);
        main.title = hero;
        card.appendChild(main);

        let minis = document.createElement('div');
        minis.className = 'teamup-minis';

        byHero[hero].forEach(tu => {
            let giver = tu.heroes[1];
            let mini = document.createElement('div');
            mini.className = 'teamup-mini';
            applyHeroImage(mini, giver);
            mini.title = `${tu.name} (${tu.heroes[0]} + ${giver})`;
            if (savedFavorites.includes(tu.name)) mini.classList.add('selected');

            mini.onclick = () => {
                mini.classList.toggle('selected');
                let current = JSON.parse(localStorage.getItem('favoriteTeamups') || '[]');
                if (mini.classList.contains('selected')) {
                    if (!current.includes(tu.name)) current.push(tu.name);
                } else {
                    current = current.filter(n => n !== tu.name);
                }
                localStorage.setItem('favoriteTeamups', JSON.stringify(current));
            };
            minis.appendChild(mini);
        });

        card.appendChild(minis);
        return card;
    }

    // карточки без известной роли не теряем — складываем в отдельную колонку
    let unknownWrap = null;
    let unknownCount = 0;

    roleColumns.forEach(col => {
        let colWrap = document.createElement('div');
        colWrap.className = 'favorites-col';

        let title = document.createElement('div');
        title.className = 'favorites-col-title';
        title.textContent = col.title;
        colWrap.appendChild(title);

        receivers.forEach(hero => {
            let role = getHeroRoleSafe(hero);
            if (role && role !== col.role) return;
            if (!role) {
                // без роли — откладываем в колонку "Прочие"
                unknownCount++;
                return;
            }
            colWrap.appendChild(makeCard(hero));
        });

        grid.appendChild(colWrap);
    });

    if (unknownCount > 0) {
        unknownWrap = document.createElement('div');
        unknownWrap.className = 'favorites-col';
        let ut = document.createElement('div');
        ut.className = 'favorites-col-title';
        ut.textContent = getTranslation('role_other', { count: unknownCount });
        unknownWrap.appendChild(ut);
        receivers.forEach(hero => {
            if (!getHeroRoleSafe(hero)) unknownWrap.appendChild(makeCard(hero));
        });
        grid.appendChild(unknownWrap);
    }
}

function appLog(...args) {
    console.log('[DESKTOP]', ...args);
}

function appLogError(...args) {
    console.error('[DESKTOP]', ...args);
}

function refreshLogs() {
    let logs = getLogStore();
    let ta = document.getElementById('logs-area');
    if (!ta) return;
    ta.value = logs.join('\n');
    ta.scrollTop = ta.scrollHeight;
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

let _logsTimer = null;
function openTab(tabId, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
    if (tabId === 'logs') {
        refreshLogs();
        if (!_logsTimer) _logsTimer = setInterval(() => { if (document.getElementById('logs').classList.contains('active')) refreshLogs(); }, 1500);
    }
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
                const url = downloadUrl + "?t=" + Date.now();
                appLog(`Скачивание базы "${fileName}" с ${url}`);
                try {
                    let res;
                    try {
                        res = await fetch(url);
                    } catch (netErr) {
                        throw new Error(`Сетевая ошибка при запросе к ${url}: ${netErr && netErr.message ? netErr.message : netErr}`);
                    }

                    appLog(`Ответ сервера: HTTP ${res.status} ${res.statusText}`);

                    if (!res.ok) {
                        let bodyText = '';
                        try { bodyText = await res.text(); } catch (_) {}
                        throw new Error(`HTTP ${res.status} ${res.statusText}. Тело ответа: ${bodyText.slice(0, 500)}`);
                    }

                    let rawText = await res.text();
                    let data;
                    try {
                        data = JSON.parse(rawText);
                    } catch (parseErr) {
                        throw new Error(`Не удалось распарсить JSON (${parseErr.message}). Начало ответа: ${rawText.slice(0, 300)}`);
                    }

                    if (!data || (typeof data === 'object' && !data.heroes && !data.teamups)) {
                        throw new Error(`Скачанный файл не похож на базу данных (нет полей heroes/teamups). Ключи: ${data && typeof data === 'object' ? Object.keys(data).join(', ') : typeof data}`);
                    }

                    let savedDbs = JSON.parse(localStorage.getItem('saved_dbs') || '{}');
                    savedDbs[fileName] = data;
                    try {
                        localStorage.setItem('saved_dbs', JSON.stringify(savedDbs));
                    } catch (storageErr) {
                        throw new Error(`Не удалось сохранить в localStorage (возможно, превышен лимит): ${storageErr.message}`);
                    }
                    localStorage.setItem('active_db_name', fileName);

                    appLog(`База "${fileName}" успешно скачана и сохранена.`);
                    reloadAppLogic(`База скачана и активирована!`);
                } catch (e) {
                    let details = e && e.message ? e.message : String(e);
                    msgEl.innerText = "Ошибка скачивания базы: " + details;
                    appLogError(`Ошибка скачивания базы "${fileName}": ${details}`);
                    if (e && e.stack) appLogError(`Stack: ${e.stack}`);
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

    let favBonusInput = document.getElementById('setting-fav-bonus');
    if (favBonusInput) {
        favBonusInput.value = localStorage.getItem('favTeamupBonus') || 25;
        favBonusInput.addEventListener('change', e => {
            let val = parseInt(e.target.value, 10);
            if (isNaN(val)) val = 25;
            val = Math.max(0, Math.min(100, val));
            localStorage.setItem('favTeamupBonus', String(val));
            if (bgWindow && bgWindow.marvelLogic) bgWindow.marvelLogic.FAVORITE_TEAMUP_BONUS = val;
            updateManualCounterpicks();
            renderTierList();
        });
    }

    let langSelect = document.getElementById('setting-language');
    if (langSelect) {
        langSelect.value = localStorage.getItem('language') || 'en';
        langSelect.addEventListener('change', (e) => {
            localStorage.setItem('language', e.target.value);
            applyTranslations();
            updateMapsOptions();
            renderFavoritesGrid();
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
            const apiUrl = DB_GITHUB_API + "&t=" + Date.now();
            appLog(`Запрос списка баз: ${apiUrl}`);
            try {
                let res;
                try {
                    res = await fetch(apiUrl);
                } catch (netErr) {
                    throw new Error(`Сетевая ошибка (возможно CORS) при запросе к GitHub API: ${netErr && netErr.message ? netErr.message : netErr}`);
                }
                appLog(`Ответ GitHub API: HTTP ${res.status} ${res.statusText}`);
                if (!res.ok) {
                    let bodyText = '';
                    try { bodyText = await res.text(); } catch (_) {}
                    throw new Error(`GitHub API HTTP ${res.status} ${res.statusText}. Тело: ${bodyText.slice(0, 500)}`);
                }
                let files = await res.json();
                if (!Array.isArray(files)) {
                    throw new Error(`GitHub API вернул не массив. Ответ: ${JSON.stringify(files).slice(0, 500)}`);
                }

                let jsonFiles = files.filter(f => f.name.endsWith('.json'));
                appLog(`Найдено .json файлов: ${jsonFiles.length} (${jsonFiles.map(f => f.name).join(', ')})`);

                msgEl.innerText = `Найдено баз: ${jsonFiles.length}`;
                setTimeout(() => { if(msgEl.innerText.includes("Найдено")) msgEl.innerText = ""; }, 3000);

                renderDbList(jsonFiles);
            } catch (e) {
                let details = e && e.message ? e.message : String(e);
                msgEl.innerText = "Ошибка получения списка баз: " + details;
                appLogError(`Ошибка получения списка баз с GitHub: ${details}`);
                if (e && e.stack) appLogError(`Stack: ${e.stack}`);
            }
        });
    }

    initData();
});