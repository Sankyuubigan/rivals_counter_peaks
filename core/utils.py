# File: core/utils.py
import mss
import numpy as np
import cv2
import os
import sys
# --- ИЗМЕНЕНИЕ ---
# Убираем импорты старой БД
# from database.heroes_bd import heroes_counters, heroes 
# Импортируем загрузчики для новой БД
from database.stats_loader import load_matchups_data, get_all_heroes, load_hero_roles
# --- КОНЕЦ ИЗМЕНЕНИЯ ---
import logging
from pathlib import Path
import re

RECOGNITION_AREA = {
    'monitor': 1, 'left_pct': 50, 'top_pct': 20, 'width_pct': 40, 'height_pct': 50
}

def _get_root_path():
    if hasattr(sys, '_MEIPASS'): 
        base_path = sys._MEIPASS
    else: 
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return base_path

def resource_path(relative_path):
    base_path = _get_root_path()
    relative_path_corrected = relative_path.replace('/', os.sep).replace('\\', os.sep)
    final_path = os.path.join(base_path, relative_path_corrected)
    return final_path

def normalize_hero_name(name: str) -> str:
    if not name: return ""
    
    normalized = name.lower()
    normalized = re.sub(r'[_ ]*v\d+$', '', normalized)
    normalized = re.sub(r'_\d+$', '', normalized)
    other_suffixes_to_remove = ["_icon", "_template", "_small", "_left", "_right", "_horizontal", "_adv", "_padded"]
    for suffix in other_suffixes_to_remove:
        if normalized.endswith(suffix): normalized = normalized[:-len(suffix)]
            
    normalized = re.sub(r'[-_]+', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # --- ИЗМЕНЕНИЕ: Получаем список героев из нового источника ---
    heroes_list = get_all_heroes(load_matchups_data())
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    for hero_canonical_name in heroes_list:
        if hero_canonical_name.lower() == normalized:
            return hero_canonical_name
            
    parts = normalized.split(' ')
    capitalized_name_attempt = " ".join(p.capitalize() for p in parts if p)
    
    for hero_canonical_name in heroes_list:
        if hero_canonical_name == capitalized_name_attempt:
            return hero_canonical_name
    
    final_return_name = capitalized_name_attempt if capitalized_name_attempt else name 
    logging.warning(f"Не удалось точно сопоставить имя '{name}' с каноническим. Возвращаем '{final_return_name}'.")
    return final_return_name

def validate_heroes():
    logging.info("[VALIDATION] Запуск проверки данных героев (новая структура)...")
    errors = []
    
    matchups_data = load_matchups_data()
    hero_roles = load_hero_roles()
    heroes_from_matchups = set(get_all_heroes(matchups_data))
    heroes_from_roles = set(hero_roles.keys())

    if not heroes_from_matchups:
        errors.append("Критическая ошибка: не удалось загрузить данные о противостояниях. Список героев пуст.")
        return errors

    # Проверка 1: Все ли герои из ролей есть в основной базе
    missing_in_matchups = heroes_from_roles - heroes_from_matchups
    if missing_in_matchups:
        errors.append(f"Герои из файла ролей отсутствуют в основной базе данных: {', '.join(sorted(list(missing_in_matchups)))}")

    # Проверка 2: У всех ли героев из основной базы есть роль
    missing_role = heroes_from_matchups - heroes_from_roles
    if missing_role:
        errors.append(f"Для следующих героев не указана роль в roles_and_groups.py: {', '.join(sorted(list(missing_role)))}")

    # Проверка 3: Валидация структуры данных для каждого героя
    for hero, matchups in matchups_data.items():
        if not isinstance(matchups, list):
            errors.append(f"Для героя '{hero}' данные о противниках не являются списком (list).")
            continue
        
        for i, matchup in enumerate(matchups):
            if not isinstance(matchup, dict):
                errors.append(f"Для героя '{hero}', запись о противнике #{i+1} не является словарем (dict).")
                continue
            
            required_keys = {"opponent", "difference"}
            if not required_keys.issubset(matchup.keys()):
                errors.append(f"Для героя '{hero}', в записи о противнике #{i+1} отсутствуют ключи: {required_keys - set(matchup.keys())}.")
            
            opponent_name = matchup.get("opponent")
            if opponent_name not in heroes_from_matchups:
                errors.append(f"Для героя '{hero}', найден неизвестный противник '{opponent_name}'.")

    unique_errors = sorted(list(set(errors)))
    if unique_errors:
        logging.error(f"[VALIDATION ERROR] Найдены ошибки в структуре данных:\n" + "\n".join(unique_errors))
        return unique_errors
    else:
        logging.info("[VALIDATION] Проверка данных (новая структура) пройдена успешно.")
        return []


def capture_screen_area(area: dict):
    logging.debug(f"[CAPTURE] Attempting capture for area definition: {area}")
    img_bgr = None 
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if not monitors: 
                logging.error("[ERROR][CAPTURE] No monitors found.")
                return None
            
            target_monitor_index = area.get('monitor', 1)
            if not (0 <= target_monitor_index < len(monitors)):
                corrected_index = 1 if len(monitors) > 1 else 0 
                if not (0 <= corrected_index < len(monitors)):
                     logging.error(f"[ERROR][CAPTURE] Corrected monitor index {corrected_index} is still invalid for {len(monitors)} monitors.")
                     return None
                logging.warning(f"[WARN][CAPTURE] Invalid monitor index {target_monitor_index}. Using monitor {corrected_index} instead.")
                target_monitor_index = corrected_index
            
            monitor_geometry = monitors[target_monitor_index] 
            mon_width, mon_height, mon_left, mon_top = monitor_geometry["width"], monitor_geometry["height"], monitor_geometry["left"], monitor_geometry["top"]
            
            use_pct = all(k in area for k in ['left_pct', 'top_pct', 'width_pct', 'height_pct'])
            if use_pct:
                left_px = int(mon_width * area['left_pct'] / 100); top_px = int(mon_height * area['top_pct'] / 100)
                width_px = int(mon_width * area['width_pct'] / 100); height_px = int(mon_height * area['height_pct'] / 100)
            else: 
                left_px = area.get('left', 0); top_px = area.get('top', 0)
                width_px = area.get('width', 100); height_px = area.get('height', 100)
            
            bbox = {"left": mon_left + left_px, "top": mon_top + top_px, "width": max(1, width_px), "height": max(1, height_px), "mon": target_monitor_index}

            if bbox['width'] <= 0 or bbox['height'] <= 0:
                logging.error(f"[ERROR][CAPTURE] Invalid calculated capture dimensions: {bbox}")
                return None
            
            sct_img = sct.grab(bbox)

            if sct_img:
                img_np = np.array(sct_img)
                if img_np.size == 0: logging.error("[ERROR][CAPTURE] Grabbed empty image."); return None
                if len(img_np.shape) < 3: logging.error(f"[ERROR][CAPTURE] Unexpected image format (shape: {img_np.shape})."); return None

                if img_np.shape == 4: img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                elif img_np.shape == 3: img_bgr = img_np 
                else: logging.error(f"[ERROR][CAPTURE] Unexpected image format (channels: {img_np.shape})."); return None
                
                logging.info(f"[CAPTURE] Area captured successfully. Shape: {img_bgr.shape if img_bgr is not None else 'None'}")
                return img_bgr
            else: 
                logging.error("[ERROR][CAPTURE] sct.grab() did not return a valid image.")
                return None
    except mss.exception.ScreenShotError as e_mss:
         logging.error(f"[ERROR][CAPTURE] mss.ScreenShotError: {e_mss}")
         return None
    except Exception as e_grab:
         logging.error(f"[ERROR][CAPTURE] Unexpected error during screen capture: {e_grab}", exc_info=True)
         return None