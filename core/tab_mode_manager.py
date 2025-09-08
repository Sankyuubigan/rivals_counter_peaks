import logging
from typing import TYPE_CHECKING
from PySide6.QtCore import QTimer, QObject, Signal
from core.tray_window import TrayWindow

if TYPE_CHECKING:
    from main_window_refactored import MainWindowRefactored

class TrayModeManager(QObject):
    """Управляет отдельным tray окном для таб-режима с оптимизацией производительности."""
    # Сигнал об обновлении UI
    ui_updated = Signal()
    
    def __init__(self, main_window: 'MainWindowRefactored'):
        super().__init__(main_window)  # Передаем parent для корректной работы с Qt
        self.mw = main_window
        self._tray_window: TrayWindow | None = None
        self._is_active = False
        self._pending_show = False  # Флаг для отложенного показа окна

    def is_active(self) -> bool:
        return self._is_active

    def enable(self):
        """Оптимизированное включение режима таба с минимальными задержками."""
        if self._is_active: 
            return
            
        if not self._tray_window:
            # Создаем окно один раз при первом включении
            self._tray_window = TrayWindow(self.mw)
                
        self._is_active = True
        # Используем отложенный показ для улучшения производительности
        self._pending_show = True
        QTimer.singleShot(0, self._show_tray_if_needed)

    def _show_tray_if_needed(self):
        """Показывает окно только если это необходимо."""
        if self._pending_show and self._tray_window:
            logging.info("[TrayModeManager] Showing tray window")
            # Показываем окно напрямую в главном потоке
            self._tray_window.show_tray()
            self._pending_show = False
            # Уведомляем об окончании обновления UI
            self.ui_updated.emit()

    def disable(self):
        """Отключение режима таба с оптимизацией."""
        if not self._is_active: 
            return
            
        self._pending_show = False
        if self._tray_window and self._tray_window.isVisible():
            logging.info("[TrayModeManager] Hiding tray window")
            # Скрываем окно напрямую в главном потоке
            self._tray_window.hide_tray()
        self._is_active = False
        # Уведомляем об окончании обновления UI
        self.ui_updated.emit()