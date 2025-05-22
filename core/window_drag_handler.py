# File: core/window_drag_handler.py
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget # Для type hinting

class WindowDragHandler:
    def __init__(self, window: QWidget, top_frame_provider: callable):
        """
        Инициализатор.
        window: ссылка на главное окно (или виджет, который нужно перетаскивать).
        top_frame_provider: функция, которая возвращает top_frame (или None).
        """
        self.window = window
        self.top_frame_provider = top_frame_provider # Функция для получения top_frame
        self._mouse_pressed = False
        self._old_pos: QPoint | None = None

    def mousePressEvent(self, event: QMouseEvent):
        # Проверяем, что это MainWindow и у него есть атрибут 'mode'
        is_min_mode = hasattr(self.window, 'mode') and self.window.mode == "min"
        top_frame = self.top_frame_provider()

        if is_min_mode and top_frame and top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton:
                 # Проверяем, не кликнули ли по кнопке закрытия (если она есть на top_frame)
                close_button = getattr(self.window, 'close_button', None) # Предполагаем, что close_button - атрибут window
                if close_button and close_button.isVisible() and \
                   close_button.geometry().contains(top_frame.mapFromGlobal(event.globalPosition().toPoint())):
                    return False # Не обрабатываем, передаем дальше

                self._mouse_pressed = True
                self._old_pos = event.globalPosition().toPoint()
                event.accept()
                return True # Событие обработано
        self._mouse_pressed = False
        return False # Событие не обработано

    def mouseMoveEvent(self, event: QMouseEvent):
        is_min_mode = hasattr(self.window, 'mode') and self.window.mode == "min"
        if is_min_mode and self._mouse_pressed and self._old_pos is not None:
            top_frame = self.top_frame_provider()
            close_button = getattr(self.window, 'close_button', None)
            if top_frame and close_button and close_button.isVisible() and \
               close_button.geometry().contains(top_frame.mapFromGlobal(event.globalPosition().toPoint())):
                 return False # Не перетаскиваем, если мышь над кнопкой

            delta = event.globalPosition().toPoint() - self._old_pos
            self.window.move(self.window.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()
            event.accept()
            return True
        return False

    def mouseReleaseEvent(self, event: QMouseEvent):
        is_min_mode = hasattr(self.window, 'mode') and self.window.mode == "min"
        if is_min_mode and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False
            self._old_pos = None
            
            top_frame = self.top_frame_provider()
            close_button = getattr(self.window, 'close_button', None)
            if top_frame and close_button and close_button.isVisible() and \
               close_button.geometry().contains(top_frame.mapFromGlobal(event.globalPosition().toPoint())):
                return False # Передаем дальше для клика по кнопке

            event.accept()
            return True
        return False
