import os
import sys
import logging
import cv2
import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
# ИМПОРТ: Получаем список героев из единого источника
from database.heroes_bd import heroes as ALL_HEROES

# Размеры для единственного режима "middle"
SIZES = {
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)} # Оставим для трея
}

class ImageManager:
    """Унифицированный менеджер для работы с изображениями и иконками"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.original_images: Dict[str, QPixmap] = {}
        self.cached_images: Dict[str, Dict[str, QPixmap]] = {}
        self.cv2_templates: Dict[str, List[np.ndarray]] = {}
        self._load_original_images()
        self._load_cv2_templates()
        
    def resource_path(self, relative_path: str) -> str:
        """Определяет путь к ресурсам в упакованном exe или development режиме"""
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        return os.path.join(base_path, relative_path)
    
    def _load_original_images(self):
        """Загружает оригинальные изображения героев"""
        if self.original_images:
            return
            
        logging.info("Loading original hero images...")
        heroes_icons_folder = self.resource_path("resources/heroes_icons")
        
        for hero in self._get_all_heroes():
            icon_filename = hero.lower().replace(' ', '_').replace('&', 'and') + '_1'
            img_path = os.path.join(heroes_icons_folder, f"{icon_filename}.png")
            
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    self.original_images[hero] = pixmap
                else:
                    logging.warning(f"Invalid pixmap for hero: {hero} at path {img_path}")
            else:
                logging.warning(f"Image not found for hero: {hero} at path {img_path}")
        
        logging.info(f"Loaded {len(self.original_images)} original images for {len(self._get_all_heroes())} heroes.")
    
    def _load_cv2_templates(self):
        """Загружает CV2 шаблоны для распознавания"""
        templates_dir = self.resource_path("resources/templates")
        if not os.path.isdir(templates_dir):
            logging.warning(f"CV2 templates directory not found at {templates_dir}")
            return
            
        hero_templates = defaultdict(list)
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        
        for filename in os.listdir(templates_dir):
            if filename.lower().endswith(valid_extensions):
                base_name, _ = os.path.splitext(filename) # Убираем расширение
                # Предполагаем формат "имя_героя_индекс"
                parts = base_name.split('_')
                
                if len(parts) >= 2 and parts[-1].isdigit():
                    hero_name_from_file = " ".join(parts[:-1]).strip().title() # Восстанавливаем имя
                    template_path = os.path.join(templates_dir, filename)
                    template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
                    
                    if template_img is not None:
                        if len(template_img.shape) == 3 and template_img.shape == 4:
                            template_img = cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR)
                        hero_templates[hero_name_from_file].append(template_img)
        
        self.cv2_templates = dict(hero_templates)
        logging.info(f"Loaded CV2 templates for {len(self.cv2_templates)} heroes.")
    
    def _get_all_heroes(self) -> List[str]:
        """Возвращает список всех героев из единого источника данных"""
        return ALL_HEROES
    
    def get_images(self, mode: str = 'middle') -> Tuple[Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap]]:
        """Возвращает изображения для указанного режима, используя кэш"""
        if mode in self.cached_images:
            return (
                self.cached_images[mode].get('right', {}),
                self.cached_images[mode].get('left', {}),
                self.cached_images[mode].get('small', {}),
                self.cached_images[mode].get('horizontal', {})
            )
        
        mode_sizes = SIZES.get(mode, SIZES['middle'])
        
        right_images, left_images, small_images, horizontal_images = {}, {}, {}, {}
        
        for hero, img in self.original_images.items():
            if not img.isNull():
                right_images[hero] = self._scale_image(img, mode_sizes['right'])
                left_images[hero] = self._scale_image(img, mode_sizes['left'])
                small_images[hero] = self._scale_image(img, mode_sizes['small'])
                horizontal_images[hero] = self._scale_image(img, mode_sizes['horizontal'])
        
        self.cached_images[mode] = {
            'right': right_images, 'left': left_images, 
            'small': small_images, 'horizontal': horizontal_images
        }
        
        return right_images, left_images, small_images, horizontal_images
    
    def get_specific_images(self, mode: str, image_type: str) -> Dict[str, QPixmap]:
        """
        Возвращает словарь с изображениями определенного типа для указанного режима.
        Например, все 'horizontal' изображения для режима 'min'.
        """
        # Сначала убеждаемся, что кэш для данного режима существует.
        # Вызов get_images() заполнит кэш, если он пуст.
        self.get_images(mode)
        
        # Теперь безопасно извлекаем данные из кэша.
        mode_cache = self.cached_images.get(mode, {})
        specific_images = mode_cache.get(image_type, {})
        
        if not specific_images and image_type in SIZES.get(mode, {}):
             logging.warning(f"Could not find cached images for mode='{mode}', type='{image_type}'.")

        return specific_images

    def _scale_image(self, pixmap: QPixmap, size: Tuple[int, int]) -> QPixmap:
        """Масштабирует изображение до указанного размера"""
        w, h = size
        if w <= 0 or h <= 0:
            return self._get_default_pixmap((1, 1))
        
        return pixmap.scaled(QSize(w, h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def _get_default_pixmap(self, size: Tuple[int, int] = (1, 1)) -> QPixmap:
        """Возвращает изображение-заглушку"""
        default = QPixmap(QSize(*size))
        default.fill(QColor("lightgray"))
        return default
    
    def get_cv2_templates(self) -> Dict[str, List[np.ndarray]]:
        """Возвращает CV2 шаблоны для распознавания"""
        return self.cv2_templates
    
    def clear_cache(self):
        """Очищает кэш изображений"""
        self.cached_images.clear()
        logging.info("Image cache cleared.")