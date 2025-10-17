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
        # ИСПРАВЛЕНИЕ: Правильно определяем базовый путь для ресурсов
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
# --- Глобальные переменные с данными ---
# Эти переменные инициализируются один раз при импорте модуля.
# ИСПРАВЛЕНО: Правильные пути к файлам данных
STATS_DATA = _load_json_data("database/marvel_rivals_stats_20251017-180727.json") or {}
COMPOSITIONS_DATA = _load_json_data("database/heroes_compositions.json") or {}
ROLES_DATA = _load_json_data("database/roles.json") or {}
# --- Формирование основных структур данных ---
heroes: List[str] = sorted(list(STATS_DATA.keys()))
heroes_counters: Dict[str, Dict[str, List[str]]] = {} # Будет заполнено при необходимости
heroes_compositions: Dict[str, List[str]] = COMPOSITIONS_DATA
hero_roles: Dict[str, List[str]] = ROLES_DATA
# Извлечение данных о матчапах и статистике из общей структуры
matchups_data: Dict[str, List[Dict[str, Any]]] = {hero: data.get("opponents", []) for hero, data in STATS_DATA.items()}
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
logging.info(f"База данных инициализирована. Загружено героев: {len(heroes)}")
# --- Логика расчета ---
SYNERGY_BONUS = 2.0  # Бонус за синергию
def calculate_team_counters(enemy_team: List[str], matchups_data: Dict, is_tier_list_calc: bool = False, **kwargs) -> List[Tuple[str, float]]:
    """Рассчитывает рейтинг героев против указанной команды врагов."""
    if not enemy_team: return []
    
    hero_scores = {}
    for hero, matchups in matchups_data.items():
        # Пропускаем героя, только если это не расчет тир-листа
        if not is_tier_list_calc and hero in enemy_team:
            continue
        
        total_difference = 0
        found_matchups = 0
        for enemy in enemy_team:
            # Для тир-листа не сравниваем героя с самим собой
            if is_tier_list_calc and hero == enemy:
                continue
            for matchup in matchups:
                if matchup.get("opponent", "").lower() == enemy.lower():
                    try:
                        # "difference" - это преимущество врага над нами, поэтому инвертируем знак.
                        difference = -float(matchup["difference"].strip('%'))
                        total_difference += difference
                        found_matchups += 1
                    except (ValueError, KeyError):
                        continue
                    break # Нашли матч, переходим к следующему врагу
        
        if found_matchups > 0:
            hero_scores[hero] = total_difference / found_matchups # Среднее преимущество
            
    # ИСПРАВЛЕНИЕ: Сортируем по значению (score), а не по имени.
    return sorted(hero_scores.items(), key=lambda item: item[1], reverse=True)
def select_optimal_team(sorted_heroes: List[Tuple[str, float]], hero_roles: Dict) -> List[str]:
    """Выбирает оптимальную команду из 6 героев с учетом ограничений на роли и синергии."""
    if not sorted_heroes or not hero_roles: return []
    # Разделяем героев по ролям
    roles_map = {hero: role for role, heroes_in_role in hero_roles.items() for hero in heroes_in_role}
    vanguards, duelists, strategists = [], [], []
    
    for hero, score in sorted_heroes:
        role = roles_map.get(hero)
        if role == "Vanguard": vanguards.append((hero, score))
        elif role == "Duelist": duelists.append((hero, score))
        elif role == "Strategist": strategists.append((hero, score))
    # Возможные комбинации ролей (V, S, D), где V>=1, 2<=S<=3, V+S+D=6
    possible_combinations = [(v, s, 6 - v - s) for v in range(1, 5) for s in range(2, 4) if 6 - v - s >= 0]
    
    best_team, best_score = [], float('-inf')
    for v_count, s_count, d_count in possible_combinations:
        if len(vanguards) >= v_count and len(strategists) >= s_count and len(duelists) >= d_count:
            team_candidates = vanguards[:v_count] + strategists[:s_count] + duelists[:d_count]
            team_names = [h for h, s in team_candidates]
            
            base_score = sum(s for h, s in team_candidates)
            
            synergy_score = 0
            for i in range(len(team_names)):
                for j in range(i + 1, len(team_names)):
                    hero1, hero2 = team_names[i], team_names[j]
                    if hero2 in COMPOSITIONS_DATA.get(hero1, []): synergy_score += SYNERGY_BONUS
                    if hero1 in COMPOSITIONS_DATA.get(hero2, []): synergy_score += SYNERGY_BONUS
            
            total_score = base_score + synergy_score
            if total_score > best_score:
                best_score = total_score
                best_team = team_names
    
    return best_team
def absolute_with_context(scores: List[Tuple[str, float]], hero_stats: Dict) -> List[Tuple[str, float]]:
    """Применяет контекст общей силы героя к его рейтингу."""
    absolute_scores = []
    for hero, score in scores:
        stats = hero_stats.get(hero, {"win_rate": 0.5})
        context_factor = stats["win_rate"] / 0.5 # Коэффициент относительно 50% винрейта
        absolute_score = (100 + score) * context_factor
        absolute_scores.append((hero, absolute_score))
        
    # ИСПРАВЛЕНИЕ: Сортируем по значению (score), а не по всему кортежу.
    return sorted(absolute_scores, key=lambda item: item[1], reverse=True)