# File: horizontal_list.py
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QFrame # Добавлены QWidget, QVBoxLayout, QFrame
from PySide6.QtCore import QSize, Qt, QRect # Добавлен QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap  # Добавлены QPainter, QColor, QPen, QFont
from translations import get_text
from images_load import TOP_HORIZONTAL_ICON_SIZE

# --- Вспомогательный виджет для иконки с рейтингом ---
class IconWithRatingWidget(QWidget):
    def __init__(self, pixmap: QPixmap, rating: float, tooltip: str, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.rating_text = f"{rating:.1f}" # Форматируем рейтинг
        self.setToolTip(tooltip)
        self.setFixedSize(pixmap.size())

        # Стиль рамки по умолчанию (можно переопределить снаружи)
        self.setStyleSheet("border: 1px solid gray; border-radius: 3px;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Рисуем иконку
        painter.drawPixmap(self.rect(), self.pixmap)

        # 2. Рисуем рейтинг в углу (например, нижнем правом)
        font = QFont()
        font.setPointSize(9) # Размер шрифта для рейтинга
        font.setBold(True)
        painter.setFont(font)

        # Задаем цвет текста (например, синий)
        pen = QPen(QColor("blue"))
        painter.setPen(pen)

        # Рассчитываем прямоугольник для текста в углу
        text_rect = QRect(self.rect())
        # Отступы от краев
        text_rect.adjust(self.width() // 2, self.height() // 2 + 5, -3, -3)

        # Рисуем текст с выравниванием по правому нижнему краю
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, self.rating_text)

        painter.end()

def update_horizontal_icon_list(window):
    """
    Обновляет горизонтальный список иконок в icons_frame.
    Отображает рекомендуемую эффективную команду с рейтингом на иконках.
    """
    if not window.icons_layout or not window.icons_frame:
        print("[!] Ошибка: icons_layout или icons_frame не найдены.")
        return

    # Очистка текущих виджетов
    while window.icons_layout.count():
        item = window.icons_layout.takeAt(0)
        widget = item.widget()
        if widget: widget.deleteLater()
        elif item.layout(): # На случай, если там layout
            while item.layout().count():
                sub_item = item.layout().takeAt(0)
                if sub_item.widget(): sub_item.widget().deleteLater()
            # Удаляем сам пустой layout
            window.icons_layout.removeItem(item)
        elif item.spacerItem(): window.icons_layout.removeItem(item)

    if not window.logic.selected_heroes:
        window.icons_frame.update()
        return

    logic = window.logic
    counter_scores = logic.calculate_counter_scores()
    effective_team = logic.calculate_effective_team(counter_scores) # Получаем команду

    if not effective_team:
        label = QLabel(get_text("no_recommendations", "Нет рекомендаций"))
        label.setStyleSheet("color: gray;")
        window.icons_layout.addWidget(label)
        window.icons_frame.update()
        return

    icon_size = TOP_HORIZONTAL_ICON_SIZE

    for hero in effective_team:
        if hero in window.horizontal_images and window.horizontal_images[hero]:
            pixmap = window.horizontal_images[hero]
            if pixmap.size() != icon_size:
                 pixmap = pixmap.scaled(icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            rating = counter_scores.get(hero, 0.0) # Получаем рейтинг героя
            tooltip = f"{hero}\nRating: {rating:.1f}"
            style = "border: 1px solid gray; border-radius: 3px;" # Стиль по умолчанию

            if hero in window.logic.selected_heroes:
                style = "border: 2px solid orange; border-radius: 3px;" # Выделяем выбранных врагов
                tooltip = f"{hero}\nRating: {rating:.1f}\n({get_text('enemy_selected_tooltip', 'Выбран врагом')})"

            # Создаем наш кастомный виджет
            icon_widget = IconWithRatingWidget(pixmap, rating, tooltip)
            icon_widget.setStyleSheet(style) # Применяем стиль к виджету
            window.icons_layout.addWidget(icon_widget)
        else:
            print(f"Пропущен герой {hero}: нет изображения в horizontal_images")

    window.icons_layout.addStretch(1)
    window.icons_frame.update()