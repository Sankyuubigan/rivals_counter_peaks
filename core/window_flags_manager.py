# File: core/window_flags_manager.py
import sys
import time
import logging
from typing import TYPE_CHECKING 
from PySide6.QtCore import Qt, QTimer, QPoint, QRect
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from main_window import MainWindow

class WindowFlagsManager:
    def __init__(self, main_window: 'MainWindow'):
        self.mw = main_window
        self._is_applying_flags_operation = False
        self._last_applied_flags = self.mw.windowFlags() 

    def _calculate_target_flags(self) -> Qt.WindowFlags:
        is_min_mode = (self.mw.mode == "min")
        if is_min_mode:
            base_flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        else:
            base_flags = Qt.WindowType.Window | Qt.WindowType.WindowSystemMenuHint | \
                         Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint | \
                         Qt.WindowType.WindowMaximizeButtonHint
        
        topmost_flag_to_add = Qt.WindowType.WindowStaysOnTopHint if self.mw._is_win_topmost else Qt.WindowType(0)
        transparent_flag_to_add = Qt.WindowType.WindowTransparentForInput if getattr(self.mw, 'mouse_invisible_mode_enabled', False) else Qt.WindowType(0)
            
        return base_flags | topmost_flag_to_add | transparent_flag_to_add

    def apply_window_flags_and_show(self, new_flags: Qt.WindowFlags, reason: str):
        if self._is_applying_flags_operation:
            logging.warning(f"    [ApplyFlags] Skipped due to _is_applying_flags_operation already True. Reason: {reason}")
            return
        self._is_applying_flags_operation = True
        logging.debug(f"    [ApplyFlags] Entered. Reason: {reason}. _is_applying_flags_operation set to True.")
        t_start_apply = time.perf_counter()

        try:
            current_actual_flags = self.mw.windowFlags()
            flags_need_change = (current_actual_flags != new_flags)
            logging.info(f"    [ApplyFlags] Current actual flags: {current_actual_flags:#x}, New target flags: {new_flags:#x}, Need change: {flags_need_change}. Reason: {reason}")

            was_visible_before_operation = self.mw.isVisible()
            was_minimized_before_operation = self.mw.isMinimized()
            geom_before_operation = self.mw.geometry()
            logging.debug(f"        State before any flag/visibility change: Visible={was_visible_before_operation}, Minimized={was_minimized_before_operation}, Geom={geom_before_operation}")

            if flags_need_change:
                logging.info(f"    [ApplyFlags] Applying new flags. Current geom: {self.mw.geometry()}")
                self.mw.setWindowFlags(new_flags)
                self._last_applied_flags = new_flags 
                logging.info(f"    [ApplyFlags] After setWindowFlags. New actual flags(): {self.mw.windowFlags():#x}. isVisible(): {self.mw.isVisible()}, geom: {self.mw.geometry()}")

            if not self.mw.isMinimized():
                if not self.mw.isVisible():
                    logging.info(f"    [ApplyFlags] Window is not visible (and not minimized). Calling show(). Reason: {reason}")
                    t_show_start = time.perf_counter()
                    self.mw.show()
                    if self.mw.isVisible(): 
                        self.mw.setWindowIcon(self.mw.windowIcon()) 
                    logging.info(f"        After show(): isVisible={self.mw.isVisible()}, isActiveWindow={self.mw.isActiveWindow()}. Time: {(time.perf_counter() - t_show_start)*1000:.2f} ms. Geom: {self.mw.geometry()}")
                else: # Окно уже видимо
                    logging.info(f"    [ApplyFlags] Window already visible or became visible after setWindowFlags. No explicit show() call needed now. Reason: {reason}. Geom: {self.mw.geometry()}")
                    # Всегда обновляем иконку, если окно видимо, даже если флаги не менялись,
                    # особенно если вызов пришел из force_taskbar_update.
                    if self.mw.isVisible():
                        self.mw.setWindowIcon(self.mw.windowIcon())


                if self.mw.isVisible() and geom_before_operation.isValid() and self.mw.geometry() != geom_before_operation:
                    logging.info(f"    [ApplyFlags] Restoring geometry from {self.mw.geometry()} to {geom_before_operation}. Reason: {reason}")
                    self.mw.setGeometry(geom_before_operation)
            
            elif self.mw.isMinimized():
                 logging.info(f"    [ApplyFlags] Window is minimized. No explicit show() or geometry restoration. Reason: {reason}")
            
            if not self.mw.isMinimized() and not self.mw.isVisible():
                logging.warning(f"    [ApplyFlags] FINAL CHECK: Window not minimized but still not visible after logic! Forcing show. Flags: {self.mw.windowFlags():#x}. Reason: {reason}")
                self.mw.show()
                if self.mw.isVisible():
                    self.mw.setWindowIcon(self.mw.windowIcon())
                if not self.mw.isVisible():
                     logging.error(f"    [ApplyFlags] FINAL CHECK FAILED: Window STILL NOT VISIBLE after force show! Flags: {self.mw.windowFlags():#x} Reason: {reason}")
                if self.mw.isVisible() and geom_before_operation.isValid() and self.mw.geometry() != geom_before_operation:
                     logging.warning(f"    [ApplyFlags] FINAL CHECK: Restoring geometry again to {geom_before_operation}")
                     self.mw.setGeometry(geom_before_operation)
        finally:
            self._is_applying_flags_operation = False
            logging.debug(f"    [ApplyFlags] END apply_window_flags_and_show. Reason: {reason}. _is_applying_flags_operation set to False. Total time: {(time.perf_counter() - t_start_apply)*1000:.2f} ms. Final state: Visible={self.mw.isVisible()}, Minimized={self.mw.isMinimized()}, Flags={self.mw.windowFlags():#x}")

    def apply_mouse_invisible_mode(self, reason: str):
        logging.debug(f"--> apply_mouse_invisible_mode called. Reason: '{reason}'")
        t_start_apply_mouse = time.perf_counter()
        target_flags = self._calculate_target_flags()
        self.apply_window_flags_and_show(target_flags, reason)
        logging.debug(f"<-- apply_mouse_invisible_mode finished. Reason: '{reason}'. Time: {(time.perf_counter() - t_start_apply_mouse)*1000:.2f} ms")

    def force_taskbar_update_internal(self, reason_suffix="unknown"):
        caller_reason = f"force_taskbar_update_{reason_suffix}"
        logging.info(f"    [TaskbarUpdate] START force_taskbar_update_internal (Simplified). Caller reason: {caller_reason}")
        t_start_force = time.perf_counter()

        if sys.platform == 'win32':
            target_flags = self._calculate_target_flags()
            current_flags = self.mw.windowFlags()
            
            # Вызываем apply_window_flags_and_show, чтобы он мог применить логику показа/обновления иконки
            logging.debug(f"        Simplified Taskbar Update: Calling apply_window_flags_and_show with target flags {target_flags:#x} (current: {current_flags:#x})")
            self.apply_window_flags_and_show(target_flags, f"simplified_taskbar_update_for_{reason_suffix}")
        else:
            logging.debug(f"    [TaskbarUpdate] Skipped on non-Windows platform. Caller reason: {caller_reason}")
        
        logging.info(f"    [TaskbarUpdate] END force_taskbar_update_internal (Simplified). Time: {(time.perf_counter() - t_start_force)*1000:.2f} ms")