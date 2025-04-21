# File: main.py
from PySide6.QtWidgets import QApplication
import sys
from gui import create_gui
from utils import validate_heroes
# <<< ИЗМЕНЕНИЕ: Импорты разделены >>>
from images_load import load_hero_templates, load_original_images
# <<< ----------------------------- >>>


if __name__ == "__main__":
    # <<< ИЗМЕНЕНИЕ: Добавлена проверка перед reconfigure >>>
    # Отключаем буферизацию stdout и stderr для немедленного вывода print(),
    # только если эти потоки существуют (т.е. запуск не в --windowed режиме без консоли)
    if sys.stdout:
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except AttributeError:
             # В некоторых средах reconfigure может отсутствовать, игнорируем
             print("[WARN] sys.stdout.reconfigure не поддерживается.")
             pass
    if sys.stderr:
        try:
            sys.stderr.reconfigure(line_buffering=True)
        except AttributeError:
             print("[WARN] sys.stderr.reconfigure не поддерживается.")
             pass
    # <<< КОНЕЦ ИЗМЕНЕНИЯ >>>

    print("--- Запуск приложения ---")
    validate_heroes()

    # Создаем QApplication ПЕРЕД загрузкой ресурсов Qt
    print("Создание QApplication...")
    app = QApplication(sys.argv)
    # Применяем стиль Fusion (опционально)
    try:
        app.setStyle("Fusion")
    except Exception as e:
        print(f"[WARN] Не удалось установить стиль Fusion: {e}")

    # Загрузка ресурсов ПОСЛЕ QApplication
    print("Предварительная загрузка ресурсов...")
    try:
        load_original_images() # Загружаем QPixmap
        load_hero_templates() # Загружаем шаблоны OpenCV
        print("Загрузка ресурсов завершена.")
    except Exception as e:
         print(f"[ERROR] Критическая ошибка при загрузке ресурсов: {e}")
         # Попытка показать сообщение, если возможно
         try:
             from PySide6.QtWidgets import QMessageBox
             QMessageBox.critical(None, "Критическая ошибка", f"Не удалось загрузить ресурсы:\n{e}")
         except: pass
         sys.exit(1) # Выход

    # Создание и запуск GUI
    print("Создание MainWindow...")
    try:
        window = create_gui()
        print("Отображение MainWindow...")
        window.show()
        print("Запуск главного цикла событий...")
        exit_code = app.exec()
        print(f"--- Приложение завершено с кодом: {exit_code} ---")
        sys.exit(exit_code)
    except Exception as e:
        print(f"[ERROR] Критическая ошибка при создании или запуске GUI: {e}")
        # Попытка показать сообщение об ошибке
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Критическая ошибка", f"Не удалось запустить приложение:\n{e}")
        except: pass
        sys.exit(1)