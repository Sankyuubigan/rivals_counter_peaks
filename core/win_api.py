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
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x00000008
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        # --- SetWindowPos ---
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, wintypes.INT, wintypes.INT,
            wintypes.INT, wintypes.INT, wintypes.UINT
        ]
        # --- GetWindowLongPtr (for 32/64 bit compatibility) ---
        if ctypes.sizeof(ctypes.c_void_p) == 8: # 64-bit
            GetWindowLongPtr = user32.GetWindowLongPtrW
        else: # 32-bit
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
# --- ---

class WinApiManager(QObject):
    """Управляет состоянием Topmost окна с помощью WinAPI."""
    # Сигнал, испускаемый ПОСЛЕ изменения состояния topmost
    topmost_state_changed = Signal(bool)

    def __init__(self, main_window: QWidget):
        super().__init__(main_window) # Вызываем конструктор родителя (QObject)
        self.main_window = main_window
        # _is_win_topmost будет хранить фактическое состояние (после API вызова или fallback)
        self._is_win_topmost = False
        self.user32 = user32
        self._last_hwnd_check_time = 0
        self._hwnd = None
        # Проверяем начальное состояние при запуске
        self._check_initial_topmost_state()

    def _check_initial_topmost_state(self):
        """Проверяет начальное состояние topmost при инициализации."""
        qt_flag_state = False
        try:
            if self.main_window: qt_flag_state = bool(self.main_window.windowFlags() & Qt.WindowStaysOnTopHint)
        except RuntimeError: logging.warning("[WinAPI Initial Check] Окно уже удалено при проверке флага Qt.")

        if self.user32 and GetWindowLongPtr:
            hwnd = self._get_hwnd(force_check=True)
            logging.debug(f"[WinAPI Initial Check] Получен HWND: {hwnd}")
            if hwnd:
                try:
                    ex_style = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
                    # Устанавливаем начальное значение _is_win_topmost на основе WinAPI
                    self._is_win_topmost = bool(ex_style & WS_EX_TOPMOST)
                    logging.info(f"[WinAPI Initial Check] HWND={hwnd}, ExStyle={ex_style:#x}, WS_EX_TOPMOST set={self._is_win_topmost}")
                except Exception as e:
                    logging.error(f"[ERROR][WinAPI] Ошибка при вызове GetWindowLongPtr для начальной проверки: {e}")
                    # В случае ошибки API используем состояние флага Qt
                    self._is_win_topmost = qt_flag_state
                    logging.warning(f"[WinAPI] GetWindowLongPtr failed, fallback to Qt flag state: {self._is_win_topmost}")
            else:
                 # Если HWND недоступен, используем состояние флага Qt
                 self._is_win_topmost = qt_flag_state
                 logging.warning(f"[WinAPI] HWND not available, fallback to Qt flag state: {self._is_win_topmost}")
        else:
             # Если WinAPI вообще недоступно, используем состояние флага Qt
             self._is_win_topmost = qt_flag_state
             logging.warning(f"[WinAPI] WinAPI not available, fallback to Qt flag state: {self._is_win_topmost}")

        logging.info(f"[WinAPI] Initial topmost state determined as: {self._is_win_topmost}")
        # Испускаем сигнал с начальным состоянием, чтобы кнопка обновилась сразу
        self.topmost_state_changed.emit(self._is_win_topmost)

    def _log_window_style(self, hwnd: int | None, when: str):
       """Логирует текущий WS_EX_TOPMOST стиль окна."""
       if not hwnd or not self.user32 or not GetWindowLongPtr:
           logging.debug(f"[WinAPI Style Log {when}] HWND invalid or WinAPI not available.")
           return
       try:
           ex_style = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
           is_set = bool(ex_style & WS_EX_TOPMOST)
           logging.info(f"[WinAPI Style Log {when}] HWND={hwnd}, ExStyle={ex_style:#x}, WS_EX_TOPMOST is set: {is_set}")
       except Exception as e:
           logging.error(f"[ERROR][WinAPI Style Log {when}] Ошибка при вызове GetWindowLongPtr: {e}")

    @property
    def is_win_topmost(self) -> bool:
        """Возвращает последнее известное состояние topmost."""
        return self._is_win_topmost

    def _get_hwnd(self, force_check=False) -> int | None:
        """Получает HWND окна, с кешированием."""
        current_time = time.time()
        # Обновляем HWND, если прошло > 0.5 сек или принудительно
        if force_check or self._hwnd is None or current_time - self._last_hwnd_check_time > 0.5:
            self._last_hwnd_check_time = current_time
            try:
                # Получаем winId только если окно видимо
                if self.main_window and self.main_window.isVisible():
                    self._hwnd = int(self.main_window.winId())
                    if not self._hwnd: self._hwnd = None # Убедимся, что 0 превращается в None
                else: self._hwnd = None
            except RuntimeError:
                 logging.warning("[WinAPI] Ошибка Runtime: Окно удалено при получении winId().")
                 self._hwnd = None
            except Exception as e:
                 logging.error(f"[ERROR][WinAPI] Ошибка при получении winId(): {e}")
                 self._hwnd = None
        return self._hwnd

    def _set_window_pos_api(self, hwnd: int, insert_after: int, flags: int) -> bool:
        """Вызывает WinAPI функцию SetWindowPos."""
        if not self.user32 or not hasattr(self.user32, 'SetWindowPos'): return False
        try:
            logging.info(f"[API] Вызов SetWindowPos: HWND={hwnd}, InsertAfter={'TOPMOST' if insert_after == HWND_TOPMOST else 'NOTOPMOST'}, Flags={flags:#04x}")
            success = self.user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
            if not success:
                 error_code = ctypes.get_last_error()
                 error_msg = "N/A"
                 try:
                     error_msg = ctypes.FormatError(error_code).strip()
                 except Exception as fmt_e:
                     logging.error(f"Failed to format WinAPI error code {error_code}: {fmt_e}")
                 logging.error(f"[API ERROR] SetWindowPos не удался: Код {error_code} - {error_msg}")
                 ctypes.set_last_error(0) # Сбрасываем ошибку
            return bool(success)
        except Exception as e:
            logging.error(f"[ERROR][WinAPI] Исключение при вызове SetWindowPos: {e}", exc_info=True)
            return False

    def _apply_qt_fallback(self, enable: bool):
        """Применяет Qt флаг WindowStaysOnTopHint как запасной вариант."""
        logging.warning("[WinAPI] Используется Qt.WindowStaysOnTopHint как fallback.")
        try:
            if not self.main_window:
                logging.error("[WinAPI Fallback] Main window object is None.")
                return
            current_flags = self.main_window.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            needs_update = enable != flag_set
            if needs_update:
                logging.info(f"[WinAPI Fallback] Установка Qt.WindowStaysOnTopHint: {enable}")
                self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                # Переприменяем флаги, показывая окно (оно может скрыться при setWindowFlag)
                if self.main_window.isVisible(): self.main_window.show()
            else:
                 logging.debug(f"[WinAPI Fallback] Qt.WindowStaysOnTopHint уже в состоянии {enable}.")

            # Обновляем внутреннее состояние и испускаем сигнал, если оно изменилось
            if self._is_win_topmost != enable:
                self._is_win_topmost = enable
                self.topmost_state_changed.emit(self._is_win_topmost)

        except RuntimeError: logging.warning("[WinAPI Fallback] Окно уже удалено, не удалось применить Qt fallback.")
        except Exception as e: logging.error(f"[ERROR][WinAPI] Ошибка при применении Qt fallback: {e}", exc_info=True)

    def set_topmost_winapi(self, enable: bool):
        """Устанавливает или снимает состояние Topmost с использованием WinAPI или Qt Fallback."""
        logging.info(f"[ACTION][WinAPI] Запрос на установку Topmost: {enable}")
        # Сначала предполагаем, что состояние не изменится
        new_state = self._is_win_topmost

        if self.user32:
            hwnd = self._get_hwnd(force_check=True)
            logging.debug(f"[WinAPI Set] Получен HWND: {hwnd}")
            if hwnd:
                self._log_window_style(hwnd, "before SetWindowPos")
                insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
                flags = SWP_NOMOVE | SWP_NOSIZE
                api_success = self._set_window_pos_api(hwnd, insert_after, flags)
                self._log_window_style(hwnd, "after SetWindowPos")

                if api_success:
                    logging.info(f"[API] SetWindowPos успешно: Topmost {'включен' if enable else 'выключен'}.")
                    new_state = enable # Состояние успешно изменено через API
                else:
                    logging.warning("[API WARN] Вызов SetWindowPos не удался, пробуем Qt fallback.")
                    self._apply_qt_fallback(enable) # Fallback сам обновит _is_win_topmost и испустит сигнал
                    return # Выходим, т.к. fallback обработал
            else:
                logging.warning("[WARN][WinAPI] Не удалось получить HWND для SetWindowPos, используем Qt fallback.")
                self._apply_qt_fallback(enable) # Fallback сам обновит _is_win_topmost и испустит сигнал
                return # Выходим
        else:
            logging.info("[INFO][WinAPI] WinAPI недоступно, используем Qt fallback.")
            self._apply_qt_fallback(enable) # Fallback сам обновит _is_win_topmost и испустит сигнал
            return # Выходим

        # Если мы дошли сюда, значит API вызов был (успешный), но fallback не использовался.
        # Обновляем состояние и испускаем сигнал, если оно изменилось.
        if self._is_win_topmost != new_state:
            self._is_win_topmost = new_state
            logging.info(f"[WinAPI] Состояние Topmost изменено на {self._is_win_topmost}, испускаем сигнал.")
            self.topmost_state_changed.emit(self._is_win_topmost)
        else:
            logging.debug(f"[WinAPI] Состояние Topmost не изменилось (осталось {self._is_win_topmost}).")


# Глобальная функция для проверки (использует менеджер окна)
def is_window_topmost(window: QWidget) -> bool:
    """Проверяет, установлено ли окно как Topmost (используя WinApiManager)."""
    if hasattr(window, 'win_api_manager') and isinstance(window.win_api_manager, WinApiManager):
        return window.win_api_manager.is_win_topmost
    # Fallback, если менеджер недоступен
    logging.warning("[WARN] Атрибут 'win_api_manager' не найден в окне. Используется Qt fallback для is_window_topmost.")
    try: return bool(window.windowFlags() & Qt.WindowStaysOnTopHint)
    except RuntimeError: return False