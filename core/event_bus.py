"""
Централизованная система событий для приложения
"""
import logging
from typing import Dict, List, Callable, Any
from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    """Централизованная шина событий для приложения"""
    
    # Сигналы для основных событий
    ui_updated = Signal(str, object)  # component_name, data
    mode_changed = Signal(str)  # new_mode
    settings_changed = Signal(str, object)  # setting_name, value
    recognition_completed = Signal(list)  # recognized_heroes
    hotkey_pressed = Signal(str)  # action_id
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, callback: Callable):
        """Подписаться на событие"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        self.logger.debug(f"Subscribed to {event_type}: {callback.__name__}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Отписаться от события"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                self.logger.debug(f"Unsubscribed from {event_type}: {callback.__name__}")
            except ValueError:
                self.logger.warning(f"Callback not found in {event_type} subscribers")
    
    def emit(self, event_type: str, *args, **kwargs):
        """Эмитировать событие"""
        if event_type in self._subscribers:
            self.logger.debug(f"Emitting event '{event_type}' with args: {args}, kwargs: {kwargs}")
            for callback in self._subscribers[event_type]:
                try:
                    # ИСПРАВЛЕНИЕ: Универсальный вызов callback(*args, **kwargs)
                    # корректно обрабатывает как один, так и несколько аргументов.
                    # Предыдущая логика с if/else ошибочно передавала кортеж (arg,)
                    # вместо самого аргумента.
                    self.logger.debug(f"Passing args to callback {callback.__name__}")
                    callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Error in callback {callback.__name__} for event {event_type}: {e}", exc_info=True)
    
    def clear_subscribers(self):
        """Очистить всех подписчиков"""
        self._subscribers.clear()
        self.logger.debug("All subscribers cleared")

# Глобальный экземпляр EventBus
event_bus = EventBus()