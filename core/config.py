"""
Конфигурация приложения для управления переходом на новую архитектуру
"""

# Флаг использования новой архитектуры
# ИЗМЕНЕНО: Активируем новую архитектуру
USE_REFACTORED_ARCHITECTURE = True

# Настройки логирования
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s.%(msecs)03d - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
LOG_DATE_FORMAT = '%H:%M:%S'