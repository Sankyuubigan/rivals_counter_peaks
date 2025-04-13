# File: delegate.py
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle
from PySide6.QtGui import QPen, QColor, Qt, QPainter
from PySide6.QtCore import QModelIndex

class HotkeyFocusDelegate(QStyledItemDelegate):
    """
    Делегат, рисующий ТОЛЬКО рамку фокуса поверх стандартной отрисовки.
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        # Синяя рамка толщиной 2 пикселя
        self.focus_pen = QPen(QColor("dodgerblue"), 2)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # 1. Выполняем стандартную отрисовку элемента (фон, иконка, текст, выделение, ховер)
        super().paint(painter, option, index)

        # 2. Проверяем, нужно ли рисовать рамку фокуса
        if not self.main_window or not self.main_window.right_list_widget or self.main_window.mode == 'min':
            return

        hotkey_index = self.main_window.hotkey_cursor_index

        # 3. Рисуем рамку, если индекс совпадает
        if index.row() == hotkey_index:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True) # Сглаживание
            painter.setPen(self.focus_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush) # Без заливки

            # Рисуем прямоугольник чуть внутри границ элемента
            pen_half_width = self.focus_pen.width() / 2.0
            rect = option.rect.adjusted(pen_half_width, pen_half_width, -pen_half_width, -pen_half_width)
            painter.drawRect(rect)

            painter.restore()