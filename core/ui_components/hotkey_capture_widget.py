# File: core/ui_components/hotkey_capture_widget.py
from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QApplication
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QKeyEvent, QFocusEvent
import logging

class HotkeyCaptureWidget(QWidget):
    """Виджет для захвата горячих клавиш"""
    hotkey_changed = Signal(str)
    
    def __init__(self, initial_hotkey: str = "", parent=None):
        super().__init__(parent)
        self.current_hotkey = initial_hotkey
        self.capturing = False
        self.pressed_keys = set()
        self.modifiers = Qt.KeyboardModifier.NoModifier  # ИЗМЕНЕНИЕ: Используем правильный тип для модификаторов
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_display)
        self.timer.start(50)  # Обновляем дисплей каждые 50мс
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self.hotkey_display = QLineEdit()
        self.hotkey_display.setText(self.current_hotkey)
        self.hotkey_display.setReadOnly(True)
        self.hotkey_display.setPlaceholderText("Нажмите чтобы задать хоткей")
        
        self.capture_button = QPushButton("Задать")
        self.capture_button.setCheckable(True)
        self.capture_button.toggled.connect(self.toggle_capture)
        
        layout.addWidget(self.hotkey_display)
        layout.addWidget(self.capture_button)
        
    def toggle_capture(self, checked: bool):
        if checked:
            self.start_capture()
        else:
            self.stop_capture()
            
    def start_capture(self):
        self.capturing = True
        self.pressed_keys.clear()
        self.modifiers = Qt.KeyboardModifier.NoModifier
        self.hotkey_display.clear()
        self.hotkey_display.setPlaceholderText("Нажмите комбинацию клавиш...")
        self.capture_button.setText("Отмена")
        # Устанавливаем фильтр событий для всего приложения
        QApplication.instance().installEventFilter(self)
        self.setFocus()
        
    def stop_capture(self):
        self.capturing = False
        self.pressed_keys.clear()
        self.modifiers = Qt.KeyboardModifier.NoModifier
        self.hotkey_display.setPlaceholderText("Нажмите чтобы задать хоткей")
        self.capture_button.setText("Задать")
        self.capture_button.setChecked(False)
        # Убираем фильтр событий
        QApplication.instance().removeEventFilter(self)
        self.clearFocus()
        
    def eventFilter(self, obj, event):
        """Фильтр событий для захвата клавиш"""
        if not self.capturing:
            return super().eventFilter(obj, event)
            
        if event.type() == QEvent.Type.KeyPress:
            self.handle_key_press(event)
            return True
        elif event.type() == QEvent.Type.KeyRelease:
            self.handle_key_release(event)
            return True
            
        return super().eventFilter(obj, event)
        
    def handle_key_press(self, event):
        """Обрабатывает нажатие клавиши"""
        key = event.key()
        
        # Сохраняем модификаторы
        if key == Qt.Key.Key_Control:
            self.modifiers |= Qt.KeyboardModifier.ControlModifier
        elif key == Qt.Key.Key_Shift:
            self.modifiers |= Qt.KeyboardModifier.ShiftModifier
        elif key == Qt.Key.Key_Alt:
            self.modifiers |= Qt.KeyboardModifier.AltModifier
        elif key == Qt.Key.Key_Meta:
            self.modifiers |= Qt.KeyboardModifier.MetaModifier
        else:
            # Добавляем основную клавишу
            self.pressed_keys.add(key)
            
        self._update_display()
        
    def handle_key_release(self, event):
        """Обрабатывает отпускание клавиши"""
        key = event.key()
        
        # Обновляем модификаторы
        if key == Qt.Key.Key_Control:
            self.modifiers &= ~Qt.KeyboardModifier.ControlModifier
        elif key == Qt.Key.Key_Shift:
            self.modifiers &= ~Qt.KeyboardModifier.ShiftModifier
        elif key == Qt.Key.Key_Alt:
            self.modifiers &= ~Qt.KeyboardModifier.AltModifier
        elif key == Qt.Key.Key_Meta:
            self.modifiers &= ~Qt.KeyboardModifier.MetaModifier
        else:
            # Убираем основную клавишу
            self.pressed_keys.discard(key)
            
        # Если все клавиши отпущены, завершаем захват
        if not self.pressed_keys and self.modifiers == Qt.KeyboardModifier.NoModifier:
            hotkey = self.hotkey_display.text()
            if hotkey:
                self.current_hotkey = hotkey
                self.hotkey_changed.emit(hotkey)
            self.stop_capture()
            
    def _update_display(self):
        """Обновляет отображение хоткея"""
        if not self.capturing:
            return
            
        parts = []
        
        # Добавляем модификаторы
        if self.modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if self.modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if self.modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
            
        # Добавляем основные клавиши
        for key in self.pressed_keys:
            key_name = self._get_key_name(key)
            if key_name:
                parts.append(key_name)
                
        if parts:
            hotkey_string = "+".join(parts)
            self.hotkey_display.setText(hotkey_string)
            
    def _get_key_name(self, key):
        """Преобразует код клавиши в строковое представление"""
        key_map = {
            Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2", Qt.Key.Key_3: "3", Qt.Key.Key_4: "4",
            Qt.Key.Key_5: "5", Qt.Key.Key_6: "6", Qt.Key.Key_7: "7", Qt.Key.Key_8: "8", Qt.Key.Key_9: "9",
            Qt.Key.Key_A: "a", Qt.Key.Key_B: "b", Qt.Key.Key_C: "c", Qt.Key.Key_D: "d", Qt.Key.Key_E: "e",
            Qt.Key.Key_F: "f", Qt.Key.Key_G: "g", Qt.Key.Key_H: "h", Qt.Key.Key_I: "i", Qt.Key.Key_J: "j",
            Qt.Key.Key_K: "k", Qt.Key.Key_L: "l", Qt.Key.Key_M: "m", Qt.Key.Key_N: "n", Qt.Key.Key_O: "o",
            Qt.Key.Key_P: "p", Qt.Key.Key_Q: "q", Qt.Key.Key_R: "r", Qt.Key.Key_S: "s", Qt.Key.Key_T: "t",
            Qt.Key.Key_U: "u", Qt.Key.Key_V: "v", Qt.Key.Key_W: "w", Qt.Key.Key_X: "x", Qt.Key.Key_Y: "y",
            Qt.Key.Key_Z: "z",
            Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3", Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6", Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9", Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
            Qt.Key.Key_Escape: "escape", Qt.Key.Key_Tab: "tab", Qt.Key.Key_Backtab: "backtab",
            Qt.Key.Key_Backspace: "backspace", Qt.Key.Key_Return: "return", Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Insert: "insert", Qt.Key.Key_Delete: "delete", Qt.Key.Key_Pause: "pause",
            Qt.Key.Key_Print: "print", Qt.Key.Key_SysReq: "sysreq", Qt.Key.Key_Clear: "clear",
            Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end", Qt.Key.Key_Left: "left", Qt.Key.Key_Up: "up",
            Qt.Key.Key_Right: "right", Qt.Key.Key_Down: "down", Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown", Qt.Key.Key_CapsLock: "capslock", Qt.Key.Key_NumLock: "numlock",
            Qt.Key.Key_ScrollLock: "scrolllock", Qt.Key.Key_Space: "space",
            Qt.Key.Key_Plus: "plus", Qt.Key.Key_Minus: "minus", Qt.Key.Key_Asterisk: "asterisk",
            Qt.Key.Key_Slash: "slash", Qt.Key.Key_Backslash: "backslash", Qt.Key.Key_Bar: "bar",
            Qt.Key.Key_BracketLeft: "bracketleft", Qt.Key.Key_BracketRight: "bracketright",
            Qt.Key.Key_BraceLeft: "braceleft", Qt.Key.Key_BraceRight: "braceright",
            Qt.Key.Key_ParenLeft: "parenleft", Qt.Key.Key_ParenRight: "parenright",
            Qt.Key.Key_Comma: "comma", Qt.Key.Key_Period: "period", Qt.Key.Key_Colon: "colon",
            Qt.Key.Key_Semicolon: "semicolon", Qt.Key.Key_Question: "question", Qt.Key.Key_Exclam: "exclam",
            Qt.Key.Key_QuoteDbl: "quotedbl", Qt.Key.Key_QuoteLeft: "quoteleft", Qt.Key.Key_Apostrophe: "apostrophe",
            Qt.Key.Key_Greater: "greater", Qt.Key.Key_Less: "less", Qt.Key.Key_Equal: "equal",
            Qt.Key.Key_Underscore: "underscore",
        }
        return key_map.get(key, "")
        
    def get_hotkey(self) -> str:
        return self.current_hotkey
        
    def set_hotkey(self, hotkey: str):
        self.current_hotkey = hotkey
        self.hotkey_display.setText(hotkey)
        
    def closeEvent(self, event):
        """Очищаем фильтр при закрытии"""
        if self.capturing:
            self.stop_capture()
        super().closeEvent(event)