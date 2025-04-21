from PySide6.QtWidgets import QApplication
import sys

from settings import LOGGING_ENABLED
from core.gui import MainWindow
from core.utils import validate_heroes
from core.hotkeys import Hotkeys
from core.win_api import WinApiManager
from core.images_load import load_hero_templates, load_original_images

class MainWindow(MainWindow):
    def __init__(self):
        super().__init__()

    def _setup_hotkeys(self):
        """Настраивает горячие клавиши."""
        print("Настройка горячих клавиш...")
        self.hotkeys = Hotkeys()
        self.hotkeys.register_hotkeys(self.mode_manager, self.ui_update, self.winapi)



    def create_gui(self):
        """Создает и настраивает GUI."""
        self._setup_ui()
        self._setup_hotkeys()
def configure_output_streams():
    """Configures stdout and stderr for line buffering if possible."""
    if LOGGING_ENABLED:
        if sys.stdout:
            try:
                sys.stdout.reconfigure(line_buffering=True)
            except AttributeError:
                 # In some environments reconfigure might be missing, ignore
                 print("[WARN] sys.stdout.reconfigure is not supported.")
                 pass
        if sys.stderr:
            try:
                sys.stderr.reconfigure(line_buffering=True)
            except AttributeError:
                 print("[WARN] sys.stderr.reconfigure is not supported.")
                 pass

if __name__ == "__main__":
    
    #configure streams
    configure_output_streams()
    

    
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
        window = MainWindow()
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
