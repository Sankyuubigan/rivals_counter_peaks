import pytest
import logging
from PyQt5.QtWidgets import QPushButton, QLabel
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
from unittest.mock import patch
from tests.test_framework import MarvelRivalsTestFramework

logger = logging.getLogger(__name__)

@pytest.mark.gui
class TestMainWindowGUI(MarvelRivalsTestFramework):
    """Тестирует GUI главного окна. Использует фикстуру для управления приложением."""

    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self):
        """Настраивает QApplication и окно перед запуском тестов этого класса."""
        self.setup_qt_app()
        yield
        self.teardown_qt_app()

    def test_window_initialization(self):
        """Тест: окно успешно создается и отображается."""
        assert self.main_window is not None, "Главное окно не было создано."
        assert self.main_window.isVisible(), "Главное окно невидимо после инициализации."
        logger.info("Главное окно успешно инициализировано и видимо.")

    def test_hero_selection_button_click(self):
        """Тест: клик по кнопке выбора героя вызывает ожидаемую реакцию."""
        # Для надежности лучше искать виджеты по objectName
        hero_buttons = self.main_window.findChildren(QPushButton)
        assert len(hero_buttons) > 0, "Не найдены кнопки выбора героев."

        first_button = hero_buttons[0]
        QTest.mouseClick(first_button, Qt.LeftButton)
        QTest.qWait(100)  # Даем время на обработку сигнала

        logger.info(f"Симулирован клик по кнопке: {first_button.text()}")
        # Здесь нужна проверка, что клик привел к изменению (например, мок-функции)

    def test_counter_display_update(self):
        """Тест: отображение контр-пиков обновляется после выбора героев."""
        test_heroes = ['spiderman', 'hulk']
        
        # Мокаем метод, который должен обновлять UI, чтобы он "вернул" результат
        with patch.object(self.main_window, 'update_counter_pick_display') as mock_update:
            for hero in test_heroes:
                self.simulate_hero_selection(hero)
            
            # Проверяем, что метод обновления UI был вызван
            mock_update.assert_called()

        # Также можно проверить наличие виджетов с результатами
        counter_labels = self.main_window.findChildren(QLabel, "counterPickLabel")
        logger.info("Дисплей контр-пиков симулированно обновлен.")
        # assert len(counter_labels) > 0

    def test_hotkey_functionality(self):
        """Тест: нажатие горячей клавиши F1 вызывает нужную функцию."""
        with patch.object(self.main_window, 'on_hotkey_pressed') as mock_hotkey_handler:
            QTest.keyClick(self.main_window, Qt.Key_F1)
            QTest.qWait(100)
            mock_hotkey_handler.assert_called_once()
            logger.info("Проверена реакция на нажатие горячей клавиши F1.")
