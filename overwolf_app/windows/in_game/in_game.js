let bgWindow = overwolf.windows.getMainWindow();

overwolf.windows.onMessageReceived.addListener((message) => {
    if (message.id === "update_data") {
        renderUI(message.content);
    }
});

function getHeroImage(name) {
    let formatted = name.toLowerCase().replace(/[- ]/g, '_');
    return `../../resources/heroes_icons/${formatted}_1.png`;
}

function getHeroRole(heroName) {
    if (!bgWindow || !bgWindow.marvelLogic || !bgWindow.marvelLogic.heroRoles) return null;
    let roles = bgWindow.marvelLogic.heroRoles;
    for (let role in roles) {
        if (roles[role].includes(heroName)) return role.toLowerCase();
    }
    return null;
}

function createHeroIcon(name, rating = null, isEffective = false, isAlly = false) {
    let div = document.createElement('div');
    div.className = 'hero-icon';
    
    // Рамка роли
    let role = getHeroRole(name);
    if (role) div.classList.add(`role-${role}`);
    
    div.style.backgroundImage = `url('${getHeroImage(name)}')`;
    
    // Значки статуса (Галочка / Восклицательный знак)
    if (isAlly) {
        let badge = document.createElement('div');
        badge.className = 'status-badge status-ally';
        badge.innerText = '✓';
        div.appendChild(badge);
    } else if (isEffective) {
        let badge = document.createElement('div');
        badge.className = 'status-badge status-priority';
        badge.innerText = '!';
        div.appendChild(badge);
    }
    
    // Рейтинг
    let showRating = localStorage.getItem('showRating') === 'true';
    if (rating !== null && showRating) {
        let rBadge = document.createElement('div');
        rBadge.className = 'rating-badge';
        rBadge.innerText = Math.round(rating);
        div.appendChild(rBadge);
    }
    return div;
}

function renderUI(data) {
    // Локализация
    document.getElementById('lbl-allies').innerText = getTranslation('tray_allies');
    document.getElementById('lbl-enemies').innerText = getTranslation('tray_enemies');
    document.getElementById('map-name').innerText = data.map || getTranslation('tray_waiting');

    let alliesList = document.getElementById('allies-list');
    alliesList.innerHTML = '';
    data.ally_heroes.forEach(h => alliesList.appendChild(createHeroIcon(h)));

    let enemiesList = document.getElementById('enemies-list');
    enemiesList.innerHTML = '';
    data.enemy_heroes.forEach(h => enemiesList.appendChild(createHeroIcon(h)));

    let countersList = document.getElementById('counters-list');
    countersList.innerHTML = '';
    
    let hideAllies = localStorage.getItem('hideAllies') === 'true';
    let priorityFirst = localStorage.getItem('priorityFirst') === 'true';
    let favoritesFirst = localStorage.getItem('favoritesFirst') === 'true';
    let favorites = JSON.parse(localStorage.getItem('favoriteHeroes') || '[]');

    let counters = Object.entries(data.counter_scores).sort((a, b) => b[1] - a[1]);
    
    if (hideAllies) {
        counters = counters.filter(([hero, score]) => !data.ally_heroes.includes(hero));
    }

    // Фильтрация забаненных героев
    if (data.banned_heroes && data.banned_heroes.length > 0) {
        counters = counters.filter(([hero, score]) => !data.banned_heroes.includes(hero));
    }

    if (priorityFirst) {
        counters.sort((a, b) => {
            let aPrior = data.effective_team.includes(a[0]) ? 1 : 0;
            let bPrior = data.effective_team.includes(b[0]) ? 1 : 0;
            return bPrior - aPrior;
        });
    }

    if (favoritesFirst) {
        counters.sort((a, b) => {
            let aFav = favorites.includes(a[0]) ? 1 : 0;
            let bFav = favorites.includes(b[0]) ? 1 : 0;
            return bFav - aFav;
        });
    }

    counters.forEach(([hero, score]) => {
        if (score > 0 || data.effective_team.includes(hero)) {
            let isEffective = data.effective_team.includes(hero);
            let isAlly = data.ally_heroes.includes(hero);
            countersList.appendChild(createHeroIcon(hero, score, isEffective, isAlly));
        }
    });
}

// При старте окна запрашиваем текущие данные у Background и применяем ширину
if (bgWindow && bgWindow.latestData) {
    renderUI(bgWindow.latestData);
}

let tw = parseInt(localStorage.getItem('trayWidth')) || 800;
overwolf.windows.getCurrentWindow(res => {
    if (res.window.width !== tw) {
        overwolf.windows.changeSize(res.window.id, tw, 180);
    }
});