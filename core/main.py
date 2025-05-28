# File: core/main.py
import sys
import os # os уже должен быть импортирован для project_root ниже

# --- ОТЛАДОЧНЫЙ БЛОК: ПРОВЕРКА ПУТЕЙ ---
print("--- [DEBUG_PYINSTALLER] Запуск отладки путей ---")
print(f"--- [DEBUG_PYINSTALLER] sys.executable: {sys.executable}")
print(f"--- [DEBUG_PYINSTALLER] sys.argv: {sys.argv}")
print(f"--- [DEBUG_PYINSTALLER] os.getcwd(): {os.getcwd()}")

print("--- [DEBUG_PYINSTALLER] sys.path ---")
for i, p in enumerate(sys.path):
    print(f"    [{i}] {p}")

# Проверяем, куда указывает _MEIPASS, если он есть (для однофайловой сборки)
if hasattr(sys, '_MEIPASS'):
    print(f"--- [DEBUG_PYINSTALLER] sys._MEIPASS: {sys._MEIPASS}")
    # Попытаемся вывести содержимое _MEIPASS/transformers/models, если возможно
    expected_transformers_models_path = os.path.join(sys._MEIPASS, 'transformers', 'models')
    print(f"--- [DEBUG_PYINSTALLER] Ожидаемый путь к transformers/models в _MEIPASS: {expected_transformers_models_path}")
    if os.path.isdir(expected_transformers_models_path):
        print(f"    Содержимое {expected_transformers_models_path} (первые 10 элементов):")
        try:
            for entry_idx, entry_name in enumerate(os.listdir(expected_transformers_models_path)):
                if entry_idx < 10:
                    print(f"        - {entry_name}")
                else:
                    print(f"        ... и еще {len(os.listdir(expected_transformers_models_path)) - 10} элементов.")
                    break
        except Exception as e_lsdir:
            print(f"        Ошибка при листинге директории: {e_lsdir}")
    else:
        print(f"    Директория {expected_transformers_models_path} НЕ НАЙДЕНА.")
else:
    print("--- [DEBUG_PYINSTALLER] sys._MEIPASS не определен (вероятно, сборка в папку или запуск не из EXE).")

# Попытка посмотреть, что видит importlib.metadata
try:
    import importlib.metadata
    print("--- [DEBUG_PYINSTALLER] importlib.metadata проверки ---")
    
    packages_to_check_metadata = ["transformers", "tqdm", "regex", "requests", "packaging", "filelock", "safetensors", "pyyaml"]
    for pkg_name in packages_to_check_metadata:
        try:
            dist = importlib.metadata.distribution(pkg_name)
            print(f"    Метаданные для '{pkg_name}' НАЙДЕНЫ. Версия: {dist.version}. Расположение: {dist.locate_file('')}")
            # Попробуем вывести некоторые файлы из метаданных, если они есть
            # if hasattr(dist, 'files') and dist.files:
            #     print(f"        Файлы (первые 3): {[str(f)[:100] for f in dist.files[:3]]}")
        except importlib.metadata.PackageNotFoundError:
            print(f"    Метаданные для '{pkg_name}' НЕ НАЙДЕНЫ.")
        except Exception as e_meta:
            print(f"    Ошибка при получении метаданных для '{pkg_name}': {e_meta}")
            
except ImportError:
    print("--- [DEBUG_PYINSTALLER] importlib.metadata не доступен.")
except Exception as e_outer_meta:
    print(f"--- [DEBUG_PYINSTALLER] Ошибка при работе с importlib.metadata: {e_outer_meta}")

print("--- [DEBUG_PYINSTALLER] Завершение отладки путей ---")
# --- КОНЕЦ ОТЛАДОЧНОГО БЛОКА ---


# Ваш остальной код начинается здесь
import logging # logging лучше импортировать до его первого использования
import datetime
import time 

# Конфигурация логирования (перенесена выше, чтобы логи отладки тоже попадали)
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s', 
                    datefmt='%H:%M:%S')
logging.info("[Main] Начало работы main.py (после отладочного блока)")


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path: sys.path.insert(0, project_root)
core_dir = os.path.dirname(__file__)
if core_dir not in sys.path: sys.path.insert(0, core_dir)

try:
    now = datetime.datetime.now()
    app_version_display = f"{str(now.year)[2:]}.{now.month:02d}.{now.day:02d}"
    logging.info(f"[Main] Application display version set to: {app_version_display} (generated from date)")
except Exception as e_ver:
    logging.error(f"[Main] Error generating display version: {e_ver}. Using 'dev'.")
    app_version_display = "dev"

from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory
import logic
import images_load 
import utils
from main_window import MainWindow # Этот импорт вызовет ошибку, если transformers не найдет свои файлы

if __name__ == "__main__":
    logging.info("[LOG] core/main.py: __main__ block started")

    app = QApplication.instance()
    if app is None:
        logging.info("Создание нового QApplication...")
        app = QApplication(sys.argv)
        app_created_now = True
    else:
        logging.info("Использование существующего QApplication...")
        app_created_now = False 

    app.setQuitOnLastWindowClosed(False) 
    logging.info(f"QApplication.quitOnLastWindowClosed set to {app.quitOnLastWindowClosed()}")


    logging.info("[LOG] Запуск валидации героев...")
    validation_errors = utils.validate_heroes()
    if validation_errors:
        error_msg = "Обнаружены ошибки в данных героев:\n\n" + "\n".join(validation_errors) + "\n\nПриложение может работать некорректно."
        QMessageBox.warning(None, "Ошибка данных", error_msg)
        logging.warning("Ошибки валидации обнаружены, но приложение продолжит работу.")
    else:
        logging.info("Валидация героев прошла успешно.")

    is_admin = False
    try:
        if sys.platform == 'win32': import ctypes; is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        elif sys.platform == 'darwin' or sys.platform.startswith('linux'): is_admin = (os.geteuid() == 0)
    except Exception as e: logging.warning(f"Не удалось проверить права администратора: {e}")
    if not is_admin: logging.warning("Приложение запущено без прав администратора. Глобальные горячие клавиши (keyboard) могут не работать.")
    else: logging.info("Приложение запущено с правами администратора.")

    logging.info(f"Используется стиль по умолчанию: {app.style().objectName()}")


    logging.info("Предварительная загрузка ресурсов...")
    hero_templates = {} 
    try:
        images_load.load_original_images()
        hero_templates = images_load.load_hero_templates_cv2() 
        
        if not hero_templates: 
             logging.warning("Шаблоны героев (CV2) не найдены или не загружены. Распознавание AKAZE в AdvancedRecognition может быть недоступно или ограничено.")
        else: 
            logging.info(f"Шаблоны героев (CV2) загружены ({len(hero_templates)} героев).")
        logging.info("Загрузка ресурсов завершена.")
    except Exception as e:
        logging.critical(f"Критическая ошибка при загрузке ресурсов: {e}", exc_info=True)
        if app_created_now: app.quit() 
        sys.exit(1)

    logging.info("Создание экземпляра CounterpickLogic...")
    try:
        logic_instance = logic.CounterpickLogic(app_version=app_version_display)
        logging.info(f"Logic instance created. App version from logic: {logic_instance.APP_VERSION}")
    except Exception as e:
        logging.error(f"Не удалось создать экземпляр CounterpickLogic: {e}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось инициализировать игровую логику:\n{e}")
        if app_created_now: app.quit()
        sys.exit(1)

    logging.info("Создание MainWindow...")
    window = None 
    try:
        window = MainWindow(logic_instance, hero_templates, app_version=app_version_display)
        logging.info("MainWindow instance created. Calling show()...")
        window.show()
        logging.info("MainWindow.show() called.")
        if window.isVisible():
            logging.info("Окно стало видимым после вызова show().")
            win_id = window.winId()
            logging.info(f"Window ID: {win_id}")
            if win_id == 0:
                logging.error("Window ID is 0, окно не было создано корректно на уровне ОС!")
        else:
            logging.error("Окно НЕ стало видимым после вызова show()!")

    except Exception as e:
        logging.error(f"Не удалось создать или показать MainWindow: {e}", exc_info=True)
        # Отладочный вывод перед падением, если ошибка происходит до инициализации логирования в файл
        print(f"CRITICAL ERROR during MainWindow creation/show: {e}") 
        # QMessageBox.critical(None, "Критическая ошибка", f"Не удалось инициализировать или показать главное окно:\n{e}")
        if app_created_now: app.quit()
        sys.exit(1)
    
    if window is None:
        logging.critical("Экземпляр MainWindow не был создан. Выход.")
        print("CRITICAL ERROR: MainWindow instance is None. Exiting.")
        sys.exit(1)

    logging.info("Запуск главного цикла приложения (app.exec())...")
    exit_code = 0
    try:
        exit_code = app.exec()
    except SystemExit as e:
        logging.info(f"Перехвачено SystemExit в app.exec(): {e}")
        exit_code = e.code if isinstance(e.code, int) else 1
    except Exception as e:
        logging.critical(f"Критическая ошибка во время app.exec(): {e}", exc_info=True)
        print(f"CRITICAL ERROR during app.exec(): {e}")
        exit_code = 1 
    finally:
        logging.info(f"--- Приложение завершено с кодом: {exit_code} (quitOnLastWindowClosed={app.quitOnLastWindowClosed()}) ---")
        print(f"--- Application finished with code: {exit_code} ---")
        sys.exit(exit_code)
