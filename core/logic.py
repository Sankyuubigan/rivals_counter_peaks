# File: core/logic.py
from collections import deque
from database.heroes_bd import heroes, heroes_counters, heroes_compositions 
from database.roles_and_groups import hero_roles
from core.lang.translations import get_text, DEFAULT_LANGUAGE as global_default_language
from core.utils import (AKAZE_MIN_MATCH_COUNT, AKAZE_LOWE_RATIO,
                       AKAZE_DESCRIPTOR_TYPE)

import cv2
import logging

MIN_TANKS = 1; MAX_TANKS = 3; MIN_SUPPORTS = 2; MAX_SUPPORTS = 3; TEAM_SIZE = 6

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
            if hero_to_add not in new_deque:
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
        counter_scores = {}
        current_selection_set = set(self.selected_heroes)
        priority_heroes_set = self.priority_heroes 

        for hero_candidate in heroes: 
            counter_scores[hero_candidate] = self._calculate_hero_score(
                hero_candidate, current_selection_set, priority_heroes_set
            )
        return counter_scores

    def calculate_effective_team(self, counter_scores):
        if not counter_scores: self.effective_team = []; return []
        candidates = {h: s for h, s in counter_scores.items() if s > 0 and h not in self.selected_heroes}
        if not candidates: self.effective_team = []; return []
        
        sorted_candidates_by_score = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        
        effective_team = deque(maxlen=TEAM_SIZE)
        added_heroes_set = set()
        tanks_count, supports_count, attackers_count = 0, 0, 0

        def role_priority_key(item_tuple):
            hero_name, score = item_tuple
            role_tanks_list = hero_roles.get("tanks", [])
            role_supports_list = hero_roles.get("supports", [])
            if hero_name in role_tanks_list: return (0, -score) 
            if hero_name in role_supports_list: return (1, -score)
            return (2, -score) 

        role_sorted_all_candidates = sorted(candidates.items(), key=role_priority_key)

        for hero, score in role_sorted_all_candidates:
            if tanks_count < MIN_TANKS and hero in hero_roles.get("tanks", []) and hero not in added_heroes_set:
                effective_team.append(hero); added_heroes_set.add(hero); tanks_count += 1
                if tanks_count >= MIN_TANKS: break 

        for hero, score in role_sorted_all_candidates:
            if supports_count < MIN_SUPPORTS and hero in hero_roles.get("supports", []) and hero not in added_heroes_set:
                effective_team.append(hero); added_heroes_set.add(hero); supports_count += 1
                if supports_count >= MIN_SUPPORTS: break

        remaining_candidates_by_score = [item for item in sorted_candidates_by_score if item[0] not in added_heroes_set]

        while len(effective_team) < TEAM_SIZE and remaining_candidates_by_score:
            best_hero_to_add = None
            best_adjusted_score = -float('inf')
            candidate_index_to_remove = -1

            for i, (hero, score) in enumerate(remaining_candidates_by_score):
                can_add_hero = False
                current_role = "unknown"
                if hero in hero_roles.get("tanks", []): current_role = "tanks"
                elif hero in hero_roles.get("supports", []): current_role = "supports"
                elif hero in hero_roles.get("attackers", []): current_role = "attackers"
                
                if current_role == "tanks" and tanks_count < MAX_TANKS: can_add_hero = True
                elif current_role == "supports" and supports_count < MAX_SUPPORTS: can_add_hero = True
                elif current_role == "attackers": can_add_hero = True 
                elif current_role == "unknown": can_add_hero = True 

                if can_add_hero:
                    synergy_bonus = 0
                    for teammate in effective_team: 
                        if hero in heroes_compositions.get(teammate, []): synergy_bonus += 0.5
                        if teammate in heroes_compositions.get(hero, []): synergy_bonus += 0.5
                    
                    adjusted_score_for_candidate = score + synergy_bonus
                    if adjusted_score_for_candidate > best_adjusted_score:
                        best_adjusted_score = adjusted_score_for_candidate
                        best_hero_to_add = hero
                        candidate_index_to_remove = i
            
            if best_hero_to_add is not None:
                effective_team.append(best_hero_to_add)
                added_heroes_set.add(best_hero_to_add)
                if best_hero_to_add in hero_roles.get("tanks", []): tanks_count += 1
                elif best_hero_to_add in hero_roles.get("supports", []): supports_count += 1
                elif best_hero_to_add in hero_roles.get("attackers", []): attackers_count +=1

                if 0 <= candidate_index_to_remove < len(remaining_candidates_by_score):
                    remaining_candidates_by_score.pop(candidate_index_to_remove)
                else: 
                    logging.warning(f"[Logic - EffectiveTeam] Invalid index {candidate_index_to_remove} for remaining_candidates.")
                    break 
            else: 
                break
        
        self.effective_team = list(effective_team)
        return self.effective_team


    def recognize_heroes_from_image(self, image_cv2, hero_templates, threshold=None):
        if image_cv2 is None: 
            logging.error("[ERROR][recognize_akaze] Input image is None.")
            return []
        if not hero_templates: 
            logging.error("[ERROR][recognize_akaze] Template dictionary is empty.")
            return []
        
        image_gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
        if image_gray is None:
            logging.error("[ERROR][recognize_akaze] Failed to convert screenshot to grayscale")
            return []
            
        logging.info(f"[RECOGNIZE AKAZE] Starting AKAZE recognition. Screenshot shape: {image_gray.shape}, Templates: {len(hero_templates)}, Min Matches: {AKAZE_MIN_MATCH_COUNT}")
        
        akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
        kp_screenshot, des_screenshot = akaze.detectAndCompute(image_gray, None)
        
        if des_screenshot is None or len(kp_screenshot) == 0: 
            logging.warning("[WARN][recognize_akaze] No descriptors found in screenshot.")
            return []
            
        logging.debug(f"[RECOGNIZE AKAZE] Found {len(kp_screenshot)} keypoints in screenshot.")
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        
        recognized_heroes_scores = {}
        for hero_name, templates in hero_templates.items():
            max_good_matches_for_hero = 0
            for i, template_cv2_single in enumerate(templates): # Изменено имя переменной
                if template_cv2_single is None: 
                    logging.warning(f"[WARN][recognize_akaze] Template {i} for hero '{hero_name}' is None.")
                    continue
                
                template_gray = None
                if len(template_cv2_single.shape) == 3: 
                    template_gray = cv2.cvtColor(template_cv2_single, cv2.COLOR_BGR2GRAY)
                else: # Уже серое
                    template_gray = template_cv2_single 
                
                if template_gray is None: 
                    logging.warning(f"[WARN][recognize_akaze] Failed to convert template {i} for '{hero_name}' to grayscale.")
                    continue
                    
                kp_template, des_template = akaze.detectAndCompute(template_gray, None)
                if des_template is None or len(kp_template) == 0: 
                    logging.warning(f"[WARN][recognize_akaze] No descriptors found for template {i} of hero '{hero_name}'.")
                    continue
                
                # Проверка на None перед knnMatch (хотя уже должны были выйти)
                if des_template is None or des_screenshot is None:
                    logging.warning(f"[WARN][recognize_akaze] Descriptors are None for template or screenshot before knnMatch. Hero: {hero_name}")
                    continue

                matches = bf.knnMatch(des_template, des_screenshot, k=2)
                good_matches = []
                # Убедимся, что есть 2 совпадения для каждого m в matches
                valid_matches = [m_pair for m_pair in matches if m_pair is not None and len(m_pair) == 2] 
                for m, n in valid_matches:
                    if m.distance < AKAZE_LOWE_RATIO * n.distance: 
                        good_matches.append(m)
                
                num_good_matches = len(good_matches)
                logging.debug(f"[RECOGNIZE AKAZE] Hero: '{hero_name}', Template: {i}, Good Matches: {num_good_matches}")
                if num_good_matches > max_good_matches_for_hero: 
                    max_good_matches_for_hero = num_good_matches
            
            recognized_heroes_scores[hero_name] = max_good_matches_for_hero
            if max_good_matches_for_hero >= AKAZE_MIN_MATCH_COUNT: 
                logging.info(f"[RECOGNIZE AKAZE] ----- РАСПОЗНАН: {hero_name} (Matches: {max_good_matches_for_hero} >= {AKAZE_MIN_MATCH_COUNT}) -----")
            elif max_good_matches_for_hero > 0 : 
                logging.info(f"[RECOGNIZE AKAZE] Герой НЕ распознан: {hero_name} (Matches: {max_good_matches_for_hero} < {AKAZE_MIN_MATCH_COUNT})")
        
        final_heroes = [hero for hero, score in recognized_heroes_scores.items() if score >= AKAZE_MIN_MATCH_COUNT]
        final_heroes_sorted = sorted(final_heroes, key=lambda h: recognized_heroes_scores.get(h, 0), reverse=True)
        logging.info(f"[RECOGNIZE AKAZE] Распознавание завершено. Итог ({len(final_heroes_sorted)}/{TEAM_SIZE}): {final_heroes_sorted}")
        
        if recognized_heroes_scores:
            sorted_best_scores = sorted(recognized_heroes_scores.items(), key=lambda item: item[1], reverse=True)
            top_n = 15
            logging.info(f"[RECOGNIZE AKAZE] Top-{top_n} best match counts found:")
            for i, (hero, score) in enumerate(sorted_best_scores[:top_n]):
                status = "PASSED" if score >= AKAZE_MIN_MATCH_COUNT else "FAILED"
                logging.info(f"[RECOGNIZE AKAZE]   {i+1}. {hero}: {score} ({status})")
            logging.info("-" * 30)
        return final_heroes_sorted[:TEAM_SIZE]
