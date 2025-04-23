# File: core/horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QFrame, QHBoxLayout
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QBrush, QPixmap
# <<< ИСПРАВЛЕНО: Используем абсолютный импорт >>>
import translations
# <<< ----------------------------------------- >>>
from translations import get_text
import math

# --- Вспомогательный виджет для иконки с рейтингом ---
class IconWithRatingWidget(QWidget):
    # Код класса IconWithRatingWidget остается без изменений
    def __init__(self, pixmap: QPixmap, rating: float, is_in_effective_team: bool, is_enemy: bool, tooltip: str, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.rating_text = f"{math.ceil(rating) if rating > 0 else math.floor(rating)}"
        self.is_in_effective_team = is_in_effective_team
        self.is_enemy = is_enemy
        self.setToolTip(tooltip)
        self.setFixedSize(pixmap.size())
        self.font = QFont(); self.font.setPointSize(10); self.font.setBold(True)
        self.fm = QFontMetrics(self.font)
        self.border_pen = QPen(Qt.PenStyle.NoPen)
        self.border_width = 1

    def set_border(self, color_name: str, width: int):
        self.border_pen = QPen(QColor(color_name), width)
        self.border_width = width
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = self.border_width / 2.0
        icon_rect = self.rect().adjusted(inset, inset, -inset, -inset)
        if icon_rect.isValid(): painter.drawPixmap(icon_rect, self.pixmap)
        if self.border_pen.style() != Qt.PenStyle.NoPen:
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(self.border_pen)
            border_rect = self.rect().adjusted(self.border_pen.widthF() / 2, self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2)
            painter.drawRoundedRect(border_rect, 3, 3)
        painter.setFont(self.font)
        text_width = self.fm.horizontalAdvance(self.rating_text); text_height = self.fm.height()
        padding_x = 3; padding_y = 1
        bg_width = text_width + 2 * padding_x; bg_height = text_height + 2 * padding_y
        bg_rect_x = self.width() - bg_width - 2; bg_rect_y = self.height() - bg_height - 2
        bg_rect = QRect(bg_rect_x, bg_rect_y, bg_width, bg_height)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawRoundedRect(bg_rect, 4, 4)
        if self.is_enemy: text_color = QColor("darkRed")
        elif self.is_in_effective_team: text_color = QColor("darkGreen")
        else: text_color = QColor("blue")
        painter.setPen(QPen(text_color))
        text_x = bg_rect.left() + padding_x; text_y = bg_rect.top() + padding_y + self.fm.ascent()
        painter.drawText(text_x, text_y, self.rating_text)
        painter.end()
# --- ---

# <<< ИСПРАВЛЕНО: Упрощенная функция обновления списка >>>
def update_horizontal_icon_list(window) -> None:
    """
    Обновляет горизонтальный список иконок в icons_scroll_content_layout.
    """
    # <<< ИСПРАВЛЕНО: Проверяем существование атрибутов перед доступом >>>
    layout = getattr(window, 'icons_scroll_content_layout', None)
    scroll_area = getattr(window, 'icons_scroll_area', None)
    # <<< ------------------------------------------------------- >>>

    if not layout or not scroll_area:
        print("[!] Ошибка: icons_scroll_content_layout или icons_scroll_area не найдены в update_horizontal_icon_list.")
        return

    # Очистка layout
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem();
        if widget: widget.deleteLater()
        elif layout_item: layout.removeItem(layout_item)
        elif spacer: layout.removeItem(spacer)

    logic = window.logic
    counter_scores = {}
    effective_team_set = set()
    selected_heroes_set = set(logic.selected_heroes)

    if selected_heroes_set:
        counter_scores = logic.calculate_counter_scores()
        if counter_scores:
             effective_team = logic.calculate_effective_team(counter_scores);
             effective_team_set = set(effective_team)
    else:
        label = QLabel(get_text("select_enemies_for_recommendations", language=logic.DEFAULT_LANGUAGE));
        label.setStyleSheet("color: gray; margin-left: 5px;")
        layout.addWidget(label); layout.addStretch(1); scroll_area.update(); return

    heroes_to_display_map = {}
    if counter_scores:
        for hero in selected_heroes_set: heroes_to_display_map[hero] = counter_scores.get(hero, -99)
        for hero in effective_team_set:
             if hero not in heroes_to_display_map: heroes_to_display_map[hero] = counter_scores.get(hero, -99)
        for hero, score in counter_scores.items():
            if score >= 1.0 and hero not in selected_heroes_set and hero not in effective_team_set:
                 heroes_to_display_map[hero] = score
    else:
         label = QLabel(get_text("no_recommendations", language=logic.DEFAULT_LANGUAGE));
         label.setStyleSheet("color: gray; margin-left: 5px;")
         layout.addWidget(label); layout.addStretch(1); scroll_area.update(); return

    sorted_heroes = sorted(heroes_to_display_map.keys(), key=lambda h: heroes_to_display_map.get(h, -99), reverse=True)

    if not sorted_heroes:
        label = QLabel(get_text("no_recommendations", language=logic.DEFAULT_LANGUAGE))
        label.setStyleSheet("color: gray; margin-left: 5px;")
        layout.addWidget(label)
        layout.addStretch(1)
        scroll_area.update()
        return

    # Добавляем виджеты напрямую в layout
    # <<< ИСПРАВЛЕНО: Проверяем window.horizontal_images на None >>>
    horizontal_images = getattr(window, 'horizontal_images', {})
    if not horizontal_images:
         print("[WARN] Атрибут horizontal_images отсутствует или пуст в update_horizontal_icon_list.")
         return
    # <<< ----------------------------------------------------- >>>

    for hero in sorted_heroes:
        if hero in horizontal_images and horizontal_images.get(hero):
            pixmap = horizontal_images[hero]
            rating = counter_scores.get(hero, 0.0)
            is_in_effective_team = hero in effective_team_set
            is_enemy = hero in selected_heroes_set
            tooltip = f"{hero}\nRating: {rating:.1f}"

            icon_widget = IconWithRatingWidget(pixmap, rating, is_in_effective_team, is_enemy, tooltip,)

            border_color = "gray"; border_width = 1
            if is_enemy:
                border_color = "orange"; border_width = 2
                tooltip += f"\n({get_text('enemy_selected_tooltip', language=logic.DEFAULT_LANGUAGE)})"
                icon_widget.setToolTip(tooltip)
            elif is_in_effective_team:
                border_color = "blue"; border_width = 2
            icon_widget.set_border(border_color, border_width)

            layout.addWidget(icon_widget)

    layout.addStretch(1)
    scroll_area.update()
# <<< ------------------------------------------------------- >>>
