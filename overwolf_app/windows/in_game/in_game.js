let bgWindow = overwolf.windows.getMainWindow();

overwolf.windows.onMessageReceived.addListener((message) => {
    if (message.id === "update_data") {
        renderUI(message.content);
    }
});

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

function applyMapImage(element, mapName) {
    if (!mapName) {
        element.style.backgroundImage = 'none';
        return;
    }
    let imgName = mapName.toUpperCase();
    let localUrl = `../../resources/maps/${imgName}.png`;
    let githubUrl = `https://raw.githubusercontent.com/Sankyuubigan/rivals_counter_peaks/master/overwolf_app/resources/maps/${imgName}.png`;

    if (imageCache['MAP_' + mapName] === 'not_found') {
        element.style.backgroundImage = 'none';
        return;
    } else if (imageCache['MAP_' + mapName]) {
        element.style.backgroundImage = `url('${imageCache['MAP_' + mapName]}')`;
        return;
    }

    element.style.backgroundImage = `url('${localUrl}')`;
    let img = new Image();
    img.onload = () => { imageCache['MAP_' + mapName] = localUrl; };
    img.onerror = () => {
        let imgGit = new Image();
        imgGit.onload = () => { 
            imageCache['MAP_' + mapName] = githubUrl; 
            element.style.backgroundImage = `url('${githubUrl}')`; 
        };
        imgGit.onerror = () => { 
            imageCache['MAP_' + mapName] = 'not_found'; 
            element.style.backgroundImage = 'none'; 
        };
        imgGit.src = githubUrl;
    };
    img.src = localUrl;
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
    
    let role = getHeroRole(name);
    if (role) div.classList.add(`role-${role}`);
    
    applyHeroImage(div, name);
    
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
    document.getElementById('lbl-allies').innerText = getTranslation('tray_allies');
    document.getElementById('lbl-enemies').innerText = getTranslation('tray_enemies');
    
    let mapContainer = document.getElementById('map-box-container');
    let mapWarning = document.getElementById('map-not-found-warning');
    
    document.getElementById('map-name').innerText = data.map || getTranslation('tray_waiting');

    if (data.map) {
        applyMapImage(mapContainer, data.map);
        
        if (data.is_map_effective) {
            mapContainer.classList.add('map-box-active');
            mapWarning.style.display = 'none';
        } else {
            mapContainer.classList.remove('map-box-active');
            mapWarning.style.display = 'block';
            mapWarning.innerText = getTranslation('map_not_found');
        }
    } else {
        mapContainer.style.backgroundImage = 'none';
        mapContainer.classList.remove('map-box-active');
        mapWarning.style.display = 'none';
    }

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
    let favoriteTeamups = JSON.parse(localStorage.getItem('favoriteTeamups') || '[]');

    let countersScores = Object.assign({}, data.counter_scores);

    if (favoritesFirst && bgWindow.marvelLogic && bgWindow.marvelLogic.applyFavoriteTeamupBonus) {
        countersScores = bgWindow.marvelLogic.applyFavoriteTeamupBonus(
            countersScores, data.ally_heroes, favoriteTeamups
        );
    }

    let counters = Object.entries(countersScores).sort((a, b) => b[1] - a[1]);
    
    if (hideAllies) {
        counters = counters.filter(([hero, score]) => !data.ally_heroes.includes(hero));
    }

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

    counters.forEach(([hero, score]) => {
        let isAlly = data.ally_heroes.includes(hero);
        let isEffective = data.effective_team.includes(hero);
        
        if (score > 0 || isEffective || isAlly) {
            countersList.appendChild(createHeroIcon(hero, score, isEffective, isAlly));
        }
    });
}

if (bgWindow && bgWindow.latestData) {
    renderUI(bgWindow.latestData);
}

let tw = parseInt(localStorage.getItem('trayWidth')) || 800;
overwolf.windows.getCurrentWindow(res => {
    if (res.window.width !== tw) {
        overwolf.windows.changeSize(res.window.id, tw, 180);
    }
});