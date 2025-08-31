# File: core/logic.py
from collections import deque
from database.heroes_bd import (heroes, heroes_counters, heroes_compositions,
                                matchups_data, hero_stats_data,
                                calculate_team_counters, absolute_with_context,
                                select_optimal_team, SYNERGY_BONUS, hero_roles)
from core.lang.translations import get_text, DEFAULT_LANGUAGE as global_default_language
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

    def _calculate_hero_score(self, hero_to_evaluate, current_enemy_selection_set, priority_enemy_heroes):
        score = 0.0

        for enemy_hero in current_enemy_selection_set:
            enemy_counters_data = heroes_counters.get(enemy_hero, {}) 
            if isinstance(enemy_counters_data, dict):
                multiplier = PRIORITY_MULTIPLIER if enemy_hero in priority_enemy_heroes else 1.0
                if hero_to_evaluate in enemy_counters_data.get("hard", []):
                    score += HARD_COUNTER_SCORE_BONUS * multiplier
                elif hero_to_evaluate in enemy_counters_data.get("soft", []):
                    score += SOFT_COUNTER_SCORE_BONUS * multiplier
        
        if hero_to_evaluate in current_enemy_selection_set:
            score -= 10.0 

        hero_to_evaluate_data = heroes_counters.get(hero_to_evaluate, {}) 
        if isinstance(hero_to_evaluate_data, dict):
            hero_hard_countered_by = hero_to_evaluate_data.get("hard", [])
            hero_soft_countered_by = hero_to_evaluate_data.get("soft", [])

            for enemy_hero in current_enemy_selection_set:
                multiplier = PRIORITY_MULTIPLIER if enemy_hero in priority_enemy_heroes else 1.0
                if enemy_hero in hero_hard_countered_by:
                    score += HARD_COUNTERED_BY_PENALTY * multiplier
                elif enemy_hero in hero_soft_countered_by:
                    score += SOFT_COUNTERED_BY_PENALTY * multiplier
        return score

    def calculate_counter_scores(self):
        if not self.selected_heroes: return {}

        # Конвертируем внутренние имена обратно в стандартный формат для матчапов
        enemy_team = list(self.selected_heroes)

        # Получаем рейтинг героев против нашей команды (выбранной команды)
        hero_scores = calculate_team_counters(
            enemy_team=enemy_team,
            matchups_data=matchups_data,
            hero_roles=hero_roles,  # Используем реальные роли в новом формате
            method="avg",
            weighting="equal"
        )

        # Применяем абсолютный контекст
        hero_scores_with_context = absolute_with_context(hero_scores, hero_stats_data)

        # Конвертируем обратно в словарь {hero: score}
        counter_scores = {hero: score for hero, score in hero_scores_with_context}

        # Убедимся, что все герои из базы данных присутствуют
        for hero in heroes:
            if hero not in counter_scores:
                counter_scores[hero] = 0.0

        return counter_scores

    def calculate_effective_team(self, counter_scores):
        """
        Рассчитывает эффективную команду с использованием новой системы синергии.

        Новая система:
        - Использует новый формат ролей Vanguard/Duelist/Strategist
        - Применяет бонус синергии 2.0 балла за каждую синергию
        - Оптимизирует сочетание героев для максимального счета

        Args:
            counter_scores (dict): Словари оценок героев {hero_name: score}

        Returns:
            list: Оптимальный список героев с учётом синергии
        """
        if not counter_scores:
            self.effective_team = []
            return []

        # Фильтруем кандидатов - только с положительной оценкой, не выбранные
        candidates = {h: s for h, s in counter_scores.items() if s > 0 and h not in self.selected_heroes}
        if not candidates:
            self.effective_team = []
            return []

        # Сортируем кандидатов по оценке (основание)
        sorted_candidates_by_score = sorted(candidates.items(), key=lambda x: x[1], reverse=True)

        # Используем новую функцию оптимизации команды с синергиями
        optimal_team = select_optimal_team(sorted_candidates_by_score, hero_roles)

        # Исключаем героев которые уже выбраны (дополнительная проверка)
        optimal_team_filtered = [hero for hero in optimal_team if hero not in self.selected_heroes]

        # Ограничиваем размер команды согласно константам
        self.effective_team = optimal_team_filtered[:TEAM_SIZE]
        return self.effective_team

    # Метод recognize_heroes_from_image удален, т.к. логика перенесена в AdvancedRecognition