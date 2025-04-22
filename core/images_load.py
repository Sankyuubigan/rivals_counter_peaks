# File: images_load.py
from PySide6.QtGui import QPixmap, Qt, QColor
from PySide6.QtCore import QSize
import os
import sys
# <<< ДОБАВЛЕНО: Импорты для загрузки шаблонов >>>
import cv2
import numpy as np
from collections import defaultdict
from heroes_bd import heroes as ALL_HERO_NAMES # Импортируем список героев
# <<< --------------------------------------- >>>


def resource_path(relative_path):
    """Получаем абсолютный путь к ресурсу, работает для обычного запуска и PyInstaller"""
    try:
        base_path = sys._MEIPASS  # PyInstaller создает временную папку и сохраняет путь в sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")  # Обычный запуск из скрипта

    return os.path.join(base_path, relative_path)

# Размеры для разных панелей в разных режимах
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
        'right': (0, 0),      # Правая панель скрыта
        'left': (50, 50),      # Левая панель (для минимального списка)
        'small': (0, 0),      # Маленькие иконки не нужны
        'horizontal': (35, 35) # Гориз. список в min режиме (использует left_images)
    }
}


# Глобальные кэши
loaded_images = {mode: {"right": {}, "left": {}, "small": {}, "horizontal": {}} for mode in SIZES}
original_images = {}  # {hero_name: QPixmap}
default_pixmap = None  # Базовая заглушка 1x1
loaded_hero_templates = None  # {hero_name: [template1_cv2, ...]}


def load_original_images():
    """Загружает оригинальные изображения героев из папки resources."""  # noqa
    global original_images
    if original_images: return # Не загружаем повторно
    print("Загрузка оригинальных изображений...")
    loaded_count = 0
    missing_heroes = []
    temp_original_images = {} # Временный словарь для загрузки
    for hero in ALL_HERO_NAMES:
        # Формируем имя файла (lowercase, _ вместо пробела, and вместо &)
        base_filename = hero.lower().replace(' ', '_').replace('&', 'and')
        # Пытаемся найти png или jpg
        img_path_png = resource_path(f"resources/{base_filename}.png")
        img_path_jpg = resource_path(f"resources/{base_filename}.jpg")
        img_path = None

        if os.path.exists(img_path_png): img_path = img_path_png
        elif os.path.exists(img_path_jpg): img_path = img_path_jpg

        if img_path:
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                temp_original_images[hero] = pixmap
                loaded_count += 1
            else:
                print(f"[WARN] Изображение для {hero} в {img_path} недействительно")
                temp_original_images[hero] = load_default_pixmap() # Заглушка
                missing_heroes.append(hero + " (invalid)")
        else:
            # print(f"[WARN] Файл изображения для {hero} не найден (искали .png и .jpg)")
            temp_original_images[hero] = load_default_pixmap() # Заглушка
            missing_heroes.append(hero)

    original_images = temp_original_images # Присваиваем глобальной переменной
    print(f"Оригинальные изображения загружены: {loaded_count} / {len(ALL_HERO_NAMES)}")  # noqa
    if missing_heroes:  # noqa
        print(f"[WARN] Отсутствуют или недействительны изображения для: {', '.join(missing_heroes)}")


def get_images_for_mode(mode='middle'):
    """
    Возвращает словари с QPixmap нужных размеров для указанного режима.
    Использует кэш.
    """
    if not original_images: load_original_images() # Гарантируем загрузку оригиналов
    if mode not in SIZES: print(f"[WARN] Неизвестный режим '{mode}'. Используется 'middle'."); mode = 'middle'

    mode_sizes = SIZES[mode]
    right_size = mode_sizes.get('right', (0,0))
    left_size = mode_sizes.get('left', (0,0))
    small_size = mode_sizes.get('small', (0,0))
    horizontal_size = mode_sizes.get('horizontal', (30, 30))

    # Проверка кэша: проверяем наличие всех нужных размеров для данного режима
    cached_data = loaded_images.get(mode)
    if cached_data:
        keys_needed = {'right': right_size, 'left': left_size, 'small': small_size, 'horizontal': horizontal_size}
        cache_complete = True
        for key, size in keys_needed.items():
             # Если размер > 0 и этого ключа нет в кеше или он пуст
            if (size[0] > 0 and size[1] > 0) and (key not in cached_data or not cached_data[key]):
                cache_complete = False
                break
        if cache_complete:  # noqa
            # print(f"Изображения для режима {mode} взяты из кэша.")
            return cached_data['right'], cached_data['left'], cached_data['small'], cached_data['horizontal']

    # Генерация и кэширование, если кэш неполный или отсутствует
    print(f"Генерация изображений для режима: {mode}")
    # Создаем временные словари для этого режима
    right_images = {}; left_images = {}; small_images = {}; horizontal_images = {}

    transform_mode = Qt.TransformationMode.SmoothTransformation # Качественное масштабирование

    for hero, img in original_images.items():
        # Пропускаем, если оригинальное изображение - это заглушка (не загрузилось)
        if img.size() == QSize(1,1): # Проверяем размер заглушки
             # Добавляем заглушки нужного размера в словари для этого режима
             if right_size[0] > 0: right_images[hero] = load_default_pixmap(right_size)
             if left_size[0] > 0: left_images[hero] = load_default_pixmap(left_size)
             if small_size[0] > 0: small_images[hero] = load_default_pixmap(small_size)
             if horizontal_size[0] > 0: horizontal_images[hero] = load_default_pixmap(horizontal_size)
             continue # Переходим к следующему герою

        # Генерируем изображения нужных размеров
        try:
            if right_size[0] > 0: right_images[hero] = img.scaled(QSize(*right_size), Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
            if left_size[0] > 0: left_images[hero] = img.scaled(QSize(*left_size), Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
            if small_size[0] > 0: small_images[hero] = img.scaled(QSize(*small_size), Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
            if horizontal_size[0] > 0: horizontal_images[hero] = img.scaled(QSize(*horizontal_size), Qt.AspectRatioMode.KeepAspectRatio, transform_mode)
        except Exception as e:
            print(f"[ERROR] Ошибка изменения размера изображения для {hero} в режиме {mode}: {e}")
            # Устанавливаем заглушки при ошибке масштабирования
            if right_size[0] > 0: right_images[hero] = load_default_pixmap(right_size)
            if left_size[0] > 0: left_images[hero] = load_default_pixmap(left_size)
            if small_size[0] > 0: small_images[hero] = load_default_pixmap(small_size)
            if horizontal_size[0] > 0: horizontal_images[hero] = load_default_pixmap(horizontal_size)

    # Сохраняем сгенерированные словари в глобальный кэш
    loaded_images[mode]['right'] = right_images
    loaded_images[mode]['left'] = left_images
    loaded_images[mode]['small'] = small_images
    loaded_images[mode]['horizontal'] = horizontal_images
    print(f"Изображения сгенерированы и кэшированы для режима: {mode}")
    return right_images, left_images, small_images, horizontal_images


def load_default_pixmap(size=(1, 1)):
    """Создает или возвращает масштабированную серую заглушку QPixmap."""
    global default_pixmap

    # Создаем базовую заглушку 1x1 один раз
    if default_pixmap is None:
         dp = QPixmap(1,1)
         dp.fill(QColor(128, 128, 128)) # Серый цвет
         default_pixmap = dp
    # Масштабируем базовую заглушку до нужного размера
    if size != (1,1):
        # Используем быстрый режим для заглушки
        return default_pixmap.scaled(QSize(*size), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
    else:
        return default_pixmap # Возвращаем базовую 1x1


def load_image(base_filename):
    """Загружает изображение героя."""
    img_path = _get_image_path(base_filename)
    return _load_image_from_file(img_path)


def _get_image_path(base_filename):
    """Формирует путь к файлу изображения."""
    img_path_png = resource_path(f"resources/{base_filename}.png")
    img_path_jpg = resource_path(f"resources/{base_filename}.jpg")
    if os.path.exists(img_path_png):
        return img_path_png
    elif os.path.exists(img_path_jpg):
        return img_path_jpg
    return None


def _load_image_from_file(img_path):
    """Загружает изображение из файла по указанному пути."""
    return QPixmap(img_path) if img_path else None

# <<< ДОБАВЛЕНО: Функция загрузки шаблонов >>>
def load_hero_templates():
    """
    Загружает изображения шаблонов героев из папки resources/templates.
    Возвращает словарь: {hero_name: [template1_cv2, template2_cv2, ...]}
    Использует кэш.
    """
    global loaded_hero_templates
    if loaded_hero_templates is not None: # Возвращаем кэш, если уже загружали
        # print("Шаблоны героев взяты из кэша.")
        return loaded_hero_templates

    templates_dir = resource_path("resources/templates")
    hero_templates = defaultdict(list)
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp') # Добавлен webp
    print(f"Поиск шаблонов в: {templates_dir}")

    if not os.path.isdir(templates_dir):
        print(f"[ERROR] Папка шаблонов не найдена: {templates_dir}")
        loaded_hero_templates = {} # Сохраняем пустой словарь в кэш
        return loaded_hero_templates

    files_found = 0
    templates_loaded = 0
    skipped_unknown_hero = 0
    skipped_bad_name = 0
    skipped_load_error = 0

    for filename in os.listdir(templates_dir):
        # Проверяем расширение файла (без учета регистра)
        if filename.lower().endswith(valid_extensions):
            files_found += 1
            # Извлекаем имя файла без расширения и разделяем по '_'
            base_name = os.path.splitext(filename)[0]
            parts = base_name.split('_')

            # Ожидаем как минимум Имя_Номер или Имя_Фамилия_Номер
            if len(parts) >= 2:
                try:
                    # Пытаемся собрать имя героя (все части, кроме последней)
                    hero_name_parts = parts[:-1]
                    hero_name_parsed = " ".join(hero_name_parts).strip() # Объединяем и убираем лишние пробелы

                    # Ищем совпадение имени героя (без учета регистра)
                    matched_hero_name = None
                    for known_hero in ALL_HERO_NAMES:
                        if known_hero.lower() == hero_name_parsed.lower():
                            matched_hero_name = known_hero
                            break

                    if matched_hero_name:
                        template_path = os.path.join(templates_dir, filename)
                        # Загружаем изображение с помощью OpenCV в цвете (BGR)
                        template_img = cv2.imread(template_path, cv2.IMREAD_COLOR)
                        if template_img is not None:
                            hero_templates[matched_hero_name].append(template_img)
                            templates_loaded += 1
                            # print(f"  Загружен шаблон: {filename} для героя: {matched_hero_name}")
                        else:
                            print(f"[WARN] Не удалось загрузить шаблон OpenCV: {template_path}")
                            skipped_load_error += 1
                    else:
                         # print(f"[DEBUG] Пропущен файл (имя героя '{hero_name_parsed}' не найдено в списке): {filename}")
                         skipped_unknown_hero +=1
                except Exception as e:
                    print(f"[ERROR] Ошибка обработки файла шаблона {filename}: {e}")
                    skipped_load_error += 1
            else:
                 # print(f"[DEBUG] Пропущен файл (неверный формат имени - ожидался 'Имя_Номер'): {filename}")
                skipped_bad_name += 1

    print(f"Обработано файлов изображений: {files_found}")
    print(f"Успешно загружено шаблонов: {templates_loaded} для {len(hero_templates)} героев.")
    if skipped_unknown_hero > 0: print(f"Пропущено из-за неизвестного имени героя: {skipped_unknown_hero}")
    if skipped_bad_name > 0: print(f"Пропущено из-за неверного формата имени: {skipped_bad_name}")
    if skipped_load_error > 0: print(f"Пропущено из-за ошибки загрузки/обработки: {skipped_load_error}")


    if not hero_templates:
        print("[WARN] Ни одного шаблона не было успешно загружено.")

    # Сохраняем результат в кэш
    loaded_hero_templates = hero_templates
    return loaded_hero_templates
# <<< КОНЕЦ Функции загрузки шаблонов >>>  # noqa
