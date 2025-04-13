# File: images_load.py
from PySide6.QtGui import QPixmap, Qt # Импортируем Qt здесь
from PySide6.QtCore import QSize    # Импортируем QSize здесь
import os
import sys

# --- РАЗМЕР ИКОНОК В ВЕРХНЕМ ГОРИЗОНТАЛЬНОМ СПИСКЕ ---
# Измените QSize(50, 50) на желаемый размер (ширина, высота)
TOP_HORIZONTAL_ICON_SIZE = QSize(50, 50)
# ----------------------------------------------------

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Размеры для разных панелей в разных режимах
SIZES = {
    'max': {
        'right': (60, 60),      # Для правой панели (QListWidget)
        'left': (50, 50),       # Для левой панели (display - большая иконка)
        'small': (35, 35),      # Для левой панели (display - маленькие иконки +/-)
        'horizontal': (25, 25)  # Для горизонтального списка под верхней панелью (устарело, используем TOP_HORIZONTAL_ICON_SIZE)
    },
    'middle': {
        'right': (40, 40),
        'left': (35, 35),
        'small': (25, 25),
        'horizontal': (25, 25) # Устарело
    },
    'min': {
        'right': (0, 0),        # Правой панели нет
        'left': (50, 50),       # Для левой панели (minimal_icon_list)
        'small': (0, 0),        # Маленьких +/- иконок нет
        'horizontal': (20, 20) # Устарело
    }
}

loaded_images = {mode: {'right': {}, 'left': {}, 'small': {}, 'horizontal': {}} for mode in SIZES}
original_images = {}
default_pixmap = None

def load_original_images():
    from heroes_bd import heroes # Импортируем здесь, чтобы избежать циклич. зависимостей
    if original_images:
        return
    print("Загрузка оригинальных изображений...")
    for hero in heroes:
        # Путь к файлу изображения героя (имя файла в нижнем регистре)
        img_path_png = resource_path(f"resources/{hero.lower().replace(' ', '_').replace('&', 'and')}.png")
        img_path_jpg = resource_path(f"resources/{hero.lower().replace(' ', '_').replace('&', 'and')}.jpg") # Добавляем проверку jpg

        img_path = None
        if os.path.exists(img_path_png):
            img_path = img_path_png
        elif os.path.exists(img_path_jpg):
             img_path = img_path_jpg

        if img_path:
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                original_images[hero] = pixmap
                # print(f"Изображение для {hero} загружено из {img_path}, размер: {pixmap.width()}x{pixmap.height()}")
            else:
                print(f"Изображение для {hero} в {img_path} недействительно")
                original_images[hero] = load_default_pixmap()
        else:
            print(f"Файл изображения для {hero} не найден ({img_path_png} или {img_path_jpg})")
            original_images[hero] = load_default_pixmap()
    print("Оригинальные изображения загружены.")


def get_images_for_mode(mode='middle'):
    """
    Возвращает словари с QPixmap нужных размеров для указанного режима.
    Использует TOP_HORIZONTAL_ICON_SIZE для горизонтального списка.
    """
    if not original_images:
        load_original_images()
    if mode not in SIZES:
        print(f"Предупреждение: Неизвестный режим '{mode}'. Используется 'middle'.")
        mode = 'middle'

    # print(f"Генерация изображений для режима: {mode}")
    mode_sizes = SIZES[mode]
    right_size = mode_sizes.get('right', (0,0))
    left_size = mode_sizes.get('left', (0,0))
    small_size = mode_sizes.get('small', (0,0))
    # Используем константу для горизонтального списка
    horizontal_icon_qsize = TOP_HORIZONTAL_ICON_SIZE
    horizontal_size = (horizontal_icon_qsize.width(), horizontal_icon_qsize.height())

    # Проверяем, кэшированы ли уже изображения для этого режима
    if loaded_images.get(mode) and all(loaded_images[mode].values()):
        # print(f"Изображения для режима {mode} взяты из кэша.")
        return loaded_images[mode]['right'], loaded_images[mode]['left'], loaded_images[mode]['small'], loaded_images[mode]['horizontal']

    # Генерируем и кэшируем, если нет в кэше
    right_images = {}
    left_images = {}
    small_images = {}
    horizontal_images = {}

    for hero, img in original_images.items():
        try:
            # Генерация с проверкой нулевого размера
            if right_size[0] > 0 and right_size[1] > 0:
                right_images[hero] = img.scaled(*right_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if left_size[0] > 0 and left_size[1] > 0:
                left_images[hero] = img.scaled(*left_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if small_size[0] > 0 and small_size[1] > 0:
                small_images[hero] = img.scaled(*small_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if horizontal_size[0] > 0 and horizontal_size[1] > 0:
                horizontal_images[hero] = img.scaled(*horizontal_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except Exception as e:
            print(f"Ошибка изменения размера изображения для {hero} в режиме {mode}: {e}")
            # Устанавливаем заглушки при ошибке
            if right_size[0] > 0: right_images[hero] = load_default_pixmap(right_size)
            if left_size[0] > 0: left_images[hero] = load_default_pixmap(left_size)
            if small_size[0] > 0: small_images[hero] = load_default_pixmap(small_size)
            if horizontal_size[0] > 0: horizontal_images[hero] = load_default_pixmap(horizontal_size)

    # Кэшируем результаты
    loaded_images[mode]['right'] = right_images
    loaded_images[mode]['left'] = left_images
    loaded_images[mode]['small'] = small_images
    loaded_images[mode]['horizontal'] = horizontal_images
    # print(f"Изображения сгенерированы и кэшированы для режима: {mode}")
    return right_images, left_images, small_images, horizontal_images

def load_default_pixmap(size=(1,1)):
    """Создает серый QPixmap указанного размера."""
    pixmap = QPixmap(size[0], size[1])
    pixmap.fill(Qt.GlobalColor.gray)
    return pixmap

# Старая функция, больше не нужна
# def load_images():
#     print("Предупреждение: Прямой вызов load_images() устарел. Используйте get_images_for_mode().")
#     return get_images_for_mode('middle')