# File: core/main.py
import sys
import os
import logging
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s', datefmt='%H:%M:%S')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path: sys.path.insert(0, project_root)
core_dir = os.path.dirname(__file__)
if core_dir not in sys.path: sys.path.insert(0, core_dir)

try:
    now = datetime.datetime.now()
    app_version_display = f"{now.day:02d}.{now.month:02d}.{str(now.year)[2:]}"
    logging.info(f"[Main] Application display version set to: {app_version_display} (generated from date)")
except Exception as e_ver:
    logging.error(f"[Main] Error generating display version: {e_ver}. Using 'dev'.")
    app_version_display = "dev"

from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory
import logic
import images_load
import utils
from main_window import MainWindow

if __name__ == "__main__":
    logging.info("[LOG] core/main.py: __main__ block started")

    # Создаем QApplication ВНАЧАЛЕ, если его еще нет
    app = QApplication.instance()
    if app is None:
        logging.info("Создание нового QApplication...")
        app = QApplication(sys.argv)
        app_created_now = True
    else:
        logging.info("Использование существующего QApplication...")
        app_created_now = False # Флаг, чтобы не выходить из приложения, если оно было создано не здесь

    logging.info("[LOG] Запуск валидации героев...")
    validation_errors = utils.validate_heroes()
    if validation_errors:
        error_msg = "Обнаружены ошибки в данных героев:\n\n" + "\n".join(validation_errors) + "\n\nПриложение может работать некорректно."
        QMessageBox.warning(None, "Ошибка данных", error_msg)
        logging.warning("Ошибки валидации обнаружены, но приложение продолжит работу.")
        # Не выходим из приложения здесь, если оно уже было создано
    else:
        logging.info("Валидация героев прошла успешно.")

    # Остальная часть __main__ без изменений в создании app
    is_admin = False
    try:
        if sys.platform == 'win32': import ctypes; is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        elif sys.platform == 'darwin' or sys.platform.startswith('linux'): is_admin = (os.geteuid() == 0)
    except Exception as e: logging.warning(f"Не удалось проверить права администратора: {e}")
    if not is_admin: logging.warning("Приложение запущено без прав администратора. Глобальные горячие клавиши (keyboard) могут не работать.")
    else: logging.info("Приложение запущено с правами администратора.")

    available_styles = QStyleFactory.keys()
    if "Fusion" in available_styles: app.setStyle("Fusion"); logging.info("Установка стиля Fusion.")
    else: logging.warning(f"Стиль Fusion не доступен. Используется стиль по умолчанию: {app.style().objectName()}") # Используем app.style()

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
        if app_created_now: app.quit() # Выходим, только если app создали здесь и сейчас
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
    try:
        window = MainWindow(logic_instance, hero_templates if hero_templates else {}, app_version=app_version_display)
        window.show()
    except Exception as e:
        logging.error(f"Не удалось создать или показать MainWindow: {e}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось инициализировать или показать главное окно:\n{e}")
        if app_created_now: app.quit()
        sys.exit(1)

    logging.info("Запуск главного цикла приложения (app.exec())...")
    exit_code = app.exec()
    logging.info(f"--- Приложение завершено с кодом: {exit_code} ---")
    sys.exit(exit_code)
