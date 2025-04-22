
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

print(f"[LOG] Пытаюсь импортировать PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    print("[LOG] if __name__ == '__main__': started")
    print("[LOG] main() started")
    print("[LOG] main() enter")

    logic = CounterpickLogic()
    print("--- Запуск приложения ---") 
    validate_heroes()
    print("Создание QApplication...")
    app = QApplication(sys.argv)
    
    
    
    try: 
        app.setStyle("Fusion")        
    except Exception as e:        
        print(f"[WARN] Не удалось установить стиль Fusion: {e}")    

    print("[LOG] main() - About to load_hero_templates()")
    
    hero_templates = load_hero_templates()
    print("Шаблоны загружены.")
    print(f"[LOG] load_hero_templates() about to return result: {locals()}")
    
    
    print("[LOG] main() - About to load_original_images()")
    
    load_original_images()
    print("Загрузка ресурсов завершена.")
    
    print("[LOG] main() - About to create MainWindow")
    print(f"[LOG] main() - About to create MainWindow with hero_templates: {hero_templates}")
    try:
        window = MainWindow(logic, hero_templates)
        print("[LOG] main() - MainWindow created")
        print("Отображение MainWindow...")
        window.show()
        print("Запуск главного цикла событий...")
        exit_code = app.exec()
        print(f"--- Приложение завершено с кодом: {exit_code} ---")
        sys.exit(exit_code)
    except Exception as e:
        print(f"[ERROR] Критическая ошибка при создании или запуске GUI: {e}\n{type(e)}")
        print(f"[LOG] Пытаюсь импортировать PySide6.QtWidgets")
        QMessageBox.critical(None, "Критическая ошибка", f"Не удалось запустить приложение:\n{e}")
        sys.exit(1)    

    subprocess.run([sys.executable, '-m', 'pip', 'freeze', '>', 'requirements.txt'], check=True)
    

