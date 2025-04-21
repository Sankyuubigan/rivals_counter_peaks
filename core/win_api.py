# File: core/win_api.py
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QApplication
import sys
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    # Константы для SetWindowPos
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    # Загружаем user32.dll
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        # Определяем прототип функции SetWindowPos
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, # hWnd
            wintypes.HWND, # hWndInsertAfter
            wintypes.INT,  # X
            wintypes.INT,  # Y
            wintypes.INT,  # cx
            wintypes.INT,  # cy
            wintypes.UINT  # uFlags
        ]
    except Exception as e:
        print(f"[WARN] Не удалось загрузить user32.dll или SetWindowPos: {e}")
        user32 = None # Помечаем, что API недоступно
else:
    user32 = None # Не Windows

from PySide6.QtCore import Qt, QApplication
import time

class WinApiManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.is_win_topmost = False
        self.user32 = user32

    def is_win_topmost(self):
        """Проверяет, находится ли окно в состоянии Topmost."""
        if self.main_window is None:
            return False
        return self.is_win_topmost

    def _get_hwnd(self):
        """Получает HWND окна."""
        hwnd = self.main_window.winId()
        # Ждем HWND, если его нет сразу (окно может еще не быть полностью создано)
        wait_count = 0
        while not hwnd and wait_count < 10:  # Ждем до 1 секунды (10 * 100мс)
            print("[WARN] HWND не получен, ожидание...")
            QApplication.processEvents()  # Обрабатываем события
            time.sleep(0.1)
            hwnd = self.main_window.winId()
            wait_count += 1
        return hwnd

    def _set_window_pos(self, hwnd, insert_after, flags):
        """Вызывает WinAPI SetWindowPos."""
        print(f"[API] Вызов SetWindowPos: HWND={hwnd}, InsertAfter={'TOPMOST' if insert_after == HWND_TOPMOST else 'NOTOPMOST'}, Flags={flags}")
        success = self.user32.SetWindowPos(int(hwnd), insert_after, 0, 0, 0, 0, flags)
        return success

    def _set_window_topmost(self, hwnd):
        """Устанавливает окну состояние Topmost."""
        
        success = self._set_window_pos(hwnd, HWND_TOPMOST, SWP_NOMOVE | SWP_NOSIZE)
        if success:
            print(f"[API] SetWindowPos успешно: Topmost включен.")
            self.is_win_topmost = True
        else:
            error_code = ctypes.get_last_error()
            print(f"[API ERROR] SetWindowPos не удался: Код ошибки {error_code}, user32: {self.user32}")

    def _set_window_not_topmost(self, hwnd):
        """Снимает с окна состояние Topmost."""
        success = self._set_window_pos(hwnd, HWND_NOTOPMOST, SWP_NOMOVE | SWP_NOSIZE)
        if success:
            print(f"[API] SetWindowPos успешно: Topmost выключен.")
            self.is_win_topmost = False
        else:
            error_code = ctypes.get_last_error()
            print(f"[API ERROR] SetWindowPos не удался: Код ошибки {error_code}, user32: {self.user32}")

    def set_topmost_winapi(self, enable: bool):
        """Устанавливает или снимает состояние HWND_TOPMOST с помощью WinAPI."""
        if not user32: # Если API недоступно (не Windows или ошибка загрузки)
            print("[INFO] WinAPI недоступно. Используется стандартный флаг Qt.")
            # Возвращаемся к стандартному поведению Qt как запасной вариант
            current_flags = self.main_window.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            if enable != flag_set:
                self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                self.is_win_topmost = enable
                # Показываем окно, чтобы флаг применился, но делаем это безопасно
                try:
                    if self.main_window.isVisible(): self.main_window.show()
                except RuntimeError: pass # Игнорируем ошибку, если виджет уже удален
            # Обновляем кнопку в любом случае
            self._update_topmost_button_visuals()
            return # Выходим, т.к. WinAPI не используется

        hwnd = self._get_hwnd()

        if not hwnd:
            print("[ERROR] Не удалось получить HWND окна для SetWindowPos после ожидания.")
            # Пытаемся использовать Qt как fallback
            current_flags = self.main_window.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
            self.is_win_topmost = enable
            try: if self.main_window.isVisible(): self.main_window.show()
            except RuntimeError: pass
            self._update_topmost_button_visuals()
            return

        # Определяем параметры для SetWindowPos
        insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
        flags = SWP_NOMOVE | SWP_NOSIZE # Не меняем позицию и размер

        if enable:
            self._set_window_topmost(hwnd)
        else:
            self._set_window_not_topmost(hwnd)

        if not self.is_win_topmost: # Пытаемся использовать стандартный флаг Qt как fallback
            print("[API ERROR] Попытка использовать Qt.WindowStaysOnTopHint как fallback.")
            current_flags = self.main_window.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            if enable != flag_set:
                self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                self._is_win_topmost = enable
                self.is_win_topmost = enable
                try:
                    if self.main_window.isVisible(): self.main_window.show()
                except RuntimeError: pass
            else: # Если флаг уже был в нужном состоянии
                self.is_win_topmost = enable # Устанавливаем флаг в соответствии с попыткой
       # Обновляем кнопку в top_panel после изменения состояния
        self._update_topmost_button_visuals()

    def _update_topmost_button_visuals(self):
        """Обновляет вид кнопки topmost."""
        try:
            if self.main_window.top_frame:
                topmost_button = self.main_window.top_frame.findChild(QPushButton, "topmost_button")
                if topmost_button:
                    # Вызываем метод обновления, сохраненный в кнопке
                    update_func = getattr(topmost_button, '_update_visual_state', None)
                    if callable(update_func):
                        update_func()
        except Exception as e:
            print(f"[WARN] Не удалось обновить вид кнопки topmost: {e}")

    