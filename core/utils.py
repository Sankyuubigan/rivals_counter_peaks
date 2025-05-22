# File: core/utils.py
import mss
import mss.tools
import numpy as np
import cv2
import os
import sys
from database.heroes_bd import heroes_counters, heroes # heroes_counters теперь новой структуры
import logging
from pathlib import Path

RECOGNITION_AREA = {
    'monitor': 1, 'left_pct': 50, 'top_pct': 20, 'width_pct': 40, 'height_pct': 50
}
SIMILARITY_THRESHOLD = 0.72
SLIDING_WINDOW_SIZE = (50, 50)
SLIDING_WINDOW_STEP = (10, 10)
RECOGNITION_THRESHOLD = 0.8
ORB_NFEATURES = 1000; ORB_MIN_MATCH_COUNT = 10; ORB_LOWE_RATIO = 0.75
AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB; AKAZE_MIN_MATCH_COUNT = 3; AKAZE_LOWE_RATIO = 0.75

def _get_root_path():
    if hasattr(sys, '_MEIPASS'): base_path = sys._MEIPASS
    else: base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return base_path

def resource_path(relative_path):
    base_path = _get_root_path()
    relative_path_corrected = relative_path.replace('/', os.sep).replace('\\', os.sep)
    final_path = os.path.join(base_path, relative_path_corrected)
    return final_path

def get_settings_path() -> Path:
    if sys.platform == "win32":
        app_data_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        app_data_dir = Path.home() / ".config"
    app_name_dir = app_data_dir / "RivalsCounterPeaks"
    app_name_dir.mkdir(parents=True, exist_ok=True)
    return app_name_dir / "hotkeys.json"

def validate_heroes():
    logging.info("[VALIDATION] Запуск проверки имен героев (новая структура)...")
    invalid_entries = []
    heroes_set = set(heroes) # Множество всех известных героев из heroes_bd.heroes

    for hero_being_countered, counters_data in heroes_counters.items():
        if hero_being_countered not in heroes_set:
            invalid_entries.append(f"Неизвестный герой '{hero_being_countered}' как ключ в heroes_counters.")
            continue # Пропускаем дальнейшую проверку для этого ключа

        if not isinstance(counters_data, dict):
            invalid_entries.append(f"Неверный формат данных для '{hero_being_countered}': ожидался словарь, получен {type(counters_data)}.")
            continue

        for counter_type in ["hard", "soft"]:
            if counter_type not in counters_data:
                # Это нормально, если нет hard или soft контр, но если есть, то должен быть список
                # invalid_entries.append(f"Отсутствует ключ '{counter_type}' для героя '{hero_being_countered}'.")
                continue 
            
            counter_list = counters_data[counter_type]
            if not isinstance(counter_list, list):
                invalid_entries.append(f"Для '{hero_being_countered}' -> '{counter_type}' ожидался список, получен {type(counter_list)}.")
                continue

            for counter_hero_name in counter_list:
                if not isinstance(counter_hero_name, str):
                    invalid_entries.append(f"В списке '{counter_type}' для '{hero_being_countered}' найден нестроковый элемент: '{counter_hero_name}' ({type(counter_hero_name)}).")
                elif counter_hero_name not in heroes_set:
                    # Это основная ошибка, которую ты видел: "hard" или "soft" вместо имени
                    invalid_entries.append(f"Неизвестный герой '{counter_hero_name}' в списке '{counter_type}' для '{hero_being_countered}'.")
    
    unique_invalid = sorted(list(set(invalid_entries)))
    if unique_invalid:
        logging.error(f"[VALIDATION ERROR] Найдены ошибки в структуре или именах героев в heroes_counters:\n" + "\n".join(unique_invalid))
        return unique_invalid
    else:
        logging.info("[VALIDATION] Проверка heroes_counters (новая структура) пройдена успешно.")
        return []


def check_if_all_elements_in_list(target_list, check_list):
    return set(check_list).issubset(set(target_list))

def capture_screen_area(area: dict): # ... (без изменений) ...
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
            mon_width = monitor_geometry["width"]; mon_height = monitor_geometry["height"]; mon_left = monitor_geometry["left"]; mon_top = monitor_geometry["top"]; use_pct = False
            if all(k in area for k in ['left_pct', 'top_pct', 'width_pct', 'height_pct']):
                use_pct = True; logging.debug(f"[CAPTURE] Using percentage values."); left_px = int(mon_width * area['left_pct'] / 100); top_px = int(mon_height * area['top_pct'] / 100); width_px = int(mon_width * area['width_pct'] / 100); height_px = int(mon_height * area['height_pct'] / 100); logging.debug(f"[CAPTURE] Calculated px: L={left_px}, T={top_px}, W={width_px}, H={height_px}")
            else: logging.debug(f"[CAPTURE] Using absolute pixel values."); left_px = area.get('left', 0); top_px = area.get('top', 0); width_px = area.get('width', 100); height_px = area.get('height', 100)
            bbox = {"left": mon_left + left_px, "top": mon_top + top_px, "width": max(1, width_px), "height": max(1, height_px), "mon": target_monitor_index}
            if bbox['width'] <= 0 or bbox['height'] <= 0: logging.error(f"[ERROR][CAPTURE] Invalid calculated capture dimensions: {bbox}"); return None
            logging.debug(f"[CAPTURE] Grabbing BBox: {bbox} on Monitor: {target_monitor_index}"); sct_img = sct.grab(bbox); img_np = np.array(sct_img)
            if img_np.size == 0: logging.error("[ERROR][CAPTURE] Grabbed empty image."); return None
            if img_np.shape[2] == 4: img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
            elif img_np.shape[2] == 3: img_bgr = img_np
            else: logging.error(f"[ERROR][CAPTURE] Unexpected image format (channels: {img_np.shape[2]})."); return None
            logging.info(f"[CAPTURE] Area captured successfully. Shape: {img_bgr.shape}"); return img_bgr
    except mss.ScreenShotError as e: logging.error(f"[ERROR][CAPTURE] mss error: {e}"); return None
    except Exception as e: logging.error(f"[ERROR][CAPTURE] Unexpected error during capture: {e}", exc_info=True); return None