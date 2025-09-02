import os
import sys
import logging
import cv2
import numpy as np
from PIL import Image, ImageFilter
# ИСПРАВЛЕНО: Добавлен импорт Qt
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
class ImageManager:
    """Унифицированный менеджер для работы с изображениями и иконками"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.original_images: Dict[str, QPixmap] = {}
        self.cached_images: Dict[str, Dict[str, Dict[str, QPixmap]]] = {}
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
        
        # Маппинг специальных имен героев
        hero_mapping = {
  
        }
        
        for hero in self._get_all_heroes():
            # Определяем имя файла
            if hero in hero_mapping:
                icon_filename = hero_mapping[hero]
            else:
                icon_filename = hero.lower().replace(' ', '_').replace('&', 'and') + '_1'
            
            img_path = os.path.join(heroes_icons_folder, f"{icon_filename}.png")
            
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    self.original_images[hero] = pixmap
                    # Сохраняем оба варианта имени для совместимости
                    if hero != icon_filename.replace('_1', '').replace('_', ' ').title():
                        self.original_images[icon_filename.replace('_1', '').replace('_', ' ').title()] = pixmap
                else:
                    logging.warning(f"Invalid pixmap for hero: {hero}")
            else:
                logging.warning(f"Image not found for hero: {hero}")
        
        logging.info(f"Loaded {len(self.original_images)} original images")
    
    def _load_cv2_templates(self):
        """Загружает CV2 шаблоны для распознавания"""
        templates_dir = self.resource_path("resources/templates")
        if not os.path.isdir(templates_dir):
            return
            
        hero_templates = defaultdict(list)
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        
        for filename in os.listdir(templates_dir):
            if filename.lower().endswith(valid_extensions):
                base_name = os.path.splitext(filename)[0]
                parts = base_name.split('_')
                
                if len(parts) >= 2:
                    hero_name = " ".join(parts[:-1]).strip()
                    template_path = os.path.join(templates_dir, filename)
                    template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
                    
                    if template_img is not None:
                        # Конвертация в BGR если нужно
                        if len(template_img.shape) == 3 and template_img.shape[2] == 4:
                            template_img = cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR)
                        hero_templates[hero_name].append(template_img)
        
        self.cv2_templates = dict(hero_templates)
        logging.info(f"Loaded CV2 templates for {len(self.cv2_templates)} heroes")
    
    def _get_all_heroes(self) -> List[str]:
        """Возвращает список всех героев согласно эталонной базе данных"""
        # Синхронизировано с marvel_rivals_stats_20250831-030213.json
        return [
            "Peni Parker",
            "Rocket Raccoon",
            "Magik",
            "Mantis",
            "Storm",
            "Hulk",
            "Ultron",
            "Captain America",
            "Mister Fantastic",
            "Iron Man",
            "Thor",
            "Loki",
            "Black Panther",
            "Iron Fist",
            "Namor",
            "The Thing",
            "Emma Frost",
            "Doctor Strange",
            "Psylocke",
            "Wolverine",
            "Human Torch",
            "Adam Warlock",
            "Magneto",
            "Hela",
            "Cloak & Dagger",
            "Venom",
            "Luna Snow",
            "Scarlet Witch",
            "Groot",
            "Spider Man",
            "Squirrel Girl",
            "Star Lord",
            "Invisible Woman",
            "Phoenix",
            "Winter Soldier",
            "Moon Knight",
            "Jeff The Land Shark",
            "Hawkeye",
            "The Punisher",
            "Black Widow",
            "Blade"
        ]
    
    def get_images_for_mode(self, mode: str = 'middle') -> Tuple[Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap]]:
        """Возвращает изображения для указанного режима"""
        if mode in self.cached_images:
            return (
                self.cached_images[mode]['right'],
                self.cached_images[mode]['left'],
                self.cached_images[mode]['small'],
                self.cached_images[mode]['horizontal']
            )
        
        # Размеры для разных режимов
        sizes = {
            'max': {'right': (60, 60), 'left': (50, 50), 'small': (35, 35), 'horizontal': (55, 55)},
            'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
            'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)}
        }
        
        if mode not in sizes:
            mode = 'middle'
        
        mode_sizes = sizes[mode]
        right_images = {}
        left_images = {}
        small_images = {}
        horizontal_images = {}
        
        for hero, img in self.original_images.items():
            if img.isNull():
                continue
                
            # Масштабируем изображения для разных размеров
            right_images[hero] = self._scale_image(img, mode_sizes['right'])
            left_images[hero] = self._scale_image(img, mode_sizes['left'])
            small_images[hero] = self._scale_image(img, mode_sizes['small'])
            horizontal_images[hero] = self._scale_image(img, mode_sizes['horizontal'])
        
        # Кэшируем результаты
        self.cached_images[mode] = {
            'right': right_images,
            'left': left_images,
            'small': small_images,
            'horizontal': horizontal_images
        }
        
        return right_images, left_images, small_images, horizontal_images
    
    def _scale_image(self, pixmap: QPixmap, size: Tuple[int, int]) -> QPixmap:
        """Масштабирует изображение до указанного размера"""
        if pixmap.isNull():
            return self._get_default_pixmap(size)
        
        w, h = size
        if w <= 0 or h <= 0:
            return self._get_default_pixmap((1, 1))
        
        scaled = pixmap.scaled(QSize(w, h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return scaled if not scaled.isNull() else self._get_default_pixmap(size)
    
    def _get_default_pixmap(self, size: Tuple[int, int] = (1, 1)) -> QPixmap:
        """Возвращает изображение-заглушку"""
        default = QPixmap(1, 1)
        default.fill(QColor(128, 128, 128))
        return default.scaled(QSize(*size), Qt.IgnoreAspectRatio, Qt.FastTransformation)
    
    def get_cv2_templates(self) -> Dict[str, List[np.ndarray]]:
        """Возвращает CV2 шаблоны для распознавания"""
        return self.cv2_templates
    
    def preprocess_image_for_dino(self, image_pil: Image.Image) -> Optional[Image.Image]:
        """Предобрабатывает изображение для DINO модели"""
        if image_pil is None:
            return None
        
        try:
            # Конвертируем в RGB если необходимо
            if image_pil.mode not in ('RGB', 'L'):
                if image_pil.mode == 'RGBA':
                    background = Image.new("RGB", image_pil.size, (255, 255, 255))
                    if 'A' in image_pil.getbands():
                        background.paste(image_pil, mask=image_pil.split()[-1])
                    image_pil = background
                else:
                    image_pil = image_pil.convert('RGB')
            
            # Применяем нерезкое маскирование
            sharpened = image_pil.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
            return sharpened
        except Exception as e:
            logging.error(f"Error preprocessing image: {e}")
            return None
    
    def clear_cache(self):
        """Очищает кэш изображений"""
        self.cached_images.clear()
        logging.info("Image cache cleared")