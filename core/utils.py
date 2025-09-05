# File: core/utils.py
import mss
import numpy as np
import cv2
import os
import sys
# ИСПРАВЛЕНО: Исправлен путь импорта
from core.database.heroes_bd import heroes_counters, heroes 
import logging
from pathlib import Path
import re

RECOGNITION_AREA = {
    'monitor': 1, 'left_pct': 50, 'top_pct': 20, 'width_pct': 20, 'height_pct': 50
}

def _get_root_path():
    if hasattr(sys, '_MEIPASS'): 
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def resource_path(relative_path):
    base_path = _get_root_path()
    return os.path.join(base_path, relative_path.replace('/', os.sep))

def normalize_hero_name(name: str) -> str:
    if not name: return ""
    
    normalized = name.lower()
    normalized = re.sub(r'[_ ]*v\d+$', '', normalized)
    normalized = re.sub(r'_\d+$', '', normalized)
    
    suffixes = ["_icon", "_template", "_small", "_left", "_right", "_horizontal", "_adv", "_padded"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            
    normalized = re.sub(r'[-_]+', ' ', normalized).strip()
    for hero_canonical in heroes:
        if hero_canonical.lower() == normalized:
            return hero_canonical
            
    capitalized_attempt = " ".join(p.capitalize() for p in normalized.split(' ') if p)
    for hero_canonical in heroes:
        if hero_canonical == capitalized_attempt:
            return hero_canonical
    
    final_name = capitalized_attempt if capitalized_attempt else name 
    logging.warning(f"Could not match '{name}' to a canonical hero name. Returning '{final_name}'.")
    return final_name

def validate_heroes():
    logging.info("[VALIDATION] Validating hero data structures...")
    errors = []
    heroes_set = set(heroes) 
    for hero, counters in heroes_counters.items():
        if hero not in heroes_set:
            errors.append(f"Unknown hero '{hero}' as key in heroes_counters.")
            continue 
        if not isinstance(counters, dict):
            errors.append(f"Invalid data for '{hero}': expected dict, got {type(counters)}.")
            continue
        for counter_type in ["hard", "soft"]:
            if counter_type in counters:
                if not isinstance(counters[counter_type], list):
                    errors.append(f"For '{hero}' -> '{counter_type}', expected list, got {type(counters[counter_type])}.")
                    continue
                for counter_hero in counters[counter_type]:
                    if counter_hero not in heroes_set:
                        errors.append(f"Unknown hero '{counter_hero}' in '{counter_type}' list for '{hero}'.")
    
    unique_errors = sorted(list(set(errors)))
    if unique_errors:
        logging.error(f"[VALIDATION FAILED] Found errors:\n" + "\n".join(unique_errors))
    else:
        logging.info("[VALIDATION] Validation successful.")
    return unique_errors

def capture_screen_area(area: dict):
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if not monitors: 
                logging.error("No monitors found.")
                return None
            
            monitor_index = area.get('monitor', 1)
            if not (0 <= monitor_index < len(monitors)):
                monitor_index = 1 if len(monitors) > 1 else 0 
                logging.warning(f"Invalid monitor index. Using monitor {monitor_index}.")
            
            monitor = monitors[monitor_index]
            
            left = monitor["left"] + int(monitor["width"] * area['left_pct'] / 100)
            top = monitor["top"] + int(monitor["height"] * area['top_pct'] / 100)
            width = int(monitor["width"] * area['width_pct'] / 100)
            height = int(monitor["height"] * area['height_pct'] / 100)
            
            bbox = {"left": left, "top": top, "width": max(1, width), "height": max(1, height)}
            sct_img = sct.grab(bbox)
            img_bgr = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
            
            logging.info(f"Area captured successfully. Shape: {img_bgr.shape}")
            return img_bgr
    except Exception as e:
         logging.error(f"Error during screen capture: {e}", exc_info=True)
         return None

def capture_full_screen():
    """Захватывает весь экран целиком."""
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if not monitors: 
                logging.error("No monitors found.")
                return None
            
            # Используем первый монитор (индекс 1), который является основным экраном
            monitor_index = 1
            if len(monitors) <= 1:
                logging.warning("Only one monitor found. Using it.")
                monitor_index = 0
            
            monitor = monitors[monitor_index]
            
            # Захватываем весь экран
            bbox = {"left": monitor["left"], "top": monitor["top"], 
                    "width": monitor["width"], "height": monitor["height"]}
            sct_img = sct.grab(bbox)
            img_bgr = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
            
            logging.info(f"Full screen captured successfully. Shape: {img_bgr.shape}")
            return img_bgr
    except Exception as e:
         logging.error(f"Error during full screen capture: {e}", exc_info=True)
         return None