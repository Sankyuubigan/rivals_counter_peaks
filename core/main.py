# File: core/main.py
import sys
import os
import logging

# Устанавливаем уровень логирования INFO по умолчанию
logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s', datefmt='%H:%M:%S')

# --- Настройка путей ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path: sys.path.insert(0, project_root)
logging.debug(f"Project root added to sys.path: {project_root}") # Оставляем DEBUG для путей
core_dir = os.path.dirname(__file__)
if core_dir not in sys.path: sys.path.insert(0, core_dir)
logging.debug(f"Core directory added to sys.path: {core_dir}")
# --- ---

# Читаем версию из _version.py
app_version = "unknown"
try:
    from _version import __version__ as version_from_file
    app_version = version_from_file
    logging.info(f"[Main] Version successfully read via import: {app_version}")
except ImportError:
    logging.error("[Main] Failed to import from _version.py. Run build script first or check path.")
    app_version = "dev"
except Exception as e_general:
     logging.error(f"[Main] General error reading version: {e_general}")
     app_version = "error"
if app_version in ["unknown", "error"]: # Если чтение не удалось
    logging.warning(f"[Main] Using fallback version 'dev' (read value: {app_version})")
    app_version = "dev"

from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory
import logic
import images_load
import utils
from main_window import MainWindow

if __name__ == "__main__":
    logging.info("[LOG] core/main.py: __main__ block started")

    # Валидация данных
    logging.info("[LOG] Запуск валидации героев...")
    validation_errors = utils.validate_heroes()
    if validation_errors:
        error_msg = "Обнаружены ошибки в данных героев:\n\n" + "\n".join(validation_errors) + "\n\nПриложение может работать некорректно."
        temp_app = QApplication.instance(); temp_app_created = False
        if temp_app is None: temp_app = QApplication([]); temp_app_created = True
        QMessageBox.warning(None, "Ошибка данных", error_msg)
        if temp_app_created: temp_app.quit()
        logging.warning("Ошибки валидации обнаружены, но приложение продолжит работу.")
    else: logging.info("Валидация героев прошла успешно.")

    # Создание QApplication
    logging.info("Создание QApplication...")
    app = QApplication(sys.argv)

    # Проверка прав администратора
    is_admin = False
    try:
        if sys.platform == 'win32': import ctypes; is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        elif sys.platform == 'darwin' or sys.platform.startswith('linux'): is_admin = (os.geteuid() == 0)
    except Exception as e: logging.warning(f"Не удалось проверить права администратора: {e}")
    if not is_admin: logging.warning("Приложение запущено без прав администратора. Глобальные горячие клавиши (keyboard) могут не работать.")
    else: logging.info("Приложение запущено с правами администратора.")

    # Установка стиля
    available_styles = QStyleFactory.keys()
    if "Fusion" in available_styles: app.setStyle("Fusion"); logging.info("Установка стиля Fusion.")
    else: logging.warning(f"Стиль Fusion не доступен. Используется стиль по умолчанию: {QApplication.style().objectName()}")

    # Загрузка ресурсов
    logging.info("Предварительная загрузка ресурсов...")
    try:
        images_load.load_original_images()
        hero_templates = images_load.load_hero_templates()
        if hero_templates is None: raise RuntimeError("Словарь шаблонов не был загружен (None).")
        elif not hero_templates:
             logging.warning("Шаблоны героев не найдены или не загружены, распознавание будет недоступно.")
             QMessageBox.warning(None, "Внимание", "Шаблоны героев не найдены. Функция распознавания будет недоступна.")
        else: logging.info(f"Шаблоны героев загружены ({len(hero_templates)} героев).")
        logging.info("Загрузка ресурсов завершена.")
    except Exception as e:
        logging.error(f"Критическая ошибка при загрузке ресурсов: {e}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось загрузить ресурсы приложения:\n{e}")
        sys.exit(1)

    # Создание экземпляра логики
    logging.info("Создание экземпляра CounterpickLogic...")
    try:
        logic_instance = logic.CounterpickLogic(app_version=app_version)
        logging.info(f"Logic instance created. App version from logic: {logic_instance.APP_VERSION}")
    except Exception as e:
        logging.error(f"Не удалось создать экземпляр CounterpickLogic: {e}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось инициализировать игровую логику:\n{e}")
        sys.exit(1)

    # Создание главного окна
    logging.info("Создание MainWindow...")
    try:
        window = MainWindow(logic_instance, hero_templates if hero_templates else {}, app_version=app_version)
        window.show()
    except Exception as e:
        logging.error(f"Не удалось создать или показать MainWindow: {e}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось инициализировать или показать главное окно:\n{e}")
        sys.exit(1)

    # Запуск главного цикла приложения
    logging.info("Запуск главного цикла приложения (app.exec())...")
    exit_code = app.exec()
    logging.info(f"--- Приложение завершено с кодом: {exit_code} ---")
    sys.exit(exit_code)
