# File: core/tab_mode_manager.py
import logging
import threading
from typing import TYPE_CHECKING
from PySide6.QtCore import QTimer
from core.tray_window import TrayWindow

if TYPE_CHECKING:
    from main_window_refactored import MainWindowRefactored

class TrayModeManager:
    """Управляет отдельным tray окном для таб-режима."""
    def __init__(self, main_window: 'MainWindowRefactored'):
        self.mw = main_window
        self._tray_window: TrayWindow | None = None
        self._is_active = False

    def is_active(self) -> bool:
        """Возвращает, активно ли tray окно."""
        return self._is_active

    def enable(self):
        """
        Планирует показ и обновление tray окна, чтобы избежать блокировки
        из-за конфликта с библиотекой глобальных хоткеев.
        """
        logging.info("[TRAY_MANAGER] Запрос на включение режима трея.")
        if self._is_active:
            logging.warning("[TRAY_MANAGER] Режим трея уже активен, запрос проигнорирован.")
            return

        if not self._tray_window:
            logging.info("[TRAY_MANAGER] Создание нового экземпляра TrayWindow.")
            self._tray_window = TrayWindow(self.mw)

        self._is_active = True
        
        # ИСПРАВЛЕНИЕ ЗАДЕРЖКИ:
        # Уменьшаем задержку таймера до 0. Это выполнит слот в следующем цикле
        # обработки событий Qt, что по-прежнему безопасно, но для пользователя будет мгновенно.
        logging.info("[TRAY_MANAGER] Планирование показа и обновления TrayWindow через QTimer (0ms) для избежания deadlock.")
        QTimer.singleShot(0, self._show_and_update_tray)

    def _show_and_update_tray(self):
        """Безопасный слот для показа и обновления окна трея."""
        logging.info("[TRAY_MANAGER_TIMER] QTimer сработал. Выполнение _show_and_update_tray в потоке: %s", threading.current_thread().name)
        if not self._is_active:
            logging.warning("[TRAY_MANAGER] Показ/обновление трея отменено, так как режим уже неактивен.")
            return

        logging.info("[TRAY_MANAGER] Шаг 1 (выполнение таймера): Вызов show_tray() для отображения окна.")
        if self._tray_window:
            self._tray_window.show_tray()

        logging.info("[TRAY_MANAGER] Шаг 2 (выполнение таймера): Инициирование обновления UI.")
        if hasattr(self.mw, 'ui_updater'):
            self.mw.ui_updater.update_ui_after_logic_change(force_update=True)
        
        logging.info("[TRAY_MANAGER] TrayWindow показан и его содержимое обновлено.")

    def disable(self):
        """Скрывает tray окно."""
        logging.info("[TRAY_MANAGER] Запрос на отключение режима трея.")
        if not self._is_active:
            logging.warning("[TRAY_MANAGER] Режим трея уже неактивен, запрос проигнорирован.")
            return
            
        if self._tray_window and self._tray_window.isVisible():
            self._tray_window.hide_tray()

        self._is_active = False
        logging.info("[TRAY_MANAGER] Режим трея отключен.")

    def show_tray(self):
        """Просто показывает tray окно (используется для внешнего доступа)."""
        if not self._is_active:
            self.enable()
        elif self._tray_window:
            self._tray_window.show_tray()

    def close_tray(self):
        """Закрывает (скрывает) tray окно."""
        if self._is_active:
            self.disable()