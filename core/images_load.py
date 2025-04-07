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
        'small': (35, 35),
        'horizontal': (25, 25)  # Такой же размер, как в среднем режиме
    },
    'middle': {
        'right': (35, 35),
        'left': (25, 25),
        'small': (18, 18),
        'horizontal': (25, 25)
    },
    'min': {
        'right': (0, 0),
        'left': (50, 50),
        'small': (25, 25),
        'horizontal': (50, 50)
    }
}

loaded_images = {mode: {'right': {}, 'left': {}, 'small': {}, 'horizontal': {}} for mode in SIZES}
original_images = {}
default_pixmap = None

def load_original_images():
    from heroes_bd import heroes
    if original_images:
        return
    print("Загрузка оригинальных изображений...")
    for hero in heroes:
        img_path = resource_path(f"resources/{hero.lower().replace(' ', '_')}.png")
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                original_images[hero] = pixmap
                print(f"Изображение для {hero} загружено из {img_path}, размер: {pixmap.width()}x{pixmap.height()}")
            else:
                print(f"Изображение для {hero} в {img_path} недействительно")
                original_images[hero] = load_default_pixmap()
        else:
            print(f"Файл изображения для {hero} не найден в {img_path}")
            original_images[hero] = load_default_pixmap()
    print("Оригинальные изображения загружены.")

def get_images_for_mode(mode='middle'):
    if not original_images:
        load_original_images()
    if mode not in SIZES:
        print(f"Предупреждение: Неизвестный режим '{mode}'. Используется 'middle'.")
        mode = 'middle'
    print(f"Генерация изображений для режима: {mode}")
    right_size = SIZES[mode]['right']
    left_size = SIZES[mode]['left']
    small_size = SIZES[mode]['small']
    horizontal_size = SIZES[mode]['horizontal']
    right_images = {}
    left_images = {}
    small_images = {}
    horizontal_images = {}
    for hero, img in original_images.items():
        try:
            if right_size != (0, 0):
                right_images[hero] = img.scaled(*right_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            left_images[hero] = img.scaled(*left_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            small_images[hero] = img.scaled(*small_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            horizontal_images[hero] = img.scaled(*horizontal_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e:
            print(f"Ошибка изменения размера изображения для {hero} в режиме {mode}: {e}")
            if right_size != (0, 0):
                right_images[hero] = load_default_pixmap()
            left_images[hero] = load_default_pixmap()
            small_images[hero] = load_default_pixmap()
            horizontal_images[hero] = load_default_pixmap()
    loaded_images[mode]['right'] = right_images
    loaded_images[mode]['left'] = left_images
    loaded_images[mode]['small'] = small_images
    loaded_images[mode]['horizontal'] = horizontal_images
    print(f"Изображения сгенерированы и кэшированы для режима: {mode}")
    return right_images, left_images, small_images, horizontal_images

def load_default_pixmap():
    global default_pixmap
    if default_pixmap is None:
        default_pixmap = QPixmap(1, 1)
        default_pixmap.fill(Qt.gray)
    return default_pixmap

def load_images():
    print("Предупреждение: Прямой вызов load_images() устарел. Используйте get_images_for_mode().")
    return get_images_for_mode('middle')