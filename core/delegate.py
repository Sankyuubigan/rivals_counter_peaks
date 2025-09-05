# File: delegate.py
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from PySide6.QtGui import QPen, QColor, QPainter
from PySide6.QtCore import Qt, QModelIndex

class HotkeyFocusDelegate(QStyledItemDelegate):
    """
    Делегат, рисующий ТОЛЬКО рамку фокуса поверх стандартной отрисовки.
    Ориентируется на main_window.hotkey_cursor_index.
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.focus_pen = QPen(QColor("dodgerblue"), 2)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # 1. Выполняем стандартную отрисовку элемента
        super().paint(painter, option, index)

        # 2. Проверяем, нужно ли рисовать рамку фокуса
        if not self.main_window or not hasattr(self.main_window, 'right_list_widget') or \
           not self.main_window.right_list_widget or not self.main_window.right_list_widget.isVisible() or \
           getattr(self.main_window, 'mode', '') == 'min':
            return

        hotkey_index = getattr(self.main_window, 'hotkey_cursor_index', -1)

        # 3. Рисуем рамку, если индекс совпадает
        if index.row() == hotkey_index:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(self.focus_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            pen_half_width = self.focus_pen.width() / 2.0
            rect = option.rect.adjusted(pen_half_width, pen_half_width, -pen_half_width, -pen_half_width)
            painter.drawRect(rect)
            painter.restore()