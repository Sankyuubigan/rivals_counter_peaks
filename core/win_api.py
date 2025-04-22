# File: core/win_api.py
import sys
import time
from PySide6.QtCore import Qt, QTimer # Добавлен QTimer
from PySide6.QtWidgets import QPushButton, QApplication, QWidget

# Проверка платформы и импорт WinAPI
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
        print("[WinAPI] user32.dll и SetWindowPos загружены успешно.")
    except OSError as e:
        print(f"[ERROR][WinAPI] Не удалось загрузить user32.dll: {e}")
        user32 = None
    except AttributeError as e:
         print(f"[ERROR][WinAPI] Функция SetWindowPos не найдена в user32.dll: {e}")
         user32 = None
    except Exception as e:
        print(f"[ERROR][WinAPI] Неизвестная ошибка при загрузке user32.dll: {e}")
        user32 = None
else:
    print("[WinAPI] Платформа не Windows, WinAPI недоступно.")
    user32 = None # Не Windows

class WinApiManager:
    """Управляет состоянием Topmost окна с помощью WinAPI."""

    def __init__(self, main_window: QWidget): # Используем QWidget для type hinting
        self.main_window = main_window
        self._is_win_topmost = False # Внутренний флаг состояния
        self.user32 = user32 # Сохраняем ссылку на библиотеку
        self._last_hwnd_check_time = 0 # Для троттлинга проверки HWND
        self._hwnd = None # Кэшируем HWND

    @property
    def is_win_topmost(self) -> bool:
        """Возвращает текущее состояние topmost (внутренний флаг)."""
        return self._is_win_topmost

    def _get_hwnd(self, force_check=False) -> int | None:
        """
        Получает HWND окна с кэшированием и троттлингом.
        force_check=True для принудительной проверки winId().
        """
        current_time = time.time()
        # Проверяем HWND не чаще раза в секунду или если его еще нет или принудительно
        if force_check or self._hwnd is None or current_time - self._last_hwnd_check_time > 1.0:
            self._last_hwnd_check_time = current_time
            try:
                # winId() может возвращать 0, если окно еще не создано или уже уничтожено
                self._hwnd = int(self.main_window.winId()) if self.main_window else 0
                if not self._hwnd:
                    # print("[WARN][WinAPI] _get_hwnd: winId() вернул 0.")
                    self._hwnd = None # Сбрасываем кэш, если HWND стал невалидным
            except Exception as e:
                 print(f"[ERROR][WinAPI] Ошибка при получении winId(): {e}")
                 self._hwnd = None
        return self._hwnd

    def _set_window_pos_api(self, hwnd: int, insert_after: int, flags: int) -> bool:
        """Безопасный вызов SetWindowPos."""
        if not self.user32 or not hasattr(self.user32, 'SetWindowPos'):
            print("[ERROR][WinAPI] user32.dll или SetWindowPos недоступны для вызова.")
            return False
        try:
            print(f"[API] Вызов SetWindowPos: HWND={hwnd}, InsertAfter={'TOPMOST' if insert_after == HWND_TOPMOST else 'NOTOPMOST'}, Flags={flags}")
            success = self.user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
            if not success:
                 error_code = ctypes.get_last_error()
                 print(f"[API ERROR] SetWindowPos не удался: Код ошибки {error_code}")
                 # Сбрасываем ошибку, чтобы она не влияла на следующие вызовы
                 ctypes.set_last_error(0)
            return bool(success)
        except Exception as e:
            print(f"[ERROR][WinAPI] Исключение при вызове SetWindowPos: {e}")
            return False

    def _apply_qt_fallback(self, enable: bool):
        """Применяет стандартный флаг Qt как запасной вариант."""
        print("[INFO][WinAPI] Попытка использовать Qt.WindowStaysOnTopHint как fallback.")
        try:
            current_flags = self.main_window.windowFlags()
            flag_set = bool(current_flags & Qt.WindowStaysOnTopHint)
            if enable != flag_set:
                self.main_window.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                if self.main_window.isVisible(): self.main_window.show() # Показать для применения флага
            self._is_win_topmost = enable # Обновляем внутренний флаг в любом случае
            # Обновляем вид кнопки после fallback
            QTimer.singleShot(0, self._update_topmost_button_visuals)
        except RuntimeError:
            print("[WARN][WinAPI] Окно уже удалено, не удалось применить Qt fallback.")
        except Exception as e:
            print(f"[ERROR][WinAPI] Ошибка при применении Qt fallback: {e}")

    def set_topmost_winapi(self, enable: bool):
        """Устанавливает или снимает состояние HWND_TOPMOST с помощью WinAPI или Qt fallback."""
        print(f"[ACTION][WinAPI] Запрос на установку Topmost: {enable}")

        # --- Попытка использовать WinAPI ---
        api_success = False
        if self.user32:
            hwnd = self._get_hwnd(force_check=True) # Принудительно проверяем HWND при смене состояния
            if hwnd:
                insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
                flags = SWP_NOMOVE | SWP_NOSIZE
                api_success = self._set_window_pos_api(hwnd, insert_after, flags)
                if api_success:
                    print(f"[API] SetWindowPos успешно: Topmost {'включен' if enable else 'выключен'}.")
                    self._is_win_topmost = enable
                else:
                    print("[API ERROR] Вызов SetWindowPos не удался.")
                    # Здесь можно не вызывать fallback, если API доступно, но вызов не прошел
                    # Возможно, проблема в правах или конфликте с другим окном
                    # Обновляем флаг до желаемого состояния, чтобы UI соответствовал попытке
                    self._is_win_topmost = enable

            else:
                print("[WARN][WinAPI] Не удалось получить HWND для SetWindowPos.")
                # Если HWND не получен, используем Qt fallback
                self._apply_qt_fallback(enable)
                return # Выходим после fallback

        else:
            # Если WinAPI вообще недоступно, используем Qt fallback
            print("[INFO][WinAPI] WinAPI недоступно.")
            self._apply_qt_fallback(enable)
            return # Выходим после fallback

        # --- Обновление UI после попытки WinAPI (даже если неуспешной) ---
        # Обновляем вид кнопки, чтобы он отражал _is_win_topmost
        # Используем QTimer, чтобы гарантировать выполнение в GUI потоке
        QTimer.singleShot(0, self._update_topmost_button_visuals)

    def _update_topmost_button_visuals(self):
        """Обновляет вид кнопки topmost в главном окне."""
        # Этот метод вызывается из set_topmost_winapi
        try:
            # Находим кнопку и вызываем ее внутренний метод обновления
            if self.main_window and self.main_window.top_panel_instance:
                button = self.main_window.top_panel_instance.topmost_button
                if button:
                    update_func = getattr(button, '_update_visual_state', None)
                    if callable(update_func):
                        update_func()
        except RuntimeError:
             print("[WARN][WinAPI] Окно или панель удалены, не удалось обновить кнопку topmost.")
        except Exception as e:
            print(f"[WARN][WinAPI] Не удалось обновить вид кнопки topmost: {e}")

def is_window_topmost(window: QWidget) -> bool:
    """Проверяет, находится ли окно в состоянии Topmost (используя менеджер)."""
    if hasattr(window, 'win_api_manager') and isinstance(window.win_api_manager, WinApiManager):
        return window.win_api_manager.is_win_topmost
    # Fallback на Qt флаг, если менеджера нет (маловероятно)
    return bool(window.windowFlags() & Qt.WindowStaysOnTopHint)
