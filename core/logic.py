# File: core/logic.py
import os
import logging
from collections import deque
from typing import List, Dict, Tuple
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
        
        if self.current_map_index >= len(self.available_maps):
            self.current_map_index = -1
            self.selected_map = None
        else:
            self.selected_map = self.available_maps[self.current_map_index]
            
        logging.info(f"Переключена карта на: {self.selected_map or 'Без карты'}")

    def set_map_by_name(self, map_name: str | None):
        """Устанавливает карту по имени. Если None, сбрасывает выбор."""
        if map_name is None:
            self.selected_map = None
            self.current_map_index = -1
        else:
            if map_name in self.available_maps:
                self.selected_map = map_name
                self.current_map_index = self.available_maps.index(map_name)
            else:
                logging.warning(f"[Logic] Попытка установить несуществующую карту: {map_name}")
                return
        
        logging.info(f"Карта установлена на: {self.selected_map or 'Без карты'}")

    def set_selection(self, desired_selection_set):
        logging.debug(f"[Logic] set_selection called with set: {desired_selection_set}")
        current_selection_list = list(self.selected_heroes)
        
        new_deque = deque(maxlen=TEAM_SIZE)
        
        for hero in current_selection_list:
            if hero in desired_selection_set:
                new_deque.append(hero)
        
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

    def calculate_counter_scores(self) -> Dict[str, float]:
        """
        Рассчитывает и возвращает финальные баллы героев для отображения в UI.
        """
        if not self.selected_heroes: 
            logging.warning("[Logic] calculate_counter_scores: No heroes selected.")
            return {}
        enemy_team = list(self.selected_heroes)
        logging.info(f"[Logic] calculate_counter_scores: Enemy team: {enemy_team}")

        # 1. Получаем "сырые" баллы преимущества против врагов для ВСЕХ героев
        # ИСПРАВЛЕНИЕ: Устанавливаем is_tier_list_calc=True, чтобы не отсекать героев
        raw_scores_tuples = calculate_team_counters(enemy_team, matchups_data, is_tier_list_calc=True)
        logging.info(f"[Logic] calculate_counter_scores: Raw scores (top 10): {raw_scores_tuples[:10]}")

        # 2. Применяем контекстные модификаторы (винрейт)
        hero_scores_with_context = absolute_with_context(raw_scores_tuples, hero_stats_data)
        final_scores = {hero: score for hero, score in hero_scores_with_context}
        logging.info(f"[Logic] calculate_counter_scores: Scores after context (top 10): {sorted(final_scores.items(), key=lambda item: item[1], reverse=True)[:10]}")

        # 3. Добавляем бонус за карту
        if self.selected_map:
            logging.info(f"[Logic] calculate_counter_scores: Applying map bonus for: {self.selected_map}")
            for hero in final_scores:
                map_bonus = get_map_score(hero, self.selected_map)
                if map_bonus > 0:
                    final_scores[hero] += map_bonus
                    logging.debug(f"[Logic] Map bonus for {hero}: +{map_bonus:.2f} -> new total: {final_scores[hero]:.2f}")
        
        sorted_final_scores = sorted(final_scores.items(), key=lambda item: item[1], reverse=True)
        logging.info(f"[Logic] calculate_counter_scores: Final scores for UI (top 10): {sorted_final_scores[:10]}")

        # 4. Рассчитываем оптимальную команду на основе финальных баллов
        self.calculate_effective_team(sorted_final_scores)

        # 5. Возвращаем финальные баллы для UI
        return dict(sorted_final_scores)

    def calculate_effective_team(self, sorted_heroes_with_scores: List[Tuple[str, float]]) -> List[str]:
        """
        Рассчитывает и сохраняет оптимальную команду на основе предоставленных финальных баллов.
        """
        logging.info(f"[Logic] calculate_effective_team: Starting calculation with {len(sorted_heroes_with_scores)} heroes.")
        if not sorted_heroes_with_scores:
            self.effective_team = []
            return []
        
        optimal_team = select_optimal_team(sorted_heroes_with_scores, hero_roles)
        # ИСПРАВЛЕНИЕ: Убираем некорректную фильтрацию врагов из оптимальной команды.
        # Теперь оптимальная команда будет включать врагов, если они являются лучшим выбором.
        self.effective_team = optimal_team
        logging.info(f"[Logic] calculate_effective_team: Optimal team found: {self.effective_team}")
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