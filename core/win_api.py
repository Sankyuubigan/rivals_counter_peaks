# File: core/win_api.py
import sys
import time
from PySide6.QtCore import Qt, QTimer, QMetaObject, QObject, Signal
from PySide6.QtWidgets import QPushButton, QApplication, QWidget
import logging

# --- WinAPI Imports ---
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    HWND_BOTTOM = 1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x00000008
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, wintypes.INT, wintypes.INT,
            wintypes.INT, wintypes.INT, wintypes.UINT
        ]
        if ctypes.sizeof(ctypes.c_void_p) == 8: 
            GetWindowLongPtr = user32.GetWindowLongPtrW
        else: 
            GetWindowLongPtr = user32.GetWindowLongW
        GetWindowLongPtr.restype = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else wintypes.LONG
        GetWindowLongPtr.argtypes = [wintypes.HWND, wintypes.INT]
        logging.info("[WinAPI] user32.dll и функции загружены успешно.")
    except Exception as e:
        logging.error(f"[ERROR][WinAPI] Ошибка при загрузке user32.dll или функций: {e}", exc_info=True)
        user32 = None; GetWindowLongPtr = None
else:
    logging.warning("[WinAPI] Платформа не Windows, WinAPI недоступно.")
    user32 = None; GetWindowLongPtr = None

class WinApiManager(QObject):
    topmost_state_changed = Signal(bool)

    def __init__(self, main_window: QWidget):
        super().__init__(main_window) 
        self.main_window = main_window
        self._is_win_topmost = False
        self.user32_lib = user32 # Используем user32_lib вместо self.user32, чтобы не конфликтовать с глобальным user32
        self.get_window_long_ptr_func = GetWindowLongPtr # Аналогично
        self._last_hwnd_check_time = 0
        self._hwnd = None
        self._check_initial_topmost_state()

    def _check_initial_topmost_state(self):
        qt_flag_state = False
        try:
            if self.main_window: qt_flag_state = bool(self.main_window.windowFlags() & Qt.WindowStaysOnTopHint)
        except RuntimeError: logging.warning("[WinAPI Initial Check] Окно уже удалено при проверке флага Qt.")

        if self.user32_lib and self.get_window_long_ptr_func:
            hwnd = self._get_hwnd(force_check=True)
            if hwnd:
                try:
                    ex_style = self.get_window_long_ptr_func(hwnd, GWL_EXSTYLE)
                    self._is_win_topmost = bool(ex_style & WS_EX_TOPMOST)
                except Exception as e:
                    logging.error(f"[ERROR][WinAPI] Ошибка при вызове GetWindowLongPtr для начальной проверки: {e}")
                    self._is_win_topmost = qt_flag_state
            else:
                 self._is_win_topmost = qt_flag_state
        else:
             self._is_win_topmost = qt_flag_state

        logging.info(f"[WinAPI] Initial topmost state determined as: {self._is_win_topmost}")
        self.topmost_state_changed.emit(self._is_win_topmost)


    @property
    def is_win_topmost(self) -> bool:
        return self._is_win_topmost

    def _get_hwnd(self, force_check=False) -> int | None:
        current_time = time.time()
        if force_check or self._hwnd is None or current_time - self._last_hwnd_check_time > 0.5:
            self._last_hwnd_check_time = current_time
            try:
                if self.main_window and self.main_window.isVisible():
                    win_id_val = self.main_window.winId()
                    # winId() может вернуть WId, который нужно преобразовать в int для ctypes
                    self._hwnd = int(win_id_val) if win_id_val else None
                else: self._hwnd = None
            except RuntimeError: self._hwnd = None
            except Exception: self._hwnd = None
        return self._hwnd

    def _set_window_pos_api(self, hwnd: int, insert_after: int, flags: int) -> bool:
        if not self.user32_lib or not hasattr(self.user32_lib, 'SetWindowPos'): return False
        try:
            success = self.user32_lib.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
            if not success:
                 error_code = ctypes.get_last_error()
                 error_msg = ctypes.FormatError(error_code).strip() if error_code else "N/A"
                 logging.error(f"[API ERROR] SetWindowPos не удался: Код {error_code} - {error_msg}")
                 ctypes.set_last_error(0) 
            return bool(success)
        except Exception as e:
            logging.error(f"[ERROR][WinAPI] Исключение при вызове SetWindowPos: {e}", exc_info=True)
            return False

    def _apply_qt_fallback(self, enable: bool):
        logging.warning("[WinAPI] Используется Qt.WindowStaysOnTopHint как fallback.")
        try:
            if not self.main_window: return
            
            current_geometry_before_flags = self.main_window.geometry()
            is_visible_before_flags = self.main_window.isVisible()

            self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
            
            # setWindowFlag может скрыть окно, нужно его снова показать
            if is_visible_before_flags: # Если окно было видимо
                self.main_window.show()
                # Восстанавливаем геометрию, если она была валидна
                if current_geometry_before_flags.isValid():
                    QTimer.singleShot(0, lambda: self.main_window.setGeometry(current_geometry_before_flags) if self.main_window.isVisible() else None)

            actual_qt_flag_state_after_set = bool(self.main_window.windowFlags() & Qt.WindowStaysOnTopHint)
            
            if self._is_win_topmost != actual_qt_flag_state_after_set:
                self._is_win_topmost = actual_qt_flag_state_after_set
                self.topmost_state_changed.emit(self._is_win_topmost)
            elif self._is_win_topmost != enable and actual_qt_flag_state_after_set == enable:
                # Если состояние _is_win_topmost не совпадает с enable, но флаг УЖЕ был таким,
                # все равно эмитируем сигнал, чтобы UI обновился, если он был рассинхронизирован.
                # Это маловероятно, если _check_initial_topmost_state работает.
                 self.topmost_state_changed.emit(self._is_win_topmost)


        except RuntimeError: logging.warning("[WinAPI Fallback] Окно уже удалено, не удалось применить Qt fallback.")
        except Exception as e: logging.error(f"[ERROR][WinAPI] Ошибка при применении Qt fallback: {e}", exc_info=True)

    def set_topmost_winapi(self, enable: bool):
        logging.info(f"[ACTION][WinAPI] Запрос на установку Topmost: {enable}")

        current_actual_state = self.is_win_topmost # Текущее известное состояние
        if current_actual_state == enable:
            logging.info(f"[WinAPI] Topmost уже в состоянии {enable}. Ничего не делаем.")
            # Эмитируем сигнал, чтобы UI (кнопка) обновился, если он был рассинхронизирован
            self.topmost_state_changed.emit(current_actual_state)
            return

        new_intended_state = enable # Какое состояние мы хотим установить

        if self.user32_lib and self.get_window_long_ptr_func: # Проверяем наличие функций
            hwnd = self._get_hwnd(force_check=True)
            if hwnd:
                insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
                flags = SWP_NOMOVE | SWP_NOSIZE
                api_success = self._set_window_pos_api(hwnd, insert_after, flags)

                if api_success:
                    # Проверяем фактическое состояние после вызова API
                    ex_style = self.get_window_long_ptr_func(hwnd, GWL_EXSTYLE)
                    actual_api_state = bool(ex_style & WS_EX_TOPMOST)
                    logging.info(f"[API] SetWindowPos {'успешно' if actual_api_state == enable else 'не изменил состояние'}. Topmost: {actual_api_state}.")
                    if self._is_win_topmost != actual_api_state:
                        self._is_win_topmost = actual_api_state
                        self.topmost_state_changed.emit(self._is_win_topmost)
                    elif self._is_win_topmost != enable and actual_api_state == enable:
                        # Если состояние не совпадает с enable, но API установило enable, эмитируем
                        self.topmost_state_changed.emit(self._is_win_topmost)
                    return # Выходим, так как API было использовано (успешно или нет)
                else:
                    logging.warning("[API WARN] Вызов SetWindowPos не удался, пробуем Qt fallback.")
                    self._apply_qt_fallback(enable)
            else:
                logging.warning("[WARN][WinAPI] Не удалось получить HWND для SetWindowPos, используем Qt fallback.")
                self._apply_qt_fallback(enable)
        else:
            logging.info("[INFO][WinAPI] WinAPI недоступно, используем Qt fallback.")
            self._apply_qt_fallback(enable)

    def set_topmost_winapi_with_zorder_management(self, enable: bool):
        """
        Улучшенная версия set_topmost_winapi с правильным управлением Z-order.
        Особое внимание снятию always-on-top статуса с полноценной Z-order манипуляцией.
        """
        logging.info(f"[ZORDER][WinAPI] Запрос на установку Topmost с Z-order управлением: {enable}")

        current_actual_state = self.is_win_topmost
        if current_actual_state == enable:
            logging.info(f"[ZORDER][WinAPI] Topmost уже в состоянии {enable}. Ничего не делаем.")
            self.topmost_state_changed.emit(current_actual_state)
            return

        if not self.user32_lib:
            logging.info("[ZORDER][WinAPI] WinAPI недоступно, используем Qt fallback.")
            self._apply_qt_fallback(enable)
            return

        hwnd = self._get_hwnd(force_check=True)
        if not hwnd:
            logging.warning("[ZORDER][WARN] Не удалось получить HWND для SetWindowPos, используем Qt fallback.")
            self._apply_qt_fallback(enable)
            return

        if enable:
            # Установка always-on-top - обычный подход
            insert_after = HWND_TOPMOST
            flags = SWP_NOMOVE | SWP_NOSIZE
            success = self._set_window_pos_api(hwnd, insert_after, flags)

            if success:
                logging.info("[ZORDER][API] Always-on-top установлен успешно")
                ex_style = self.get_window_long_ptr_func(hwnd, GWL_EXSTYLE)
                self._is_win_topmost = bool(ex_style & WS_EX_TOPMOST)
                self.topmost_state_changed.emit(self._is_win_topmost)
            else:
                logging.warning("[ZORDER][API] Вызов SetWindowPos для установки failed, Qt fallback")
                self._apply_qt_fallback(enable)

        else:
            # Снятие always-on-top - упрощенный подход без агрессивной Z-order манипуляции
            logging.info("[ZORDER][API] Начинаем снятие always-on-top без агрессивных Z-order манипуляций")

            # Простое снятие always-on-top флага без дополнительных переключений
            success = self._set_window_pos_api(hwnd, HWND_NOTOPMOST, SWP_NOMOVE | SWP_NOSIZE)
            logging.info(f"[ZORDER][API] Снятие флага always-on-top: {'успешно' if success else 'не удалось'}")

            if success:
                logging.info("[ZORDER][API] Always-on-top снят успешно")
                ex_style = self.get_window_long_ptr_func(hwnd, GWL_EXSTYLE)
                self._is_win_topmost = bool(ex_style & WS_EX_TOPMOST)
                self.topmost_state_changed.emit(self._is_win_topmost)
            else:
                logging.warning("[ZORDER][API] Снятие always-on-top failed, Qt fallback")
                self._apply_qt_fallback(enable)