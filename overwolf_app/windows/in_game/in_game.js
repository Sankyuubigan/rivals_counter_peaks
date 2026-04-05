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

function createHeroIcon(name, rating = null, isEffective = false) {
    let div = document.createElement('div');
    div.className = 'hero-icon';
    if (isEffective) div.classList.add('effective');
    div.style.backgroundImage = `url('${getHeroImage(name)}')`;
    
    let showRating = localStorage.getItem('showRating') === 'true';
    if (rating !== null && showRating) {
        let badge = document.createElement('div');
        badge.className = 'rating-badge';
        badge.innerText = Math.round(rating);
        div.appendChild(badge);
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
            countersList.appendChild(createHeroIcon(hero, score, isEffective));
        }
    });
}

// При старте окна запрашиваем текущие данные у Background
if (bgWindow && bgWindow.latestData) {
    renderUI(bgWindow.latestData);
}