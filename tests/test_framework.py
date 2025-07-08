import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication

# Добавляем путь к корневой директории 'core' в sys.path
# Это позволяет импортировать модули из core, например, main_window
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

# Настраиваем логирование для тестов
# Результаты будут сохраняться в файл и выводиться в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tests/test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MarvelRivalsTestFramework:
    """
    Базовый класс-фреймворк для настройки и проведения тестов GUI.
    Отвечает за инициализацию и закрытие QApplication и главного окна.
    """
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.test_images_path = Path('resources/templates')
        self.embeddings_path = Path('resources/embeddings_padded')
        
    def setup_qt_app(self):
        """Инициализирует QApplication и создает экземпляр главного окна."""
        logger.info("Инициализация Qt-приложения для тестов...")
        # Создаем экземпляр QApplication, если он еще не существует
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        # Импортируем и создаем главное окно приложения
        try:
            from main_window import MainWindow
            self.main_window = MainWindow()
            logger.info("Главное окно успешно инициализировано.")
        except ImportError as e:
            logger.error(f"Не удалось импортировать MainWindow из core/main_window.py: {e}")
            raise
    
    def teardown_qt_app(self):
        """Корректно закрывает окно и выходит из QApplication."""
        logger.info("Завершение работы Qt-приложения...")
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        if self.app:
            self.app.quit()
    
    def simulate_hero_selection(self, hero_name: str):
        """
        Симулирует выбор героя в интерфейсе.
        Этот метод должен быть реализован в дочерних классах или расширен.
        """
        logger.info(f"Симуляция выбора героя: {hero_name}")
        # Пример реализации:
        # self.main_window.team_composition_widget.select_hero(hero_name)
        pass
    
    def get_counter_suggestions(self) -> list:
        """
        Получает предложенные контр-пики из UI.
        Этот метод должен быть адаптирован под конкретную реализацию UI.
        """
        logger.info("Запрос предложений контр-пиков из UI.")
        # Пример реализации:
        # return self.main_window.counter_pick_display.get_displayed_counters()
        return []
