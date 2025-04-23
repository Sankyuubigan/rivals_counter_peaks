# File: images_load.py
from PySide6.QtGui import QPixmap, Qt, QColor, QTransform
from PySide6.QtCore import QSize
import os
import sys
import cv2
import numpy as np
from collections import defaultdict
from heroes_bd import heroes as ALL_HERO_NAMES
import logging # <<< Добавлено логирование

def resource_path(relative_path):
    """Получаем абсолютный путь к ресурсу, работает для обычного запуска и PyInstaller"""
    try:
        # PyInstaller создает временную папку и сохраняет путь в sys._MEIPASS
        base_path = sys._MEIPASS
        # logging.debug(f"Running in PyInstaller mode. Base path: {base_path}")
    except AttributeError:
        # Обычный запуск из скрипта
        base_path = os.path.abspath(".")
        # logging.debug(f"Running in standard mode. Base path: {base_path}")
    return os.path.join(base_path, relative_path)

# Размеры для разных панелей в разных режимах
SIZES = {
    'max': {
        'right': (60, 60),
        'left': (50, 50),
        'small': (35, 35),
        'horizontal': (55, 55)
    },
    'middle': {
        'right': (40, 40),
        'left': (35, 35),
        'small': (25, 25),
        'horizontal': (45, 45)
    },
    'min': {
        'right': (0, 0),      # Правая панель скрыта
        'left': (40, 40),      # <<< ИЗМЕНЕНО: Увеличим left для min, т.к. horizontal их использует >>>
        'small': (0, 0),      # Маленькие иконки не нужны
        'horizontal': (40, 40) # <<< ИЗМЕНЕНО: Размер иконок в горизонтальном списке для min режима >>>
    }
}

# Глобальные кэши
loaded_images = {mode: {"right": {}, "left": {}, "small": {}, "horizontal": {}} for mode in SIZES}
original_images = {}  # {hero_name: QPixmap}
default_pixmap = None  # Базовая заглушка 1x1
loaded_hero_templates = None  # {hero_name: [template1_cv2, ...]}

def load_original_images():
    """Загружает оригинальные изображения героев из папки resources."""
    global original_images
    if original_images: logging.debug("Original images already loaded."); return
    logging.info("Loading original hero images...")
    loaded_count = 0
    missing_heroes = []
    temp_original_images = {}
    resources_folder = resource_path("resources")
    logging.info(f"Searching for images in: {resources_folder}")
    if not os.path.isdir(resources_folder):
        logging.error(f"Resources folder not found: {resources_folder}")
        return # Не можем загрузить, если папки нет

    for hero in ALL_HERO_NAMES:
        base_filename = hero.lower().replace(' ', '_').replace('&', 'and')
        img_path_png = os.path.join(resources_folder, f"{base_filename}.png")
        img_path_jpg = os.path.join(resources_folder, f"{base_filename}.jpg")
        img_path = None

        if os.path.exists(img_path_png): img_path = img_path_png
        elif os.path.exists(img_path_jpg): img_path = img_path_jpg

        if img_path:
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                temp_original_images[hero] = pixmap
                loaded_count += 1
            else:
                logging.warning(f"Image for {hero} at {img_path} is invalid (isNull).")
                temp_original_images[hero] = load_default_pixmap()
                missing_heroes.append(f"{hero} (invalid)")
        else:
            logging.warning(f"Image file not found for hero: {hero} (Searched for {base_filename}.png/.jpg)")
            temp_original_images[hero] = load_default_pixmap()
            missing_heroes.append(hero)

    original_images = temp_original_images
    logging.info(f"Original images loaded: {loaded_count} / {len(ALL_HERO_NAMES)}")
    if missing_heroes: logging.warning(f"Missing or invalid original images for: {', '.join(missing_heroes)}")

def get_images_for_mode(mode='middle'):
    """Возвращает словари с QPixmap нужных размеров для указанного режима. Использует кэш."""
    if not original_images: load_original_images()
    if mode not in SIZES: logging.warning(f"Unknown mode '{mode}'. Using 'middle'."); mode = 'middle'

    mode_sizes = SIZES[mode]
    right_size = mode_sizes.get('right', (0,0)); left_size = mode_sizes.get('left', (0,0))
    small_size = mode_sizes.get('small', (0,0)); horizontal_size = mode_sizes.get('horizontal', (30, 30))
    logging.debug(f"Getting images for mode '{mode}'. Sizes: R={right_size}, L={left_size}, S={small_size}, H={horizontal_size}")

    cached_data = loaded_images.get(mode)
    if cached_data:
        keys_needed = {'right': right_size, 'left': left_size, 'small': small_size, 'horizontal': horizontal_size}
        cache_complete = True
        for key, size in keys_needed.items():
            if (size[0] > 0 and size[1] > 0) and (key not in cached_data or not cached_data[key]):
                cache_complete = False; logging.debug(f"Cache incomplete for mode '{mode}', missing key '{key}' or empty."); break
        if cache_complete:
            logging.debug(f"Returning cached images for mode '{mode}'.")
            return cached_data['right'], cached_data['left'], cached_data['small'], cached_data['horizontal']

    logging.info(f"Generating images for mode: {mode}")
    right_images = {}; left_images = {}; small_images = {}; horizontal_images = {}
    transform_mode = Qt.TransformationMode.SmoothTransformation

    for hero, img in original_images.items():
        if img.isNull() or img.size() == QSize(1,1): # Проверяем заглушку
             if right_size[0] > 0: right_images[hero] = load_default_pixmap(right_size)
             if left_size[0] > 0: left_images[hero] = load_default_pixmap(left_size)
             if small_size[0] > 0: small_images[hero] = load_default_pixmap(small_size)
             if horizontal_size[0] > 0: horizontal_images[hero] = load_default_pixmap(horizontal_size)
             continue

        # <<< ИЗМЕНЕНИЕ: Добавлена проверка результата scaled() >>>
        def scale_image(target_size, panel_name):
            if target_size[0] > 0 and target_size[1] > 0:
                scaled_pixmap = img.scaled(QSize(*target_size), Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
                if scaled_pixmap.isNull():
                     logging.error(f"Failed to scale image for '{hero}' to {target_size} for panel '{panel_name}'. Original size: {img.size()}")
                     return load_default_pixmap(target_size)
                return scaled_pixmap
            return None # Возвращаем None если размер 0

        scaled_right = scale_image(right_size, 'right')
        scaled_left = scale_image(left_size, 'left')
        scaled_small = scale_image(small_size, 'small')
        scaled_horizontal = scale_image(horizontal_size, 'horizontal')

        if scaled_right: right_images[hero] = scaled_right
        if scaled_left: left_images[hero] = scaled_left
        if scaled_small: small_images[hero] = scaled_small
        if scaled_horizontal: horizontal_images[hero] = scaled_horizontal
        # <<< ------------------------------------------------ >>>

    loaded_images[mode]['right'] = right_images
    loaded_images[mode]['left'] = left_images
    loaded_images[mode]['small'] = small_images
    loaded_images[mode]['horizontal'] = horizontal_images
    logging.info(f"Images generated and cached for mode: {mode}")
    return right_images, left_images, small_images, horizontal_images

def load_right_panel_images():
    """Загружает изображения для правой панели (используется в RightPanel, но может быть устаревшим)."""
    # Эта функция может быть не нужна, если get_images_for_mode используется везде
    logging.warning("load_right_panel_images() called, potentially deprecated. Use get_images_for_mode().")
    if not original_images: load_original_images()
    # Используем размеры для 'middle' режима как пример, если эта функция все еще нужна
    right_size = SIZES['middle']['right']
    hero_images = {}
    for hero, img in original_images.items():
        if not img.isNull() and img.size() != QSize(1,1):
            scaled_img = img.scaled(QSize(*right_size), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if not scaled_img.isNull(): hero_images[hero] = scaled_img # Используем оригинальное имя героя
            else: hero_images[hero] = load_default_pixmap(right_size)
        else: hero_images[hero] = load_default_pixmap(right_size)
    return hero_images


def load_default_pixmap(size=(1, 1)):
    """Создает или возвращает масштабированную серую заглушку QPixmap."""
    global default_pixmap
    if default_pixmap is None or default_pixmap.isNull():
         dp = QPixmap(1,1); dp.fill(QColor(128, 128, 128)); default_pixmap = dp
         logging.debug("Created base default 1x1 pixmap.")
    if size != (1,1):
        scaled_dp = default_pixmap.scaled(QSize(*size), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        if scaled_dp.isNull(): logging.error(f"Failed to scale default pixmap to size {size}"); return default_pixmap # Return 1x1 if scale fails
        return scaled_dp
    else: return default_pixmap

def _get_image_path(base_filename):
    """Формирует путь к файлу изображения (устаревшая, лучше использовать resource_path напрямую)."""
    resources_folder = resource_path("resources")
    img_path_png = os.path.join(resources_folder, f"{base_filename}.png")
    img_path_jpg = os.path.join(resources_folder, f"{base_filename}.jpg")
    if os.path.exists(img_path_png): return img_path_png
    elif os.path.exists(img_path_jpg): return img_path_jpg
    return None

def load_hero_templates():
    """Загружает изображения шаблонов героев из папки resources/templates. Использует кэш."""
    global loaded_hero_templates
    if loaded_hero_templates is not None: logging.debug("Returning cached hero templates."); return loaded_hero_templates

    templates_dir = resource_path("resources/templates")
    hero_templates = defaultdict(list)
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
    logging.info(f"Loading hero templates from: {templates_dir}")

    if not os.path.isdir(templates_dir):
        logging.error(f"Templates directory not found: {templates_dir}. Recognition will not work."); return {}

    files_found = 0; templates_loaded = 0; skipped_unknown_hero = 0; skipped_bad_name = 0; skipped_load_error = 0
    all_hero_names_lower = {name.lower(): name for name in ALL_HERO_NAMES} # Для быстрого поиска

    for filename in os.listdir(templates_dir):
        if filename.lower().endswith(valid_extensions):
            files_found += 1
            base_name = os.path.splitext(filename)[0]
            parts = base_name.split('_')

            if len(parts) >= 2:
                hero_name_parsed_lower = " ".join(parts[:-1]).strip().lower()
                matched_hero_name = all_hero_names_lower.get(hero_name_parsed_lower) # Ищем по lowercase

                if matched_hero_name:
                    template_path = os.path.join(templates_dir, filename)
                    try:
                        # Загружаем с флагом IMREAD_UNCHANGED для поддержки альфа-канала, если он есть
                        template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
                        if template_img is not None:
                            # Если есть альфа-канал, можно его использовать для маски (но matchTemplate обычно работает с BGR/Gray)
                            # Если нужно BGR, конвертируем:
                            if template_img.shape[2] == 4:
                                template_img = cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR)

                            hero_templates[matched_hero_name].append(template_img)
                            templates_loaded += 1
                        else:
                            logging.warning(f"Failed to load template with OpenCV: {template_path}")
                            skipped_load_error += 1
                    except Exception as e_cv:
                        logging.error(f"Error processing template file {template_path}: {e_cv}")
                        skipped_load_error += 1
                else:
                    # logging.debug(f"Skipped file (hero name '{hero_name_parsed_lower}' not found in heroes list): {filename}")
                    skipped_unknown_hero +=1
            else:
                # logging.debug(f"Skipped file (invalid name format - expected 'Name_Number'): {filename}")
                skipped_bad_name += 1

    logging.info(f"Template files processed: {files_found}")
    logging.info(f"Templates loaded successfully: {templates_loaded} for {len(hero_templates)} heroes.")
    if skipped_unknown_hero > 0: logging.warning(f"Skipped templates due to unknown hero name: {skipped_unknown_hero}")
    if skipped_bad_name > 0: logging.warning(f"Skipped templates due to invalid name format: {skipped_bad_name}")
    if skipped_load_error > 0: logging.warning(f"Skipped templates due to loading/processing error: {skipped_load_error}")
    if not templates_loaded: logging.error("No hero templates were loaded successfully!")

    loaded_hero_templates = dict(hero_templates) # Преобразуем defaultdict в dict для кэша
    return loaded_hero_templates