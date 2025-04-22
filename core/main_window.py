from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon

from logic import CounterpickLogic
from images_load import load_hero_templates, load_default_pixmap
from recognition import RecognitionManager


class MainWindow(QMainWindow):
    def __init__(self, logic: CounterpickLogic, hero_templates):
        """
        Инициализирует главное окно приложения.

        Args:
            logic: Экземпляр класса CounterpickLogic.
            hero_templates (dict): Шаблоны для распознавания героев.
        """
        print("[LOG] MainWindow.__init__ started")
        super().__init__()
        self.logic = logic  # экземпляр логики, инициализированный в main.py
        self.setWindowTitle("Rivals Counter-Peaks")  # Заголовок окна
        self.setWindowIcon(QIcon(load_default_pixmap()))

        # Загрузка шаблонов
        self.hero_templates = load_hero_templates()
        print("[LOG] MainWindow.__init__ load_hero_templates() finished")



        # Создаем RecognitionManager, передавая ему экземпляр логики
        print(f"[LOG] MainWindow.__init__ - About to create RecognitionManager from file {RecognitionManager.__module__}")
        print("[LOG] MainWindow.__init__ about to create RecognitionManager")
        self.rec_manager = RecognitionManager(main_window = self, logic=self.logic, hero_templates=hero_templates)
        print(f"[LOG] MainWindow.__init__ - RecognitionManager created: {self.rec_manager}")
        
        # Создание и настройка интерфейса
        #self.create_main_ui()
        #self.update_ui()
        print("[LOG] MainWindow.__init__ finished")