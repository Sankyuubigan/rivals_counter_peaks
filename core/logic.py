# File: core/logic.py
from collections import deque
from core.lang.translations import get_text, DEFAULT_LANGUAGE as global_default_language
from database.stats_loader import (
    load_matchups_data,
    load_hero_stats,
    load_hero_roles,
    get_all_heroes
)
import logging
import math

# Константы для новой логики расчета
MIN_TANKS = 1
MAX_TANKS = 4 # Повышено до 4 на всякий случай, если композиция потребует
MIN_SUPPORTS = 2
MAX_SUPPORTS = 3
TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self, app_version="unknown"):
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set() # Приоритеты пока не используются в новой логике, но оставим для будущего
        self.effective_team = []
        self.DEFAULT_LANGUAGE = global_default_language
        self.APP_VERSION = app_version
        self.main_window = None

        # Загрузка данных при инициализации
        logging.info("[Logic] Loading new stats data...")
        self.matchups_data = load_matchups_data()
        self.hero_stats = load_hero_stats()
        self.hero_roles = load_hero_roles()
        self.all_heroes = get_all_heroes(self.matchups_data)
        logging.info(f"[Logic] Initialized with {len(self.all_heroes)} heroes from new database. APP_VERSION: '{self.APP_VERSION}'")

    def set_selection(self, desired_selection_set):
        logging.debug(f"[Logic] set_selection called with set: {desired_selection_set}")
        
        # Фильтруем только тех героев, которые есть в нашей базе
        valid_selection = {hero for hero in desired_selection_set if hero in self.all_heroes}
        if len(valid_selection) != len(desired_selection_set):
            logging.warning(f"Some heroes from selection were not found in the database: {desired_selection_set - valid_selection}")

        self.selected_heroes = deque(list(valid_selection), maxlen=TEAM_SIZE)
        self.effective_team = []
        logging.debug(f"[Logic] Selection updated. New selection: {list(self.selected_heroes)}")

    def clear_all(self):
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        self.effective_team = []

    def set_priority(self, hero):
        # Функциональность приоритетов может быть пересмотрена с новой логикой
        if hero not in self.selected_heroes: return
        if hero in self.priority_heroes: self.priority_heroes.discard(hero)
        else: self.priority_heroes.add(hero)
        self.effective_team = []

    def get_selected_heroes_text(self):
        count = len(self.selected_heroes)
        heroes_list = list(self.selected_heroes)
        lang = self.DEFAULT_LANGUAGE
        if not heroes_list:
            return get_text('selected_none', language=lang, max_team_size=TEAM_SIZE)
        else:
            header = f"{get_text('selected_some', language=lang)} ({count}/{TEAM_SIZE}): "
            return f"{header}{', '.join(heroes_list)}"

    def calculate_counter_scores(self):
        """
        Рассчитывает рейтинг героев против указанной команды врагов на основе новой логики.
        Возвращает словарь {hero: score}.
        """
        if not self.selected_heroes:
            return {}
        
        enemy_team = list(self.selected_heroes)
        hero_scores_list_of_tuples = self._calculate_team_counters(enemy_team, self.matchups_data, method="avg", weighting="equal")
        
        # Преобразуем в словарь для совместимости со старым кодом
        return dict(hero_scores_list_of_tuples)

    def calculate_effective_team(self, counter_scores):
        """
        Выбирает оптимальную команду на основе рассчитанных очков.
        """
        if not counter_scores:
            self.effective_team = []
            return []

        # 1. Применяем контекст (общий винрейт) к очкам
        scores_with_context = self._absolute_with_context(counter_scores.items(), self.hero_stats)

        # 2. Сортируем по новому абсолютному значению
        scores_with_context.sort(key=lambda x: x, reverse=True)

        # 3. Выбираем оптимальную команду с учетом ролей
        optimal_team_names = self._select_optimal_team(scores_with_context, self.hero_roles)
        
        self.effective_team = optimal_team_names
        return self.effective_team

    # --- Вспомогательные методы из test_manual_raiting.py ---

    def _calculate_team_counters(self, enemy_team, matchups_data, method="avg", weighting="equal"):
        """
        Адаптированная версия из файла для тестов.
        """
        hero_scores = []
        
        for hero in self.all_heroes:
            if hero in enemy_team: continue # Не предлагаем врагов в качестве контрпиков

            matchups = matchups_data.get(hero, [])
            total_weighted_difference = 0
            total_weight = 0
            
            for enemy in enemy_team:
                for matchup in matchups:
                    if matchup["opponent"].lower() == enemy.lower():
                        diff_str = matchup["difference"].replace('%', '').strip()
                        try:
                            difference = -float(diff_str) # Инвертируем, чтобы положительное значение было "хорошо"
                        except ValueError:
                            continue
                        
                        weight = 1
                        total_weighted_difference += difference * weight
                        total_weight += weight
                        break
            
            if total_weight > 0:
                rating = total_weighted_difference / total_weight
                hero_scores.append((hero, rating))
        
        hero_scores.sort(key=lambda x: x, reverse=True)
        return hero_scores

    def _absolute_with_context(self, scores, hero_stats):
        """
        Адаптированная версия из файла для тестов.
        """
        absolute_scores = []
        for hero, score in scores:
            if hero in hero_stats:
                overall_winrate_str = hero_stats[hero].get("win_rate", "50.0%")
                overall_winrate = float(overall_winrate_str.replace('%', ''))
            else:
                overall_winrate = 50.0
            
            context_factor = overall_winrate / 50.0
            absolute_score = (100 + score) * context_factor
            absolute_scores.append((hero, absolute_score))
        return absolute_scores

    def _select_optimal_team(self, sorted_heroes, hero_roles):
        """
        Адаптированная версия из файла для тестов.
        """
        vanguards, strategists, duelists = [], [], []
        
        for hero, diff in sorted_heroes:
            role = hero_roles.get(hero, "Unknown")
            if role == "tank": vanguards.append((hero, diff))
            elif role == "support": strategists.append((hero, diff))
            elif role == "dd": duelists.append((hero, diff))
        
        vanguards.sort(key=lambda x: x, reverse=True)
        strategists.sort(key=lambda x: x, reverse=True)
        duelists.sort(key=lambda x: x, reverse=True)
        
        possible_combinations = []
        for v in range(1, 5):
            for s in range(2, 4):
                d = 6 - v - s
                if d >= 0: possible_combinations.append((v, s, d))
        
        best_team, best_score = None, float('-inf')
        
        for v_count, s_count, d_count in possible_combinations:
            if len(vanguards) >= v_count and len(strategists) >= s_count and len(duelists) >= d_count:
                team = vanguards[:v_count] + strategists[:s_count] + duelists[:d_count]
                score = sum(diff for _, diff in team)
                if score > best_score:
                    best_score = score
                    best_team = team
        
        if best_team is None:
            team = []
            if vanguards: team.append(vanguards)
            team.extend(strategists[:min(2, len(strategists))])
            remaining = vanguards[1:] + strategists[min(2, len(strategists)):3] + duelists
            remaining.sort(key=lambda x: x, reverse=True)
            while len(team) < 6 and remaining: team.append(remaining.pop(0))
            best_team = team
        
        return [hero for hero, score in best_team[:6]]