# File: delegate.py
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle
from PySide6.QtGui import QPen, QColor, Qt, QPainter
from PySide6.QtCore import QModelIndex, QRect

class HotkeyFocusDelegate(QStyledItemDelegate):
    """
    Делегат, рисующий ТОЛЬКО рамку фокуса поверх стандартной отрисовки.
    Ориентируется на main_window.hotkey_cursor_index.
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        # Синяя рамка толщиной 2 пикселя
        self.focus_pen = QPen(QColor("dodgerblue"), 2)
        # Прозрачное перо для отладки (если нужно убрать рамку)
        # self.focus_pen = QPen(Qt.PenStyle.NoPen)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # print(f"[Delegate Paint] Index: {index.row()}, State: {option.state}") # DEBUG LOG
        # 1. Выполняем стандартную отрисовку элемента
        # Это важно, чтобы фон выделения/наведения рисовался правильно
        super().paint(painter, option, index)

        # 2. Проверяем, нужно ли рисовать рамку фокуса
        # Добавлена проверка на main_window.right_list_widget.isVisible()
        if not self.main_window or not self.main_window.right_list_widget or not self.main_window.right_list_widget.isVisible() or self.main_window.mode == 'min':
            return

        hotkey_index = self.main_window.hotkey_cursor_index
        # print(f"[Delegate Paint] Hotkey Index: {hotkey_index}") # DEBUG LOG

        # 3. Рисуем рамку, если индекс совпадает
        if index.row() == hotkey_index:
            # print(f"[Delegate Paint] Drawing focus border for index {index.row()}") # DEBUG LOG
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True) # Сглаживание
            painter.setPen(self.focus_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush) # Без заливки

            # Рисуем прямоугольник чуть внутри границ элемента
            pen_half_width = self.focus_pen.width() / 2.0
            # Используем adjusted для одинаковых отступов со всех сторон
            rect = option.rect.adjusted(pen_half_width, pen_half_width, -pen_half_width, -pen_half_width)
            painter.drawRect(rect)

            painter.restore()
        # else:
            # print(f"[Delegate Paint] No border for index {index.row()}") # DEBUG LOG