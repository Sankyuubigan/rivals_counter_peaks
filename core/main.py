
import sys
import os


# Добавление пути к корневой папке проекта в sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
print(f"sys.path: {sys.path}")
print("[LOG] core/main.py started")

print(f"[LOG] Пытаюсь импортировать PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication

from core.main_window import MainWindow
from core.utils import validate_heroes
from core.images_load import load_original_images


if __name__ == "__main__":
    print("[LOG] if __name__ == '__main__': started")
    print("[LOG] main() started")


    print("--- Запуск приложения ---")


    validate_heroes()

    # Создание QApplication
    print("Создание QApplication...")
    app = QApplication(sys.argv)
    # Применяем стиль Fusion (опционально)
    try:
        app.setStyle("Fusion")
    except Exception as e:
        print(f"[WARN] Не удалось установить стиль Fusion: {e}")
        
    # Загрузка ресурсов
    print("[LOG] main() - About to load_original_images()")
    try:
        load_original_images()  # Загружаем QPixmap
        print("Загрузка ресурсов завершена.")
    except Exception as e:
        print(f"[ERROR] Критическая ошибка при загрузке ресурсов: {e}")
        # Попытка показать сообщение, если возможно
        try:
            print(f"[LOG] Пытаюсь импортировать PySide6.QtWidgets")
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(None, "Критическая ошибка", f"Не удалось загрузить ресурсы:\n{e}")
        except:
            pass
        sys.exit(1)  # Выход

    # Создание MainWindow
    print("[LOG] main() - About to create MainWindow")

    try:
        window = MainWindow()
        print("[LOG] main() - MainWindow created")
        print("Отображение MainWindow...")

        window.show()
        print("Запуск главного цикла событий...")
        exit_code = app.exec()
        print(f"--- Приложение завершено с кодом: {exit_code} ---")
        sys.exit(exit_code)
    except Exception as e:
        print(f"[ERROR] Критическая ошибка при создании или запуске GUI: {e}\n{type(e)}")
        try:
            print(f"[LOG] Пытаюсь импортировать PySide6.QtWidgets")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Критическая ошибка", f"Не удалось запустить приложение:\n{e}")
        except:
            pass
        sys.exit(1)

