# File: core/tab_mode_manager.py
import logging
from typing import TYPE_CHECKING
from core.tray_window import TrayWindow

if TYPE_CHECKING:
    from main_window import MainWindow

class TrayModeManager:
    """Управляет отдельным tray окном для таб-режима."""
    def __init__(self, main_window: 'MainWindow'):
        self.mw = main_window
        self._tray_window: TrayWindow | None = None
        self._is_active = False

    def is_active(self) -> bool:
        """Возвращает, активно ли tray окно."""
        return self._is_active

    def enable(self):
        """Включает tray окно."""
        logging.info("TrayModeManager: enable() called.")
        logging.info(f"ROO DEBUG: tab_mode_manager enable - previous _is_active: {self._is_active}")

        if self._is_active:
            logging.warning("TrayModeManager: enable() called, but already active.")
            return

        # Создаем tray window один раз, если не существует
        if not self._tray_window:
            logging.info("[TrayModeManager] Creating new TrayWindow")
            self._tray_window = TrayWindow(self.mw)

        self._is_active = True
        logging.info("ROO DEBUG: tab_mode_manager enable - set _is_active = True")

        # Показываем tray окно
        if self._tray_window:
            self._tray_window._skip_content_update = True
            logging.info("ROO DEBUG: tray_window.show_tray() called")
            self._tray_window.show_tray()
            self._tray_window._skip_content_update = False
            logging.info("ROO DEBUG: tray_window.show_tray() called")

        logging.info("[TrayModeManager] Tray mode enabled")


    def disable(self):
        """Скрывает tray окно."""
        logging.info("TrayModeManager: disable() called.")
        was_active = self._is_active  # Запоминаем предыдущее состояние

        # Скрываем tray окно, если оно видимо
        if self._tray_window and self._tray_window.isVisible():
            self._tray_window.hide_tray()

        self._is_active = False  # Обновляем флаг, независимо от предыдущего состояния

        # Логируем в зависимости от предыдущего состояния
        if not was_active:
            logging.warning("TrayModeManager: disable() called, but not active.")
        else:
            logging.info("[TrayModeManager] Tray mode disabled")

    def show_tray(self):
        """Показывает tray окно (используется для внешнего доступа)."""
        logging.info("TrayModeManager: show_tray() called.")
        if self._tray_window:
            self._tray_window.show_tray()
        else:
            self.enable()

    def close_tray(self):
        """Закрывает tray окно."""
        logging.info("TrayModeManager: close_tray() called.")
        if self._is_active:
            self.disable()
