from PySide6.QtGui import QPixmap, Qt
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

SIZES = {
    'max': {
        'right': (60, 60),
        'left': (50, 50),
        'small': (35, 35)
    },
    'middle': {
        'right': (35, 35),
        'left': (25, 25),
        'small': (18, 18)
    },
    'min': {
        'right': (0, 0),
        'left': (35, 35),  # Увеличиваем иконки в минимальном режиме
        'small': (25, 25)  # Увеличиваем маленькие иконки
    }
}

loaded_images = {mode: {'right': {}, 'left': {}, 'small': {}} for mode in SIZES}
original_images = {}

def load_original_images():
    from heroes_bd import heroes
    if original_images:
        return
    print("Loading original images...")
    for hero in heroes:
        img_path = resource_path(f"resources/{hero.lower().replace(' ', '_')}.png")
        if os.path.exists(img_path):  # Проверяем, существует ли файл
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():  # Проверяем, что изображение валидно
                original_images[hero] = pixmap
                print(f"Loaded image for {hero} from {img_path}")
            else:
                print(f"Image for {hero} at {img_path} is invalid")
                original_images[hero] = load_default_pixmap()  # Используем запасное изображение
        else:
            print(f"Image file for {hero} not found at {img_path}")
            original_images[hero] = load_default_pixmap()  # Используем запасное изображение
    print("Original images loaded.")

def get_images_for_mode(mode='middle'):
    if not original_images:
        load_original_images()
    if mode not in SIZES:
        print(f"Warning: Unknown mode '{mode}'. Using 'middle'.")
        mode = 'middle'
    print(f"Generating images for mode: {mode}")
    right_size = SIZES[mode]['right']
    left_size = SIZES[mode]['left']
    small_size = SIZES[mode]['small']
    right_images = {}
    left_images = {}
    small_images = {}
    for hero, img in original_images.items():
        try:
            if right_size != (0, 0):  # Пропускаем, если размер нулевой (режим min)
                right_images[hero] = img.scaled(*right_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            left_images[hero] = img.scaled(*left_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            small_images[hero] = img.scaled(*small_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e:
            print(f"Error resizing image for {hero} in mode {mode}: {e}")
            if right_size != (0, 0):
                right_images[hero] = load_default_pixmap()  # Запасное изображение для right
            left_images[hero] = load_default_pixmap()  # Запасное изображение для left
            small_images[hero] = load_default_pixmap()  # Запасное изображение для small
    loaded_images[mode]['right'] = right_images
    loaded_images[mode]['left'] = left_images
    loaded_images[mode]['small'] = small_images
    print(f"Images generated and cached for mode: {mode}")
    return right_images, left_images, small_images

def load_default_pixmap():
    global default_pixmap
    if default_pixmap is None:
        # Создаем простое серое изображение 1x1 как запасное
        default_pixmap = QPixmap(1, 1)
        default_pixmap.fill(Qt.gray)
    return default_pixmap

def load_images():
    print("Warning: Direct call to load_images() is deprecated. Use get_images_for_mode().")
    return get_images_for_mode('middle')