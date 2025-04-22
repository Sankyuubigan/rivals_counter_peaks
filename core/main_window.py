from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QHBoxLayout, QPushButton
from PySide6.QtGui import QPixmap, QFont, QColor, QPalette, QIcon
from PySide6.QtCore import Qt, QSize, QTimer

from logic import CounterpickLogic
from images_load import get_images_for_mode, load_original_images, load_hero_templates, load_default_pixmap
from recognition import RecognitionManager
import time
import sys
import os
from heroes_bd import heroes


class MainWindow(QMainWindow):
    def __init__(self, logic: CounterpickLogic):
        """
        Инициализирует главное окно приложения.

        Args:
            logic: Экземпляр класса CounterpickLogic.
        """
        super().__init__()
        self.logic = logic  # экземпляр логики, инициализированный в main.py
        self.setWindowTitle("Rivals Counter-Peaks")  # Заголовок окна
        self.setWindowIcon(QIcon(load_default_pixmap()))

        # Загрузка шаблонов
        self.hero_templates = load_hero_templates()



        # Создаем RecognitionManager, передавая ему экземпляр логики
        print("[LOG] MainWindow.__init__ about to create RecognitionManager")
        self.rec_manager = RecognitionManager(logic=self.logic)
        
        # Создание и настройка интерфейса
        self.create_main_ui()
        self.update_ui()