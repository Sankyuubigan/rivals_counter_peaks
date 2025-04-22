# File: core/main.py
import sys
import os

# --- Настройка путей ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f"Project root added to sys.path: {project_root}")
# Добавляем папку core в sys.path, чтобы импорты работали и из корня, и внутри core
core_dir = os.path.dirname(__file__)
if core_dir not in sys.path:
     sys.path.insert(0, core_dir)
print(f"Core directory added to sys.path: {core_dir}")
# --- ---

from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory
# <<< ИСПРАВЛЕНО: Используем абсолютные импорты от корня или от core >>>
from logic import CounterpickLogic
from images_load import load_hero_templates, load_original_images
from main_window import MainWindow
from utils import validate_heroes
# <<< ---------------------------------------------------------------- >>>

if __name__ == "__main__":
    print("[LOG] core/main.py: __main__ block started")

    # 1. Валидация данных
    print("[LOG] Запуск валидации героев...")
    validation_errors = validate_heroes()
    if validation_errors:
        error_msg = "Обнаружены ошибки в данных героев:\n\n" + "\n".join(validation_errors) + "\n\nПриложение может работать некорректно."
        temp_app = QApplication.instance()
        if temp_app is None:
            temp_app = QApplication([])
            temp_app_created = True
        else:
            temp_app_created = False
        QMessageBox.warning(None, "Ошибка данных", error_msg)
        if temp_app_created:
             temp_app.quit()
        print("[WARN] Ошибки валидации обнаружены, но приложение продолжит работу.")
    else:
        print("[LOG] Валидация героев прошла успешно.")

    # 2. Создание QApplication
    print("[LOG] Создание QApplication...")
    app = QApplication(sys.argv)

    # 3. Установка стиля
    available_styles = QStyleFactory.keys()
    if "Fusion" in available_styles:
        print("[LOG] Установка стиля Fusion.")
        app.setStyle("Fusion")
    else:
        print(f"[WARN] Стиль Fusion не доступен. Используется стиль по умолчанию: {QApplication.style().objectName()}")

    # 4. Загрузка ресурсов
    print("[LOG] Предварительная загрузка ресурсов...")
    try:
        load_original_images()
        hero_templates = load_hero_templates()
        if hero_templates is None:
             raise RuntimeError("Словарь шаблонов не был загружен (None).")
        elif not hero_templates:
             print("[WARN] Шаблоны героев не найдены или не загружены, распознавание будет недоступно.")
             QMessageBox.warning(None, "Внимание", "Шаблоны героев не найдены. Функция распознавания будет недоступна.")
        else:
            print(f"[LOG] Шаблоны героев загружены ({len(hero_templates)} героев).")
        print("[LOG] Загрузка ресурсов завершена.")
    except Exception as e:
        print(f"[ERROR] Критическая ошибка при загрузке ресурсов: {e}")
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось загрузить ресурсы приложения:\n{e}")
        sys.exit(1)

    # 5. Создание экземпляра логики
    print("[LOG] Создание экземпляра CounterpickLogic...")
    try:
        logic = CounterpickLogic()
    except Exception as e:
        print(f"[ERROR] Не удалось создать экземпляр CounterpickLogic: {e}")
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось инициализировать игровую логику:\n{e}")
        sys.exit(1)

    # 6. Создание главного окна
    print("[LOG] Создание MainWindow...")
    try:
        window = MainWindow(logic, hero_templates if hero_templates else {})
        window.show()
    except Exception as e:
        print(f"[ERROR] Не удалось создать или показать MainWindow: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось инициализировать или показать главное окно:\n{e}")
        sys.exit(1)

    # 7. Запуск главного цикла приложения
    print("[LOG] Запуск главного цикла приложения (app.exec())...")
    exit_code = app.exec()
    print(f"[LOG] --- Приложение завершено с кодом: {exit_code} ---")
    sys.exit(exit_code)