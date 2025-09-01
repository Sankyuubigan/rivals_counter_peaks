# File: images_load.py
from PySide6.QtGui import QPixmap, Qt, QColor
from PySide6.QtCore import QSize
import os
import sys
import cv2 # Оставляем cv2 для load_hero_templates (AKAZE шаблоны)
from collections import defaultdict
from database.heroes_bd import heroes as ALL_HERO_NAMES
import logging

def resource_path(relative_path):
    """Определяет путь к ресурсам в упакованном exe или development режиме."""
    try:
        # PyInstaller устанавливает sys._MEIPASS в путь к временной папке с распакованными ресурсами
        base_path = sys._MEIPASS
        logging.debug(f"resource_path: Используется sys._MEIPASS: {base_path}")
    except AttributeError:
        # В режиме разработки - путь к корню проекта (родительская дир от core/)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        logging.debug(f"resource_path: Режим разработки, используем путь: {base_path}")

    # Убеждаемся, что путь к resources правильный
    resources_path = os.path.join(base_path, 'resources')
    if not os.path.exists(resources_path):
        logging.error(f"resource_path: Путь к resources не найден: {resources_path}")
        # Попытка найти resources по другим путям
        alt_base = os.path.dirname(sys.executable) if hasattr(sys, 'executable') else base_path
        alt_resources = os.path.join(alt_base, 'resources')
        if os.path.exists(alt_resources):
            logging.info(f"resource_path: Найдена папка resources по альтернативному пути: {alt_resources}")
            base_path = alt_base
        else:
            logging.error(f"resource_path: Папка resources не найдена даже по альтернативному пути: {alt_resources}")

    logging.debug(f"resource_path: Финальный базовый путь: {base_path}")
    final_path = os.path.join(base_path, relative_path)
    logging.debug(f"resource_path: Финальный путь к {relative_path}: {final_path}")

    return final_path

SIZES = {
    'max': {'right': (60, 60), 'left': (50, 50), 'small': (35, 35), 'horizontal': (55, 55)},
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)}
}

loaded_images = {mode: {"right": {}, "left": {}, "small": {}, "horizontal": {}} for mode in SIZES}
original_images = {}
default_pixmap = None
# Глобальная переменная для CV2 шаблонов (используется AdvancedRecognition)
CV2_HERO_TEMPLATES: dict[str, list] = {}


def is_invalid_pixmap(pixmap: QPixmap | None) -> bool:
    return pixmap is None or pixmap.isNull() or pixmap.size() == QSize(1, 1)

def load_original_images():
    global original_images
    if original_images: logging.debug("Original images already loaded."); return
    logging.info("Loading original hero images...")
    loaded_count = 0; missing_heroes = []; invalid_load_heroes = []
    temp_original_images = {}

    # ИСПОЛЬЗУЕМ heroes_icons ПАΠОКУ ВМЕСТО resources
    heroes_icons_folder = resource_path("resources/heroes_icons")
    logging.debug(f"Searching for images in: {heroes_icons_folder}")
    if not os.path.isdir(heroes_icons_folder):
        logging.error(f"Heroes icons folder not found: {heroes_icons_folder}")
        return

    # Add debug logs
    logging.info(f"ALL_HERO_NAMES count: {len(ALL_HERO_NAMES)}")
    if ALL_HERO_NAMES:
        logging.info(f"Sample ALL_HERO_NAMES: {list(ALL_HERO_NAMES)[:5]}")
    else:
        logging.error("ALL_HERO_NAMES is empty!")
        return

    try:
        files_in_dir = os.listdir(heroes_icons_folder)
        logging.info(f"Files in heroes_icons folder: {len(files_in_dir)} total - Sample: {files_in_dir[:10]}")
    except Exception as e:
        logging.error(f"Cannot list directory {heroes_icons_folder}: {e}")

    for hero in ALL_HERO_NAMES:
        # Конвертируем название героя в filename для иконок
        # Сначала конвертируем специальные случаи
        if hero == "Jeff":
            icon_filename = "jeff_the_land_shark_1"
        elif hero == "Widow":
            icon_filename = "black_widow_1"
        elif hero == "Fister":
            icon_filename = "iron_fist_1"
        elif hero == "SpiderMan":
            icon_filename = "spider_man_1"
        elif hero == "StarLord":
            icon_filename = "star_lord_1"
        elif hero == "Rocket Racoon":
            icon_filename = "rocket_raccoon_1"
        elif hero == "Witch":
            icon_filename = "scarlet_witch_1"
        elif hero == "Cloak and Dagger":
            icon_filename = "cloak_and_dagger_1"
        elif hero == "Punisher":
            icon_filename = "the_punisher_1"
        elif hero == "The Thing":
            icon_filename = "the_thing_1"
        elif hero == "Mister Fantastic":
            icon_filename = "mister_fantastic_1"
        elif hero == "Doctor Strange":
            icon_filename = "doctor_strange_1"
        elif hero == "Human Torch":
            icon_filename = "human_torch_1"
        elif hero == "Moon Knight":
            icon_filename = "moon_knight_1"
        elif hero == "Winter Soldier":
            icon_filename = "winter_soldier_1"
        elif hero == "Squirrel Girl":
            icon_filename = "squirrel_girl_1"
        else:
            # Стандартная конвертация для остальных героев
            icon_filename = hero.lower().replace(' ', '_').replace('&', 'and') + '_1'

        img_path = os.path.join(heroes_icons_folder, f"{icon_filename}.png")

        logging.debug(f"Processing hero: {hero}, icon_filename: {icon_filename}, img_path: {img_path}")
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if is_invalid_pixmap(pixmap):
                logging.warning(f"Image for hero '{hero}' at '{img_path}' failed to load or is invalid (isNull/1x1). Using placeholder.")
                temp_original_images[hero] = load_default_pixmap()
                invalid_load_heroes.append(hero)
            else:
                temp_original_images[hero] = pixmap
                loaded_count += 1
        else:
            logging.warning(f"Image file not found for hero: '{hero}' (Searched for '{icon_filename}.png' in {heroes_icons_folder})")
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
            if (size_tuple[0] > 0 and size_tuple[1] > 0) and (key not in cached_data or not cached_data[key]):
                cache_complete = False
                logging.debug(f"Cache incomplete for mode '{mode}', missing key '{key}' or empty.")
                break
        if cache_complete:
            logging.debug(f"Returning cached images for mode '{mode}'.")
            return cached_data['right'], cached_data['left'], cached_data['small'], cached_data['horizontal']

    logging.debug(f"Generating images for mode: {mode}") # ИЗМЕНЕНО: DEBUG
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
    logging.info(f"Images generated and cached for mode: {mode}") # Оставляем INFO
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
    
    if size == (1,1): 
        return default_pixmap

    scaled_dp = default_pixmap.scaled(QSize(*size), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
    if scaled_dp.isNull(): 
        logging.error(f"Failed to scale default pixmap to size {size}")
        return default_pixmap 
    return scaled_dp


def load_hero_templates_cv2() -> dict[str, list]:
    """
    Загружает шаблоны героев в формате CV2. Используется для AKAZE в AdvancedRecognition.
    """
    global CV2_HERO_TEMPLATES
    if CV2_HERO_TEMPLATES: 
        logging.debug("Returning cached CV2 hero templates.")
        return CV2_HERO_TEMPLATES
        
    templates_dir = resource_path("resources/templates")
    hero_templates_cv2_local = defaultdict(list)
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
    logging.info(f"Loading CV2 hero templates from: {templates_dir}")
    
    if not os.path.isdir(templates_dir): 
        logging.error(f"CV2 Templates directory not found: {templates_dir}.")
        CV2_HERO_TEMPLATES = {} 
        return {} 
        
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
                    template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED) 
                    if template_img is not None:
                        if len(template_img.shape) == 3 and template_img.shape[2] == 4: 
                            template_img_converted = cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR)
                            if template_img_converted is None:
                                logging.warning(f"Failed to convert BGRA template {filename} to BGR.")
                                skipped_load_error += 1
                                continue
                            template_img = template_img_converted
                        elif len(template_img.shape) == 2: 
                            pass 
                        elif len(template_img.shape) != 3 or template_img.shape[2] != 3: 
                            logging.warning(f"Template {filename} has unexpected shape {template_img.shape}. Skipping conversion.")
                            skipped_load_error += 1
                            continue 
                        
                        hero_templates_cv2_local[matched_hero_name].append(template_img)
                        templates_loaded += 1
                    else: 
                        logging.warning(f"Failed to load template with OpenCV: {template_path}")
                        skipped_load_error += 1
                else: 
                    skipped_unknown_hero +=1
            else: 
                skipped_bad_name += 1
                
    logging.info(f"CV2 Template files processed: {files_found}")
    logging.info(f"CV2 Templates loaded successfully: {templates_loaded} for {len(hero_templates_cv2_local)} heroes.")
    if skipped_unknown_hero > 0: logging.warning(f"Skipped CV2 templates due to unknown hero name: {skipped_unknown_hero}")
    if skipped_bad_name > 0: logging.warning(f"Skipped CV2 templates due to invalid name format: {skipped_bad_name}")
    if skipped_load_error > 0: logging.warning(f"Skipped CV2 templates due to loading/processing error: {skipped_load_error}")
    
    if not templates_loaded and files_found > 0 : 
        logging.error("No CV2 hero templates were loaded successfully, although files were found!")
    elif not files_found: 
         logging.warning("No CV2 template files found in the templates directory.")

    CV2_HERO_TEMPLATES = dict(hero_templates_cv2_local)
    return CV2_HERO_TEMPLATES

# Заменяем старый вызов load_hero_templates на новый для CV2
# Старый load_hero_templates удален, т.к. он был идентичен новому _cv2.
# Убедимся, что при старте приложения вызывается load_hero_templates_cv2()
# для заполнения CV2_HERO_TEMPLATES, если это требуется где-то еще кроме AdvancedRecognition.
# Если AdvancedRecognition - единственное место, где нужны CV2 шаблоны,
# то этот глобальный CV2_HERO_TEMPLATES и функция его загрузки могут быть инкапсулированы
# внутри AdvancedRecognition или передаваться ему при инициализации.
# Для текущего запроса я оставлю load_hero_templates_cv2 как глобальную функцию загрузки,
# а RecognitionManager будет ее использовать для передачи шаблонов в AdvancedRecognition.

# Вызов для предварительной загрузки при импорте модуля (если это нужно)
# load_hero_templates_cv2()