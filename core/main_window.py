from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QWidget
from PySide6.QtGui import QIcon
from core.translations import get_text

from core.logic import CounterpickLogic
from core.mode import ModeManager
from core.win_api import WinApiManager
from core.images_load import load_hero_templates, load_default_pixmap
from core.recognition import RecognitionManager

from core.top_panel import create_top_panel
from core.left_panel import create_left_panel
from core.right_panel import create_right_panel
from core.ui_update import UiUpdateManager



class MainWindow(QMainWindow):
    @property
    def _is_win_topmost(self):
        return self.win_api_manager.is_win_topmost

    def switch_mode(self):
        print("switch_mode callback")

    def set_topmost_winapi(self):
        self.win_api_manager.set_topmost_winapi(not self.win_api_manager.is_win_topmost)
        
    def __init__(self, logic: CounterpickLogic, hero_templates):
        """
        Инициализирует главное окно приложения.

        Args:
            logic: Экземпляр класса CounterpickLogic.
            hero_templates (dict): Шаблоны для распознавания героев.
        """
        print(f"[LOG] MainWindow.__init__ started with hero_templates: {len(hero_templates)}")
        super().__init__()
        
        self.get_text = get_text
        
        self.logic = logic  # экземпляр логики, инициализированный в main.py
        self.setWindowTitle("Rivals Counter-Peaks")  # Заголовок окна
        self.setWindowIcon(QIcon(load_default_pixmap()))

        self.hero_templates = hero_templates
        self.mode_manager = ModeManager(self)
        print("[LOG] MainWindow.__init__ load_hero_templates() finished")

        self.win_api_manager = WinApiManager(self)
        

        # Создаем RecognitionManager, передавая ему экземпляр логики
        # print(f"[LOG] MainWindow.__init__ - About to create RecognitionManager with: logic={self.logic}, hero_templates={self.hero_templates}")
        print(f"[LOG] MainWindow.__init__ - About to create RecognitionManager from file {RecognitionManager.__module__}")
        print("[LOG] MainWindow.__init__ about to create RecognitionManager")

        self.rec_manager = RecognitionManager(main_window=self,logic=self.logic, win_api_manager = self.win_api_manager)
        self.ui_update_manager = UiUpdateManager(self, self.rec_manager.win_api_manager, self)
        print(f"[LOG] MainWindow.__init__ - RecognitionManager created: {self.rec_manager}")
        
        self.create_main_ui()
        self.ui_update_manager.update_ui()
        print("[LOG] MainWindow.__init__ finished")

    def create_main_ui(self):
        """
        Создает и настраивает основной интерфейс приложения.
        """
        print("[LOG] MainWindow.create_main_ui() started")
        # Создаем панели
        self.top_panel = create_top_panel(self, self.switch_mode, self.logic, '0.1.0')
        self.left_panel = create_left_panel(self)
        self.right_panel = create_right_panel(self)

        # Создаем главный макет
        main_layout = QVBoxLayout()

        # Добавляем top panel
        main_layout.addWidget(self.top_panel)

        # Создаем горизонтальный макет для left и right панелей
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addWidget(self.left_panel)
        horizontal_layout.addWidget(self.right_panel)
        main_layout.addLayout(horizontal_layout)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)