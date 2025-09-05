# File: core/win_api.py
import sys
import time
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtWidgets import QWidget
import logging

if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x00000008
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        GetWindowLongPtr = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
        GetWindowLongPtr.argtypes = [wintypes.HWND, wintypes.INT]
        GetWindowLongPtr.restype = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else wintypes.LONG
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.UINT]
        user32.SetWindowPos.restype = wintypes.BOOL
    except Exception as e:
        logging.error(f"Failed to load user32.dll functions: {e}")
        user32 = None
else:
    user32 = None

class WinApiManager(QObject):
    topmost_state_changed = Signal(bool)

    def __init__(self, main_window: QWidget):
        super().__init__(main_window) 
        self.main_window = main_window
        self._is_win_topmost = False
        self._hwnd = None
        QTimer.singleShot(100, self._check_initial_topmost_state)

    def _get_hwnd(self):
        if self._hwnd is None:
            try:
                self._hwnd = int(self.main_window.winId())
            except (RuntimeError, Exception):
                self._hwnd = None
        return self._hwnd

    def _check_initial_topmost_state(self):
        qt_flag_state = bool(self.main_window.windowFlags() & Qt.WindowStaysOnTopHint)
        if user32:
            hwnd = self._get_hwnd()
            if hwnd:
                ex_style = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
                self._is_win_topmost = bool(ex_style & WS_EX_TOPMOST)
            else:
                self._is_win_topmost = qt_flag_state
        else:
            self._is_win_topmost = qt_flag_state
        self.topmost_state_changed.emit(self._is_win_topmost)

    def set_topmost(self, enable: bool):
        if self._is_win_topmost == enable:
            return

        if user32:
            hwnd = self._get_hwnd()
            if hwnd:
                insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
                if user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE):
                    self._is_win_topmost = enable
                    self.topmost_state_changed.emit(enable)
                    return
        
        # Fallback to Qt method
        self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
        self.main_window.show() # setWindowFlag can hide the window
        self._is_win_topmost = enable
        self.topmost_state_changed.emit(enable)