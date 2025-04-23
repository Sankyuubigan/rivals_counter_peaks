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
             # Используем безопасный доступ к атрибутам родителя
             parent_window = getattr(parent, 'window', parent) # Получаем главное окно или сам родитель
             current_mode = getattr(parent_window, 'mode', 'middle') # Получаем режим
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
        painter.setFont(self.font); text_width = self.fm.horizontalAdvance(self.rating_text); text_height = self.fm.height()
        padding_x = 3; padding_y = 1; bg_width = text_width + 2 * padding_x; bg_height = text_height + 2 * padding_y
        bg_rect_x = widget_rect.width() - bg_width - 2; bg_rect_y = widget_rect.height() - bg_height - 2
        bg_rect = QRect(bg_rect_x, bg_rect_y, bg_width, bg_height)
        if bg_rect.isValid():
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QBrush(QColor(255, 255, 255, 200))); painter.drawRoundedRect(bg_rect, 4, 4)
            if self.is_enemy: text_color = QColor("darkRed")
            elif self.is_in_effective_team: text_color = QColor("darkGreen")
            else: text_color = QColor("blue")
            painter.setPen(QPen(text_color)); text_x = bg_rect.left() + padding_x; text_y = bg_rect.top() + padding_y + self.fm.ascent()
            painter.drawText(text_x, text_y, self.rating_text)
        painter.end()

def update_horizontal_icon_list(window) -> None:
    """Обновляет горизонтальный список иконок (вверху окна)."""
    layout = getattr(window, 'icons_scroll_content_layout', None); scroll_area = getattr(window, 'icons_scroll_area', None)
    logging.debug("Starting update_horizontal_icon_list"); logic = window.logic
    if not layout or not scroll_area: logging.error("icons_scroll_content_layout or icons_scroll_area not found."); return
    clear_layout(layout); logging.debug("Old horizontal list layout cleared.")
    counter_scores = {}; effective_team_set = set(); selected_heroes_set = set(logic.selected_heroes)
    if not selected_heroes_set:
        label = QLabel(get_text("select_enemies_for_recommendations", language=logic.DEFAULT_LANGUAGE)); label.setStyleSheet("color: gray; margin-left: 5px;")
        layout.addWidget(label); layout.addStretch(1); scroll_area.update(); logging.debug("No selected heroes, showing 'select enemies' message."); return
    counter_scores = logic.calculate_counter_scores()
    if counter_scores:
         if not logic.effective_team or not set(logic.effective_team).isdisjoint(selected_heroes_set):
              logging.debug("Recalculating effective team for horizontal list.")
              effective_team = logic.calculate_effective_team(counter_scores); effective_team_set = set(effective_team); logic.effective_team = effective_team
         else: logging.debug("Using cached effective team for horizontal list."); effective_team_set = set(logic.effective_team)
    else: logging.warning("Counter scores calculation returned empty.")
    heroes_to_display_map = {}
    if counter_scores:
        for hero in selected_heroes_set: heroes_to_display_map[hero] = counter_scores.get(hero, -99)
        for hero in effective_team_set:
             if hero not in heroes_to_display_map: heroes_to_display_map[hero] = counter_scores.get(hero, -99)
        for hero, score in counter_scores.items():
            if score >= 1.0 and hero not in selected_heroes_set and hero not in effective_team_set: heroes_to_display_map[hero] = score
    sorted_heroes = sorted(heroes_to_display_map.keys(), key=lambda h: heroes_to_display_map.get(h, -99), reverse=True)
    logging.debug(f"Heroes to display in horizontal list ({len(sorted_heroes)}): {sorted_heroes}")
    if not sorted_heroes:
        label = QLabel(get_text("no_recommendations", language=logic.DEFAULT_LANGUAGE)); label.setStyleSheet("color: gray; margin-left: 5px;")
        layout.addWidget(label); layout.addStretch(1); scroll_area.update(); logging.debug("No heroes to display, showing 'no recommendations' message."); return

    horizontal_images = getattr(window, 'horizontal_images', {})
    if not horizontal_images:
         logging.warning("Attribute 'horizontal_images' is missing or empty. Reloading...")
         try: _, _, _, window.horizontal_images = images_load.get_images_for_mode(window.mode); horizontal_images = window.horizontal_images; logging.info(f"Reloaded horizontal images for mode '{window.mode}'.")
         except Exception as e: logging.error(f"Failed to reload horizontal images: {e}"); label = QLabel("Error loading icons"); label.setStyleSheet("color: red; margin-left: 5px;"); layout.addWidget(label); layout.addStretch(1); scroll_area.update(); return

    items_added = 0; logging.debug(f"Adding icons to horizontal list for mode '{window.mode}'...")
    for hero in sorted_heroes:
        pixmap = horizontal_images.get(hero)
        if is_invalid_pixmap(pixmap):
            logging.warning(f"[Horizontal List] Invalid or missing pixmap for hero '{hero}'. Using placeholder widget.")
            h_size = IMG_SIZES.get(window.mode, {}).get('horizontal', (35, 35))
            placeholder = QLabel(f"{hero[0] if hero else '?'}")
            placeholder.setFixedSize(QSize(*h_size)); placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("background-color: lightgrey; border: 1px solid grey; border-radius: 3px; color: black;")
            placeholder.setToolTip(f"{hero}\n(Icon Error)")
            layout.addWidget(placeholder); items_added += 1
        else:
            rating = counter_scores.get(hero, 0.0); is_in_effective_team = hero in effective_team_set; is_enemy = hero in selected_heroes_set
            tooltip = f"{hero}\nRating: {rating:.1f}"
            logging.debug(f"Creating IconWithRatingWidget for '{hero}' (Enemy: {is_enemy}, Effective: {is_in_effective_team}, Rating: {rating:.1f}) with pixmap size {pixmap.size()}")
            icon_widget = IconWithRatingWidget(pixmap, rating, is_in_effective_team, is_enemy, tooltip, parent=window) # Передаем window как родителя
            border_color = "gray"; border_width = 1
            if is_enemy: border_color = "orange"; border_width = 2; tooltip += f"\n({get_text('enemy_selected_tooltip', language=logic.DEFAULT_LANGUAGE)})"; icon_widget.setToolTip(tooltip)
            elif is_in_effective_team: border_color = "blue"; border_width = 2
            icon_widget.set_border(border_color, border_width)
            layout.addWidget(icon_widget); items_added += 1

    layout.addStretch(1); scroll_area.update(); logging.debug(f"Horizontal icon list updated with {items_added} items.")

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
