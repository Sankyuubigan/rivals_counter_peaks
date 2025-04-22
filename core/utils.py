# File: core/utils.py
# Импорты остаются те же
import mss
import mss.tools
import numpy as np
import cv2
import os
import sys
# Импортируем данные о героях напрямую, так как utils используется в main перед созданием logic
from heroes_bd import heroes_counters, heroes

# Константы для распознавания (оставляем как есть, но пользователь должен их настроить)
RECOGNITION_AREA = {'monitor': 1, 'left': 100, 'top': 50, 'width': 600, 'height': 60}
RECOGNITION_THRESHOLD = 0.8

# --- Функции определения путей ---
def _get_root_path():
    """Получает базовый путь к ресурсам (для PyInstaller или обычного запуска)."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        # Исправлено: используем __file__ для определения пути utils.py
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return base_path

def resource_path(relative_path):
    """ Получаем абсолютный путь к ресурсу, работает для обычного запуска и PyInstaller """
    base_path = _get_root_path()
    relative_path_corrected = relative_path.replace('/', os.sep).replace('\\', os.sep)
    return os.path.join(base_path, relative_path_corrected)
# --- ---

def validate_heroes():
    """
    Проверяет, что все герои из heroes_counters существуют в списке heroes.
    Возвращает список невалидных имен или пустой список.
    """
    print("[VALIDATION] Запуск проверки имен героев...")
    invalid_heroes = []
    heroes_set = set(heroes)

    for hero in heroes_counters.keys():
        if hero not in heroes_set:
            invalid_heroes.append(f"{hero} (как ключ в heroes_counters)")
    for hero, counters in heroes_counters.items():
        if hero not in heroes_set: continue # Ошибка уже добавлена
        for counter in counters:
            if counter not in heroes_set:
                invalid_heroes.append(f"{counter} (в списке контрпиков для {hero})")

    unique_invalid = sorted(list(set(invalid_heroes)))

    if unique_invalid:
        error_message = (f"[VALIDATION ERROR] Найдены герои, не соответствующие списку 'heroes' в heroes_bd.py:\n"
                         f"{chr(10).join(unique_invalid)}")
        print(error_message)
        return unique_invalid # Возвращаем список ошибок
    else:
        print("[VALIDATION] Проверка имен героев в heroes_counters пройдена успешно.")
        return [] # Возвращаем пустой список при успехе

def check_if_all_elements_in_list(target_list, check_list):
    """Проверяет, что все элементы из check_list присутствуют в target_list."""
    return set(check_list).issubset(set(target_list))


def capture_screen_area(area: dict):
    """
    Захватывает указанную область экрана с помощью mss.
    Возвращает изображение в формате OpenCV (BGR) или None.
    """
    print(f"[CAPTURE] Попытка захвата области: {area}")
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            if not monitors:
                print("[ERROR][CAPTURE] Не удалось получить список мониторов.")
                return None

            target_monitor_index = area.get('monitor', 1)

            if target_monitor_index >= len(monitors):
                 print(f"[ERROR][CAPTURE] Неверный номер монитора: {target_monitor_index}. Доступно: {len(monitors)}")
                 if len(monitors) > 1: target_monitor_index = 1; print(f"[WARN][CAPTURE] Используется основной монитор (индекс {target_monitor_index}) как fallback.")
                 elif len(monitors) >= 1: target_monitor_index = 1 if len(monitors) > 1 else 0; print(f"[WARN][CAPTURE] Используется монитор с индексом {target_monitor_index}.")
                 else: print(f"[ERROR][CAPTURE] Не найдено подходящего монитора."); return None

            try:
                 monitor_geometry = monitors[target_monitor_index]
            except IndexError:
                 print(f"[ERROR][CAPTURE] Ошибка индекса при доступе к монитору {target_monitor_index}. Доступно: {monitors}")
                 return None

            bbox = {
                "left": monitor_geometry["left"] + area.get('left', 0),
                "top": monitor_geometry["top"] + area.get('top', 0),
                "width": area.get('width', 100),
                "height": area.get('height', 100),
            }
            if bbox['width'] <= 0 or bbox['height'] <= 0:
                print(f"[ERROR][CAPTURE] Ширина или высота области захвата не положительны: {bbox}")
                return None

            print(f"[CAPTURE] Захват области: Monitor={target_monitor_index}, BBox={bbox}")

            sct_img = sct.grab(bbox)
            img_np = np.array(sct_img)

            if img_np.size == 0:
                 print("[ERROR][CAPTURE] Захвачено пустое изображение.")
                 return None

            if img_np.shape[2] == 4: img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
            elif img_np.shape[2] == 3: img_bgr = img_np
            else: print(f"[ERROR][CAPTURE] Неожиданный формат изображения (каналы: {img_np.shape[2]})."); return None

            print(f"[CAPTURE] Область успешно захвачена. Размер: {img_bgr.shape}")

            # --- Отладка: Сохранение скриншота ---
            # try:
            #     debug_path = resource_path("debug_screenshot.png")
            #     cv2.imwrite(debug_path, img_bgr)
            #     print(f"[DEBUG][CAPTURE] Скриншот сохранен в: {debug_path}")
            # except Exception as e_write:
            #     print(f"[ERROR][CAPTURE] Не удалось сохранить отладочный скриншот: {e_write}")
            # --- ---

            return img_bgr

    except mss.ScreenShotError as e:
        print(f"[ERROR][CAPTURE] Ошибка mss при захвате экрана: {e}")
        return None
    except Exception as e:
        print(f"[ERROR][CAPTURE] Неожиданная ошибка при захвате или обработке экрана: {e}")
        import traceback
        traceback.print_exc()
        return None