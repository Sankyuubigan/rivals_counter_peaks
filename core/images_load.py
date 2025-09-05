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

# Глобальный экземпляр менеджера изображений (Singleton)
_image_manager_instance: Optional[ImageManager] = None

def get_image_manager() -> ImageManager:
    """Получает или создает единственный экземпляр ImageManager."""
    global _image_manager_instance
    if _image_manager_instance is None:
        # Определяем корень проекта относительно этого файла
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        _image_manager_instance = ImageManager(project_root)
    return _image_manager_instance

def get_images_for_mode(mode: str = 'middle') -> Tuple[Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap], Dict[str, QPixmap]]:
    """Возвращает изображения для указанного режима через ImageManager."""
    manager = get_image_manager()
    return manager.get_images_for_mode(mode)

def load_hero_templates_cv2() -> Dict[str, List[np.ndarray]]:
    """Загружает CV2 шаблоны через ImageManager."""
    manager = get_image_manager()
    return manager.get_cv2_templates()

def clear_image_cache():
    """Очищает кэш изображений в ImageManager."""
    manager = get_image_manager()
    manager.clear_cache()

# --- Функции и переменные для обратной совместимости ---

def load_default_pixmap(size=(1, 1)) -> QPixmap:
    """Возвращает изображение-заглушку."""
    manager = get_image_manager()
    return manager._get_default_pixmap(size)

def is_invalid_pixmap(pixmap: Optional[QPixmap]) -> bool:
    """Проверяет, является ли QPixmap невалидным."""
    return pixmap is None or pixmap.isNull()

# Глобальная переменная для совместимости со старым кодом
SIZES = {
    'max': {'right': (60, 60), 'left': (50, 50), 'small': (35, 35), 'horizontal': (55, 55)},
    'middle': {'right': (40, 40), 'left': (35, 35), 'small': (25, 25), 'horizontal': (45, 45)},
    'min': {'right': (0, 0), 'left': (40, 40), 'small': (0, 0), 'horizontal': (40, 40)}
}

# Функция-заглушка для совместимости
def load_original_images():
    """Эта функция больше ничего не делает, так как ImageManager загружает все при инициализации."""
    logging.debug("`images_load.load_original_images()` is deprecated. ImageManager handles loading automatically.")
    get_image_manager() # Убедимся, что менеджер инициализирован