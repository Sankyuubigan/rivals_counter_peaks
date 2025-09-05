"""
Упрощенная версия images_load.py, использующая ImageManager.
Оставлена для обратной совместимости с частями кода, которые могут ее импортировать.
"""
import logging
import os
from PySide6.QtGui import QPixmap
from typing import Dict, Tuple, Optional, List
import numpy as np
from core.image_manager import ImageManager

_image_manager_instance: Optional[ImageManager] = None

def get_image_manager() -> ImageManager:
    """Получает или создает единственный экземпляр ImageManager."""
    global _image_manager_instance
    if _image_manager_instance is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        _image_manager_instance = ImageManager(project_root)
    return _image_manager_instance

def get_images_for_mode(mode: str = 'middle') -> Tuple[Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap]]:
    """Возвращает изображения для указанного режима через ImageManager."""
    return get_image_manager().get_images(mode)

def load_hero_templates_cv2() -> Dict[str, List[np.ndarray]]:
    """Загружает CV2 шаблоны через ImageManager."""
    return get_image_manager().get_cv2_templates()

def is_invalid_pixmap(pixmap: Optional[QPixmap]) -> bool:
    """Проверяет, является ли QPixmap невалидным."""
    return pixmap is None or pixmap.isNull()

SIZES = {
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)}
}

def load_original_images():
    """Эта функция больше ничего не делает, так как ImageManager загружает все при инициализации."""
    logging.debug("`images_load.load_original_images()` is deprecated. ImageManager handles loading automatically.")
    get_image_manager()