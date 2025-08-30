# File: core/log_handler.py
import logging
from PySide6.QtCore import QObject, Signal

class QLogHandler(logging.Handler, QObject):
    """
    Кастомный обработчик логов Python, который испускает сигнал Qt
    с отформатированным сообщением лога.
    Это позволяет безопасно обновлять GUI (QTextBrowser) из других потоков.
    """
    message_logged = Signal(str)

    def __init__(self, parent=None):
        """
        Инициализирует обработчик и родительский QObject.
        """
        logging.Handler.__init__(self)
        QObject.__init__(self, parent) # Важно инициализировать QObject

    def emit(self, record):
        """
        Форматирует запись лога и испускает сигнал message_logged.
        Этот метод вызывается механизмом логирования Python.
        """
        try:
            # Форматируем сообщение с помощью форматтера, установленного для этого хендлера
            msg = self.format(record)
            # Испускаем сигнал с отформатированным сообщением
            self.message_logged.emit(msg)
        except RecursionError: # Избегаем бесконечной рекурсии
            raise
        except Exception:
            # В случае ошибки при форматировании или испускании сигнала,
            # вызываем стандартный обработчик ошибок logging.Handler
            self.handleError(record)
