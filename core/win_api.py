# File: core/win_api.py
import sys
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QPushButton, QApplication, QWidget

# Проверка платформы и импорт WinAPI
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, wintypes.INT, wintypes.INT,
            wintypes.INT, wintypes.INT, wintypes.UINT
        ]
        print("[WinAPI] user32.dll и SetWindowPos загружены успешно.")
    except Exception as e:
        print(f"[ERROR][WinAPI] Ошибка при загрузке user32.dll или SetWindowPos: {e}")
        user32 = None
else:
    print("[WinAPI] Платформа не Windows, WinAPI недоступно.")
    user32 = None

class WinApiManager:
    """Управляет состоянием Topmost окна с помощью WinAPI."""
    def __init__(self, main_window: QWidget):
        self.main_window = main_window
        self._is_win_topmost = False
        self.user32 = user32
        self._last_hwnd_check_time = 0
        self._hwnd = None

    @property
    def is_win_topmost(self) -> bool:
        return self._is_win_topmost

    def _get_hwnd(self, force_check=False) -> int | None:
        current_time = time.time()
        if force_check or self._hwnd is None or current_time - self._last_hwnd_check_time > 1.0:
            self._last_hwnd_check_time = current_time
            try:
                self._hwnd = int(self.main_window.winId()) if self.main_window else 0
                if not self._hwnd: self._hwnd = None
            except Exception as e:
                 print(f"[ERROR][WinAPI] Ошибка при получении winId(): {e}")
                 self._hwnd = None
        return self._hwnd

    def _set_window_pos_api(self, hwnd: int, insert_after: int, flags: int) -> bool:
        if not self.user32 or not hasattr(self.user32, 'SetWindowPos'): return False
        try:
            print(f"[API] Вызов SetWindowPos: HWND={hwnd}, InsertAfter={'TOPMOST' if insert_after == HWND_TOPMOST else 'NOTOPMOST'}, Flags={flags}")
            success = self.user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
            if not success:
                 error_code = ctypes.get_last_error()
                 print(f"[API ERROR] SetWindowPos не удался: Код ошибки {error_code}")
                 ctypes.set_last_error(0)
            return bool(success)
        except Exception as e:
            print(f"[ERROR][WinAPI] Исключение при вызове SetWindowPos: {e}")
            return False

    def _apply_qt_fallback(self, enable: bool):
        print("[INFO][WinAPI] Попытка использовать Qt.WindowStaysOnTopHint как fallback.")
        try:
            current_flags = self.main_window.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            if enable != flag_set:
                self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                if self.main_window.isVisible(): self.main_window.show()
            self._is_win_topmost = enable
            QTimer.singleShot(0, self._update_topmost_button_visuals)
        except RuntimeError: print("[WARN][WinAPI] Окно уже удалено, не удалось применить Qt fallback.")
        except Exception as e: print(f"[ERROR][WinAPI] Ошибка при применении Qt fallback: {e}")

    def set_topmost_winapi(self, enable: bool):
        print(f"[ACTION][WinAPI] Запрос на установку Topmost: {enable}")
        api_success = False
        if self.user32:
            hwnd = self._get_hwnd(force_check=True)
            if hwnd:
                insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
                flags = SWP_NOMOVE | SWP_NOSIZE
                api_success = self._set_window_pos_api(hwnd, insert_after, flags)
                if api_success:
                    print(f"[API] SetWindowPos успешно: Topmost {'включен' if enable else 'выключен'}.")
                    self._is_win_topmost = enable
                else:
                    print("[API ERROR] Вызов SetWindowPos не удался.")
                    self._is_win_topmost = enable # Обновляем флаг до желаемого состояния
            else:
                print("[WARN][WinAPI] Не удалось получить HWND для SetWindowPos.")
                self._apply_qt_fallback(enable)
                return
        else:
            print("[INFO][WinAPI] WinAPI недоступно.")
            self._apply_qt_fallback(enable)
            return
        QTimer.singleShot(0, self._update_topmost_button_visuals)

    def _update_topmost_button_visuals(self):
        try:
            if self.main_window and hasattr(self.main_window, 'top_panel_instance') and self.main_window.top_panel_instance:
                button = getattr(self.main_window.top_panel_instance, 'topmost_button', None)
                if button:
                    update_func = getattr(button, '_update_visual_state', None)
                    if callable(update_func): update_func()
        except RuntimeError: print("[WARN][WinAPI] Окно или панель удалены, не удалось обновить кнопку topmost.")
        except Exception as e: print(f"[WARN][WinAPI] Не удалось обновить вид кнопки topmost: {e}")

def is_window_topmost(window: QWidget) -> bool:
    if hasattr(window, 'win_api_manager') and isinstance(window.win_api_manager, WinApiManager):
        return window.win_api_manager.is_win_topmost
    print("[WARN] Атрибут 'win_api_manager' не найден в окне. Используется Qt fallback для is_window_topmost.")
    return bool(window.windowFlags() & Qt.WindowStaysOnTopHint)
