"""
Менеджер состояний UI
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum
from core.event_bus import event_bus

class UIState(Enum):
    """Состояния UI"""
    MINIMIZED = "min"
    NORMAL = "middle"
    MAXIMIZED = "max"
    TAB_MODE = "tab"

class UIStateManager:
    """Менеджер состояний UI"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_state = UIState.NORMAL
        self.previous_state = UIState.NORMAL
        self.state_data: Dict[UIState, Dict[str, Any]] = {}
        
        # Подписка на события
        event_bus.subscribe("mode_changed", self._on_mode_changed)
    
    def _on_mode_changed(self, new_mode: str):
        """Обработка смены режима"""
        try:
            new_state = UIState(new_mode)
            self.set_state(new_state)
        except ValueError:
            self.logger.error(f"Unknown mode: {new_mode}")
    
    def set_state(self, new_state: UIState, data: Optional[Dict[str, Any]] = None):
        """Установить новое состояние"""
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            
            # Сохраняем данные состояния
            if data:
                self.state_data[new_state] = data
            
            # Уведомляем об изменении состояния
            event_bus.emit("ui_state_changed", new_state, data)
            
            self.logger.info(f"UI state changed: {self.previous_state.value} -> {new_state.value}")
    
    def get_state(self) -> UIState:
        """Получить текущее состояние"""
        return self.current_state
    
    def get_previous_state(self) -> UIState:
        """Получить предыдущее состояние"""
        return self.previous_state
    
    def get_state_data(self, state: UIState) -> Dict[str, Any]:
        """Получить данные состояния"""
        return self.state_data.get(state, {})
    
    def restore_state(self, state: UIState):
        """Восстановить состояние"""
        data = self.get_state_data(state)
        self.set_state(state, data)
    
    def is_minimized(self) -> bool:
        """Проверить, минимизировано ли окно"""
        return self.current_state == UIState.MINIMIZED
    
    def is_maximized(self) -> bool:
        """Проверить, максимизировано ли окно"""
        return self.current_state == UIState.MAXIMIZED
    
    def is_tab_mode(self) -> bool:
        """Проверить, находится ли в режиме таба"""
        return self.current_state == UIState.TAB_MODE
    
    def toggle_minimize(self):
        """Переключить состояние минимизации"""
        if self.is_minimized():
            self.restore_state(self.previous_state)
        else:
            self.set_state(UIState.MINIMIZED)
    
    def toggle_tab_mode(self):
        """Переключить режим таба"""
        if self.is_tab_mode():
            self.restore_state(self.previous_state)
        else:
            self.set_state(UIState.TAB_MODE)