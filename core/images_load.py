# File: images_load.py
from PySide6.QtGui import QPixmap, Qt, QColor
from PySide6.QtCore import QSize
import os
import sys
import cv2
from collections import defaultdict
from database.heroes_bd import heroes as ALL_HERO_NAMES
import logging

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Поднимаемся на уровень выше из core
    return os.path.join(base_path, relative_path)

SIZES = {
    'max': {'right': (60, 60), 'left': (50, 50), 'small': (35, 35), 'horizontal': (55, 55)},
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)}
}

loaded_images = {mode: {"right": {}, "left": {}, "small": {}, "horizontal": {}} for mode in SIZES}
original_images = {}
default_pixmap = None
loaded_hero_templates = None

def is_invalid_pixmap(pixmap: QPixmap | None) -> bool:
    return pixmap is None or pixmap.isNull() or pixmap.size() == QSize(1, 1)

def load_original_images():
    global original_images
    if original_images: logging.debug("Original images already loaded."); return
    logging.info("Loading original hero images...")
    loaded_count = 0; missing_heroes = []; invalid_load_heroes = []
    temp_original_images = {}
    resources_folder = resource_path("resources") # resource_path теперь корректно указывает на папку resources в корне
    logging.info(f"Searching for images in: {resources_folder}")
    if not os.path.isdir(resources_folder): 
        logging.error(f"Resources folder not found: {resources_folder}")
        return

    for hero in ALL_HERO_NAMES:
        base_filename = hero.lower().replace(' ', '_').replace('&', 'and')
        img_path_png = os.path.join(resources_folder, f"{base_filename}.png")
        img_path_jpg = os.path.join(resources_folder, f"{base_filename}.jpg")
        img_path = None
        if os.path.exists(img_path_png): img_path = img_path_png
        elif os.path.exists(img_path_jpg): img_path = img_path_jpg

        if img_path:
            pixmap = QPixmap(img_path)
            if is_invalid_pixmap(pixmap):
                logging.warning(f"Image for hero '{hero}' at '{img_path}' failed to load or is invalid (isNull/1x1). Using placeholder.")
                temp_original_images[hero] = load_default_pixmap()
                invalid_load_heroes.append(hero)
            else:
                temp_original_images[hero] = pixmap
                loaded_count += 1
        else:
            logging.warning(f"Image file not found for hero: '{hero}' (Searched for '{base_filename}.png' / '{base_filename}.jpg' in {resources_folder})")
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
        for key, size_tuple in keys_needed.items(): # Изменено имя переменной
            if (size_tuple[0] > 0 and size_tuple[1] > 0) and (key not in cached_data or not cached_data[key]):
                cache_complete = False
                logging.debug(f"Cache incomplete for mode '{mode}', missing key '{key}' or empty.")
                break
        if cache_complete:
            logging.debug(f"Returning cached images for mode '{mode}'.")
            return cached_data['right'], cached_data['left'], cached_data['small'], cached_data['horizontal']

    logging.info(f"Generating images for mode: {mode}")
    right_images = {}; left_images = {}; small_images = {}; horizontal_images = {}
    transform_mode = Qt.TransformationMode.SmoothTransformation

    for hero, img in original_images.items():
        if is_invalid_pixmap(img):
             logging.debug(f"Original image for '{hero}' is invalid/placeholder. Scaling placeholder.")
             if right_size[0] > 0: right_images[hero] = load_default_pixmap(right_size)
             if left_size[0] > 0: left_images[hero] = load_default_pixmap(left_size)
             if small_size[0] > 0: small_images[hero] = load_default_pixmap(small_size)
             if horizontal_size[0] > 0: horizontal_images[hero] = load_default_pixmap(horizontal_size)
             continue

        def scale_image(target_size, panel_name):
            if target_size[0] > 0 and target_size[1] > 0:
                scaled_pixmap = img.scaled(QSize(*target_size), Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
                if is_invalid_pixmap(scaled_pixmap):
                     logging.error(f"Failed to scale image for '{hero}' to {target_size} for panel '{panel_name}'. Original size: {img.size()}")
                     return load_default_pixmap(target_size)
                return scaled_pixmap
            return None # Возвращаем None, если размер 0

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

def load_right_panel_images():
    logging.warning("load_right_panel_images() called, potentially deprecated. Use get_images_for_mode().")
    if not original_images: load_original_images()
    right_size = SIZES['middle']['right']; hero_images = {}
    for hero, img in original_images.items():
        if is_invalid_pixmap(img): hero_images[hero] = load_default_pixmap(right_size)
        else:
            scaled_img = img.scaled(QSize(*right_size), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if is_invalid_pixmap(scaled_img): hero_images[hero] = load_default_pixmap(right_size)
            else: hero_images[hero] = scaled_img
    return hero_images

def load_default_pixmap(size=(1, 1)):
    global default_pixmap
    if default_pixmap is None or default_pixmap.isNull():
         dp = QPixmap(1,1); dp.fill(QColor(128, 128, 128)); default_pixmap = dp
         logging.debug("Created base default 1x1 pixmap.")
    
    if size == (1,1): # Если запрашивается базовый 1x1, возвращаем его
        return default_pixmap

    # Масштабируем базовый, если нужен другой размер
    scaled_dp = default_pixmap.scaled(QSize(*size), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
    if scaled_dp.isNull(): 
        logging.error(f"Failed to scale default pixmap to size {size}")
        # В случае ошибки масштабирования, возвращаем базовый 1x1, а не None
        return default_pixmap 
    return scaled_dp


def load_hero_templates():
    global loaded_hero_templates
    if loaded_hero_templates is not None: 
        logging.debug("Returning cached hero templates.")
        return loaded_hero_templates
        
    templates_dir = resource_path("resources/templates")
    hero_templates = defaultdict(list)
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
    logging.info(f"Loading hero templates from: {templates_dir}")
    
    if not os.path.isdir(templates_dir): 
        logging.error(f"Templates directory not found: {templates_dir}.")
        loaded_hero_templates = {} # Устанавливаем пустой словарь, чтобы не пытаться загрузить снова
        return {} # Возвращаем пустой словарь
        
    files_found, templates_loaded, skipped_unknown_hero, skipped_bad_name, skipped_load_error = 0, 0, 0, 0, 0
    all_hero_names_lower = {name.lower(): name for name in ALL_HERO_NAMES}
    
    for filename in os.listdir(templates_dir):
        if filename.lower().endswith(valid_extensions):
            files_found += 1
            base_name = os.path.splitext(filename)[0]
            parts = base_name.split('_')
            if len(parts) >= 2:
                hero_name_parsed_lower = " ".join(parts[:-1]).strip().lower()
                matched_hero_name = all_hero_names_lower.get(hero_name_parsed_lower)
                if matched_hero_name:
                    template_path = os.path.join(templates_dir, filename)
                    template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED) # Замена try-except
                    if template_img is not None:
                        # Проверка и конвертация формата
                        if len(template_img.shape) == 3 and template_img.shape[2] == 4: 
                            template_img_converted = cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR)
                            if template_img_converted is None:
                                logging.warning(f"Failed to convert BGRA template {filename} to BGR.")
                                skipped_load_error += 1
                                continue
                            template_img = template_img_converted
                        elif len(template_img.shape) == 2: 
                            pass # Already grayscale
                        elif len(template_img.shape) != 3 or template_img.shape[2] != 3: 
                            logging.warning(f"Template {filename} has unexpected shape {template_img.shape}. Skipping conversion.")
                            skipped_load_error += 1
                            continue # Пропускаем этот шаблон
                        
                        hero_templates[matched_hero_name].append(template_img)
                        templates_loaded += 1
                    else: 
                        logging.warning(f"Failed to load template with OpenCV: {template_path}")
                        skipped_load_error += 1
                else: 
                    skipped_unknown_hero +=1
            else: 
                skipped_bad_name += 1
                
    logging.info(f"Template files processed: {files_found}")
    logging.info(f"Templates loaded successfully: {templates_loaded} for {len(hero_templates)} heroes.")
    if skipped_unknown_hero > 0: logging.warning(f"Skipped templates due to unknown hero name: {skipped_unknown_hero}")
    if skipped_bad_name > 0: logging.warning(f"Skipped templates due to invalid name format: {skipped_bad_name}")
    if skipped_load_error > 0: logging.warning(f"Skipped templates due to loading/processing error: {skipped_load_error}")
    
    if not templates_loaded and files_found > 0 : # Если были файлы, но ничего не загружено
        logging.error("No hero templates were loaded successfully, although files were found!")
    elif not files_found: # Если вообще не было файлов
         logging.warning("No template files found in the templates directory.")

    loaded_hero_templates = dict(hero_templates)
    return loaded_hero_templates