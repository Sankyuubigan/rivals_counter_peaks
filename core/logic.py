import os
import json
import logging
from collections import deque
from typing import List, Dict, Tuple
from core.database.heroes_bd import (
    heroes, heroes_counters, matchups_data, hero_stats_data,
    calculate_team_counters, absolute_with_context, select_optimal_team,
    hero_roles, get_map_score, STATS_DATA, resolve_map_name
)
from core.utils import resource_path
from info.translations import get_text, DEFAULT_LANGUAGE as global_default_language

TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self, app_version="unknown"):
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set()
        self.effective_team =[]
        self.DEFAULT_LANGUAGE = global_default_language
        self.APP_VERSION = app_version
        
        self.available_maps: List[str] = self._load_available_maps()
        self.current_map_index: int = -1  
        self.selected_map: str | None = None
        
        logging.info(f"[Logic] Initialized. APP_VERSION set to: '{self.APP_VERSION}'")
        self.main_window = None

    def _load_available_maps(self) -> List[str]:
        maps_set = set()
        try:
            if STATS_DATA:
                first_hero_data = next(iter(STATS_DATA.values()))
                for map_info in first_hero_data.get("maps",[]):
                    raw_map_name = map_info.get("map_name")
                    if raw_map_name:
                        # Применяем маппинг: img_map_xxx -> читаемое имя
                        maps_set.add(resolve_map_name(raw_map_name))
            
            if maps_set:
                logging.info(f"[Logic] Успешно загружен список карт из базы данных: {len(maps_set)} шт.")
                return sorted(list(maps_set))
        except Exception as e:
            logging.error(f"[Logic] Ошибка при извлечении карт из базы данных: {e}")
            
        try:
            maps_dir = resource_path("resources/maps")
            if not os.path.isdir(maps_dir): return[]
            map_names = [os.path.splitext(f)[0] for f in os.listdir(maps_dir) if f.lower().endswith('.png')]
            logging.info(f"[Logic] Загружен список карт из папки resources/maps (fallback): {len(map_names)} шт.")
            return sorted(map_names)
        except Exception as e:
            logging.error(f"[Logic] Ошибка при загрузке карт из папки (fallback): {e}")
            return[]

    def cycle_next_map(self):
        if not self.available_maps: return
        self.current_map_index += 1
        if self.current_map_index >= len(self.available_maps):
            self.current_map_index = -1
            self.selected_map = None
        else:
            self.selected_map = self.available_maps[self.current_map_index]
        
    def cycle_previous_map(self):
        if not self.available_maps: return
        self.current_map_index -= 1
        if self.current_map_index < -1:
            self.current_map_index = len(self.available_maps) - 1
            self.selected_map = self.available_maps[self.current_map_index]
        elif self.current_map_index == -1:
            self.selected_map = None
        else:
            self.selected_map = self.available_maps[self.current_map_index]

    def reset_map(self):
        self.selected_map = None
        self.current_map_index = -1

    def set_map_by_name(self, map_name: str | None):
        if map_name is None or map_name.lower() == "none" or map_name == "":
            self.selected_map = None
            self.current_map_index = -1
        else:
            logging.info(f"[Logic] Получена карта от Overwolf: '{map_name}'")
            map_name_lower = map_name.lower().strip()
            
            # Маппинг Overwolf-имён на читаемые названия карт (совпадают с map_filename_to_name)
            map_mapping = {
                "birnin t'challa": "Birnin T'Challa",
                "birnin t'challa 1": "Birnin T'Challa",
                "birnin t'challa 2": "Birnin T'Challa",
                "birnin t'challa 3": "Birnin T'Challa",
                "hall of djalia": "Hall Of Djalia",
                "hall of djaalia": "Hall Of Djalia",
                "celestial husk": "Celestial Husk",
                "symbiotic surface": "Symbiotic Surface",
                "yggdrasill path": "Yggdrasill Path",
                "yggdrasil path": "Yggdrasill Path",
                "royal palace": "Yggdrasill Path",
                "shin-shibuya": "Shin-Shibuya",
                "spider-islands": "Spider-Islands",
                "spider islands": "Spider-Islands",
                "hell's heaven 1": "Hell's Heaven",
                "hell's heaven 2": "Hell's Heaven",
                "hell's heaven 3": "Hell's Heaven",
                "midtown оборона": "Midtown",
                "midtown атака": "Midtown",
                # Также поддерживаем img_map_xxx форматы на случай если придут сырые
                "img_map_practicerance": "Birnin T'Challa",
                "img_map_celestial_heart": "Celestial Husk",
                "img_map_krakoa_carousel": "Krakoa",
                "img_map_hellfiregala_arakko": "Arakko",
                "img_map_hydracharterisbase": "Hell's Heaven",
                "img_map_museum_collectorpark": "Museum of Contemplation",
                "img_map_yggdrasil": "Yggdrasill Path",
                "img_map_tokyowebworld_spiderisland": "Spider-Islands",
                "img_map_midtown": "Midtown",
                "img_map_klyntar_ruins": "Symbiotic Surface",
                "img_map_kunlun_heartoftiandu": "Heart Of Heaven",
                "img_map_centralpark": "Central Park",
                "img_map_hallofdialia": "Hall Of Djalia",
                "img_map_tokyowebworld_metropolis": "Shin-Shibuya",
            }
            
            mapped_name = map_mapping.get(map_name_lower, map_name.title())
            
            matched_map = next((m for m in self.available_maps if m.lower() == mapped_name.lower()), None)
            
            if not matched_map:
                for m in self.available_maps:
                    if mapped_name.lower() in m.lower() or m.lower() in mapped_name.lower():
                        matched_map = m
                        break
            
            if matched_map:
                self.selected_map = matched_map
                self.current_map_index = self.available_maps.index(matched_map)
                logging.info(f"[Logic] Карта успешно распознана и выбрана: '{matched_map}'")
            else:
                logging.warning(f"[Logic] ВНИМАНИЕ: Overwolf прислал неизвестную карту: '{map_name}' (mapped to '{mapped_name}'). Доступные карты в БД: {self.available_maps}")
                self.selected_map = mapped_name

    def set_selection(self, desired_selection_set):
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
        self.effective_team =[] 
        
    def clear_all(self):
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        self.effective_team =[]
        
    def set_priority(self, hero):
        if hero not in self.selected_heroes: return
        if hero in self.priority_heroes: self.priority_heroes.discard(hero)
        else: self.priority_heroes.add(hero)
        self.effective_team =[]
        
    def get_selected_heroes_text(self):
        count = len(self.selected_heroes)
        heroes_list = list(self.selected_heroes)
        lang = self.DEFAULT_LANGUAGE
        if not heroes_list: return get_text('selected_none', language=lang, max_team_size=TEAM_SIZE)
        else: return f"{get_text('selected_some', language=lang)} ({count}/{TEAM_SIZE}): {', '.join(heroes_list)}"

    def calculate_counter_scores(self) -> Dict[str, float]:
        if not self.selected_heroes: return {}
        enemy_team = list(self.selected_heroes)

        raw_scores_tuples = calculate_team_counters(enemy_team, matchups_data, is_tier_list_calc=True)
        hero_scores_with_context = absolute_with_context(raw_scores_tuples, hero_stats_data)
        final_scores = {hero: score for hero, score in hero_scores_with_context}

        if self.selected_map:
            for hero in final_scores:
                map_bonus = get_map_score(hero, self.selected_map)
                if map_bonus > 0:
                    final_scores[hero] += map_bonus
        
        sorted_final_scores = sorted(final_scores.items(), key=lambda item: item[1], reverse=True)
        self.calculate_effective_team(sorted_final_scores)
        return dict(sorted_final_scores)

    def calculate_effective_team(self, sorted_heroes_with_scores: List[Tuple[str, float]]) -> List[str]:
        if not sorted_heroes_with_scores:
            self.effective_team = []
            return[]
        optimal_team = select_optimal_team(sorted_heroes_with_scores, hero_roles)
        self.effective_team = optimal_team
        return self.effective_team
        
    def calculate_tier_list_scores(self) -> dict[str, float]:
        hero_scores_tuples = calculate_team_counters(
            enemy_team=heroes,
            matchups_data=matchups_data,
            is_tier_list_calc=True
        )
        hero_scores_with_context = absolute_with_context(hero_scores_tuples, hero_stats_data)
        return {hero: score for hero, score in hero_scores_with_context}
        
    def calculate_tier_list_scores_with_map(self, map_name: str | None = None) -> dict[str, float]:
        hero_scores = self.calculate_tier_list_scores()
        if map_name:
            for hero in hero_scores:
                map_bonus = get_map_score(hero, map_name)
                if map_bonus > 0:
                    hero_scores[hero] += map_bonus
        return hero_scores

    def calculate_counter_scores_for_team(self, enemy_team: list, map_name: str | None = None) -> Tuple[Dict[str, float], List[str]]:
        """
        Рассчитывает контр-очки для произвольной команды врагов.
        НЕ модифицирует состояние (selected_heroes, effective_team).
        Возвращает (scores_dict, effective_team_list).
        Используется треем для Overwolf-данных, не затрагивая главную вкладку.
        """
        if not enemy_team:
            logging.info(f"[Logic] calculate_counter_scores_for_team: враги не выбраны, возвращаем пустой результат")
            return {}, []
        logging.info(f"[Logic] calculate_counter_scores_for_team: враги={enemy_team}, карта={map_name}")
        raw_scores_tuples = calculate_team_counters(enemy_team, matchups_data, is_tier_list_calc=True)
        hero_scores_with_context = absolute_with_context(raw_scores_tuples, hero_stats_data)
        final_scores = {hero: score for hero, score in hero_scores_with_context}
        if map_name:
            for hero in final_scores:
                map_bonus = get_map_score(hero, map_name)
                if map_bonus > 0:
                    final_scores[hero] += map_bonus
        sorted_final_scores = sorted(final_scores.items(), key=lambda item: item[1], reverse=True)
        optimal_team = select_optimal_team(sorted_final_scores, hero_roles)
        logging.info(f"[Logic] calculate_counter_scores_for_team: рассчитано {len(final_scores)} героев, оптимальная команда={optimal_team}")
        return dict(sorted_final_scores), optimal_team