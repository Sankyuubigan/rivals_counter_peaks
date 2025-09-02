"""
Конфигурация приложения для управления переходом на новую архитектуру
"""

# Флаг использования новой архитектуры
USE_REFACTORED_ARCHITECTURE = False

# Настройки логирования
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
LOG_DATE_FORMAT = '%H:%M:%S'

# Настройки распознавания
RECOGNITION_THRESHOLD = 0.8
SIMILARITY_THRESHOLD = 0.72

# Настройки UI
DEFAULT_THEME = "light"
DEFAULT_LANGUAGE = "ru_RU"

# Настройки производительности
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
WINDOW_SIZE_W_DINO = 95
WINDOW_SIZE_H_DINO = 95