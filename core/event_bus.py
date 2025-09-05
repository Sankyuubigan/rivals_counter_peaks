"""
Централизованная система событий для приложения
"""
import logging
from typing import Dict, List, Callable, Any

class EventBus:
    """
    Централизованная шина событий для приложения, основанная на словаре.
    Не использует QObject, чтобы избежать сложностей с потоками и владением.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, callback: Callable):
        """Подписаться на событие"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        self.logger.debug(f"Subscribed to '{event_type}': {callback.__name__}")
    
    def emit(self, event_type: str, *args, **kwargs):
        """Эмитировать событие"""
        if event_type in self._subscribers:
            self.logger.debug(f"Emitting event '{event_type}' with args: {args}, kwargs: {kwargs}")
            # Копируем список подписчиков, чтобы избежать проблем при отписке во время вызова
            for callback in self._subscribers[event_type][:]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Error in callback {callback.__name__} for event '{event_type}': {e}", exc_info=True)

# Глобальный экземпляр EventBus
event_bus = EventBus()