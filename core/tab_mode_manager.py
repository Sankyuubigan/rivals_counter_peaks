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
        return self._is_active
    def enable(self):
        if self._is_active: return
        if not self._tray_window:
            self._tray_window = TrayWindow(self.mw)
        self._is_active = True
        # ИЗМЕНЕНО: Используем QTimer.singleShot для гарантированного показа окна в главном потоке
        QTimer.singleShot(0, self._show_and_update_tray)
    def _show_and_update_tray(self):
        if not self._is_active: return
        if self._tray_window: 
            logging.info("[TrayModeManager] Showing tray window")
            self._tray_window.show_tray()
        if hasattr(self.mw, 'ui_updater'):
            self.mw.ui_updater.update_ui_after_logic_change(force_update=True)
        logging.info("TrayWindow shown and updated.")
    def disable(self):
        if not self._is_active: return
        if self._tray_window and self._tray_window.isVisible():
            logging.info("[TrayModeManager] Hiding tray window")
            self._tray_window.hide_tray()
        self._is_active = False