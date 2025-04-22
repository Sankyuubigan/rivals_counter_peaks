# File: utils.py
from heroes_bd import heroes_counters, heroes
# <<< ДОБАВЛЕНО: Импорты для скриншотов и обработки >>>
import mss
import mss.tools
import numpy as np
import cv2
import os # Для resource_path
import sys # Для resource_path
# <<< --------------------------------------------- >>>

# <<< ДОБАВЛЕНО: Константы для распознавания >>>
# ================================================================
# !!! НАСТРОЙ ЭТУ ОБЛАСТЬ ЭКРАНА !!!
# ================================================================
# 'monitor': Номер монитора (1 - основной, 0 - все мониторы как один)
# 'left', 'top': Координаты верхнего левого угла области относительно монитора
# 'width', 'height': Размеры области захвата
# Пример: захват области шириной 600 и высотой 60 пикселей,
# начиная с отступа 100 пикселей слева и 50 пикселей сверху на основном мониторе.
RECOGNITION_AREA = {'monitor': 1, 'left': 100, 'top': 50, 'width': 600, 'height': 60}

# Порог уверенности для распознавания (0.0 до 1.0).
# Чем выше значение, тем точнее должно быть совпадение шаблона.
# Начни с 0.8 и корректируй по результатам.
RECOGNITION_THRESHOLD = 0.8
# ================================================================
# <<< --------------------------------------- >>>

def _get_file_path():
    """Получает путь к файлу скрипта или исполняемому файлу."""
    return os.path.abspath(".")


def _get_root_path():
    """Получает базовый путь к ресурсам (для PyInstaller или обычного запуска)."""
    base_path = None
    if hasattr(sys, '_MEIPASS'):
      base_path = sys._MEIPASS
    else:
      base_path = _get_file_path()  # Обычный запуск из скрипта
    return base_path if base_path else _get_file_path()

def resource_path(relative_path):
    """ Получаем абсолютный путь к ресурсу, работает для обычного запуска и PyInstaller """
    base_path = _get_root_path()
    return os.path.join(base_path, relative_path)


def validate_heroes():
    """Проверяет, что все герои из heroes_counters существуют в списке heroes."""
    invalid_heroes = []
    # Проверяем ключи словаря counters
    for hero in heroes_counters.keys():
        if hero not in heroes:
            invalid_heroes.append(f"{hero} (как ключ в heroes_counters)")
    # Проверяем значения (списки контрпиков)
    for hero, counters in heroes_counters.items():
        for counter in counters:
            if counter not in heroes:
                invalid_heroes.append(f"{counter} (в списке контрпиков для {hero})")

    if invalid_heroes:
        unique_invalid = sorted(list(set(invalid_heroes))) # Убираем дубликаты и сортируем
        error_message = (f"Ошибка: Найдены герои, не соответствующие списку 'heroes' в heroes_bd.py:\n"
                         f"{chr(10).join(unique_invalid)}") # Используем chr(10) для переноса строки
        print(error_message)
        # Можно раскомментировать, чтобы остановить программу при ошибке
        # raise ValueError(error_message)
    else:
        print("Проверка имен героев в heroes_counters пройдена успешно.")


def check_if_all_elements_in_list(target_list, check_list):
    """Проверяет, что все элементы из check_list присутствуют в target_list."""
    for element in check_list:
        if element not in target_list: return False
    return True


# <<< ДОБАВЛЕНО: Функция захвата области экрана >>>
def capture_screen_area(area: dict):
    """
    Захватывает указанную область экрана с помощью mss.

    Args:
        area (dict): Словарь с ключами 'monitor', 'left', 'top', 'width', 'height'.

    Returns:
        np.array: Изображение в формате OpenCV (BGR) или None в случае ошибки.
    """
    with mss.mss() as sct:
        monitors = sct.monitors
        if not monitors:
            print("[ERROR][CAPTURE] Не удалось получить список мониторов.")
            return None

        # Проверяем номер монитора
        if area['monitor'] >= len(monitors):
             print(f"[ERROR][CAPTURE] Неверный номер монитора: {area['monitor']}. Доступные мониторы: {len(monitors)}")
             # Используем основной монитор (индекс 1), если он есть
             if len(monitors) > 1:
                 target_monitor_index = 1
                 print(f"[WARN][CAPTURE] Используется основной монитор (индекс {target_monitor_index}) как fallback.")
             elif len(monitors) == 1: # Если только один монитор (обычно индекс 0 - весь экран)
                 target_monitor_index = 0 # Или 1, если индекс 0 действительно "все мониторы"
                 print(f"[WARN][CAPTURE] Используется единственный монитор (индекс {target_monitor_index}).")
             else: # Не должно произойти, если monitors не пустой
                 print(f"[ERROR][CAPTURE] Не найдено подходящего монитора.")
                 return None
        else:
            target_monitor_index = area['monitor']

        # Получаем геометрию нужного монитора
        monitor_geometry = monitors[target_monitor_index]

        # Формируем Bounding Box для захвата внутри этого монитора
        # Координаты left/top берутся относительно верхнего левого угла монитора
        bbox = {
            "left": monitor_geometry["left"] + area['left'],
            "top": monitor_geometry["top"] + area['top'],
            "width": area['width'],
            "height": area['height'],
            # "mon": target_monitor_index, # 'mon' больше не используется в grab
        }
        print(f"[CAPTURE] Захват области: Monitor={target_monitor_index}, BBox={bbox}")

        # Захватываем изображение
        try:
          sct_img = sct.grab(bbox)
        except mss.ScreenShotError as e:
          print(f"[ERROR][CAPTURE] Ошибка mss при захвате экрана: {e}")
          return None

        # Конвертируем в numpy массив
        img_np = np.array(sct_img)

        # MSS захватывает в формате BGRA, OpenCV обычно работает с BGR
        # Убираем альфа-канал и получаем BGR
        if img_np.shape[2] == 4:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
        elif img_np.shape[2] == 3:
             img_bgr = img_np # Уже BGR
        else:
             print(f"[ERROR][CAPTURE] Неожиданный формат изображения (каналы: {img_np.shape[2]}).")
             return None
        if len(monitors) < target_monitor_index:
          print(f"[ERROR][CAPTURE] Ошибка индекса при доступе к монитору. Доступно мониторов: {len(monitors)}")
          return None
        print(f"[CAPTURE] Область успешно захвачена. Размер: {img_bgr.shape}")

        debug_path = resource_path("debug_screenshot.png")
        try:
          cv2.imwrite(debug_path, img_bgr)
          print(f"[DEBUG][CAPTURE] Скриншот сохранен в: {debug_path}")
        except Exception as e_write:
          print(f"[ERROR][CAPTURE] Не удалось сохранить отладочный скриншот: {e_write}")
        return img_bgr

# <<< КОНЕЦ Функции захвата >>>