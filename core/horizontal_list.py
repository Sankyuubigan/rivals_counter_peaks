# File: core/horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QFrame, QHBoxLayout
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QBrush, QPixmap
import translations
from translations import get_text
from images_load import is_invalid_pixmap, SIZES as IMG_SIZES, load_default_pixmap
import math
import logging

class IconWithRatingWidget(QWidget):
    """Виджет для отображения иконки героя с его рейтингом."""
    def __init__(self, pixmap: QPixmap, rating: float, is_in_effective_team: bool, is_enemy: bool, tooltip: str, parent=None):
        super().__init__(parent)
        self.hero_name = tooltip.split('\n')[0]
        self.pixmap = pixmap
        self.rating_text = f"{math.ceil(rating) if rating > 0 else math.floor(rating)}"
        self.is_in_effective_team = is_in_effective_team; self.is_enemy = is_enemy
        self.setToolTip(tooltip)
        if is_invalid_pixmap(self.pixmap):
             logging.warning(f"IconWithRatingWidget '{self.hero_name}' initialized with invalid pixmap. Using default size.")
             default_size = (35, 35)
             parent_window = getattr(parent, 'window', parent)
             current_mode = getattr(parent_window, 'mode', 'middle')
             h_size = IMG_SIZES.get(current_mode, {}).get('horizontal', default_size)
             self.setFixedSize(QSize(*h_size))
        else: self.setFixedSize(pixmap.size())
        self.font = QFont(); self.font.setPointSize(10); self.font.setBold(True)
        self.fm = QFontMetrics(self.font); self.border_pen = QPen(Qt.PenStyle.NoPen); self.border_width = 1

    def set_border(self, color_name: str, width: int):
        try: color = QColor(color_name); valid = color.isValid()
        except Exception as e: logging.error(f"Error setting border color '{color_name}' for {self.hero_name}: {e}"); color = QColor("gray"); valid = False
        if not valid: logging.warning(f"Invalid color '{color_name}' for {self.hero_name}. Using gray."); color = QColor("gray")
        self.border_pen = QPen(color, width); self.border_width = width; self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        widget_rect = self.rect()
        inset = self.border_width / 2.0; icon_rect = widget_rect.adjusted(inset, inset, -inset, -inset)
        if is_invalid_pixmap(self.pixmap) or not icon_rect.isValid():
            logging.warning(f"Drawing placeholder for '{self.hero_name}' in horizontal list (pixmap invalid: {is_invalid_pixmap(self.pixmap)}, icon_rect valid: {icon_rect.isValid()})")
            painter.setBrush(QColor(200, 200, 200)); painter.setPen(QColor("gray"))
            painter.drawRoundedRect(widget_rect.adjusted(1, 1, -1, -1), 3, 3)
        else: painter.drawPixmap(icon_rect, self.pixmap)
        if self.border_pen.style() != Qt.PenStyle.NoPen:
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(self.border_pen)
            border_rect = widget_rect.adjusted(self.border_pen.widthF() / 2, self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2)
            if border_rect.isValid(): painter.drawRoundedRect(border_rect, 3, 3)
        if not self.is_enemy:
            painter.setFont(self.font)
            text_width = self.fm.horizontalAdvance(self.rating_text)
            text_height = self.fm.height()
            padding_x = 3
            padding_y = 1
            bg_width = text_width + 2 * padding_x
            bg_height = text_height + 2 * padding_y
            bg_rect_x = widget_rect.width() - bg_width - 2
            bg_rect_y = widget_rect.height() - bg_height - 2
            bg_rect = QRect(bg_rect_x, bg_rect_y, bg_width, bg_height)
            if bg_rect.isValid():
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
                painter.drawRoundedRect(bg_rect, 4, 4)
                if self.is_in_effective_team: text_color = QColor("darkGreen")
                else: text_color = QColor("blue")
                painter.setPen(QPen(text_color)); text_x = bg_rect.left() + padding_x
                text_y = bg_rect.top() + padding_y + self.fm.ascent()
                painter.drawText(text_x, text_y, self.rating_text)
        painter.end()

def update_horizontal_icon_list(window, target_layout: QHBoxLayout) -> None:
    """
    Обновляет горизонтальный список иконок КОНТРПИКОВ (вверху окна, левая часть в min режиме).
    Добавляет виджеты в переданный target_layout.
    """
    logging.debug("Starting update_horizontal_icon_list (counter picks)")
    logic = window.logic
    if not target_layout: logging.error("Target layout for counter-picks not provided."); return
    clear_layout(target_layout)

    counter_scores = {}; effective_team_set = set(); selected_heroes_set = set(logic.selected_heroes)

    if not selected_heroes_set:
        target_layout.addStretch(1)
        return

    counter_scores = logic.calculate_counter_scores()
    if counter_scores:
        effective_team = logic.calculate_effective_team(counter_scores)
        effective_team_set = set(effective_team)
        logic.effective_team = effective_team
    else:
        logging.warning("Counter scores calculation returned empty.")
        target_layout.addStretch(1)
        return

    heroes_to_display_map = {}
    if counter_scores:
        for hero in effective_team_set:
            if hero not in heroes_to_display_map: heroes_to_display_map[hero] = counter_scores.get(hero, -99)
        for hero, score in counter_scores.items():
            if score >= 1.0 and hero not in selected_heroes_set and hero not in effective_team_set:
                heroes_to_display_map[hero] = score

    sorted_heroes = sorted(heroes_to_display_map.keys(), key=lambda h: heroes_to_display_map.get(h, -99), reverse=True)

    if not sorted_heroes:
        target_layout.addStretch(1)
        return

    horizontal_images = getattr(window, 'horizontal_images', {})
    if not horizontal_images:
        logging.warning("Attribute 'horizontal_images' is missing or empty. Cannot display counter-picks.")
        label = QLabel("Err")
        label.setStyleSheet("color: red;")
        target_layout.addWidget(label)
        target_layout.addStretch(1)
        return

    items_added = 0
    for hero in sorted_heroes:
        rating = counter_scores.get(hero, 0.0)

        if rating >= 1.0:
            pixmap = horizontal_images.get(hero)
            if is_invalid_pixmap(pixmap):
                logging.warning(f"[Horizontal List - Counters] Invalid or missing pixmap for hero '{hero}'. Using placeholder.")
                h_size = IMG_SIZES.get(window.mode, {}).get('horizontal', (35, 35))
                placeholder = QLabel(f"{hero[0] if hero else '?'}")
                placeholder.setFixedSize(QSize(*h_size)); placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("background-color: lightgrey; border: 1px solid grey; border-radius: 3px; color: black;")
                placeholder.setToolTip(f"{hero}\n(Icon Error)")
                target_layout.addWidget(placeholder); items_added += 1
            else:
                is_in_effective_team = hero in effective_team_set
                tooltip = f"{hero}\nRating: {rating:.1f}"
                icon_widget = IconWithRatingWidget(pixmap, rating, is_in_effective_team, False, tooltip, parent=window)
                border_color = "gray"; border_width = 1
                if is_in_effective_team:
                    border_color = "blue"; border_width = 2
                icon_widget.set_border(border_color, border_width)
                target_layout.addWidget(icon_widget); items_added += 1

    target_layout.addStretch(1)
    logging.debug(f"Horizontal counter-pick list updated with {items_added} items.")


def update_enemy_horizontal_list(window, target_layout: QHBoxLayout) -> None:
    """
    Обновляет горизонтальный список иконок ВРАГОВ (правая часть в min режиме).
    Добавляет виджеты в переданный target_layout.
    """
    logging.debug("Starting update_enemy_horizontal_list")
    logic = window.logic
    if not target_layout: logging.error("Target layout for enemies not provided."); return

    enemies_widget = target_layout.parentWidget()
    if not isinstance(enemies_widget, QWidget):
        logging.error("Target layout parent is not a QWidget, cannot apply border.")
        enemies_widget = None

    clear_layout(target_layout)

    selected_heroes = list(logic.selected_heroes)

    # <<< ИЗМЕНЕНО: Увеличена толщина рамки и немного увеличен padding >>>
    if selected_heroes and enemies_widget:
        enemies_widget.setStyleSheet("QWidget#enemies_widget { border: 2px solid red; border-radius: 4px; padding: 2px; }") # Толще рамка, больше радиус и паддинг
    elif enemies_widget:
        enemies_widget.setStyleSheet("QWidget#enemies_widget { border: none; }")
    # <<< END ИЗМЕНЕНО >>>

    if not selected_heroes:
        target_layout.addStretch(1)
        return

    horizontal_images = getattr(window, 'horizontal_images', {})
    if not horizontal_images:
        logging.warning("Attribute 'horizontal_images' is missing or empty. Cannot display enemies.")
        label = QLabel("Err")
        label.setStyleSheet("color: red;")
        target_layout.addWidget(label)
        target_layout.addStretch(1)
        return

    items_added = 0
    for hero in selected_heroes:
        pixmap = horizontal_images.get(hero)
        if is_invalid_pixmap(pixmap):
            logging.warning(f"[Horizontal List - Enemies] Invalid or missing pixmap for enemy '{hero}'. Using placeholder.")
            h_size = IMG_SIZES.get(window.mode, {}).get('horizontal', (35, 35))
            placeholder = QLabel(f"{hero[0] if hero else '?'}")
            placeholder.setFixedSize(QSize(*h_size)); placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("background-color: lightgrey; border: 1px solid grey; border-radius: 3px; color: black;")
            placeholder.setToolTip(f"{hero}\n({get_text('enemy_selected_tooltip', language=logic.DEFAULT_LANGUAGE)})")
            target_layout.addWidget(placeholder); items_added += 1
        else:
            icon_label = QLabel()
            icon_label.setPixmap(pixmap)
            icon_label.setFixedSize(pixmap.size())
            icon_label.setStyleSheet("border: none; border-radius: 3px; padding: 0px;") # Убрали индивидуальную рамку
            icon_label.setToolTip(f"{hero}\n({get_text('enemy_selected_tooltip', language=logic.DEFAULT_LANGUAGE)})")
            target_layout.addWidget(icon_label); items_added += 1

    target_layout.addStretch(1)
    logging.debug(f"Horizontal enemy list updated with {items_added} items.")

def clear_layout(layout):
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0);
        if item is None: continue
        widget = item.widget()
        if widget: widget.deleteLater()
        else:
             sub_layout = item.layout()
             if sub_layout: clear_layout(sub_layout)
             if layout and sub_layout:
                 layout.removeItem(item)
