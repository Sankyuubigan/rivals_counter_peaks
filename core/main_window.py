from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QTimer, QRect
from core.images_load import load_hero_templates, get_images_for_mode
from logic import CounterpickLogic
from manager import RecognitionManager

class MainWindow(QWidget):
    def __init__(self):
        print("[LOG] MainWindow.__init__ started")
        super().__init__()
        # Подключаем логику
        self.logic = CounterpickLogic()

        # Инициализируем RecognitionManager
        print("[LOG] MainWindow.__init__ about to create RecognitionManager")
        self.recognition_manager = RecognitionManager(logic=self.logic)

        # Загружаем шаблоны героев (теперь без аргументов)
        self.hero_templates = load_hero_templates()

        # Получаем изображения для режима 'middle'
        self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(
            mode='middle')
        # ... (остальной код класса MainWindow) ...