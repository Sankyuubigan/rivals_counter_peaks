# File: core/image_manager.py
import os
import sys
import logging
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
# ИСПРАВЛЕНО: Исправлен путь импорта
from core.database.heroes_bd import heroes as ALL_HEROES
SIZES = {
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    # ИСПРАВЛЕНИЕ: Устанавливаем корректный размер для режима 'min' чтобы избежать растягивания иконок
    'min': {'right': (30, 30), 'left': (30, 30), 'small': (20, 20), 'horizontal': (30, 30)}
}
class ImageManager:
    """Унифицированный менеджер для работы с изображениями и иконками"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.original_images: Dict[str, QPixmap] = {}
        self.cached_images: Dict[str, Dict[str, QPixmap]] = {}
        self._load_original_images()
        
    def resource_path(self, relative_path: str) -> str:
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = self.project_root
        return os.path.join(base_path, relative_path)
    
    def _load_original_images(self):
        if self.original_images: return
            
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
        
        logging.info(f"Loaded {len(self.original_images)} original images.")
    
    def _get_all_heroes(self) -> List[str]:
        return ALL_HEROES
    
    def get_images(self, mode: str = 'middle') -> Tuple[Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap]]:
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
                # ИСПРАВЛЕНИЕ: Используем оператор * для распаковки кортежа с размерами (w, h)
                # в отдельные аргументы для метода .scaled(w, h, ...).
                right_images[hero] = img.scaled(*mode_sizes['right'], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                left_images[hero] = img.scaled(*mode_sizes['left'], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                small_images[hero] = img.scaled(*mode_sizes['small'], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                horizontal_images[hero] = img.scaled(*mode_sizes['horizontal'], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.cached_images[mode] = {
            'right': right_images, 'left': left_images, 
            'small': small_images, 'horizontal': horizontal_images
        }
        
        return right_images, left_images, small_images, horizontal_images
    
    def get_specific_images(self, mode: str, image_type: str) -> Dict[str, QPixmap]:
        self.get_images(mode)
        return self.cached_images.get(mode, {}).get(image_type, {})
    def clear_cache(self):
        self.cached_images.clear()
        logging.info("Image cache cleared.")