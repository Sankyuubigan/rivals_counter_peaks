"""
Упрощенная версия images_load.py с использованием ImageManager
"""
import logging
import os
from PySide6.QtGui import QPixmap
from typing import Dict, Tuple, Optional
from core.image_manager import ImageManager

# Глобальный экземпляр менеджера изображений
_image_manager: Optional[ImageManager] = None

def get_image_manager(project_root: str) -> ImageManager:
    """Получает или создает экземпляр ImageManager"""
    global _image_manager
    if _image_manager is None:
        _image_manager = ImageManager(project_root)
    return _image_manager

def get_images_for_mode(mode: str = 'middle', project_root: str = None) -> Tuple[Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap]]:
    """Возвращает изображения для указанного режима"""
    manager = get_image_manager(project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    return manager.get_images_for_mode(mode)

def load_hero_templates_cv2(project_root: str = None):
    """Загружает CV2 шаблоны"""
    manager = get_image_manager(project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    return manager.get_cv2_templates()

def clear_image_cache():
    """Очищает кэш изображений"""
    global _image_manager
    if _image_manager:
        _image_manager.clear_cache()
    logging.info("Image cache cleared")

# Функции-обертки для обратной совместимости
def load_default_pixmap(size=(1, 1)) -> QPixmap:
    """Обертка для ImageManager.get_default_pixmap()"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    manager = get_image_manager(project_root)
    return manager._get_default_pixmap(size)

def is_invalid_pixmap(pixmap) -> bool:
    """Проверяет, является ли QPixmap невалидным"""
    if pixmap is None:
        return True
    return pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0

# Глобальные переменные для совместимости со старым кодом
loaded_images = {}
original_images = {}
CV2_HERO_TEMPLATES = {}

def load_original_images():
    """Загружает оригинальные изображения героев для обратной совместимости"""
    global original_images, loaded_images
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    manager = get_image_manager(project_root)
    
    # Копируем изображения из менеджера в глобальные переменные
    original_images.clear()
    loaded_images.clear()
    
    for hero_name, pixmap in manager.original_images.items():
        original_images[hero_name] = pixmap
        loaded_images[hero_name] = pixmap
    
    logging.info(f"Loaded {len(original_images)} original images for compatibility")

# Оставляем константу SIZES для совместимости
SIZES = {
    'max': {'right': (60, 60), 'left': (50, 50), 'small': (35, 35), 'horizontal': (55, 55)},
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)}
}