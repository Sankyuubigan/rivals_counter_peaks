# File: core/logic.py
import os
import logging
from collections import deque
from typing import List
from core.database.heroes_bd import (
    heroes, heroes_counters, matchups_data, hero_stats_data,
    calculate_team_counters, absolute_with_context, select_optimal_team,
    hero_roles, get_map_score
)
from core.utils import resource_path
from info.translations import get_text, DEFAULT_LANGUAGE as global_default_language

TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self, app_version="unknown"):
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set()
        self.effective_team = []
        self.DEFAULT_LANGUAGE = global_default_language
        self.APP_VERSION = app_version
        
        # Новые атрибуты для управления картами
        self.available_maps: List[str] = self._load_available_maps()
        self.current_map_index: int = -1  # -1 означает "карта не выбрана"
        self.selected_map: str | None = None
        
        logging.info(f"[Logic] Initialized. APP_VERSION set to: '{self.APP_VERSION}'")
        self.main_window = None

    def _load_available_maps(self) -> List[str]:
        """Загружает названия карт из директории resources/maps."""
        try:
            maps_dir = resource_path("resources/maps")
            if not os.path.isdir(maps_dir):
                logging.error(f"Директория с картами не найдена: {maps_dir}")
                return []
            
            # ИСПРАВЛЕНИЕ: os.path.splitext(f) возвращает ('ИМЯ', '.расширение').
            # Берем только первую часть (имя) и формируем чистый список строк.
            map_names = [
                os.path.splitext(f)[0]
                for f in os.listdir(maps_dir)
                if f.lower().endswith('.png')
            ]
            logging.info(f"Загружено {len(map_names)} карт: {map_names}")
            return sorted(map_names)
        except Exception as e:
            logging.error(f"Не удалось загрузить названия карт: {e}")
            return []

    def cycle_next_map(self):
        """Переключает на следующую карту в списке, включая опцию "без карты"."""
        if not self.available_maps:
            return
        
        self.current_map_index += 1
        
        # Если вышли за пределы списка, возвращаемся к состоянию "без карты" (-1)
        if self.current_map_index >= len(self.available_maps):
            self.current_map_index = -1
            self.selected_map = None
        else:
            self.selected_map = self.available_maps[self.current_map_index]
            
        logging.info(f"Переключена карта на: {self.selected_map or 'Без карты'}")

    def set_selection(self, desired_selection_set):
        logging.debug(f"[Logic] set_selection called with set: {desired_selection_set}")
        current_selection_list = list(self.selected_heroes)
        
        new_deque = deque(maxlen=TEAM_SIZE)
        
        # Сохраняем существующих героев, которые есть в новом выборе
        for hero in current_selection_list:
            if hero in desired_selection_set:
                new_deque.append(hero)
        
        # Добавляем новых героев
        for hero_to_add in desired_selection_set:
            if hero_to_add not in new_deque:
                 if len(new_deque) < TEAM_SIZE:
                    new_deque.append(hero_to_add)
                 else:
                    new_deque.popleft()
                    new_deque.append(hero_to_add)
        self.selected_heroes = new_deque
        self.priority_heroes.intersection_update(set(self.selected_heroes)) 
        self.effective_team = [] 
        logging.debug(f"[Logic] Selection updated. New selection: {list(self.selected_heroes)}")
    def clear_all(self):
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        self.effective_team = []
    def set_priority(self, hero):
        if hero not in self.selected_heroes: return
        if hero in self.priority_heroes: self.priority_heroes.discard(hero)
        else: self.priority_heroes.add(hero)
        self.effective_team = []
    def get_selected_heroes_text(self):
        count = len(self.selected_heroes)
        heroes_list = list(self.selected_heroes)
        lang = self.DEFAULT_LANGUAGE
        if not heroes_list: return get_text('selected_none', language=lang, max_team_size=TEAM_SIZE)
        else: return f"{get_text('selected_some', language=lang)} ({count}/{TEAM_SIZE}): {', '.join(heroes_list)}"

    def calculate_counter_scores(self):
        if not self.selected_heroes: return {}
        enemy_team = list(self.selected_heroes)

        # Базовый расчет без карты
        hero_scores_with_context = absolute_with_context(
            calculate_team_counters(enemy_team, matchups_data),
            hero_stats_data
        )

        final_scores = {hero: score for hero, score in hero_scores_with_context}

        # Если выбрана карта, добавляем бонус
        if self.selected_map:
            logging.info(f"Применяется бонус за карту: {self.selected_map}")
            for hero in final_scores:
                map_bonus = get_map_score(hero, self.selected_map)
                if map_bonus > 0:
                    final_scores[hero] += map_bonus
                    logging.debug(f"Бонус для {hero}: +{map_bonus:.2f} -> итого {final_scores[hero]:.2f}")

        # ИСПРАВЛЕНИЕ: Сортируем результаты по убыванию рейтинга
        sorted_scores = dict(sorted(final_scores.items(), key=lambda item: item[1], reverse=True))
        logging.debug(f"Отсортированные рейтинги героев: {list(sorted_scores.items())[:5]}")

        return sorted_scores

    def calculate_effective_team(self, counter_scores):
        if not counter_scores:
            self.effective_team = []
            return []
        # ИСПРАВЛЕНИЕ: Возвращена правильная сортировка по очкам (второй элемент кортежа)
        sorted_candidates = sorted(counter_scores.items(), key=lambda item: item[1], reverse=True)
        optimal_team = select_optimal_team(sorted_candidates, hero_roles)
        self.effective_team = [hero for hero in optimal_team if hero not in self.selected_heroes]
        return self.effective_team
    def calculate_tier_list_scores(self) -> dict[str, float]:
        logging.info("[Logic] Calculating tier list scores...")
        hero_scores_tuples = calculate_team_counters(
            enemy_team=heroes,
            matchups_data=matchups_data,
            is_tier_list_calc=True
        )
        hero_scores_with_context = absolute_with_context(hero_scores_tuples, hero_stats_data)
        return {hero: score for hero, score in hero_scores_with_context}