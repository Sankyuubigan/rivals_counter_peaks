class CounterpickLogic {
    constructor() {
        this.statsData = {};
        this.gameEntities = {};
        this.teamupsData =[];
        this.heroRoles = {};
        this.matchupsData = {};
        this.heroStatsData = {};
        this.allHeroes =[];
        this.availableMaps =[];
        this.SYNERGY_BONUS = 10.0;
        this.isReady = false;
    }

    async init() {
        try {
            const statsRes = await fetch('database/stats.json');
            const fullData = await statsRes.json();
            
            const entitiesRes = await fetch('database/game_entities_dict.json');
            this.gameEntities = await entitiesRes.json();

            this.statsData = fullData.heroes || {};
            this.teamupsData = fullData.teamups ||[];
            this.allHeroes = Object.keys(this.statsData).sort();

            for (let hero of this.allHeroes) {
                let role = this.statsData[hero].role;
                if (role) {
                    if (!this.heroRoles[role]) this.heroRoles[role] =[];
                    this.heroRoles[role].push(hero);
                }

                this.matchupsData[hero] = this.statsData[hero].opponents ||[];

                let wrStr = this.statsData[hero].win_rate || "50%";
                let wr = parseFloat(wrStr.replace('%', '')) / 100;
                this.heroStatsData[hero] = { win_rate: wr };
            }

            let mapsSet = new Set();
            if (this.allHeroes.length > 0) {
                let firstHeroMaps = this.statsData[this.allHeroes[0]].maps ||[];
                for (let m of firstHeroMaps) {
                    if (m.map_name) mapsSet.add(this.resolveMapName(m.map_name));
                }
            }
            this.availableMaps = Array.from(mapsSet).sort();
            this.isReady = true;
        } catch (e) {
            console.error("Ошибка загрузки баз данных:", e);
        }
    }

    resolveMapName(rawName) {
        if (this.gameEntities.map_filename_to_name && this.gameEntities.map_filename_to_name[rawName]) {
            return this.gameEntities.map_filename_to_name[rawName];
        }
        return rawName;
    }

    normalizeHeroName(name) {
        if (!name) return "";
        let normalized = name.toLowerCase();
        normalized = normalized.replace(/[_ ]*v\d+$/, '');
        normalized = normalized.replace(/_\d+$/, '');
        
        const suffixes =["_icon", "_template", "_small", "_left", "_right", "_horizontal", "_adv", "_padded"];
        for (let s of suffixes) {
            if (normalized.endsWith(s)) normalized = normalized.slice(0, -s.length);
        }
        normalized = normalized.replace(/[-_]+/g, ' ').trim();

        const aliases = {
            "bruce banner": "Hulk",
            "deadpool duelist": "Deadpool (Duelist)",
            "deadpool strategist": "Deadpool (Strategist)",
            "deadpool vanguard": "Deadpool (Vanguard)"
        };

        if (aliases[normalized]) {
            let canonical = aliases[normalized];
            let found = this.allHeroes.find(h => h.toLowerCase() === canonical.toLowerCase());
            return found || canonical;
        }

        let found = this.allHeroes.find(h => h.toLowerCase() === normalized);
        if (found) return found;

        let capitalized = normalized.split(' ').map(p => p ? p[0].toUpperCase() + p.slice(1) : '').join(' ');
        found = this.allHeroes.find(h => h === capitalized);
        return found || capitalized || name;
    }

    getMapScore(heroName, mapName, minScore = 0, maxScore = 20) {
        let heroData = this.statsData[heroName];
        if (!heroData || !heroData.maps) return 0;

        let winRates =[];
        let targetMapWr = null;

        for (let m of heroData.maps) {
            let wr = parseFloat(m.win_rate.replace('%', ''));
            if (isNaN(wr)) continue;
            winRates.push(wr);
            
            let dbMapName = this.resolveMapName(m.map_name);
            if (dbMapName.toLowerCase() === mapName.toLowerCase()) {
                targetMapWr = wr;
            }
        }

        if (targetMapWr === null || winRates.length === 0) return 0;

        let minWr = Math.min(...winRates);
        let maxWr = Math.max(...winRates);

        if (minWr === maxWr) return minScore;

        let score = minScore + (targetMapWr - minWr) * (maxScore - minScore) / (maxWr - minWr);
        return Math.round(score * 100) / 100;
    }

    calculateTeamCounters(enemyTeam, isTierListCalc = false) {
        if (!enemyTeam || enemyTeam.length === 0) return[];
        let heroScores = {};

        for (let hero of this.allHeroes) {
            if (!isTierListCalc && enemyTeam.includes(hero)) continue;
            
            let totalDifference = 0;
            let foundMatchups = 0;
            let matchups = this.matchupsData[hero] ||[];

            for (let enemy of enemyTeam) {
                if (isTierListCalc && hero === enemy) continue;
                
                let matchup = matchups.find(m => m.opponent && m.opponent.toLowerCase() === enemy.toLowerCase());
                if (matchup) {
                    let diff = -parseFloat(matchup.difference.replace('%', ''));
                    if (!isNaN(diff)) {
                        totalDifference += diff;
                        foundMatchups++;
                    }
                }
            }

            if (foundMatchups > 0) {
                heroScores[hero] = totalDifference / foundMatchups;
            }
        }
        return Object.entries(heroScores).sort((a, b) => b[1] - a[1]);
    }

    absoluteWithContext(scoresTuples) {
        let originalScores =[];
        for (let [hero, score] of scoresTuples) {
            let overallWinrate = this.heroStatsData[hero] ? this.heroStatsData[hero].win_rate * 100 : 50.0;
            let contextFactor = overallWinrate / 50.0;
            let absoluteScore = (100 + score) * contextFactor;
            originalScores.push([hero, absoluteScore]);
        }

        if (originalScores.length === 0) return {};

        let values = originalScores.map(s => s[1]);
        let minScore = Math.min(...values);
        let maxScore = Math.max(...values);

        let finalScores = {};
        for (let [hero, originalScore] of originalScores) {
            if (maxScore === minScore) {
                finalScores[hero] = 50.5;
            } else {
                let displayScore = (originalScore - minScore) / (maxScore - minScore) * 99 + 1;
                finalScores[hero] = displayScore;
            }
        }
        return finalScores;
    }

    selectOptimalTeam(sortedScoresObj) {
        let sortedHeroes = Object.entries(sortedScoresObj).sort((a, b) => b[1] - a[1]);
        if (sortedHeroes.length === 0) return[];

        let vanguards =[], duelists = [], strategists = [];
        
        for (let [hero, score] of sortedHeroes) {
            let role = null;
            for (let r in this.heroRoles) {
                if (this.heroRoles[r].includes(hero)) { role = r; break; }
            }
            if (role === "Vanguard") vanguards.push([hero, score]);
            else if (role === "Duelist") duelists.push([hero, score]);
            else if (role === "Strategist") strategists.push([hero, score]);
        }

        let bestTeam =[];
        let bestScore = -Infinity;

        for (let v = 1; v <= 4; v++) {
            for (let s = 2; s <= 3; s++) {
                let d = 6 - v - s;
                if (d >= 0 && vanguards.length >= v && strategists.length >= s && duelists.length >= d) {
                    let teamCandidates =[
                        ...vanguards.slice(0, v),
                        ...strategists.slice(0, s),
                        ...duelists.slice(0, d)
                    ];

                    let baseScore = teamCandidates.reduce((sum, curr) => sum + curr[1], 0);
                    let teamNames = teamCandidates.map(c => c[0]);
                    
                    let synergyScore = 0;
                    for (let teamup of this.teamupsData) {
                        let heroesInTeamup = teamup.heroes ||[];
                        let isSubset = heroesInTeamup.every(h => teamNames.includes(h));
                        if (heroesInTeamup.length > 1 && isSubset) {
                            synergyScore += this.SYNERGY_BONUS;
                        }
                    }

                    let totalScore = baseScore + synergyScore;
                    if (totalScore > bestScore) {
                        bestScore = totalScore;
                        bestTeam = teamNames;
                    }
                }
            }
        }

        if (bestTeam.length === 0) {
            bestTeam = sortedHeroes.slice(0, 6).map(h => h[0]);
        }
        return bestTeam;
    }

    getRecommendedHeroes(sortedScoresObj, allyTeam = []) {
        let sortedHeroes = Object.entries(sortedScoresObj).sort((a, b) => b[1] - a[1]);
        
        let currentRoles = { Vanguard: 0, Duelist: 0, Strategist: 0 };
        for (let hero of allyTeam) {
            for (let r in this.heroRoles) {
                if (this.heroRoles[r].includes(hero)) {
                    currentRoles[r]++;
                    break;
                }
            }
        }

        let v = currentRoles.Vanguard;
        let d = currentRoles.Duelist;
        let s = currentRoles.Strategist;
        
        let neededRoles = [];
        
        // 1. Сначала смотреть Strategists: 2-3
        if (s < 2) {
            neededRoles.push("Strategist");
        } 
        // 2. Затем смотреть Vanguards: 1-2 
        else if (v < 1) {
            neededRoles.push("Vanguard");
        } 
        // 3. Затем смотреть Duelists 1-3 
        else if (d < 1) {
            neededRoles.push("Duelist");
        } 
        // 4. Если всё удовлетворяет минимальным требованиям, стремимся к 2-2-2
        else {
            if (v < 2) neededRoles.push("Vanguard");
            if (d < 2) neededRoles.push("Duelist");
        }
        
        // Если у нас уже идеальные 2-2-2 (или больше), просто предлагаем лучших контрпиков 
        // из тех ролей, которых не перебор (меньше 3)
        if (neededRoles.length === 0) {
            if (v < 3) neededRoles.push("Vanguard");
            if (d < 3) neededRoles.push("Duelist");
            if (s < 3) neededRoles.push("Strategist");
        }
        
        let recommended = [];
        for (let role of neededRoles) {
            let candidates = sortedHeroes.filter(h => 
                this.heroRoles[role] && 
                this.heroRoles[role].includes(h[0]) && 
                !allyTeam.includes(h[0])
            );
            // Убрали ограничение .slice(0, 3) — теперь берем ВСЕХ героев нужной роли
            recommended.push(...candidates.map(h => h[0]));
        }
        
        // Если ничего не найдено (крайний случай)
        if (recommended.length === 0) {
            recommended = sortedHeroes.filter(h => !allyTeam.includes(h[0])).slice(0, 5).map(h => h[0]);
        }
        
        return [...new Set(recommended)];
    }

    calculateCounterScoresForTeam(enemyTeam, mapName = null) {
        if (!enemyTeam || enemyTeam.length === 0) return { scores: {}, optimalTeam:[] };

        let rawScoresTuples = this.calculateTeamCounters(enemyTeam, true);
        let finalScores = this.absoluteWithContext(rawScoresTuples);

        if (mapName) {
            for (let hero in finalScores) {
                let mapBonus = this.getMapScore(hero, mapName);
                if (mapBonus > 0) finalScores[hero] += mapBonus;
            }
        }

        let optimalTeam = this.selectOptimalTeam(finalScores);
        return { scores: finalScores, optimalTeam: optimalTeam };
    }

    calculateTierListScores() {
        let rawScoresTuples = this.calculateTeamCounters(this.allHeroes, true);
        return this.absoluteWithContext(rawScoresTuples);
    }

    calculateTierListScoresWithMap(mapName = null) {
        let scores = this.calculateTierListScores();
        if (mapName) {
            for (let hero in scores) {
                let mapBonus = this.getMapScore(hero, mapName);
                if (mapBonus > 0) scores[hero] += mapBonus;
            }
        }
        return scores;
    }
}