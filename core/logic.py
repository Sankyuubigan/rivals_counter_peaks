# File: core/logic.py
from collections import deque
from heroes_bd import heroes, heroes_counters, hero_roles, heroes_compositions
from core.translations import get_text, DEFAULT_LANGUAGE as global_default_language
try:
    from ._version import __version__ as app_version_from_file
except ImportError:
    try: from _version import __version__ as app_version_from_file
    except ImportError: app_version_from_file = "dev"

import cv2
import numpy as np
import os
import logging

MIN_TANKS = 1; MAX_TANKS = 3; MIN_SUPPORTS = 2; MAX_SUPPORTS = 3; TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self, app_version="unknown"):
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set(); self.effective_team = []
        self.DEFAULT_LANGUAGE = global_default_language; self.APP_VERSION = app_version
        logging.info(f"[Logic] Initialized. APP_VERSION set to: '{self.APP_VERSION}'")

    def set_selection(self, desired_selection_set):
        logging.debug(f"[Logic] set_selection called with set: {desired_selection_set}")
        logging.debug(f"[Logic] Current internal selection (before): {list(self.selected_heroes)}")
        current_selection_list = list(self.selected_heroes); current_selection_set = set(current_selection_list)
        added_heroes = desired_selection_set - current_selection_set; removed_heroes = current_selection_set - desired_selection_set
        logging.debug(f"[Logic] Heroes to add: {added_heroes}"); logging.debug(f"[Logic] Heroes to remove: {removed_heroes}")
        new_deque = deque(maxlen=TEAM_SIZE)
        for hero in current_selection_list:
            if hero not in removed_heroes: new_deque.append(hero)
        for hero in added_heroes:
            if hero not in new_deque: new_deque.append(hero); logging.debug(f"[Logic] Appended '{hero}'. Deque state: {list(new_deque)}")
        self.selected_heroes = new_deque; self.priority_heroes.intersection_update(set(self.selected_heroes))
        logging.debug(f"[Logic] Final internal selection: {list(self.selected_heroes)}"); logging.debug(f"[Logic] Final priority: {self.priority_heroes}"); self.effective_team = []

    def clear_all(self):
        logging.info("[Logic] Clearing all selections.")
        self.selected_heroes.clear(); self.priority_heroes.clear(); self.effective_team = []

    def set_priority(self, hero):
        if hero not in self.selected_heroes: logging.warning(f"[Logic] Cannot set priority for non-selected hero: {hero}"); return
        if hero in self.priority_heroes: self.priority_heroes.discard(hero); logging.info(f"[Logic] Priority removed from {hero}")
        else: self.priority_heroes.add(hero); logging.info(f"[Logic] Priority set for {hero}")
        self.effective_team = []

    def get_selected_heroes_text(self):
        count = len(self.selected_heroes); heroes_list = list(self.selected_heroes); lang = self.DEFAULT_LANGUAGE
        if not heroes_list: return get_text('selected_none', language=lang, max_team_size=TEAM_SIZE)
        else: header = f"{get_text('selected_some', language=lang)} ({count}/{TEAM_SIZE}): "; return f"{header}{', '.join(heroes_list)}"

    def _calculate_hero_score(self, hero, current_selection_set, priority_heroes):
        score = 0.0
        for enemy in current_selection_set:
            if hero in heroes_counters.get(enemy, []): score += 2.0 if enemy in priority_heroes else 1.0
        if hero in current_selection_set: score -= 5.0
        counters_for_hero = heroes_counters.get(hero, [])
        for enemy in current_selection_set:
            if enemy in counters_for_hero: score -= 1.5 if enemy in priority_heroes else 1.0
        return score

    def calculate_counter_scores(self):
        if not self.selected_heroes: return {}
        counter_scores = {}; current_selection_set = set(self.selected_heroes); priority_heroes_set = self.priority_heroes
        for hero in heroes: counter_scores[hero] = self._calculate_hero_score(hero, current_selection_set, priority_heroes_set)
        return counter_scores

    def calculate_effective_team(self, counter_scores):
        if not counter_scores: self.effective_team = []; return []
        candidates = {h: s for h, s in counter_scores.items() if s > 0 and h not in self.selected_heroes}
        if not candidates: self.effective_team = []; return []
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        effective_team = deque(maxlen=TEAM_SIZE); added_heroes_set = set(); tanks_count, supports_count, attackers_count = 0, 0, 0
        def role_priority_key(item):
            h, s = item; role_tanks = hero_roles.get("tanks", []); role_supports = hero_roles.get("supports", [])
            if h in role_tanks: return (0, -s)
            if h in role_supports: return (1, -s)
            return (2, -s)
        role_sorted_candidates = sorted(candidates.items(), key=role_priority_key)
        for hero, score in role_sorted_candidates:
             if tanks_count < MIN_TANKS and hero in hero_roles.get("tanks", []): effective_team.append(hero); added_heroes_set.add(hero); tanks_count += 1; break
        support_added_count_step1 = 0
        for hero, score in role_sorted_candidates:
             if hero not in added_heroes_set and support_added_count_step1 < MIN_SUPPORTS and hero in hero_roles.get("supports", []):
                 effective_team.append(hero); added_heroes_set.add(hero); supports_count += 1; support_added_count_step1 += 1
                 if support_added_count_step1 >= MIN_SUPPORTS: break
        remaining_candidates = [(h, s) for h, s in sorted_candidates if h not in added_heroes_set]
        while len(effective_team) < TEAM_SIZE and remaining_candidates:
            best_hero_to_add = None; best_adjusted_score = -float('inf'); candidate_index_to_remove = -1
            for i, (hero, score) in enumerate(remaining_candidates):
                 can_add = False; role = "unknown"; role_tanks = hero_roles.get("tanks", []); role_supports = hero_roles.get("supports", []); role_attackers = hero_roles.get("attackers", [])
                 if hero in role_tanks: role = "tanks"
                 elif hero in role_supports: role = "supports"
                 elif hero in role_attackers: role = "attackers"
                 if role == "tanks" and tanks_count < MAX_TANKS: can_add = True
                 elif role == "supports" and supports_count < MAX_SUPPORTS: can_add = True
                 elif role == "attackers": can_add = True
                 elif role == "unknown": can_add = True
                 if can_add:
                     synergy_bonus = 0
                     for teammate in effective_team:
                         if hero in heroes_compositions.get(teammate, []): synergy_bonus += 0.5
                         if teammate in heroes_compositions.get(hero, []): synergy_bonus += 0.5
                     adjusted_score = score + synergy_bonus
                     if adjusted_score > best_adjusted_score: best_adjusted_score = adjusted_score; best_hero_to_add = hero; candidate_index_to_remove = i
            if best_hero_to_add is not None:
                effective_team.append(best_hero_to_add); added_heroes_set.add(best_hero_to_add)
                if best_hero_to_add in hero_roles.get("tanks", []): tanks_count += 1
                elif best_hero_to_add in hero_roles.get("supports", []): supports_count += 1
                elif best_hero_to_add in hero_roles.get("attackers", []): attackers_count += 1
                if 0 <= candidate_index_to_remove < len(remaining_candidates): remaining_candidates.pop(candidate_index_to_remove)
                else: logging.warning(f"[Logic] Invalid index {candidate_index_to_remove} for remaining_candidates"); break
            else: break
        self.effective_team = list(effective_team); return self.effective_team

    def recognize_heroes_from_image(self, image_cv2, hero_templates, threshold=0.8):
        if image_cv2 is None: logging.error("[ERROR][recognize] Входное изображение пустое."); return []
        if not hero_templates: logging.error("[ERROR][recognize] Словарь шаблонов пуст."); return []
        recognized_heroes = set(); all_match_values = {}
        try: image_gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
        except cv2.error as e: logging.error(f"[ERROR][recognize] Ошибка конвертации изображения в серое: {e}"); return []
        logging.info(f"[RECOGNIZE] Начало распознавания. Изображение: {image_gray.shape}, Шаблонов: {len(hero_templates)}, Порог: {threshold}")

        for hero_name, templates in hero_templates.items():
            best_match_val_for_hero = -1; found_hero_this_iteration = False
            for i, template_cv2 in enumerate(templates):
                if template_cv2 is None: continue
                try:
                    if len(template_cv2.shape) == 3: template_gray = cv2.cvtColor(template_cv2, cv2.COLOR_BGR2GRAY)
                    else: template_gray = template_cv2
                    if template_gray is None: continue
                    h, w = template_gray.shape
                    if h > image_gray.shape[0] or w > image_gray.shape[1]: continue
                    res = cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED) # TM_CCOEFF_NORMED TM_CCORR_NORMED TM_SQDIFF_NORMED
                    if res is None: continue
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    if max_val > best_match_val_for_hero: best_match_val_for_hero = max_val
                    if max_val >= threshold:
                        if not found_hero_this_iteration: logging.info(f"[RECOGNIZE] ----- НАЙДЕН: {hero_name} (шаблон {i}, уверенность: {max_val:.4f} >= {threshold}) -----")
                        recognized_heroes.add(hero_name); found_hero_this_iteration = True
                except cv2.error as e: logging.error(f"[ERROR][recognize] Ошибка OpenCV при обработке шаблона {i} для {hero_name}: {e}")
                except Exception as e: logging.error(f"[ERROR][recognize] Неожиданная ошибка при обработке шаблона {i} для {hero_name}: {e}")

            all_match_values[hero_name] = best_match_val_for_hero
            # <<< ИЗМЕНЕНО: Логгируем нераспознанных героев уровнем INFO, остальных DEBUG >>>
            if not found_hero_this_iteration and best_match_val_for_hero > 0.1: # Порог для логирования, чтобы не спамить нулевыми
                 logging.info(f"[RECOGNIZE] Герой НЕ найден: {hero_name} (Лучшая уверенность: {best_match_val_for_hero:.4f} < {threshold})")
            elif not found_hero_this_iteration:
                 logging.debug(f"[RECOGNIZE] Нет значимых совпадений для: {hero_name} (Max val: {best_match_val_for_hero:.4f})")
            # <<< -------------------------------------------------------------------- >>>

        final_list = list(recognized_heroes)
        logging.info(f"[RECOGNIZE] Распознавание завершено. Итог ({len(final_list)}/{TEAM_SIZE}): {final_list}")
        if all_match_values:
            sorted_matches = sorted(all_match_values.items(), key=lambda item: item[1], reverse=True); top_n = 10
            logging.info(f"[RECOGNIZE] Топ-{top_n} лучших совпадений (даже ниже порога):")
            for i, (hero, val) in enumerate(sorted_matches[:top_n]): logging.info(f"[RECOGNIZE]   {i+1}. {hero}: {val:.4f}")
        return final_list[:TEAM_SIZE]
