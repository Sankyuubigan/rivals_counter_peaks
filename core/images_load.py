# File: images_load.py
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtCore import QSize
import os
import sys

# --- УДАЛЕНА КОНСТАНТА TOP_HORIZONTAL_ICON_SIZE ---

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Размеры для разных панелей в разных режимах
# Теперь ключ 'horizontal' будет использоваться!
# НАСТРАИВАЙТЕ ЭТИ ЗНАЧЕНИЯ
SIZES = {
    'max': {
        'right': (60, 60),
        'left': (50, 50),
        'small': (35, 35),
        'horizontal': (55, 55) # Гориз. список в max режиме
    },
    'middle': {
        'right': (40, 40),
        'left': (35, 35),
        'small': (25, 25),
        'horizontal': (45, 45) # Гориз. список в middle режиме
    },
    'min': {
        'right': (0, 0),
        'left': (50, 50),
        'small': (0, 0),
        'horizontal': (35, 35) # Гориз. список в min режиме
    }
}

loaded_images = {mode: {'right': {}, 'left': {}, 'small': {}, 'horizontal': {}} for mode in SIZES}
original_images = {}
default_pixmap = None

def load_original_images():
    from heroes_bd import heroes
    if original_images: return
    print("Загрузка оригинальных изображений...")
    for hero in heroes:
        img_path_png = resource_path(f"resources/{hero.lower().replace(' ', '_').replace('&', 'and')}.png")
        img_path_jpg = resource_path(f"resources/{hero.lower().replace(' ', '_').replace('&', 'and')}.jpg")
        img_path = None
        if os.path.exists(img_path_png): img_path = img_path_png
        elif os.path.exists(img_path_jpg): img_path = img_path_jpg

        if img_path:
            pixmap = QPixmap(img_path)
            if not pixmap.isNull(): original_images[hero] = pixmap
            else: print(f"[WARN] Изображение для {hero} в {img_path} недействительно"); original_images[hero] = load_default_pixmap()
        else:
            print(f"[WARN] Файл изображения для {hero} не найден ({img_path_png} или {img_path_jpg})"); original_images[hero] = load_default_pixmap()
    print("Оригинальные изображения загружены.")


def get_images_for_mode(mode='middle'):
    """
    Возвращает словари с QPixmap нужных размеров для указанного режима.
    Использует SIZES[mode]['horizontal'] для горизонтального списка.
    """
    if not original_images: load_original_images()
    if mode not in SIZES: print(f"[WARN] Неизвестный режим '{mode}'. Используется 'middle'."); mode = 'middle'

    mode_sizes = SIZES[mode]
    right_size = mode_sizes.get('right', (0,0))
    left_size = mode_sizes.get('left', (0,0))
    small_size = mode_sizes.get('small', (0,0))
    # <<< ИЗМЕНЕНИЕ: Берем размер из SIZES >>>
    horizontal_size = mode_sizes.get('horizontal', (30, 30)) # Запасной размер 30x30

    # Проверка кэша
    cached_data = loaded_images.get(mode)
    if cached_data:
        horizontal_needed = horizontal_size[0] > 0 and horizontal_size[1] > 0
        right_needed = right_size[0] > 0 and right_size[1] > 0
        left_needed = left_size[0] > 0 and left_size[1] > 0
        small_needed = small_size[0] > 0 and small_size[1] > 0
        # Проверяем, что все нужные словари не пусты
        if (cached_data['right'] or not right_needed) and \
           (cached_data['left'] or not left_needed) and \
           (cached_data['small'] or not small_needed) and \
           (cached_data['horizontal'] or not horizontal_needed) :
            # print(f"Изображения для режима {mode} взяты из кэша.")
            return cached_data['right'], cached_data['left'], cached_data['small'], cached_data['horizontal']

    # Генерация и кэширование
    print(f"Генерация изображений для режима: {mode}")
    right_images = {}; left_images = {}; small_images = {}; horizontal_images = {}

    # --- ИСПОЛЬЗУЕМ SmoothTransformation для лучшего качества при масштабировании ---
    # Но помните, что при сильном увеличении качество все равно упадет, если исходник маленький
    transform_mode = Qt.TransformationMode.SmoothTransformation
    # --------------------------------------------------------------------------------

    for hero, img in original_images.items():
        try:
            if right_size[0] > 0: right_images[hero] = img.scaled(*right_size, Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
            if left_size[0] > 0: left_images[hero] = img.scaled(*left_size, Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
            if small_size[0] > 0: small_images[hero] = img.scaled(*small_size, Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
            if horizontal_size[0] > 0: horizontal_images[hero] = img.scaled(*horizontal_size, Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
        except Exception as e:
            print(f"[ERROR] Ошибка изменения размера изображения для {hero} в режиме {mode}: {e}")
            if right_size[0] > 0: right_images[hero] = load_default_pixmap(right_size)
            if left_size[0] > 0: left_images[hero] = load_default_pixmap(left_size)
            if small_size[0] > 0: small_images[hero] = load_default_pixmap(small_size)
            if horizontal_size[0] > 0: horizontal_images[hero] = load_default_pixmap(horizontal_size)

    loaded_images[mode]['right'] = right_images
    loaded_images[mode]['left'] = left_images
    loaded_images[mode]['small'] = small_images
    loaded_images[mode]['horizontal'] = horizontal_images
    print(f"Изображения сгенерированы и кэшированы для режима: {mode}")
    return right_images, left_images, small_images, horizontal_images

def load_default_pixmap(size=(1,1)):
    """Создает серый QPixmap указанного размера."""
    pixmap = QPixmap(size[0], size[1])
    pixmap.fill(Qt.GlobalColor.gray)
    return pixmap