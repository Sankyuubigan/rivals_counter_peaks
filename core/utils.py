# File: core/utils.py
import mss
import mss.tools
import numpy as np
import cv2
import os
import sys
from heroes_bd import heroes_counters, heroes
import logging

# --- Константы для распознавания ---
RECOGNITION_AREA = {
    'monitor': 1,
    'left_pct': 50,
    'top_pct': 20,
    'width_pct': 40,
    'height_pct': 50
}
RECOGNITION_THRESHOLD = 0.8 # Для Template Matching

# ORB (оставляем на всякий случай)
ORB_NFEATURES = 1000
ORB_MIN_MATCH_COUNT = 10
ORB_LOWE_RATIO = 0.75

# <<< ИЗМЕНЕНО: Константы для AKAZE >>>
AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
# !!! Понижаем порог еще немного, до 4 !!!
AKAZE_MIN_MATCH_COUNT = 4
AKAZE_LOWE_RATIO = 0.75 # Вернем 0.75, как было у ORB, часто это стандартное значение
# <<< ---------------------------- >>>


def _get_root_path():
    if hasattr(sys, '_MEIPASS'): base_path = sys._MEIPASS
    else: base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return base_path

def resource_path(relative_path):
    base_path = _get_root_path()
    relative_path_corrected = relative_path.replace('/', os.sep).replace('\\', os.sep)
    return os.path.join(base_path, relative_path_corrected)

def validate_heroes():
    logging.info("[VALIDATION] Запуск проверки имен героев...")
    invalid_heroes = []; heroes_set = set(heroes)
    for hero in heroes_counters.keys():
        if hero not in heroes_set: invalid_heroes.append(f"{hero} (ключ в heroes_counters)")
    for hero, counters in heroes_counters.items():
        if hero not in heroes_set: continue
        for counter in counters:
            if counter not in heroes_set: invalid_heroes.append(f"{counter} (контрпик для {hero})")
    unique_invalid = sorted(list(set(invalid_heroes)))
    if unique_invalid: logging.error(f"[VALIDATION ERROR] Найдены невалидные имена героев:\n{chr(10).join(unique_invalid)}"); return unique_invalid
    else: logging.info("[VALIDATION] Проверка имен героев в heroes_counters пройдена успешно."); return []

def check_if_all_elements_in_list(target_list, check_list):
    return set(check_list).issubset(set(target_list))

def capture_screen_area(area: dict):
    logging.debug(f"[CAPTURE] Attempting capture for area definition: {area}")
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if not monitors: logging.error("[ERROR][CAPTURE] No monitors found."); return None
            target_monitor_index = area.get('monitor', 1)
            if target_monitor_index >= len(monitors):
                 corrected_index = 1 if len(monitors) > 1 else 0
                 logging.warning(f"[WARN][CAPTURE] Invalid monitor index {target_monitor_index}. Available: {len(monitors)}. Using monitor {corrected_index} instead.")
                 target_monitor_index = corrected_index
                 if target_monitor_index >= len(monitors): logging.error("[ERROR][CAPTURE] Corrected monitor index still invalid."); return None
            try: monitor_geometry = monitors[target_monitor_index]
            except IndexError: logging.error(f"[ERROR][CAPTURE] IndexError accessing monitor {target_monitor_index}. Monitors: {monitors}"); return None

            mon_width = monitor_geometry["width"]; mon_height = monitor_geometry["height"]
            mon_left = monitor_geometry["left"]; mon_top = monitor_geometry["top"]
            use_pct = False
            if all(k in area for k in ['left_pct', 'top_pct', 'width_pct', 'height_pct']):
                use_pct = True; logging.debug(f"[CAPTURE] Using percentage values.")
                left_px = int(mon_width * area['left_pct'] / 100); top_px = int(mon_height * area['top_pct'] / 100)
                width_px = int(mon_width * area['width_pct'] / 100); height_px = int(mon_height * area['height_pct'] / 100)
                logging.debug(f"[CAPTURE] Calculated px: L={left_px}, T={top_px}, W={width_px}, H={height_px}")
            else:
                logging.debug(f"[CAPTURE] Using absolute pixel values.")
                left_px = area.get('left', 0); top_px = area.get('top', 0)
                width_px = area.get('width', 100); height_px = area.get('height', 100)

            bbox = {"left": mon_left + left_px, "top": mon_top + top_px, "width": max(1, width_px), "height": max(1, height_px), "mon": target_monitor_index}
            if bbox['width'] <= 0 or bbox['height'] <= 0: logging.error(f"[ERROR][CAPTURE] Invalid calculated capture dimensions: {bbox}"); return None
            logging.debug(f"[CAPTURE] Grabbing BBox: {bbox} on Monitor: {target_monitor_index}")
            sct_img = sct.grab(bbox); img_np = np.array(sct_img)
            if img_np.size == 0: logging.error("[ERROR][CAPTURE] Grabbed empty image."); return None
            if img_np.shape[2] == 4: img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
            elif img_np.shape[2] == 3: img_bgr = img_np
            else: logging.error(f"[ERROR][CAPTURE] Unexpected image format (channels: {img_np.shape[2]})."); return None
            logging.info(f"[CAPTURE] Area captured successfully. Shape: {img_bgr.shape}"); return img_bgr
    except mss.ScreenShotError as e: logging.error(f"[ERROR][CAPTURE] mss error: {e}"); return None
    except Exception as e: logging.error(f"[ERROR][CAPTURE] Unexpected error during capture: {e}", exc_info=True); return None
