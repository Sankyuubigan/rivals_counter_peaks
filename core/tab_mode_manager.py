import logging
from typing import TYPE_CHECKING
from PySide6.QtCore import QTimer, QObject, Signal
from core.tray_window import TrayWindow

if TYPE_CHECKING:
    from main_window_refactored import MainWindowRefactored

class TrayModeManager(QObject):
    ui_updated = Signal()
    
    def __init__(self, main_window: 'MainWindowRefactored'):
        super().__init__(main_window) 
        self.mw = main_window
        self._tray_window: TrayWindow | None = None
        self._is_active = False
        self._pending_show = False 

    def is_active(self) -> bool:
        return self._is_active

    def enable(self):
        if self._is_active: return
        if not self._tray_window:
            self._tray_window = TrayWindow(self.mw)
        self._is_active = True
        self._pending_show = True
        QTimer.singleShot(0, self._show_tray_if_needed)

    def _show_tray_if_needed(self):
        if self._pending_show and self._tray_window:
            logging.debug("[TrayModeManager] Showing tray window")
            self._tray_window.show_tray()
            self._pending_show = False
            
            if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
                self.mw.ui_updater.update_ui_after_logic_change()
            self.ui_updated.emit()

    def disable(self):
        if not self._is_active: return
        self._pending_show = False
        if self._tray_window and self._tray_window.isVisible():
            logging.debug("[TrayModeManager] Hiding tray window")
            self._tray_window.hide_tray()
        self._is_active = False
        self.ui_updated.emit()