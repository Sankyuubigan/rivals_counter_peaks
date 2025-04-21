# File: horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QFrame
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QBrush, QPixmap
from translations import get_text
import math

# --- Вспомогательный виджет для иконки с рейтингом ---
class IconWithRatingWidget(QWidget):
    def __init__(self, pixmap: QPixmap, rating: float, is_in_effective_team: bool, is_enemy: bool, tooltip: str, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        # Отображаем рейтинг как целое число
        self.rating_text = f"{math.ceil(rating) if rating > 0 else math.floor(rating)}"
        self.is_in_effective_team = is_in_effective_team
        self.is_enemy = is_enemy
        self.setToolTip(tooltip)
        self.setFixedSize(pixmap.size()) # Размер виджета равен размеру иконки
        self.font = QFont(); self.font.setPointSize(10); self.font.setBold(True)
        self.fm = QFontMetrics(self.font)
        # Перо по умолчанию "без пера"
        self.border_pen = QPen(Qt.PenStyle.NoPen)
        self.border_width = 1 # Ширина по умолчанию

    def set_border(self, color_name: str, width: int):
        """Устанавливает цвет и толщину рамки для отрисовки."""
        self.border_pen = QPen(QColor(color_name), width)
        self.border_width = width # Сохраняем ширину для расчета отступа иконки
        self.update() # Перерисовываем виджет с новой рамкой

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Рисуем иконку с отступом, равным половине ширины рамки
        # Это предотвратит перекрытие иконкой толстой рамки
        inset = self.border_width / 2.0
        icon_rect = self.rect().adjusted(inset, inset, -inset, -inset)
        if icon_rect.isValid(): # Проверяем валидность прямоугольника
            painter.drawPixmap(icon_rect, self.pixmap)

        # 2. Рисуем рамку ПОВЕРХ иконки, если она задана
        if self.border_pen.style() != Qt.PenStyle.NoPen:
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(self.border_pen)
            # Рисуем рамку по границам виджета, учитывая ширину пера
            border_rect = self.rect().adjusted(self.border_pen.widthF() / 2, self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2, -self.border_pen.widthF() / 2)
            painter.drawRoundedRect(border_rect, 3, 3) # Скругленные углы

        # 3. Рисуем рейтинг в правом нижнем углу
        painter.setFont(self.font)
        text_width = self.fm.horizontalAdvance(self.rating_text); text_height = self.fm.height()
        padding_x = 3; padding_y = 1 # Отступы внутри фона
        bg_width = text_width + 2 * padding_x; bg_height = text_height + 2 * padding_y
        # Позиция фона справа внизу с небольшим отступом
        bg_rect_x = self.width() - bg_width - 2; bg_rect_y = self.height() - bg_height - 2
        bg_rect = QRect(bg_rect_x, bg_rect_y, bg_width, bg_height)

        # Рисуем полупрозрачный белый фон для рейтинга
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawRoundedRect(bg_rect, 4, 4)

        # Выбираем цвет текста рейтинга
        if self.is_enemy:
             text_color = QColor("darkRed") # Красный для врагов
        elif self.is_in_effective_team:
             text_color = QColor("darkGreen") # Зеленый для рекомендованных
        else:
             text_color = QColor("blue") # Синий для остальных

        painter.setPen(QPen(text_color))
        # Рисуем текст рейтинга
        text_x = bg_rect.left() + padding_x; text_y = bg_rect.top() + padding_y + self.fm.ascent()
        painter.drawText(text_x, text_y, self.rating_text)
        painter.end()

def update_horizontal_icon_list(window) -> None:
    """
    Обновляет горизонтальный список иконок.
    Показывает врагов и рекомендованных героев (score >= 1 или в effective_team).
    Сортирует по убыванию рейтинга.
    Выделяет рамкой: оранжевой - врагов, синей - топ-6 (если не враг), серой - остальных.
    """
    _update_horizontal_icon_list(window)

class HorizontalList:
    def __init__(self, layout) -> None:
        self.layout = layout

    def set_items(self, items) -> None:
        self._clear_layout()
        self._add_items_to_layout(items)

def _update_horizontal_icon_list(window) -> None:

    if not window.icons_scroll_content_layout or not window.icons_scroll_area:
        print("[!] Ошибка: icons_scroll_content_layout или icons_scroll_area не найдены.")
        return
    layout = window.icons_scroll_content_layout

    # Очистка layout перед заполнением
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem();
        if widget: widget.deleteLater()
        elif layout_item: layout.removeItem(layout_item) # Удаляем сам layout item
        elif spacer: layout.removeItem(spacer) # Удаляем spacer item

    logic = window.logic;
    # Получаем очки и команду только если есть выбранные герои
    counter_scores = {}
    effective_team_set = set()
    selected_heroes_set = set(logic.selected_heroes) # Множество выбранных героев

    if selected_heroes_set:
        counter_scores = logic.calculate_counter_scores()
        if counter_scores: # Проверка, что счет не пустой
             effective_team = logic.calculate_effective_team(counter_scores);
             effective_team_set = set(effective_team)
    else: # Если враги не выбраны, показываем сообщение
        label = QLabel(get_text("select_enemies_for_recommendations", language=logic.DEFAULT_LANGUAGE));
        label.setStyleSheet("color: gray; margin-left: 5px;")
        layout.addWidget(label); layout.addStretch(1); window.icons_scroll_area.update(); return

    # Формируем словарь героев для отображения {hero: score}
    heroes_to_display_map = {}
    if counter_scores:
        # Добавляем всех выбранных врагов
        for hero in selected_heroes_set:
             heroes_to_display_map[hero] = counter_scores.get(hero, -99) # Используем реальный score или -99
        # Добавляем рекомендованных (в effective_team или score >= 1), если они еще не добавлены
        for hero in effective_team_set:
             if hero not in heroes_to_display_map:
                 heroes_to_display_map[hero] = counter_scores.get(hero, -99)
        for hero, score in counter_scores.items():
            if score >= 1.0 and hero not in selected_heroes_set and hero not in effective_team_set:
                 heroes_to_display_map[hero] = score
    else: # Если нет counter_scores (хотя selected_heroes есть), показываем сообщение
         label = QLabel(get_text("no_recommendations", language=logic.DEFAULT_LANGUAGE));
         label.setStyleSheet("color: gray; margin-left: 5px;")
         layout.addWidget(label); layout.addStretch(1); window.icons_scroll_area.update(); return

    # Сортируем героев по убыванию рейтинга
    # Враги с отрицательным рейтингом будут в конце
    sorted_heroes = sorted(heroes_to_display_map.keys(), key=lambda h: heroes_to_display_map.get(h, -99), reverse=True)

    if not sorted_heroes:
        label = QLabel(get_text("no_recommendations", language=logic.DEFAULT_LANGUAGE))
        label.setStyleSheet("color: gray; margin-left: 5px;")
        layout.addWidget(label)
        layout.addStretch(1)
        window.icons_scroll_area.update()
        return
    
    horizontal_list = HorizontalList(layout)
    horizontal_list.set_items(sorted_heroes)

    layout.addStretch(1) # Добавляем растяжку в конец
    window.icons_scroll_area.update() # Обновляем область прокрутки

    
class HorizontalList:

    def __init__(self, layout):
        self.layout = layout
    
    def _clear_layout(self):
        layout = self.layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem()
            if widget: widget.deleteLater()
            elif layout_item: layout.removeItem(layout_item) # Удаляем сам layout item
            elif spacer: layout.removeItem(spacer) # Удаляем spacer item

    def _add_items_to_layout(self, sorted_heroes):
        for hero in sorted_heroes:
            self._add_item(hero)

    def _add_item(self, hero):
        window = self.layout.parentWidget().parentWidget()
        layout = self.layout
        logic = window.logic

    # Отображаем список
        if hero in window.horizontal_images and window.horizontal_images.get(hero):
                pixmap = window.horizontal_images[hero]
                logic = window.logic; heroes_to_display_map = {}
                counter_scores = logic.calculate_counter_scores(); effective_team_set = set(logic.calculate_effective_team(counter_scores))
                selected_heroes_set = set(logic.selected_heroes) # Множество выбранных героев
                rating = heroes_to_display_map.get(hero, 0.0) # Берем рейтинг из нашего словаря
                is_in_effective_team = hero in effective_team_set
                is_enemy = hero in selected_heroes_set
                tooltip = f"{hero}\nRating: {rating:.1f}"

                # Создаем виджет иконки с рейтингом
                icon_widget = IconWithRatingWidget(pixmap, rating, is_in_effective_team, is_enemy, tooltip,)

                # --- Устанавливаем параметры рамки через метод ---
                border_color = "gray"; border_width = 1 # По умолчанию серая тонкая
                if is_enemy:
                    border_color = "orange"; border_width = 2
                    tooltip += f"\n({get_text('enemy_selected_tooltip', language=logic.DEFAULT_LANGUAGE)})"
                    icon_widget.setToolTip(tooltip) # Обновляем тултип
                elif is_in_effective_team:
                    border_color = "blue"; border_width = 2 # Синяя толстая для топ-6
                icon_widget.set_border(border_color, border_width)
                # -----------------------------------------------

                layout.addWidget(icon_widget)