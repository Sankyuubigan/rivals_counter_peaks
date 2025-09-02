"""
Менеджер управления окном приложения
"""
import logging
from typing import Optional, Dict, Any
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtWidgets import QApplication
from core.ui_base import BaseWindow
from core.event_bus import event_bus

class WindowManager:
    """Менеджер управления состоянием окна"""
    
    def __init__(self, window: BaseWindow):
        self.window = window
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mode_positions: Dict[str, QPoint] = {}
        self.current_mode = "middle"
        self._is_maximized = False
        
        # Подписка на события
        event_bus.subscribe("mode_changed", self._on_mode_changed)
    
    def _on_mode_changed(self, new_mode: str):
        """Обработка смены режима"""
        self.save_current_position()
        self.current_mode = new_mode
        self.restore_position(new_mode)
    
    def save_current_position(self):
        """Сохранить текущую позицию окна"""
        if self.window.isVisible():
            self.mode_positions[self.current_mode] = self.window.pos()
            self.logger.debug(f"Saved position for mode {self.current_mode}: {self.window.pos()}")
    
    def restore_position(self, mode: str):
        """Восстановить позицию окна для режима"""
        if mode in self.mode_positions:
            self.window.move(self.mode_positions[mode])
            self.logger.debug(f"Restored position for mode {mode}: {self.mode_positions[mode]}")
    
    def set_window_flags(self, flags: Qt.WindowFlags):
        """Установить флаги окна"""
        self.window.setWindowFlags(flags)
        if self.window.isVisible():
            self.window.show()
    
    def toggle_maximize(self):
        """Переключить состояние максимизации"""
        if self._is_maximized:
            self.window.showNormal()
        else:
            self.window.showMaximized()
        self._is_maximized = not self._is_maximized
    
    def center_on_screen(self):
        """Центрировать окно на экране"""
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.window.size()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.window.move(x, y)
    
    def set_minimum_size(self, width: int, height: int):
        """Установить минимальный размер окна"""
        self.window.setMinimumSize(width, height)
    
    def set_maximum_size(self, width: int, height: int):
        """Установить максимальный размер окна"""
        self.window.setMaximumSize(width, height)
    
    def resize_to_content(self):
        """Изменить размер окна под содержимое"""
        self.window.adjustSize()
    
    def get_window_geometry(self) -> QRect:
        """Получить геометрию окна"""
        return self.window.geometry()
    
    def set_window_geometry(self, geometry: QRect):
        """Установить геометрию окна"""
        self.window.setGeometry(geometry)