# File: horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QFrame
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QBrush, QPixmap
from translations import get_text
# Размер берется из images_load
import math # Для округления

# --- Вспомогательный виджет для иконки с рейтингом ---
class IconWithRatingWidget(QWidget):
    def __init__(self, pixmap: QPixmap, rating: float, is_in_effective_team: bool, tooltip: str, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.rating_text = f"{math.ceil(rating)}" if rating > 0 else f"{math.floor(rating)}"
        self.is_in_effective_team = is_in_effective_team
        self.setToolTip(tooltip)
        self.setFixedSize(pixmap.size())
        self.font = QFont(); self.font.setPointSize(10); self.font.setBold(True)
        self.fm = QFontMetrics(self.font)
        self.border_pen = QPen(QColor("gray"), 1) # Серая рамка по умолчанию

    def set_border(self, color_name: str, width: int):
        """Устанавливает цвет и толщину рамки для отрисовки."""
        self.border_pen = QPen(QColor(color_name), width)
        self.update() # Запросить перерисовку при смене рамки

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Рисуем рамку
        if self.border_pen.style() != Qt.PenStyle.NoPen:
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(self.border_pen)
            border_rect = self.rect().adjusted(self.border_pen.widthF() / 2, self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2)
            painter.drawRoundedRect(border_rect, 3, 3)
        # Рисуем иконку чуть внутри рамки
        inset = self.border_pen.width()
        icon_rect = self.rect().adjusted(inset, inset, -inset, -inset)
        if icon_rect.width() > 0 and icon_rect.height() > 0: # Рисуем только если есть место
            painter.drawPixmap(icon_rect, self.pixmap)
        # Рисуем рейтинг
        painter.setFont(self.font)
        text_width = self.fm.horizontalAdvance(self.rating_text); text_height = self.fm.height()
        padding_x = 3; padding_y = 1
        bg_width = text_width + 2 * padding_x; bg_height = text_height + 2 * padding_y
        bg_rect_x = self.width() - bg_width - 2; bg_rect_y = self.height() - bg_height - 2
        bg_rect = QRect(bg_rect_x, bg_rect_y, bg_width, bg_height)
        # Рисуем белый фон
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawRoundedRect(bg_rect, 4, 4)
        # Цвет текста
        text_color = QColor("darkGreen") if self.is_in_effective_team else QColor("blue")
        painter.setPen(QPen(text_color))
        # Рисуем текст
        text_x = bg_rect.left() + padding_x; text_y = bg_rect.top() + padding_y + self.fm.ascent()
        painter.drawText(text_x, text_y, self.rating_text)
        painter.end()

# <<< Убедимся, что имя функции правильное >>>
def update_horizontal_icon_list(window):
    """
    Обновляет горизонтальный список.
    Показывает всех героев с рейтингом >= 1 и/или из effective_team.
    Сортирует по убыванию рейтинга.
    Выделяет рамкой: оранжевой - врагов, синей - топ-6 (если не враг).
    """
    if not window.icons_scroll_content_layout or not window.icons_scroll_area:
        print("[!] Ошибка: icons_scroll_content_layout или icons_scroll_area не найдены.")
        return
    layout = window.icons_scroll_content_layout

    # Очистка
    while layout.count():
        item = layout.takeAt(0)
        if item is None: continue
        widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem()
        if widget: widget.deleteLater()
        elif layout_item:
             while layout_item.count(): sub_item = layout_item.takeAt(0)
             if sub_item and sub_item.widget(): sub_item.widget().deleteLater()
             layout.removeItem(layout_item)
        elif spacer: layout.removeItem(spacer)

    if not window.logic.selected_heroes: window.icons_scroll_area.update(); return

    logic = window.logic; counter_scores = logic.calculate_counter_scores()
    effective_team = logic.calculate_effective_team(counter_scores); effective_team_set = set(effective_team)

    heroes_to_display_map = {}
    for hero in effective_team: heroes_to_display_map[hero] = counter_scores.get(hero, -99)
    for hero, score in counter_scores.items():
        if score >= 1.0 and hero not in heroes_to_display_map: heroes_to_display_map[hero] = score

    sorted_heroes = sorted(heroes_to_display_map.keys(), key=lambda h: heroes_to_display_map[h], reverse=True)

    if not sorted_heroes:
        label = QLabel(get_text("no_recommendations", "Нет рекомендаций")); label.setStyleSheet("color: gray;")
        layout.addWidget(label); layout.addStretch(1); window.icons_scroll_area.update(); return

    # Отображаем список
    for hero in sorted_heroes:
        if hero in window.horizontal_images and window.horizontal_images[hero]:
            pixmap = window.horizontal_images[hero]
            rating = counter_scores.get(hero, 0.0)
            is_in_effective_team = hero in effective_team_set
            tooltip = f"{hero}\nRating: {rating:.1f}"
            is_enemy = hero in window.logic.selected_heroes

            # Создаем виджет
            icon_widget = IconWithRatingWidget(pixmap, rating, is_in_effective_team, tooltip)

            # Устанавливаем рамку через метод
            border_color = "gray"; border_width = 1
            if is_enemy:
                border_color = "orange"; border_width = 2
                tooltip += f"\n({get_text('enemy_selected_tooltip', 'Выбран врагом')})"
                icon_widget.setToolTip(tooltip)
            elif is_in_effective_team:
                 border_color = "blue"; border_width = 2
            icon_widget.set_border(border_color, border_width)

            layout.addWidget(icon_widget)
        else:
            print(f"Пропущен герой {hero}: нет изображения в horizontal_images")

    layout.addStretch(1)
    window.icons_scroll_area.update()