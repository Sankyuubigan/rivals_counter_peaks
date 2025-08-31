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
    'monitor': 1, 'left_pct': 50, 'top_pct': 20, 'width_pct': 20, 'height_pct': 50
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

def get_settings_path() -> Path:
    app_data_dir_str = "" 
    if sys.platform == "win32":
        app_data_dir_str = os.getenv("APPDATA")
        if not app_data_dir_str:
            app_data_dir_str = str(Path.home() / "AppData" / "Roaming")
    else: 
        app_data_dir_str = str(Path.home() / ".config")
    
    app_data_dir = Path(app_data_dir_str)
    app_name_dir = app_data_dir / "RivalsCounterPeaks"
    
    # Используем if-else для создания директории, если это возможно без try-except
    # Однако, os.makedirs может вызывать ошибки по разным причинам (например, права доступа)
    # поэтому try-except здесь более надежен.
    if not app_name_dir.exists():
        try: 
            app_name_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e: # Оставляем try-except для критической операции I/O
            logging.error(f"Не удалось создать директорию настроек {app_name_dir}: {e}")
    
    return app_name_dir / "hotkeys.json" # Имя файла настроек теперь другое

def normalize_hero_name(name: str) -> str:
    """
    Нормализует имя героя, удаляя числовые и общие суффиксы.
    Приводит к нижнему регистру, заменяет разделители на пробелы,
    и пытается найти каноническое имя.
    """
    if not name:
        return ""
    
    normalized = name.lower()
    
    # 1. Удаляем числовые суффиксы типа _1, _2, _v2, _v3 и т.д.
    normalized = re.sub(r'[_ ]*v\d+$', '', normalized) # Удаляет '_v2', ' v2' и т.п. в конце
    normalized = re.sub(r'_\d+$', '', normalized)     # Удаляет '_2', '_3' и т.п. в конце

    # 2. Удаляем другие общие суффиксы
    other_suffixes_to_remove = ["_icon", "_template", "_small", "_left", "_right", "_horizontal", "_adv", "_padded"]
    for suffix in other_suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            
    # 3. Заменяем тире, подчеркивания на пробелы, убираем лишние пробелы
    normalized = re.sub(r'[-_]+', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # 4. Поиск канонического имени
    # Сначала ищем точное совпадение (без учета регистра)
    for hero_canonical_name in heroes: # heroes из heroes_bd
        if hero_canonical_name.lower() == normalized:
            return hero_canonical_name
            
    # Если не найдено, пробуем капитализировать слова в нормализованном имени
    parts = normalized.split(' ')
    capitalized_name_attempt = " ".join(p.capitalize() for p in parts if p) # if p - чтобы избежать ошибок с пустыми строками
    
    # Ищем совпадение с капитализированной версией
    for hero_canonical_name in heroes:
        if hero_canonical_name == capitalized_name_attempt:
            return hero_canonical_name
    
    # Если все попытки не увенчались успехом, логируем предупреждение и возвращаем капитализированную версию
    # Это поведение сохранено из логов, где для 'cloak and dagger 3' возвращалось 'Cloak And Dagger 3'
    # Однако, если `capitalized_name_attempt` пустое (например, исходное имя было `_1`),
    # то нужно вернуть что-то осмысленное или исходное имя.
    final_return_name = capitalized_name_attempt if capitalized_name_attempt else name 

    logging.warning(
        f"Не удалось точно сопоставить имя '{name}' (нормализовано до '{normalized}') "
        f"с каноническим. Возвращаем '{final_return_name}'."
    )
    return final_return_name


def validate_heroes():
    logging.info("[VALIDATION] Запуск проверки имен героев (новая структура)...")
    invalid_entries = []
    heroes_set = set(heroes) 

    for hero_being_countered, counters_data in heroes_counters.items():
        if hero_being_countered not in heroes_set:
            invalid_entries.append(f"Неизвестный герой '{hero_being_countered}' как ключ в heroes_counters.")
            # Нет смысла продолжать проверку для этого ключа, если он сам невалиден
            continue 

        # Проверяем, что counters_data это словарь
        if not isinstance(counters_data, dict):
            invalid_entries.append(f"Неверный формат данных для '{hero_being_countered}': ожидался словарь, получен {type(counters_data)}.")
            continue # Если формат неверный, дальнейшие проверки .get() могут вызвать ошибку

        for counter_type in ["hard", "soft"]:
            # Проверяем, существует ли ключ counter_type в словаре
            if counter_type not in counters_data:
                # Это не обязательно ошибка, может быть, у героя нет hard или soft контрпиков
                # logging.debug(f"Для '{hero_being_countered}' отсутствует ключ '{counter_type}'.")
                continue 
            
            counter_list = counters_data[counter_type] # Получаем значение по ключу
            # Проверяем, что значение является списком
            if not isinstance(counter_list, list):
                invalid_entries.append(f"Для '{hero_being_countered}' -> '{counter_type}' ожидался список, получен {type(counter_list)}.")
                continue # Если не список, итерация по нему вызовет ошибку

            for counter_hero_name in counter_list:
                if not isinstance(counter_hero_name, str):
                    invalid_entries.append(f"В списке '{counter_type}' для '{hero_being_countered}' найден нестроковый элемент: '{counter_hero_name}' ({type(counter_hero_name)}).")
                elif counter_hero_name not in heroes_set:
                    invalid_entries.append(f"Неизвестный герой '{counter_hero_name}' в списке '{counter_type}' для '{hero_being_countered}'.")
    
    # Убираем дубликаты ошибок и сортируем для консистентного вывода
    unique_invalid = sorted(list(set(invalid_entries)))
    if unique_invalid:
        logging.error(f"[VALIDATION ERROR] Найдены ошибки в структуре или именах героев в heroes_counters:\n" + "\n".join(unique_invalid))
        return unique_invalid
    else:
        logging.info("[VALIDATION] Проверка heroes_counters (новая структура) пройдена успешно.")
        return []


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