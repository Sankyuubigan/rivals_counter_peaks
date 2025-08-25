# File: core/utils.py
import mss
import numpy as np
import cv2
import os
import sys
from database.heroes_bd import heroes_counters, heroes 
import logging
from pathlib import Path
import re # Добавлен re для нормализации имен

# RECOGNITION_AREA теперь не используется RecognitionManager напрямую для захвата,
# но может использоваться другими частями или для справки.
# Если он больше нигде не нужен, его можно удалить.
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



def check_if_all_elements_in_list(target_list, check_list):
    return set(check_list).issubset(set(target_list))

def capture_screen_area(area: dict):
    logging.debug(f"[CAPTURE] Attempting capture for area definition: {area}")
    img_bgr = None 
    # Оставляем try-except для mss, так как это внешняя библиотека
    # и ошибки могут быть разнообразными (например, проблемы с драйверами дисплея).
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if not monitors: 
                logging.error("[ERROR][CAPTURE] No monitors found.")
                return None
            
            target_monitor_index = area.get('monitor', 1)
            # Проверка индекса монитора
            if not (0 <= target_monitor_index < len(monitors)):
                corrected_index = 1 if len(monitors) > 1 else 0 
                if not (0 <= corrected_index < len(monitors)):
                     logging.error(f"[ERROR][CAPTURE] Corrected monitor index {corrected_index} is still invalid for {len(monitors)} monitors.")
                     return None
                logging.warning(f"[WARN][CAPTURE] Invalid monitor index {target_monitor_index}. Available: {len(monitors)}. Using monitor {corrected_index} instead.")
                target_monitor_index = corrected_index
            
            monitor_geometry = monitors[target_monitor_index] 
            
            mon_width = monitor_geometry["width"]; mon_height = monitor_geometry["height"]
            mon_left = monitor_geometry["left"]; mon_top = monitor_geometry["top"]
            
            # Определяем, используются ли процентные или абсолютные значения
            use_pct = False
            if all(k in area for k in ['left_pct', 'top_pct', 'width_pct', 'height_pct']):
                use_pct = True
                logging.debug(f"[CAPTURE] Using percentage values.")
                left_px = int(mon_width * area['left_pct'] / 100)
                top_px = int(mon_height * area['top_pct'] / 100)
                width_px = int(mon_width * area['width_pct'] / 100)
                height_px = int(mon_height * area['height_pct'] / 100)
                logging.debug(f"[CAPTURE] Calculated px: L={left_px}, T={top_px}, W={width_px}, H={height_px}")
            else: 
                logging.debug(f"[CAPTURE] Using absolute pixel values.")
                left_px = area.get('left', 0); top_px = area.get('top', 0)
                width_px = area.get('width', 100); height_px = area.get('height', 100)
            
            # Формируем bounding box для захвата
            bbox = {
                "left": mon_left + left_px, "top": mon_top + top_px,
                "width": max(1, width_px), "height": max(1, height_px), # Ширина и высота не могут быть 0 или меньше
                "mon": target_monitor_index # mss использует 0-based индекс для grab, но sct.monitors уже 0-based.
                                           # Если 'monitor' в area был 1-based, то target_monitor_index уже исправлен.
            }

            if bbox['width'] <= 0 or bbox['height'] <= 0:
                logging.error(f"[ERROR][CAPTURE] Invalid calculated capture dimensions: {bbox}")
                return None
            
            logging.debug(f"[CAPTURE] Grabbing BBox: {bbox} on Monitor: {target_monitor_index}")
            
            sct_img = sct.grab(bbox) # Захват области

            if sct_img:
                img_np = np.array(sct_img)
                if img_np.size == 0: 
                    logging.error("[ERROR][CAPTURE] Grabbed empty image.")
                    return None
                
                # Проверка формы изображения
                if len(img_np.shape) < 3: 
                    logging.error(f"[ERROR][CAPTURE] Unexpected image format (shape: {img_np.shape}). Expected 3 or 4 channels.")
                    return None

                # Конвертация в BGR формат, если необходимо
                if img_np.shape[2] == 4: # BGRA
                    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                elif img_np.shape[2] == 3: # BGR (или RGB, mss обычно BGRA или BGR)
                    img_bgr = img_np 
                else: 
                    logging.error(f"[ERROR][CAPTURE] Unexpected image format (channels: {img_np.shape[2]}).")
                    return None
                
                logging.info(f"[CAPTURE] Area captured successfully. Shape: {img_bgr.shape if img_bgr is not None else 'None'}")
                return img_bgr
            else: 
                logging.error("[ERROR][CAPTURE] sct.grab() did not return a valid image.")
                return None
    except mss.exception.ScreenShotError as e_mss: # Явное исключение mss
         logging.error(f"[ERROR][CAPTURE] mss.ScreenShotError: {e_mss}")
         return None
    except Exception as e_grab: # Другие возможные исключения
         logging.error(f"[ERROR][CAPTURE] Unexpected error during screen capture: {e_grab}", exc_info=True)
         return None