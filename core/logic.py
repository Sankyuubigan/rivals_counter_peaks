# File: core/logic.py
from collections import deque
from database.heroes_bd import heroes, heroes_counters, heroes_compositions
from database.roles_and_groups import hero_roles
from core.lang.translations import get_text, DEFAULT_LANGUAGE as global_default_language
# <<< ИЗМЕНЕНО: Импорт констант AKAZE из utils >>>
from core.utils import (AKAZE_MIN_MATCH_COUNT, AKAZE_LOWE_RATIO,
                       AKAZE_DESCRIPTOR_TYPE)
# <<< ------------------------------------------- >>>
try:
    from ._version import __version__ as app_version_from_file
except ImportError:
    try: from _version import __version__ as app_version_from_file
    except ImportError: app_version_from_file = "dev"

import cv2
import logging

# Убираем импорты torch, torchvision, PIL, т.к. возвращаемся к AKAZE
# import torch
# import torchvision.transforms as transforms
# import torchvision.models as models
# from PIL import Image
# import torch.nn.functional as F
# from PySide6.QtCore import QBuffer, QByteArray, QIODevice # Убираем
# import io # Убираем

MIN_TANKS = 1; MAX_TANKS = 3; MIN_SUPPORTS = 2; MAX_SUPPORTS = 3; TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self, app_version="unknown"):
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set(); self.effective_team = []
        self.DEFAULT_LANGUAGE = global_default_language; self.APP_VERSION = app_version
        logging.info(f"[Logic] Initialized. APP_VERSION set to: '{self.APP_VERSION}'")
        # <<< Убираем инициализацию модели эмбеддингов >>>
        # self.embedding_model = None
        # self.preprocess = None
        # self.device = None
        # self.hero_embeddings = {}
        # self.icon_size = (95, 95)
        # self._initialize_embedding_model()
        # if self.embedding_model: self._precompute_hero_embeddings()
        # else: logging.error("[Logic Init] Embedding model failed to initialize, skipping embedding precomputation.")
        # <<< ------------------------------------------ >>>


    # <<< Убираем методы, связанные с эмбеддингами >>>
    # def _initialize_embedding_model(self): ...
    # def _precompute_hero_embeddings(self): ...
    # <<< ------------------------------------- >>>


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

    # <<< ВОЗВРАЩАЕМ ЛОГИКУ С AKAZE >>>
    def recognize_heroes_from_image(self, image_cv2, hero_templates, threshold=None): # threshold не используется
        """
        Ищет героев на изображении image_cv2 с использованием AKAZE Feature Matching.
        Порог определяется константой AKAZE_MIN_MATCH_COUNT из utils.
        """
        if image_cv2 is None: logging.error("[ERROR][recognize_akaze] Input image is None."); return []
        if not hero_templates: logging.error("[ERROR][recognize_akaze] Template dictionary is empty."); return []

        try:
            image_gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
            if image_gray is None: raise ValueError("Failed to convert screenshot to grayscale")
        except cv2.error as e: logging.error(f"[ERROR][recognize_akaze] OpenCV error converting screenshot to gray: {e}"); return []
        except Exception as e: logging.error(f"[ERROR][recognize_akaze] Error converting screenshot to gray: {e}"); return []

        logging.info(f"[RECOGNIZE AKAZE] Starting AKAZE recognition. Screenshot shape: {image_gray.shape}, Templates: {len(hero_templates)}, Min Matches: {AKAZE_MIN_MATCH_COUNT}")
        try:
            akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
            kp_screenshot, des_screenshot = akaze.detectAndCompute(image_gray, None)
            if des_screenshot is None or len(kp_screenshot) == 0: logging.warning("[WARN][recognize_akaze] No descriptors found in screenshot."); return []
            logging.debug(f"[RECOGNIZE AKAZE] Found {len(kp_screenshot)} keypoints in screenshot.")
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        except cv2.error as e: logging.error(f"[ERROR][recognize_akaze] OpenCV error during AKAZE/Matcher initialization or screenshot processing: {e}"); return []
        except Exception as e: logging.error(f"[ERROR][recognize_akaze] Error during AKAZE/Matcher initialization or screenshot processing: {e}"); return []

        recognized_heroes_scores = {}
        for hero_name, templates in hero_templates.items():
            max_good_matches_for_hero = 0
            for i, template_cv2 in enumerate(templates):
                if template_cv2 is None: logging.warning(f"[WARN][recognize_akaze] Template {i} for hero '{hero_name}' is None."); continue
                try:
                    if len(template_cv2.shape) == 3: template_gray = cv2.cvtColor(template_cv2, cv2.COLOR_BGR2GRAY)
                    else: template_gray = template_cv2
                    if template_gray is None: logging.warning(f"[WARN][recognize_akaze] Failed to convert template {i} for '{hero_name}' to grayscale."); continue
                    kp_template, des_template = akaze.detectAndCompute(template_gray, None)
                    if des_template is None or len(kp_template) == 0: logging.warning(f"[WARN][recognize_akaze] No descriptors found for template {i} of hero '{hero_name}'."); continue
                    matches = bf.knnMatch(des_template, des_screenshot, k=2)
                    good_matches = []; valid_matches = [m for m in matches if len(m) == 2]
                    for m, n in valid_matches:
                        if m.distance < AKAZE_LOWE_RATIO * n.distance: good_matches.append(m)
                    num_good_matches = len(good_matches)
                    logging.debug(f"[RECOGNIZE AKAZE] Hero: '{hero_name}', Template: {i}, Good Matches: {num_good_matches}")
                    if num_good_matches > max_good_matches_for_hero: max_good_matches_for_hero = num_good_matches
                except cv2.error as e: logging.error(f"[ERROR][recognize_akaze] OpenCV error processing template {i} for '{hero_name}': {e}")
                except Exception as e: logging.error(f"[ERROR][recognize_akaze] Unexpected error processing template {i} for '{hero_name}': {e}", exc_info=True)

            recognized_heroes_scores[hero_name] = max_good_matches_for_hero # Сохраняем лучший результат для героя
            if max_good_matches_for_hero >= AKAZE_MIN_MATCH_COUNT: logging.info(f"[RECOGNIZE AKAZE] ----- РАСПОЗНАН: {hero_name} (Matches: {max_good_matches_for_hero} >= {AKAZE_MIN_MATCH_COUNT}) -----")
            elif max_good_matches_for_hero > 0 : logging.info(f"[RECOGNIZE AKAZE] Герой НЕ распознан: {hero_name} (Matches: {max_good_matches_for_hero} < {AKAZE_MIN_MATCH_COUNT})")

        final_heroes = [hero for hero, score in recognized_heroes_scores.items() if score >= AKAZE_MIN_MATCH_COUNT]
        final_heroes_sorted = sorted(final_heroes, key=lambda h: recognized_heroes_scores.get(h, 0), reverse=True)
        logging.info(f"[RECOGNIZE AKAZE] Распознавание завершено. Итог ({len(final_heroes_sorted)}/{TEAM_SIZE}): {final_heroes_sorted}")

        # Логирование топ-N лучших скоров (по количеству совпадений)
        if recognized_heroes_scores:
            sorted_best_scores = sorted(recognized_heroes_scores.items(), key=lambda item: item[1], reverse=True)
            top_n = 15
            logging.info(f"[RECOGNIZE AKAZE] Top-{top_n} best match counts found:") # Используем INFO
            for i, (hero, score) in enumerate(sorted_best_scores[:top_n]):
                status = "PASSED" if score >= AKAZE_MIN_MATCH_COUNT else "FAILED"
                logging.info(f"[RECOGNIZE AKAZE]   {i+1}. {hero}: {score} ({status})") # Используем INFO
            logging.info("-" * 30)

        return final_heroes_sorted[:TEAM_SIZE]
    # <<< ------------------------------------------------------ >>>
