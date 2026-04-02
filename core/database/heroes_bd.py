# File: core/database/heroes_bd.py
# Модуль для работы с базой данных героев в формате JSON
import json
import os
import sys
import logging
from typing import List, Dict, Any, Tuple

# --- Управление путями к ресурсам ---
def resource_path(relative_path: str) -> str:
    """Определяет абсолютный путь к ресурсу, работая как в режиме разработки, так и в собранном .exe."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(base_path, relative_path)

# --- Загрузка данных ---
def _load_json_data(file_path: str) -> Any:
    """Безопасно загружает данные из JSON файла."""
    full_path = resource_path(file_path)
    if not os.path.exists(full_path):
        logging.error(f"Файл данных не найден: {full_path}")
        return None
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Ошибка при чтении файла {full_path}: {e}")
        return None

def _get_latest_db_file() -> str:
    """Автоматически находит самый свежий файл базы данных."""
    db_dir = resource_path("database")
    try:
        if os.path.exists(db_dir):
            files =[f for f in os.listdir(db_dir) if f.startswith("marvel_rivals_stats_") and f.endswith(".json")]
            if files:
                latest_file = sorted(files)[-1]  # Сортировка по имени (там дата) даст самый новый
                logging.info(f"Актуальный файл БД: {latest_file}")
                return f"database/{latest_file}"
    except Exception as e:
        logging.error(f"Ошибка при поиске БД: {e}")
    # Возвращаем дефолтный, если ничего не найдено
    return "database/marvel_rivals_stats_20260402-031716.json"

# --- Глобальные переменные с данными ---
# Теперь мы загружаем самый свежий файл автоматически!
FULL_DATA = _load_json_data(_get_latest_db_file()) or {}
STATS_DATA = FULL_DATA.get("heroes", {})

# --- Извлекаем роли из основного файла БД ---
ROLES_DATA: Dict[str, List[str]] = {}
for hero, data in STATS_DATA.items():
    role = data.get("role")
    if role:
        if role not in ROLES_DATA:
            ROLES_DATA[role] = []
        ROLES_DATA[role].append(hero)

# --- НОВАЯ ЛОГИКА ДЛЯ СИНЕРГИЙ ---
teamups_list = FULL_DATA.get("teamups",[])
TEAMUPS_DATA = {}
for teamup in teamups_list:
    heroes_in_teamup = teamup.get("heroes",[])
    if heroes_in_teamup:
        normalized_heroes = frozenset(str(hero).strip() for hero in heroes_in_teamup)
        if len(normalized_heroes) > 1:
            TEAMUPS_DATA[normalized_heroes] = teamup

# --- Формирование основных структур данных ---
heroes: List[str] = sorted(list(STATS_DATA.keys()))
heroes_counters: Dict[str, Dict[str, List[str]]] = {}
hero_roles: Dict[str, List[str]] = ROLES_DATA

matchups_data: Dict[str, List[Dict[str, Any]]] = {hero: data.get("opponents",[]) for hero, data in STATS_DATA.items()}
hero_stats_data: Dict[str, Dict[str, Any]] = {}
for hero, data in STATS_DATA.items():
    try:
        hero_stats_data[hero] = {
            "win_rate": float(data["win_rate"].replace('%', '')) / 100,
            "pick_rate": float(data["pick_rate"].replace('%', '')) / 100,
            "matches": int(data["matches"].replace(',', ''))
        }
    except (KeyError, ValueError, AttributeError) as e:
        logging.warning(f"Не удалось обработать статистику для героя '{hero}': {e}. Используются значения по умолчанию.")
        hero_stats_data[hero] = {"win_rate": 0.5, "pick_rate": 0.0, "matches": 0}

logging.info(f"База данных инициализирована. Загружено героев: {len(heroes)}, тимапов: {len(TEAMUPS_DATA)}")

# --- Логика расчета ---
SYNERGY_BONUS = 10.0

def get_map_score(hero_name: str, map_name: str, min_score: float = 0, max_score: float = 20) -> float:
    hero_data = STATS_DATA.get(hero_name)
    if not hero_data: return 0
    maps_list = hero_data.get('maps',[])
    if not maps_list: return 0
    win_rates =[]
    target_map_wr = None
    for map_info in maps_list:
        try:
            wr = float(map_info['win_rate'].replace('%', ''))
            win_rates.append(wr)
            if map_info['map_name'] == map_name:
                target_map_wr = wr
        except (KeyError, ValueError): continue
    if target_map_wr is None or not win_rates: return 0
    min_wr = min(win_rates)
    max_wr = max(win_rates)
    if min_wr == max_wr: return float(min_score)
    score = min_score + (target_map_wr - min_wr) * (max_score - min_score) / (max_wr - min_wr)
    return round(score, 2)

def calculate_team_counters(enemy_team: List[str], matchups_data: Dict, is_tier_list_calc: bool = False, **kwargs) -> List[Tuple[str, float]]:
    if not enemy_team: return[]
    logging.info(f"[DB] calculate_team_counters: входная команда врагов={enemy_team}, is_tier_list_calc={is_tier_list_calc}")
    hero_scores = {}
    for hero, matchups in matchups_data.items():
        if not is_tier_list_calc and hero in enemy_team: continue
        total_difference, found_matchups = 0, 0
        for enemy in enemy_team:
            if is_tier_list_calc and hero == enemy: continue
            for matchup in matchups:
                if matchup.get("opponent", "").lower() == enemy.lower():
                    try:
                        difference = -float(matchup["difference"].strip('%'))
                        total_difference += difference
                        found_matchups += 1
                    except (ValueError, KeyError): continue
                    break
        if found_matchups > 0:
            hero_scores[hero] = total_difference / found_matchups
    logging.info(f"[DB] calculate_team_counters: рассчитаны очки для {len(hero_scores)} героев")
    return sorted(hero_scores.items(), key=lambda item: item[1], reverse=True)

def select_optimal_team(sorted_heroes: List[Tuple[str, float]], hero_roles: Dict) -> List[str]:
    if not sorted_heroes or not hero_roles: 
        return[]
    
    roles_map = {hero: role for role, heroes_in_role in hero_roles.items() for hero in heroes_in_role}
    vanguards, duelists, strategists = [], [],[]
    for hero, score in sorted_heroes:
        role = roles_map.get(hero)
        if role == "Vanguard": vanguards.append((hero, score))
        elif role == "Duelist": duelists.append((hero, score))
        elif role == "Strategist": strategists.append((hero, score))

    possible_combinations =[(v, s, 6 - v - s) for v in range(1, 5) for s in range(2, 4) if 6 - v - s >= 0]
    best_team, best_score =[], float('-inf')
    
    for v_count, s_count, d_count in possible_combinations:
        if len(vanguards) >= v_count and len(strategists) >= s_count and len(duelists) >= d_count:
            team_candidates = vanguards[:v_count] + strategists[:s_count] + duelists[:d_count]
            base_score = sum(s for h, s in team_candidates)
            team_names_set = {str(hero).strip() for hero, score in team_candidates}
            
            synergy_score = 0
            for teamup_heroes_set, teamup_data in TEAMUPS_DATA.items():
                if teamup_heroes_set.issubset(team_names_set):
                    synergy_score += SYNERGY_BONUS
            
            total_score = base_score + synergy_score
            team_names = [h for h, s in team_candidates]

            if total_score > best_score:
                best_score = total_score
                best_team = team_names
    
    if not best_team:
        best_team =[h for h, s in sorted_heroes[:6]]

    return best_team

def absolute_with_context(scores: List[Tuple[str, float]], hero_stats: Dict) -> List[Tuple[str, float]]:
    original_scores =[]
    for hero, score in scores:
        if hero in hero_stats:
            overall_winrate = hero_stats[hero]["win_rate"] * 100
        else: 
            overall_winrate = 50.0
        context_factor = overall_winrate / 50.0
        absolute_score = (100 + score) * context_factor
        original_scores.append((hero, absolute_score))
    
    if not original_scores: return[]
    original_values = [score for _, score in original_scores]
    min_score, max_score = min(original_values), max(original_values)
    display_scores =[]
    if max_score == min_score:
        for hero, _ in original_scores: display_scores.append((hero, 50.5))
    else:
        for hero, original_score in original_scores:
            display_score = (original_score - min_score) / (max_score - min_score) * 99 + 1
            display_scores.append((hero, display_score))
    return sorted(display_scores, key=lambda item: item[1], reverse=True)