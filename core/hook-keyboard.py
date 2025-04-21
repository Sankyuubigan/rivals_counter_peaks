import keyboard

from core.win_api import WinApiManager


class HookKeyboard:
    def __init__(self, hotkeys: Hotkeys):
        self._hotkeys = hotkeys

    def _check_topmost_key(self, key):
        """
        Проверяет, нажата ли клавиша для переключения topmost.
        """
        if key == self._hotkeys.topmost_key:
            WinApiManager.toggle_topmost_winapi()
            return True
        return False

    def _check_recognition_key(self, key):
        """
        Проверяет, нажата ли клавиша для распознавания.
        """
        if key == self._hotkeys.recognition_key:
            self._hotkeys.trigger_recognition()
            return True
        return False

    def _check_change_mode_key(self, key):
        """
        Проверяет, нажата ли клавиша для смены режима.
        """
        if key == self._hotkeys.change_mode_key:
            self._hotkeys.change_mode()
            return True
        return False

    def _on_press(self, event):
        """
        Обработчик события нажатия клавиши.
        """
        key = event.name
        if self._check_topmost_key(key):
            return
        if self._check_recognition_key(key):
            return
        if self._check_change_mode_key(key):
            return

    def listen(self):
        keyboard.on_press(self._on_press)
