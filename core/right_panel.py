from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QScrollArea, QWidget, QHeaderView)  # Убираем QtWidgets, добавляем QHeaderView
from PySide6.QtCore import Qt, Signal
from heroes_bd import heroes
from translations import get_text
from horizontal_list import update_horizontal_icon_list

class HeroButton(QWidget):
    clicked = Signal()
    customContextMenuRequested = Signal(object)

    def __init__(self, hero, icon, initial_mode, logic):
        super().__init__()
        self.hero = hero
        self.logic = logic

        # Задаём минимальные размеры кнопки в зависимости от режима
        if initial_mode == "max":
            self.setMinimumSize(60, 90)  # Размер иконки 60x60 + место для текста
        else:  # "middle" режим
            self.setMinimumSize(35, 35)  # Размер иконки 35x35, текст скрыт

        # Основной layout для кнопки
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)

        # Иконка
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setContentsMargins(0, 0, 0, 0)
        self.icon_label.setStyleSheet("padding: 0px; margin: 0px; background-color: transparent;")

        if initial_mode == "max":
            self.icon_label.setMinimumSize(60, 60)
        else:
            self.icon_label.setMinimumSize(35, 35)

        layout.addWidget(self.icon_label, stretch=0)

        # Текст
        self.text_label = QLabel(hero if initial_mode == "max" else "")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("font-size: 8pt; line-height: 8pt; padding: 0px; margin: 0px; background-color: transparent;")
        self.text_label.setContentsMargins(0, 0, 0, 0)
        self.text_label.setWordWrap(True)

        if initial_mode == "max":
            self.text_label.setMinimumWidth(60)
            self.text_label.setMaximumHeight(30)
        else:
            self.text_label.setMaximumHeight(0)

        layout.addWidget(self.text_label, stretch=0)

        # Начальный стиль кнопки
        self.setStyleSheet("background-color: transparent;")

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        # Логирование размеров для отладки
        print(
            f"HeroButton для {hero}: icon_label size = {self.icon_label.size().width()}x{self.icon_label.size().height()}, button min size = {self.minimumSize().width()}x{self.minimumSize().height()}"
        )
        print(
            f"HeroButton для {hero}: text_label size = {self.text_label.size().width()}x{self.text_label.size().height()}"
        )

    def update_style(self, selected=False):
        background_style = "background-color: lightblue;" if selected else "background-color: transparent;"
        self.setStyleSheet(background_style)
        print(f"Обновлён стиль для {self.hero}: {self.styleSheet()}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def on_context_menu(self, pos):
        self.customContextMenuRequested.emit(pos)

def create_right_panel(parent, logic, buttons, copy_to_clipboard, result_frame, result_label, canvas,
                       update_scrollregion, initial_mode="middle"):
    right_frame = QFrame(parent)
    layout = QVBoxLayout(right_frame)
    layout.setContentsMargins(5, 5, 5, 5)

    scroll_area = QScrollArea(right_frame)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    # Заменяем QGridLayout на QTableWidget
    table_widget = QTableWidget()
    table_widget.setShowGrid(True)  # Включаем отображение сетки
    table_widget.setStyleSheet("""
        QTableWidget {
            background-color: white;
            border: 1px solid #d3d3d3;
            gridline-color: #d3d3d3;
        }
        QTableWidget::item {
            border: none;  /* Убираем границы ячеек, оставляем только сетку */
        }
    """)

    # Устанавливаем количество строк и столбцов
    cols = 5
    rows = (len(heroes) + cols - 1) // cols  # Округляем вверх
    table_widget.setRowCount(rows)
    table_widget.setColumnCount(cols)

    # Устанавливаем минимальные размеры ячеек
    if initial_mode == "max":
        for i in range(rows):
            table_widget.setRowHeight(i, 100)  # Высота строки (иконка + текст)
        for j in range(cols):
            table_widget.setColumnWidth(j, 80)  # Минимальная ширина столбца
        print(f"Установлены минимальные размеры ячеек для режима max")
    else:
        for i in range(rows):
            table_widget.setRowHeight(i, 40)  # Высота строки (только иконка)
        for j in range(cols):
            table_widget.setColumnWidth(j, 40)  # Минимальная ширина столбца
        print(f"Установлены минимальные размеры ячеек для режима middle")

    # Делаем столбцы растягиваемыми
    table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Используем QHeaderView

    # Отключаем заголовки таблицы
    table_widget.horizontalHeader().setVisible(False)
    table_widget.verticalHeader().setVisible(False)

    def update_counters_wrapper():
        print(f"update_counters_wrapper вызвана с selected_heroes: {logic.selected_heroes}")
        current_mode = parent.mode
        for widget in parent.result_frame.findChildren(QFrame):
            widget.deleteLater()

        if logic.selected_heroes:
            from images_load import get_images_for_mode
            right_images, left_images, small_images, horizontal_images = get_images_for_mode(current_mode)
            parent.right_images = right_images
            parent.left_images = left_images
            parent.small_images = small_images
            parent.horizontal_images = horizontal_images
            print(f"Обновлены horizontal_images, размер: {len(parent.horizontal_images)}")
            if current_mode == "min":
                logic.generate_minimal_icon_list(parent.result_frame, parent.result_label, left_images)
            else:
                logic.generate_counterpick_display(parent.result_frame, parent.result_label, left_images, small_images)
        update_selected_label_wrapper()
        update_scrollregion()
        parent.result_frame.update()
        parent.canvas.update()
        print("Вызываем update_horizontal_icon_list для обновления горизонтального списка")
        update_horizontal_icon_list(parent)

    def update_selected_label_wrapper():
        if parent.selected_heroes_label and hasattr(parent.selected_heroes_label, 'setText'):
            parent.selected_heroes_label.setText(logic.get_selected_heroes_text())
            parent.selected_heroes_label.adjustSize()
            new_width = max(right_frame.minimumWidth(), parent.selected_heroes_label.sizeHint().width() + 30)
            right_frame.setMinimumWidth(new_width)
            print(f"Обновлена минимальная ширина правой панели: {new_width} пикселей")

    # Размещаем кнопки в таблице
    for i, hero in enumerate(heroes):
        row = i // cols
        col = i % cols
        icon = parent.right_images.get(hero, None)
        if icon is None or icon.isNull():
            print(f"Предупреждение: Нет валидной иконки для {hero} в режиме '{initial_mode}'")
            continue
        btn = HeroButton(hero, icon, initial_mode, logic)
        btn.clicked.connect(
            lambda h=hero: logic.toggle_hero(
                h, buttons, lambda: update_counters_wrapper()
            )
        )
        btn.customContextMenuRequested.connect(
            lambda pos, h=hero, b=btn: logic.set_priority(
                h, b, b.parent(), lambda: update_counters_wrapper()
            )
        )
        table_widget.setCellWidget(row, col, btn)
        buttons[hero] = btn

    scroll_area.setWidget(table_widget)
    layout.addWidget(scroll_area)

    selected_heroes_label = QLabel(get_text('selected'))
    selected_heroes_label.setWordWrap(True)
    layout.addWidget(selected_heroes_label)

    copy_button = QPushButton(get_text('copy_rating'))
    copy_button.clicked.connect(lambda: copy_to_clipboard(logic))
    layout.addWidget(copy_button)

    clear_button = QPushButton(get_text('clear_all'))
    clear_button.clicked.connect(
        lambda: logic.clear_all(
            buttons,
            lambda: update_selected_label_wrapper(),
            lambda: update_counters_wrapper()
        )
    )
    layout.addWidget(clear_button)

    selected_heroes_label.adjustSize()
    copy_button.adjustSize()
    clear_button.adjustSize()

    # Устанавливаем минимальную ширину правой панели на основе содержимого
    label_width = selected_heroes_label.sizeHint().width()
    copy_button_width = copy_button.sizeHint().width()
    clear_button_width = clear_button.sizeHint().width()
    extra_elements_width = max(label_width, copy_button_width, clear_button_width)

    # Минимальная ширина правой панели
    min_width = extra_elements_width + layout.contentsMargins().left() + layout.contentsMargins().right() + 20
    right_frame.setMinimumWidth(min_width)
    print(f"Минимальная ширина правой панели ({initial_mode}): {min_width} пикселей")

    # Минимальная высота правой панели
    total_height = (
        sum(table_widget.rowHeight(i) for i in range(rows)) +
        selected_heroes_label.sizeHint().height() +
        copy_button.sizeHint().height() +
        clear_button.sizeHint().height() +
        layout.contentsMargins().top() + layout.contentsMargins().bottom() +
        layout.spacing() * 2
    )
    right_frame.setMinimumHeight(total_height)
    print(f"Минимальная высота правой панели ({initial_mode}): {total_height} пикселей")

    return right_frame, selected_heroes_label, update_counters_wrapper, update_selected_label_wrapper