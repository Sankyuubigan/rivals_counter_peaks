# File: core/logic.py
from collections import deque
from database.heroes_bd import (heroes, heroes_counters, heroes_compositions,
                                matchups_data, hero_stats_data,
                                calculate_team_counters, absolute_with_context,
                                select_optimal_team, SYNERGY_BONUS, hero_roles)
from info.translations import get_text, DEFAULT_LANGUAGE as global_default_language
# Убраны неиспользуемые константы AKAZE
# from core.utils import (AKAZE_MIN_MATCH_COUNT, AKAZE_LOWE_RATIO,
#                        AKAZE_DESCRIPTOR_TYPE)

# import cv2 # cv2 больше не используется напрямую в этом файле
import logging

# Константы для формирования команды в новом формате ролей
MIN_VANGUARDS = 1; MAX_VANGUARDS = 3; MIN_STRATEGISTS = 2; MAX_STRATEGISTS = 3; TEAM_SIZE = 6

HARD_COUNTER_SCORE_BONUS = 2.0
SOFT_COUNTER_SCORE_BONUS = 1.0
HARD_COUNTERED_BY_PENALTY = -1.5 
SOFT_COUNTERED_BY_PENALTY = -1.0 
PRIORITY_MULTIPLIER = 1.5 


class CounterpickLogic:
    def __init__(self, app_version="unknown"):
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set()
        self.effective_team = []
        self.DEFAULT_LANGUAGE = global_default_language
        self.APP_VERSION = app_version
        logging.info(f"[Logic] Initialized. APP_VERSION set to: '{self.APP_VERSION}'")
        self.main_window = None 

    def set_selection(self, desired_selection_set):
        logging.debug(f"[Logic] set_selection called with set: {desired_selection_set}")
        current_selection_list = list(self.selected_heroes)
        current_selection_set = set(current_selection_list)

        added_heroes = list(desired_selection_set - current_selection_set) 
        removed_heroes = current_selection_set - desired_selection_set

        new_deque = deque(maxlen=TEAM_SIZE)
        
        for hero in current_selection_list:
            if hero not in removed_heroes:
                new_deque.append(hero)
        
        for hero_to_add in added_heroes:
            if hero_to_add not in new_deque: # Убедимся, что не добавляем дубликаты, если maxlen был достигнут
                 if len(new_deque) < TEAM_SIZE:
                    new_deque.append(hero_to_add)
                 else: # Если очередь полная, удаляем самый старый и добавляем новый
                    new_deque.popleft()
                    new_deque.append(hero_to_add)


        self.selected_heroes = new_deque
        self.priority_heroes.intersection_update(set(self.selected_heroes)) 
        self.effective_team = [] 
        logging.debug(f"[Logic] Selection updated. New selection: {list(self.selected_heroes)}")


    def clear_all(self):
        self.selected_heroes.clear(); self.priority_heroes.clear(); self.effective_team = []

    def set_priority(self, hero):
        if hero not in self.selected_heroes: return
        if hero in self.priority_heroes: self.priority_heroes.discard(hero)
        else: self.priority_heroes.add(hero)
        self.effective_team = []

    def get_selected_heroes_text(self):
        count = len(self.selected_heroes); heroes_list = list(self.selected_heroes); lang = self.DEFAULT_LANGUAGE
        if not heroes_list: return get_text('selected_none', language=lang, max_team_size=TEAM_SIZE)
        else: header = f"{get_text('selected_some', language=lang)} ({count}/{TEAM_SIZE}): "; return f"{header}{', '.join(heroes_list)}"

    def calculate_counter_scores(self):
        if not self.selected_heroes: return {}

        enemy_team = list(self.selected_heroes)
        
        hero_scores = calculate_team_counters(
            enemy_team=enemy_team,
            matchups_data=matchups_data,
            hero_roles=hero_roles,
            method="avg",
            weighting="equal"
        )

        hero_scores_with_context = absolute_with_context(hero_scores, hero_stats_data)
        
        counter_scores = {hero: score for hero, score in hero_scores_with_context}

        for hero in heroes:
            if hero not in counter_scores:
                counter_scores[hero] = 0.0

        return counter_scores

    def calculate_effective_team(self, counter_scores):
        """
        Рассчитывает эффективную команду с использованием новой системы синергии.
        """
        if not counter_scores:
            self.effective_team = []
            return []

        candidates = {h: s for h, s in counter_scores.items() if s > 0}
        if not candidates:
            self.effective_team = []
            return []

        sorted_candidates_by_score = sorted(candidates.items(), key=lambda x: x, reverse=True)

        optimal_team = select_optimal_team(sorted_candidates_by_score, hero_roles)
        optimal_team_filtered = [hero for hero in optimal_team if hero not in self.selected_heroes]
        self.effective_team = optimal_team_filtered[:TEAM_SIZE]
        return self.effective_team

    def calculate_tier_list_scores(self) -> dict[str, float]:
        """
        Рассчитывает "мета-рейтинг" (тир-лист) для каждого героя против всех остальных.
        """
        logging.info("[Logic] Calculating tier list scores...")
        
        all_heroes_as_enemies = heroes
        
        # ИСПРАВЛЕНИЕ: Передаем is_tier_list_calc=True, чтобы обойти проверку "герой против себя"
        hero_scores_tuples = calculate_team_counters(
            enemy_team=all_heroes_as_enemies,
            matchups_data=matchups_data,
            hero_roles=hero_roles,
            method="avg",
            weighting="equal",
            is_tier_list_calc=True
        )
        
        hero_scores_with_context = absolute_with_context(hero_scores_tuples, hero_stats_data)
        
        tier_list_scores = {hero: score for hero, score in hero_scores_with_context}
        
        top_hero = max(tier_list_scores, key=tier_list_scores.get, default='N/A')
        logging.info(f"[Logic] Tier list calculation finished. Top hero: {top_hero}")
        
        return tier_list_scores