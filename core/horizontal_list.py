# File: core/horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QBrush, QPixmap
from core.images_load import is_invalid_pixmap
import math
import logging
class IconWithRatingWidget(QWidget):
    """Виджет для отображения иконки героя с его рейтингом."""
    def __init__(self, pixmap: QPixmap, rating: float, is_in_effective_team: bool, is_enemy: bool, tooltip: str, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.rating_text = f"{rating:.1f}"
        self.is_in_effective_team = is_in_effective_team
        self.is_enemy = is_enemy
        self.setToolTip(tooltip)
        
        if not is_invalid_pixmap(self.pixmap):
            # ИСПРАВЛЕНИЕ: Устанавливаем минимальный размер на основе размера иконки
            self.setMinimumSize(pixmap.size())
        
        self.font = QFont()
        self.font.setPointSize(4)  # Маленький размер шрифта для рейтинга на иконках
        self.font.setBold(True)
        self.fm = QFontMetrics(self.font)
        self.border_pen = QPen(Qt.PenStyle.NoPen)
        self.border_width = 1
        
        # Подсветка роли (для tray window)
        self._highlighted = False
        self._highlight_color = QColor()
        self._highlight_outer_color = QColor()
        
        # Показывать ли рейтинг (по умолчанию True, для трея можно выключить)
        self.show_rating = True
        
    def update_rating(self, rating: float, tooltip: str = None):
        """Обновляет рейтинг и подсказку виджета."""
        self.rating_text = f"{rating:.1f}"
        if tooltip is not None:
            self.setToolTip(tooltip)
        self.update()  # Перерисовываем виджет с новым рейтингом
        
    def set_border(self, color: QColor, width: int):
        self.border_pen = QPen(color, width)
        self.border_width = width
        self.update()
    
    def set_highlight(self, highlighted: bool, highlight_color: QColor = None, outer_color: QColor = None):
        """Включает/выключает подсветку героя (жирная рамка для рекомендуемой роли).
        
        При highlight=True рисуется двойная рамка:
          - Внешняя (6px) цвета outer_color (обычно цвет фона трея)
          - Внутренняя (3px) цвета highlight_color (цвет роли)
        Визуально это выглядит как рамка роли толщиной 6px, но размер виджета не меняется.
        """
        self._highlighted = highlighted
        if highlighted:
            self._highlight_color = highlight_color or QColor("#FFD700")
            self._highlight_outer_color = outer_color or QColor(40, 40, 40, 200)
        else:
            self._highlight_color = QColor()
            self._highlight_outer_color = QColor()
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        widget_rect = self.rect()
        
        if not is_invalid_pixmap(self.pixmap):
            # ИСПРАВЛЕНИЕ: Центрируем иконку без растягивания
            pixmap_size = self.pixmap.size()
            x = (widget_rect.width() - pixmap_size.width()) // 2
            y = (widget_rect.height() - pixmap_size.height()) // 2
            painter.drawPixmap(x, y, self.pixmap)
        
        # --- Рамка роли (всегда рисуется) ---
        if self.border_pen.style() != Qt.PenStyle.NoPen:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(self.border_pen)
            border_rect = widget_rect.adjusted(self.border_width / 2, self.border_width / 2, -self.border_width / 2, -self.border_width / 2)
            painter.drawRoundedRect(border_rect, 3, 3)
        
        # --- Подсветка рекомендуемой роли (двойная рамка) ---
        if self._highlighted:
            outer_width = 6
            inner_width = 3
            
            # Внешняя рамка (6px) — цвет подсветки (роль)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            outer_pen = QPen(self._highlight_color, outer_width)
            outer_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(outer_pen)
            outer_rect = widget_rect.adjusted(outer_width / 2, outer_width / 2, -outer_width / 2, -outer_width / 2)
            painter.drawRoundedRect(outer_rect, 4, 4)
            
            # Внутренняя рамка (3px) — цвет роли, чтобы сохранить оригинальный вид
            inner_pen = QPen(self.border_pen.color() if self.border_pen.style() != Qt.PenStyle.NoPen else self._highlight_color, inner_width)
            inner_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(inner_pen)
            inner_rect = widget_rect.adjusted(inner_width / 2, inner_width / 2, -inner_width / 2, -inner_width / 2)
            painter.drawRoundedRect(inner_rect, 3, 3)
        if not self.is_enemy and self.show_rating:
            painter.setFont(self.font)
            text_width = self.fm.horizontalAdvance(self.rating_text)
            text_height = self.fm.height()
            padding_x, padding_y = 1, 0  # Минимальные отступы для компактности
            
            # Размещаем рейтинг в правом нижнем углу иконки
            bg_rect = QRect(widget_rect.width() - (text_width + 2 * padding_x) - 1,
                            widget_rect.height() - (text_height + 2 * padding_y) - 1,
                            text_width + 2 * padding_x,
                            text_height + 2 * padding_y)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.drawRoundedRect(bg_rect, 2, 2)
            
            text_color = QColor("darkGreen") if self.is_in_effective_team else QColor("blue")
            painter.setPen(QPen(text_color))
            painter.drawText(bg_rect.left() + padding_x, bg_rect.top() + padding_y + self.fm.ascent(), self.rating_text)
def clear_layout(layout):
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0)
        if item is None: continue
        widget = item.widget()
        if widget: widget.deleteLater()
        else:
             sub_layout = item.layout()
             if sub_layout: clear_layout(sub_layout)