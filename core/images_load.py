# File: images_load.py
from PySide6.QtGui import QPixmap, Qt, QColor
from PySide6.QtCore import QSize
import os
import sys
import cv2
from collections import defaultdict
# --- ИЗМЕНЕНИЕ ---
# Убираем импорт старой БД, будем загружать список героев из нового источника
# from database.heroes_bd import heroes as ALL_HERO_NAMES
from database.stats_loader import load_matchups_data, get_all_heroes
# --- КОНЕЦ ИЗМЕНЕНИЯ ---
import logging

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
    return os.path.join(base_path, relative_path)

SIZES = {
    'max': {'right': (60, 60), 'left': (50, 50), 'small': (35, 35), 'horizontal': (55, 55)},
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)}
}

# --- ИЗМЕНЕНИЕ ---
# Загружаем список героев при инициализации модуля
_matchups = load_matchups_data()
ALL_HERO_NAMES = get_all_heroes(_matchups)
if not ALL_HERO_NAMES:
    logging.critical("[images_load] Не удалось загрузить список героев из новой базы данных. Изображения не будут загружены.")
# --- КОНЕЦ ИЗМЕНЕНИЯ ---

loaded_images = {mode: {"right": {}, "left": {}, "small": {}, "horizontal": {}} for mode in SIZES}
original_images = {}
default_pixmap = None
CV2_HERO_TEMPLATES: dict[str, list] = {}


def is_invalid_pixmap(pixmap: QPixmap | None) -> bool:
    return pixmap is None or pixmap.isNull() or pixmap.size() == QSize(1, 1)

def load_original_images():
    global original_images
    if original_images: logging.debug("Original images already loaded."); return
    logging.info("Loading original hero images...")
    loaded_count = 0; missing_heroes = []; invalid_load_heroes = []
    temp_original_images = {}
    
    # --- ИЗМЕНЕНИЕ: Путь к иконкам ---
    # Старый путь был 'resources', теперь 'resources/heroes_icons'
    icons_folder = resource_path("resources/heroes_icons") 
    logging.debug(f"Searching for images in: {icons_folder}")
    if not os.path.isdir(icons_folder): 
        logging.error(f"Icons folder not found: {icons_folder}")
        return
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    for hero in ALL_HERO_NAMES:
        # Имена файлов теперь hero_name_1.png, hero_name_2.png и т.д.
        # Будем искать все совпадения и брать первое.
        base_filename_prefix = hero.lower().replace(' ', '_').replace('&', 'and')
        found_path = None
        # Ищем файлы, которые начинаются с имени героя, чтобы найти, например, "hulk_1.png", "hulk_2.png"
        try:
            for f in os.listdir(icons_folder):
                if f.lower().startswith(base_filename_prefix) and f.lower().endswith(('.png', '.jpg')):
                    found_path = os.path.join(icons_folder, f)
                    break # Берем первый найденный файл
        except FileNotFoundError:
            pass # os.listdir может выдать ошибку, если папки нет

        if found_path:
            pixmap = QPixmap(found_path)
            if is_invalid_pixmap(pixmap):
                logging.warning(f"Image for hero '{hero}' at '{found_path}' failed to load or is invalid. Using placeholder.")
                temp_original_images[hero] = load_default_pixmap()
                invalid_load_heroes.append(hero)
            else:
                temp_original_images[hero] = pixmap
                loaded_count += 1
        else:
            logging.warning(f"Image file not found for hero: '{hero}' (Searched for prefix '{base_filename_prefix}' in {icons_folder})")
            temp_original_images[hero] = load_default_pixmap()
            missing_heroes.append(hero)

    original_images = temp_original_images
    logging.info(f"Original images loaded: {loaded_count} / {len(ALL_HERO_NAMES)}")
    if missing_heroes: logging.warning(f"Missing image files for: {', '.join(missing_heroes)}")
    if invalid_load_heroes: logging.warning(f"Failed to load valid QPixmap for: {', '.join(invalid_load_heroes)}")


def get_images_for_mode(mode='middle'):
    if not original_images: load_original_images()
    if mode not in SIZES: 
        logging.warning(f"Unknown mode '{mode}'. Using 'middle'.")
        mode = 'middle'

    mode_sizes = SIZES[mode]
    right_size = mode_sizes.get('right', (0,0)); left_size = mode_sizes.get('left', (0,0))
    small_size = mode_sizes.get('small', (0,0)); horizontal_size = mode_sizes.get('horizontal', (30, 30))
    logging.debug(f"Getting images for mode '{mode}'. Sizes: R={right_size}, L={left_size}, S={small_size}, H={horizontal_size}")

    cached_data = loaded_images.get(mode)
    if cached_data:
        keys_needed = {'right': right_size, 'left': left_size, 'small': small_size, 'horizontal': horizontal_size}
        cache_complete = True
        for key, size_tuple in keys_needed.items(): 
            if (size_tuple > 0 and size_tuple > 0) and (key not in cached_data or not cached_data[key]):
                cache_complete = False
                logging.debug(f"Cache incomplete for mode '{mode}', missing key '{key}' or empty.")
                break
        if cache_complete:
            logging.debug(f"Returning cached images for mode '{mode}'.")
            return cached_data['right'], cached_data['left'], cached_data['small'], cached_data['horizontal']

    logging.debug(f"Generating images for mode: {mode}")
    right_images = {}; left_images = {}; small_images = {}; horizontal_images = {}
    transform_mode = Qt.TransformationMode.SmoothTransformation

    for hero, img in original_images.items():
        if is_invalid_pixmap(img):
             logging.debug(f"Original image for '{hero}' is invalid/placeholder. Scaling placeholder.")
             if right_size > 0: right_images[hero] = load_default_pixmap(right_size)
             if left_size > 0: left_images[hero] = load_default_pixmap(left_size)
             if small_size > 0: small_images[hero] = load_default_pixmap(small_size)
             if horizontal_size > 0: horizontal_images[hero] = load_default_pixmap(horizontal_size)
             continue

        def scale_image(target_size, panel_name):
            if target_size > 0 and target_size > 0:
                scaled_pixmap = img.scaled(QSize(*target_size), Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
                if is_invalid_pixmap(scaled_pixmap):
                     logging.error(f"Failed to scale image for '{hero}' to {target_size} for panel '{panel_name}'. Original size: {img.size()}")
                     return load_default_pixmap(target_size)
                return scaled_pixmap
            return None 

        scaled_right = scale_image(right_size, 'right'); 
        if scaled_right is not None: right_images[hero] = scaled_right
        
        scaled_left = scale_image(left_size, 'left')
        if scaled_left is not None: left_images[hero] = scaled_left
        
        scaled_small = scale_image(small_size, 'small')
        if scaled_small is not None: small_images[hero] = scaled_small
        
        scaled_horizontal = scale_image(horizontal_size, 'horizontal')
        if scaled_horizontal is not None: horizontal_images[hero] = scaled_horizontal


    loaded_images[mode]['right'] = right_images; loaded_images[mode]['left'] = left_images
    loaded_images[mode]['small'] = small_images; loaded_images[mode]['horizontal'] = horizontal_images
    logging.info(f"Images generated and cached for mode: {mode}")
    return right_images, left_images, small_images, horizontal_images

def load_default_pixmap(size=(1, 1)):
    global default_pixmap
    if default_pixmap is None or default_pixmap.isNull():
         dp = QPixmap(1,1); dp.fill(QColor(128, 128, 128)); default_pixmap = dp
         logging.debug("Created base default 1x1 pixmap.")
    
    if size == (1,1): 
        return default_pixmap

    scaled_dp = default_pixmap.scaled(QSize(*size), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
    if scaled_dp.isNull(): 
        logging.error(f"Failed to scale default pixmap to size {size}")
        return default_pixmap 
    return scaled_dp


def load_hero_templates_cv2() -> dict[str, list]:
    global CV2_HERO_TEMPLATES
    if CV2_HERO_TEMPLATES: 
        logging.debug("Returning cached CV2 hero templates.")
        return CV2_HERO_TEMPLATES
        
    templates_dir = resource_path("resources/embeddings_padded") # Используем ту же папку, что и для эмбеддингов
    hero_templates_cv2_local = defaultdict(list)
    valid_extensions = ('.png', '.jpg', '.jpeg')
    logging.info(f"Loading CV2 hero templates from icon folder: {templates_dir}")
    
    icons_dir = resource_path("resources/heroes_icons")
    if not os.path.isdir(icons_dir): 
        logging.error(f"CV2 Templates (icons) directory not found: {icons_dir}.")
        CV2_HERO_TEMPLATES = {} 
        return {} 
        
    loaded_count = 0
    for hero_canonical_name in ALL_HERO_NAMES:
        base_filename_prefix = hero_canonical_name.lower().replace(' ', '_').replace('&', 'and')
        try:
            for f in os.listdir(icons_dir):
                if f.lower().startswith(base_filename_prefix) and f.lower().endswith(valid_extensions):
                    template_path = os.path.join(icons_dir, f)
                    template_img = cv2.imread(template_path, cv2.IMREAD_COLOR) # Загружаем как BGR
                    if template_img is not None:
                        hero_templates_cv2_local[hero_canonical_name].append(template_img)
                        loaded_count += 1
                    else:
                        logging.warning(f"Failed to load template icon with OpenCV: {template_path}")
        except FileNotFoundError:
            continue

    logging.info(f"CV2 Templates (from icons) loaded successfully: {loaded_count} for {len(hero_templates_cv2_local)} heroes.")
    CV2_HERO_TEMPLATES = dict(hero_templates_cv2_local)
    return CV2_HERO_TEMPLATES