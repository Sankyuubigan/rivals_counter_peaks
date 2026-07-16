// === DEBUG ONLY: панель ручного ввода матча для проверки UI без игры ===
(function () {
    const panel = document.getElementById('debug-panel');
    if (!panel) return;

    let selectedEnemies = [];
    let selectedAllies = [];
    let selectedBans = [];
    let selectedMap = "";

    async function ensureReady() {
        if (window.__debugReady) await window.__debugReady;
    }

    function heroBtn(name, store, color) {
        const btn = document.createElement('button');
        btn.className = 'dbg-hero-btn';
        btn.title = name;
        btn.style.borderColor = color;
        // иконка через тот же механизм, что в desktop.js
        if (typeof applyHeroImage === 'function') applyHeroImage(btn, name);
        else btn.innerText = name.substring(0, 4);
        btn.onclick = () => {
            const idx = store.indexOf(name);
            if (idx >= 0) {
                store.splice(idx, 1);
                btn.classList.remove('dbg-selected');
            } else {
                if (store.length >= 6) {
                    alert('Максимум 6 героев в этом поле');
                    return;
                }
                store.push(name);
                btn.classList.add('dbg-selected');
            }
            updateCounts();
        };
        btn._name = name;
        btn._store = store;
        return btn;
    }

    function buildGrid(container, store, color) {
        container.innerHTML = '';
        if (!window.marvelLogic || !window.marvelLogic.allHeroes) {
            container.innerHTML = '<div style="color:#f38ba8;padding:10px">База ещё не загружена...</div>';
            return;
        }
        window.marvelLogic.allHeroes.forEach(h => {
            container.appendChild(heroBtn(h, store, color));
        });
    }

    function updateCounts() {
        document.getElementById('dbg-enemies-count').innerText =
            `Враги (${selectedEnemies.length}/6): ${selectedEnemies.join(', ')}`;
        document.getElementById('dbg-allies-count').innerText =
            `Союзники (${selectedAllies.length}/6): ${selectedAllies.join(', ')}`;
        document.getElementById('dbg-bans-count').innerText =
            `Баны (${selectedBans.length}): ${selectedBans.join(', ')}`;
    }

    function renderPanel() {
        panel.innerHTML = `
            <div class="dbg-panel-header">
                <button class="dbg-btn" id="dbg-toggle" title="Свернуть/развернуть панель">▾ DEBUG</button>
                <span class="dbg-hint">кликай по иконкам, затем «Применить»</span>
                <button class="dbg-btn" id="dbg-apply">Применить</button>
                <button class="dbg-btn" id="dbg-random">Случайный матч</button>
                <button class="dbg-btn" id="dbg-clear">Очистить</button>
            </div>
            <div id="dbg-body">
                <div id="dbg-status" style="margin-top:6px; font-size:11px; color:#a6e3a1;">Загрузка базы...</div>
                <div class="dbg-row">
                    <div class="dbg-col">
                        <div class="dbg-col-title" style="color:#f38ba8">ВРАГИ</div>
                        <div class="dbg-grid" id="dbg-enemies-grid"></div>
                        <div class="dbg-count" id="dbg-enemies-count">Враги (0/6):</div>
                    </div>
                    <div class="dbg-col">
                        <div class="dbg-col-title" style="color:#a6e3a1">СОЮЗНИКИ</div>
                        <div class="dbg-grid" id="dbg-allies-grid"></div>
                        <div class="dbg-count" id="dbg-allies-count">Союзники (0/6):</div>
                    </div>
                    <div class="dbg-col">
                        <div class="dbg-col-title" style="color:#f9e2af">БАНЫ</div>
                        <div class="dbg-grid" id="dbg-bans-grid"></div>
                        <div class="dbg-count" id="dbg-bans-count">Баны (0):</div>
                    </div>
                    <div class="dbg-col dbg-col-map">
                        <div class="dbg-col-title">КАРТА</div>
                        <select id="dbg-map-select"><option value="">Без карты</option></select>
                        <div class="dbg-col-title" style="margin-top:10px">Язык</div>
                        <select id="dbg-lang">
                            <option value="en">English</option>
                            <option value="ru">Русский</option>
                        </select>
                        <label class="dbg-check"><input type="checkbox" id="dbg-hide-allies"> скрыть союзников</label>
                        <label class="dbg-check"><input type="checkbox" id="dbg-show-rating"> рейтинг</label>
                        <label class="dbg-check"><input type="checkbox" id="dbg-priority-first"> приоритет (!)</label>
                        <label class="dbg-check"><input type="checkbox" id="dbg-favorites-first"> избранные first</label>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('dbg-toggle').onclick = togglePanel;

        buildGrid(document.getElementById('dbg-enemies-grid'), selectedEnemies, '#f38ba8');
        buildGrid(document.getElementById('dbg-allies-grid'), selectedAllies, '#a6e3a1');
        buildGrid(document.getElementById('dbg-bans-grid'), selectedBans, '#f9e2af');

        const mapSel = document.getElementById('dbg-map-select');
        if (window.marvelLogic && window.marvelLogic.availableMaps) {
            window.marvelLogic.availableMaps.forEach(m => {
                const o = document.createElement('option');
                o.value = m; o.innerText = m;
                mapSel.appendChild(o);
            });
        }
        mapSel.value = selectedMap;
        mapSel.onchange = () => { selectedMap = mapSel.value; };

        document.getElementById('dbg-apply').onclick = applyMatch;
        document.getElementById('dbg-clear').onclick = () => {
            selectedEnemies = []; selectedAllies = []; selectedBans = []; selectedMap = "";
            renderPanel();
            resetResults();
        };
        document.getElementById('dbg-random').onclick = randomMatch;

        updateCounts();
    }

    function resetResults() {
        window.latestData = {
            map: null, is_map_effective: false,
            enemy_heroes: [], ally_heroes: [], banned_heroes: [],
            counter_scores: {}, effective_team: []
        };
        if (typeof updateManualCounterpicks === 'function') updateManualCounterpicks();
        if (typeof renderTierList === 'function') renderTierList();
    }

    function applyMatch() {
        if (!window.marvelLogic || !window.marvelLogic.isReady) {
            alert('База данных ещё загружается, подождите...');
            return;
        }

        // Настройки localStorage (как в desktop.js renderUI)
        localStorage.setItem('hideAllies', document.getElementById('dbg-hide-allies').checked ? 'true' : 'false');
        localStorage.setItem('showRating', document.getElementById('dbg-show-rating').checked ? 'true' : 'false');
        localStorage.setItem('priorityFirst', document.getElementById('dbg-priority-first').checked ? 'true' : 'false');
        localStorage.setItem('favoritesFirst', document.getElementById('dbg-favorites-first').checked ? 'true' : 'false');
        localStorage.setItem('language', document.getElementById('dbg-lang').value);
        if (typeof applyTranslations === 'function') applyTranslations();

        // Логика как в background.js processGameData (без Overwolf)
        const logic = window.marvelLogic;
        const enemyHeroes = selectedEnemies.slice();
        const allyHeroes = selectedAllies.slice();
        const bannedHeroes = selectedBans.slice();

        let finalMapName = selectedMap;
        let isMapEffective = false;
        if (finalMapName) {
            const resolved = logic.resolveMapName(finalMapName);
            finalMapName = logic.availableMaps.find(m => m.toLowerCase() === resolved.toLowerCase()) || resolved;
            isMapEffective = logic.doesMapAffectScores(finalMapName);
        }

        const activeEnemies = enemyHeroes.filter(h => !bannedHeroes.includes(h));
        let result;
        if (activeEnemies.length === 0) {
            const tierScores = logic.calculateTierListScoresWithMap(finalMapName);
            result = {
                scores: tierScores,
                optimalTeam: allyHeroes.length > 0 ? logic.getRecommendedHeroes(tierScores, allyHeroes, bannedHeroes) : []
            };
        } else {
            result = logic.calculateCounterScoresForTeam(activeEnemies, finalMapName);
            result.optimalTeam = allyHeroes.length > 0 ? logic.getRecommendedHeroes(result.scores, allyHeroes, bannedHeroes) : [];
        }

        window.latestData = {
            map: finalMapName,
            is_map_effective: isMapEffective,
            enemy_heroes: enemyHeroes,
            ally_heroes: allyHeroes,
            banned_heroes: bannedHeroes,
            counter_scores: result.scores,
            effective_team: result.optimalTeam
        };

        // Перерисовываем вкладки desktop-окна
        if (typeof updateManualCounterpicks === 'function') updateManualCounterpicks();
        if (typeof renderTierList === 'function') renderTierList();

        console.log('[DEBUG] Применён матч:', window.latestData);
    }

    function randomMatch() {
        if (!window.marvelLogic || !window.marvelLogic.isReady) {
            alert('База данных ещё загружается, подождите...');
            return;
        }
        const all = window.marvelLogic.allHeroes.slice();
        function pick(n) {
            const out = [];
            const pool = all.slice();
            for (let i = 0; i < n && pool.length; i++) {
                out.push(pool.splice(Math.floor(Math.random() * pool.length), 1)[0]);
            }
            return out;
        }
        selectedEnemies = pick(6);
        selectedAllies = pick(2);
        selectedBans = pick(2);
        const maps = window.marvelLogic.availableMaps;
        selectedMap = maps.length ? maps[Math.floor(Math.random() * maps.length)] : "";
        renderPanel();
        applyMatch();
    }

    let panelCollapsed = false;
    function togglePanel() {
        panelCollapsed = !panelCollapsed;
        const body = document.getElementById('dbg-body');
        const btn = document.getElementById('dbg-toggle');
        if (!body || !btn) return;
        body.style.display = panelCollapsed ? 'none' : 'block';
        btn.innerText = (panelCollapsed ? '▸ ' : '▾ ') + 'DEBUG';
    }

    ensureReady().then(() => {
        renderPanel();
        const st = document.getElementById('dbg-status');
        if (st) {
            if (window.marvelLogic && window.marvelLogic.isReady) {
                st.style.color = '#a6e3a1';
                st.innerText = `БД загружена: героев ${window.marvelLogic.allHeroes.length}, карт ${window.marvelLogic.availableMaps.length}`;
            } else {
                st.style.color = '#f38ba8';
                st.innerText = 'ОШИБКА загрузки базы (смотри консоль F12)';
            }
        }
    });
})();
