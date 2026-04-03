# File: core/horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QFontMetrics, QBrush, QPixmap
from core.images_load import is_invalid_pixmap
class IconWithRatingWidget(QWidget):
    """Виджет для отображения иконки героя с его рейтингом."""
    def __init__(self, pixmap: QPixmap, rating: float, is_in_effective_team: bool, is_enemy: bool, tooltip: str, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.rating_text = f"{rating:.0f}"
        self.is_in_effective_team = is_in_effective_team
        self.is_enemy = is_enemy
        self.setToolTip(tooltip)
        
        if not is_invalid_pixmap(self.pixmap):
            # ИСПРАВЛЕНИЕ: Устанавливаем минимальный размер на основе размера иконки
            self.setMinimumSize(pixmap.size())
        
        self.font = QFont()
        self.font.setPointSize(7)  # Размер шрифта для рейтинга на иконках
        self.font.setBold(True)
        self.fm = QFontMetrics(self.font)
        self.border_pen = QPen(Qt.PenStyle.NoPen)
        self.border_width = 1
        
        # Подсветка роли (для tray window) — больше не используется, утолщение заменено на !
        self._highlighted = False
        self._highlight_color = QColor()
        self._highlight_outer_color = QColor()
        
        # Показывать ли рейтинг (по умолчанию True, для трея можно выключить)
        self.show_rating = True
        
        # Маркеры в левом нижнем углу (для tray counters)
        self.is_ally_in_counters = False  # Зелёная галочка — герой в союзниках
        self.show_exclamation = False     # Красный ! — рекомендуемая роль
        
    def set_ally_marker(self, is_ally: bool):
        """Устанавливает зелёную галочку для героя, который в союзной команде."""
        import logging
        logging.debug(f"[Marker] set_ally_marker({is_ally}) for is_enemy={self.is_enemy}")
        self.is_ally_in_counters = is_ally
        self.update()
    
    def set_exclamation_marker(self, show: bool):
        """Устанавливает красный восклицательный знак для рекомендуемой роли."""
        self.show_exclamation = show
        self.update()
        
    def update_rating(self, rating: float, tooltip: str = None):
        """Обновляет рейтинг и подсказку виджета."""
        self.rating_text = f"{rating:.0f}"
        if tooltip is not None:
            self.setToolTip(tooltip)
        self.update()  # Перерисовываем виджет с новым рейтингом
        
    def set_border(self, color: QColor, width: int):
        self.border_pen = QPen(color, width)
        self.border_width = width
        self.update()
    
    def paintEvent(self, event):
        import logging
        logging.debug(f"[Paint] paintEvent: is_ally={self.is_ally_in_counters}, is_excl={self.show_exclamation}, is_enemy={self.is_enemy}, rect={self.rect()}")
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
        
        # --- Маркеры в левом нижнем углу (только для контрпиков в трее) ---
        # Приоритет: зелёная галочка (союзник) > красный ! (recommended role)
        marker_size = 12
        margin = 2
        marker_x = margin
        marker_y = widget_rect.height() - marker_size - margin
        marker_rect = QRect(marker_x, marker_y, marker_size, marker_size)
        
        if self.is_ally_in_counters:
            # Зелёная галочка на тёмном круглом фоне для контраста
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.drawEllipse(marker_rect)
            # Рисуем галочку
            painter.setPen(QPen(QColor("#00FF00"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            check_path = QPainterPath()
            check_path.moveTo(marker_x + 2, marker_y + 6)
            check_path.lineTo(marker_x + 5, marker_y + 9)
            check_path.lineTo(marker_x + 10, marker_y + 3)
            painter.drawPath(check_path)
        elif self.show_exclamation:
            # Красный восклицательный знак на тёмном круглом фоне
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.drawEllipse(marker_rect)
            # Рисуем !
            painter.setPen(QPen(QColor("#FF3333"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.drawText(marker_rect, Qt.AlignCenter, "!")
        
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