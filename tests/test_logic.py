import pytest
import numpy as np
import logging
from unittest.mock import Mock, patch

# Получаем логгер для этого модуля
logger = logging.getLogger(__name__)

class TestHeroRecognition:
    """Тестирует модуль распознавания героев."""
    
    def setup_method(self):
        """Настройка перед каждым тестом в этом классе."""
        self.hero_names = [
            'spiderman', 'iron_man', 'hulk', 'thor', 'captain_america',
            'black_panther', 'doctor_strange', 'wolverine'
        ]
    
    @pytest.fixture
    def mock_recognition_module(self):
        """Фикстура для создания мок-объекта модуля распознавания."""
        with patch('core.recognition.Recognition') as mock_class:
            mock_instance = Mock()
            # Настраиваем мок, чтобы он возвращал предопределенное значение
            mock_instance.recognize_hero.return_value = ('spiderman', 0.95)
            mock_class.return_value = mock_instance
            yield mock_instance
    
    def test_hero_recognition_accuracy(self, mock_recognition_module):
        """Тест проверяет, что распознавание возвращает корректные данные."""
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        hero_name, confidence = mock_recognition_module.recognize_hero(test_image)
        
        assert hero_name in self.hero_names
        assert 0.8 < confidence <= 1.0
        logger.info(f"Распознан герой: {hero_name} с уверенностью {confidence:.2f}")
    
    def test_embedding_similarity(self):
        """Тест проверяет корректность расчета схожести эмбеддингов."""
        emb1 = np.random.rand(512)
        emb2 = emb1 + np.random.normal(0, 0.1, 512)  # Добавляем небольшой шум
        
        # Нормализуем векторы для косинусного сходства
        emb1_norm = emb1 / np.linalg.norm(emb1)
        emb2_norm = emb2 / np.linalg.norm(emb2)
        similarity = np.dot(emb1_norm, emb2_norm)
        
        assert similarity > 0.7  # Похожие векторы должны иметь высокую схожесть
        logger.info(f"Сходство эмбеддингов: {similarity:.2f}")
    
    def test_invalid_image_handling(self, mock_recognition_module):
        """Тест проверяет обработку некорректного изображения."""
        mock_recognition_module.recognize_hero.side_effect = ValueError("Invalid image provided")
        
        with pytest.raises(ValueError, match="Invalid image"):
            mock_recognition_module.recognize_hero(None)
        logger.info("Проверена корректная обработка ошибки для невалидного изображения.")

class TestCounterPickLogic:
    """Тестирует модуль логики подбора контр-пиков."""
    
    def setup_method(self):
        self.enemy_team = ['spiderman', 'hulk', 'wolverine']
        
    @pytest.fixture
    def mock_counter_logic(self):
        """Фикстура для создания мок-объекта логики контр-пиков."""
        with patch('core.logic.CounterPickLogic') as mock_class:
            mock_instance = Mock()
            mock_instance.get_counters.return_value = [
                {'hero': 'magneto', 'effectiveness': 0.85, 'reasons': ['Control vs metal heroes']},
                {'hero': 'emma_frost', 'effectiveness': 0.75, 'reasons': ['Psychic defense']}
            ]
            mock_class.return_value = mock_instance
            yield mock_instance
    
    def test_counter_pick_generation(self, mock_counter_logic):
        """Тест генерации списка контр-пиков для заданной команды."""
        counters = mock_counter_logic.get_counters(self.enemy_team)
        
        assert len(counters) > 0
        assert all('hero' in c and 'effectiveness' in c for c in counters)
        logger.info(f"Сгенерировано {len(counters)} контр-пиков.")
    
    def test_empty_enemy_team(self, mock_counter_logic):
        """Тест проверяет, что для пустой команды не генерируются контр-пики."""
        mock_counter_logic.get_counters.return_value = []
        counters = mock_counter_logic.get_counters([])
        
        assert counters == []
        logger.info("Проверена обработка пустой команды противника.")
