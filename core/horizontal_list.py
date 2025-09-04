# File: core/horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout, QApplication, QSizePolicy
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QBrush, QPixmap
from info.translations import get_text
from images_load import is_invalid_pixmap, SIZES as IMG_SIZES
import math
import logging

class IconWithRatingWidget(QWidget):
    """Виджет для отображения иконки героя с его рейтингом."""
    def __init__(self, pixmap: QPixmap, rating: float, is_in_effective_team: bool, is_enemy: bool, tooltip: str, parent=None):
        super().__init__(parent)
        self.hero_name = tooltip.split('\n')
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
              self.setMinimumSize(QSize(*h_size))
              self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed))
        else:
            self.setMinimumSize(pixmap.size())
            self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed))
        self.font = QFont(); self.font.setPointSize(10); self.font.setBold(True)
        self.fm = QFontMetrics(self.font); self.border_pen = QPen(Qt.PenStyle.NoPen); self.border_width = 1
        logging.debug(f"IconWithRatingWidget: Final size: {self.size()}, pixmap size: {self.pixmap.size() if 'invalid' not in str(self.pixmap) else 'invalid'}")

    def set_border(self, color_name: str, width: int):
        logging.debug(f"[DEBUG] set_border called for {self.hero_name} with color='{color_name}', width={width}")

        if color_name == "" and width == 0:
            # Убираем рамку полностью для врагов
            self.border_pen = QPen(Qt.PenStyle.NoPen)
            self.border_width = 0
            logging.debug(f"[DEBUG] Border removed completely for {self.hero_name}")
        else:
            try:
                color = QColor(color_name)
                valid = color.isValid()
                logging.debug(f"[DEBUG] QColor created: valid={valid}, rgba={color.rgba() if valid else 'invalid'}")
            except Exception as e:
                logging.error(f"Error setting border color '{color_name}' for {self.hero_name}: {e}")
                color = QColor("gray")
                valid = False

            if not valid:
                logging.warning(f"[WARNING] Invalid color '{color_name}' for {self.hero_name}. Using gray.")
                color = QColor("gray")

            self.border_pen = QPen(color, width)
            self.border_width = width
            logging.debug(f"[DEBUG] Border applied: pen={self.border_pen.style()}, color={self.border_pen.color().name()}, width={width}")
        self.update()

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

def update_horizontal_icon_list(window, target_layout: QHBoxLayout, counter_scores=None, effective_team=None) -> int:
    """Обновляет список иконок КОНТРПИКОВ с адаптацией ширины контейнера для таб-режима при большом количестве."""
    """
    Обновляет горизонтальный список иконок КОНТРПИКОВ.
    Добавляет виджеты в переданный target_layout.
    Возвращает количество добавленных элементов.
    """
    logic = window.logic
    is_tab_mode = window.tab_mode_manager.is_active() if hasattr(window, 'tab_mode_manager') else False

    if not target_layout:
        logging.error("Target layout for counter-picks not provided.")
        return

    # clear_layout(target_layout) # ИЗМЕНЕНО: Очистка layout'а теперь выполняется вызывающей функцией (ui_updater)

    selected_heroes_set = set(logic.selected_heroes)

    if not selected_heroes_set:
        target_layout.addStretch(1)
        return

    # Используем переданные параметры или рассчитываем если None
    cached_scores = counter_scores is not None
    cached_team = effective_team is not None

    if counter_scores is None:
        counter_scores = logic.calculate_counter_scores()
        cached_scores = False
    if counter_scores:
        if not cached_scores:
            logging.info(f"[TAB MODE] Counter scores calculated for {len(counter_scores)} heroes")
        if effective_team is None:
            effective_team = logic.calculate_effective_team(counter_scores)
            cached_team = False
        if not cached_team:
            logging.info(f"[TAB MODE] Effective team calculated size: {len(effective_team) if effective_team else 0}")
        effective_team_set = set(effective_team) if effective_team else set()
        logic.effective_team = effective_team
    else:
        logging.warning(f"[TAB MODE] Counter scores calculation returned empty (selected_heroes: {selected_heroes_set})")
        target_layout.addStretch(1)
        return

    heroes_to_display_map = {}
    if counter_scores:
        for hero in effective_team_set:
            if hero not in heroes_to_display_map: heroes_to_display_map[hero] = counter_scores.get(hero, -99)
        for hero, score in counter_scores.items():
            if score >= 1.0 and hero not in effective_team_set:
                heroes_to_display_map[hero] = score

    sorted_heroes = sorted(heroes_to_display_map.keys(), key=lambda h: heroes_to_display_map.get(h, -99), reverse=True)

    if not sorted_heroes:
        logging.info(f"[TAB MODE] No counter-picks to display (empty sorted_heroes)")
        target_layout.addStretch(1)
        return 0

    horizontal_images = getattr(window, 'horizontal_images', {})
    if not horizontal_images:
        logging.warning("Attribute 'horizontal_images' is missing or empty. Cannot display counter-picks.")
        label = QLabel("Err")
        label.setStyleSheet("color: red;")
        target_layout.addWidget(label)
        target_layout.addStretch(1)
    
        logging.info(f"[TAB MODE] Counters: added {items_added} heroes to layout")
        return items_added
        logging.info("[TAB MODE] Counters: added 0 error messages to layout")
        return

    items_added = 0
    # В таб-режиме показываем иконки без рейтинга
    is_tab_mode = window.tab_mode_manager.is_active() if hasattr(window, 'tab_mode_manager') else False

    logging.info(f"[TAB MODE] Processing {len(sorted_heroes)} counter candidates")

    for hero in sorted_heroes:
        rating = counter_scores.get(hero, 0.0)

        if rating >= 1.0:
            pixmap = horizontal_images.get(hero)
            if is_invalid_pixmap(pixmap):
                logging.warning(f"[Horizontal List - Counters] Invalid or missing pixmap for hero '{hero}'. Using placeholder.")
                h_size = IMG_SIZES.get(window.mode, {}).get('horizontal', (35, 35))
                placeholder = QLabel(f"{hero if hero else '?'}")
                placeholder.setFixedSize(QSize(*h_size)); placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("background-color: lightgrey; border: 1px solid grey; border-radius: 3px; color: black;")
                placeholder.setToolTip(f"{hero}\n(Icon Error)")
                logging.info(f"[Horizontal List - Counters] Adding placeholder widget for '{hero}': size {placeholder.size()}, sizeHint: {placeholder.sizeHint()}")
                target_layout.addWidget(placeholder); items_added += 1
            else:
                is_in_effective_team = hero in effective_team_set
                tooltip = f"{hero}\nRating: {rating:.1f}"

                # В таб-режиме и обычном режиме используем IconWithRatingWidget для consistent API
                display_rating = 0.0 if is_tab_mode else rating
                icon_widget = IconWithRatingWidget(pixmap, display_rating, is_in_effective_team, False, tooltip, parent=window)

                if is_tab_mode:
                    # В таб-режиме без рамки и рейтинга
                    icon_widget.set_border("", 0)
                else:
                    # В обычном режиме с рамкой
                    border_color = "gray"; border_width = 1
                    if is_in_effective_team:
                        border_color = "blue"; border_width = 2
                    icon_widget.set_border(border_color, border_width)

                target_layout.addWidget(icon_widget); items_added += 1

    target_layout.addStretch(1)

    # Адаптация ширины контейнера для таб-режима при большом количестве контрпиков (>20)
    if is_tab_mode and hasattr(window, 'tab_counters_container') and len(sorted_heroes) > 20:
        icon_width = IMG_SIZES.get(window.mode, {}).get('horizontal', [35, 35])[0]
        spacing = 4  # spacing между иконками
        margin = 4   # margins контейнера
        optimal_width = min(icon_width * len(sorted_heroes) + (len(sorted_heroes) - 1) * spacing + 2 * margin, 1200)
        window.tab_counters_container.setMinimumWidth(optimal_width)
        logging.debug(f"[TAB MODE] Counters container adapted to width: {optimal_width}, heroes count: {len(sorted_heroes)}")


def update_enemy_horizontal_list(window, target_layout: QHBoxLayout) -> None:
    """Обновляет горизонтальный список иконок ВРАГОВ с адаптивной шириной."""
    logging.info("ROO DEBUG: update_enemy_horizontal_list called")
    logic = window.logic
    if not target_layout:
        logging.error("ROO DEBUG: Target layout for enemies not provided.")
        return
    logging.info(f"ROO DEBUG: update_enemy_horizontal_list proceeding, selected_heroes: {logic.selected_heroes}")

    is_tab_mode = window.tab_mode_manager.is_active() if hasattr(window, 'tab_mode_manager') else False

    # Управление рамкой родительского виджета только в min-режиме (не таб)
    if not is_tab_mode:
        enemies_widget = target_layout.parentWidget()
        if not isinstance(enemies_widget, QWidget):
            logging.error("Target layout parent is not a QWidget, cannot apply border.")
            enemies_widget = None

        if logic.selected_heroes and enemies_widget:
            enemies_widget.setStyleSheet("QWidget#enemies_widget { border: 2px solid red; border-radius: 4px; padding: 2px; }")
        elif enemies_widget:
            enemies_widget.setStyleSheet("QWidget#enemies_widget { border: none; }")

    # Адаптация ширины контейнера для таб-режима
    if is_tab_mode and hasattr(window, 'tab_enemies_container'):
        selected_heroes_count = len(logic.selected_heroes)
        if selected_heroes_count > 0:
            # Рассчитываем оптимальную ширину на основе количества врагов
            icon_width = IMG_SIZES.get(window.mode, {}).get('horizontal', [35, 35])[0]
            spacing = 4  # spacing между иконками
            margin = 4   # margins контейнера
            min_width = icon_width + 2 * margin  # Минимальная ширина для одного героя

            # Находим оптимальную ширину: не менее min_width, не более 70% от экрана
            screen = QApplication.primaryScreen()
            max_width = int(screen.availableGeometry().width() * 0.7) if screen else 800
            optimal_width = min(icon_width * selected_heroes_count + (selected_heroes_count - 1) * spacing + 2 * margin, max_width)

            # Устанавливаем минимальную ширину чтобы не сжималось
            window.tab_enemies_container.setMinimumWidth(optimal_width)
            logging.debug(f"[TAB MODE] Enemy container adapted to width: {optimal_width}, heroes count: {selected_heroes_count}")
        else:
            window.tab_enemies_container.setMinimumWidth(100)  # Минимальная ширина при отсутствии врагов

    selected_heroes = list(logic.selected_heroes)

    if is_tab_mode and len(selected_heroes) > 12:  # Более гибкое ограничение для прокрутки
        # Даем возможность прокрутки при > 12 героях
        logging.debug(f"Many enemies ({len(selected_heroes)}), enable scrolling")

    if not selected_heroes:
        logging.info(f"[TAB MODE] No selected heroes to display in enemy list")
        return 0

    logging.debug(f"[TAB MODE] Displaying {len(selected_heroes)} enemies")

    horizontal_images = getattr(window, 'horizontal_images', {})
    if not horizontal_images:
        logging.warning("Attribute 'horizontal_images' is missing or empty. Cannot display enemies.")
        label = QLabel("Err")
        label.setStyleSheet("color: red;")
        target_layout.addWidget(label)
        return

    # Оптимизированное выравнивание по правому краю для таб-режима с учетом прокрутки
    if is_tab_mode:
        # В таб режиме без левой растяжки для правильного выравнивания при прокрутке
        pass
    else:
        target_layout.addStretch(1)

    items_added = 0
    for hero in selected_heroes:
        pixmap = horizontal_images.get(hero)
        if is_invalid_pixmap(pixmap):
            logging.warning(f"[Horizontal List - Enemies] Invalid or missing pixmap for enemy '{hero}'. Using placeholder.")
            h_size = IMG_SIZES.get(window.mode, {}).get('horizontal', (35, 35))
            placeholder = QLabel(f"{hero if hero else '?'}")
            placeholder.setFixedSize(QSize(*h_size)); placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("background-color: lightgrey; border: 1px solid grey; border-radius: 3px; color: black;")
            placeholder.setToolTip(f"{hero}\n({get_text('enemy_selected_tooltip', language=logic.DEFAULT_LANGUAGE)})")
            target_layout.addWidget(placeholder); items_added += 1
        else:
            # В таб-режиме и обычном режиме используем IconWithRatingWidget для consistent API
            icon_widget = IconWithRatingWidget(pixmap, 0.0, False, True, f"{hero}\n({get_text('enemy_selected_tooltip', language=logic.DEFAULT_LANGUAGE)})", parent=window)
            icon_widget.set_border("", 0)  # Без рамки
            logging.debug(f"[TAB MODE] Created enemy widget for '{hero}' with empty border")
            target_layout.addWidget(icon_widget); items_added += 1

    # Не добавляем правую растяжку в таб режиме для правильного выравнивания
    if not is_tab_mode:
        target_layout.addStretch(1)

    logging.info(f"[TAB MODE] Enemies: added {items_added} heroes to layout (adaptive width)")
    return items_added

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