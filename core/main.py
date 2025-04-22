
import sys
import importlib
importlib.invalidate_caches()
import os
from logic import CounterpickLogic
from core.images_load import load_hero_templates, load_original_images
from PySide6.QtWidgets import QApplication, QMessageBox
from core.main_window import MainWindow
from core.utils import validate_heroes


import subprocess

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
print(f"sys.path: {sys.path}")
print("[LOG] core/main.py started")
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    print("[LOG] if __name__ == '__main__': started")
    print("[LOG] main() started")
    print("[LOG] main() enter")
    
    print("[LOG] Проверка валидации героев...")
    if not validate_heroes():
        print("[ERROR] Ошибка валидации героев. ")
        # sys.exit(1)
    else:
        print("[LOG] Валидация героев прошла успешно.")

    print("Создание QApplication...")
    app = QApplication(sys.argv)

    # Проверяем доступность стиля Fusion перед попыткой его установить
    available_styles = QApplication.style()
    if "Fusion" == available_styles.name():
        print("[LOG] Стиль Fusion доступен. Устанавливаем.")
        app.setStyle("Fusion")
    else:
        print(f"[WARN] Стиль Fusion не доступен. Используется стиль по умолчанию.")

    print("[LOG] main() - Creating WinApiManager and ModeManager")

    print("[LOG] Создание экземпляра CounterpickLogic...")
    logic = CounterpickLogic()
    if not logic:
        print("[ERROR] Не удалось создать экземпляр CounterpickLogic.")
        QMessageBox.critical(None, "Критическая ошибка", "Не удалось инициализировать игровую логику.")
        sys.exit(1)

    print("[LOG] main() - About to load_hero_templates()")
    hero_templates = load_hero_templates()
    if not hero_templates:
        print("[ERROR] Не удалось загрузить шаблоны героев.")
        QMessageBox.critical(None, "Критическая ошибка", "Не удалось загрузить шаблоны героев.")
        sys.exit(1)
    else:
        print("[LOG] Шаблоны героев успешно загружены.")

    load_original_images() # Оригиналы загружаются без проверок, заглушки вместо ошибок
    print("[LOG] Загрузка ресурсов завершена.")

    print("[LOG] main() - About to create MainWindow")
    window = MainWindow(logic, hero_templates)
    if not window:
        print("[ERROR] Не удалось создать экземпляр MainWindow.")
        QMessageBox.critical(None, "Критическая ошибка", "Не удалось инициализировать главное окно.")
        sys.exit(1)
    window.show()
    exit_code = app.exec()
    print(f"[LOG] --- Приложение завершено с кодом: {exit_code} ---")
    sys.exit(exit_code)

    subprocess.run([sys.executable, '-m', 'pip', 'freeze', '>', 'requirements.txt'], check=True)

