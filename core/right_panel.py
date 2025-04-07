from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QGridLayout, QVBoxLayout, QScrollArea, QWidget
from PySide6.QtCore import Qt, Signal
from heroes_bd import heroes
from translations import get_text
from horizontal_list import update_horizontal_icon_list

class HeroButton(QWidget):
    clicked = Signal()
    customContextMenuRequested = Signal(object)

    def __init__(self, hero, icon, initial_mode):
        super().__init__()
        self.hero = hero

        # Задаём минимальные размеры кнопки в зависимости от режима
        if initial_mode == "max":
            self.setMinimumSize(60, 90)  # Размер иконки 60x60 + место для текста
        else:  # "middle" режим
            self.setMinimumSize(35, 35)  # Размер иконки 35x35, текст скрыт

        layout = QVBoxLayout(self)
        # Добавляем внутренние отступы (2 пикселя со всех сторон) для красоты
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)  # Оставляем расстояние между элементами нулевым
        # Центрируем содержимое по вертикали
        layout.setAlignment(Qt.AlignVCenter)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon)
        self.icon_label.setAlignment(Qt.AlignCenter)  # Центрируем иконку по горизонтали
        self.icon_label.setContentsMargins(0, 0, 0, 0)  # Убираем отступы у иконки
        self.icon_label.setStyleSheet("padding: 0px; margin: 0px;")

        # Задаём фиксированные размеры для icon_label, соответствующие ширине кнопки
        if initial_mode == "max":
            self.icon_label.setFixedSize(60, 60)  # Устанавливаем ширину равной ширине кнопки (60 пикселей)
        else:
            self.icon_label.setFixedSize(35, 35)  # Соответствует SIZES['middle']['right']

        layout.addWidget(self.icon_label, stretch=0)

        self.text_label = QLabel(hero if initial_mode == "max" else "")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("font-size: 8pt; line-height: 8pt; padding: 0px; margin: 0px;")
        self.text_label.setContentsMargins(0, 0, 0, 0)  # Убираем отступы у текста
        self.text_label.setWordWrap(True)

        # Устанавливаем ширину text_label равной ширине кнопки и корректируем высоту
        if initial_mode == "max":
            self.text_label.setFixedWidth(60)  # Ширина равна ширине кнопки
            self.text_label.setMaximumHeight(30)  # Оставляем максимальную высоту 30
        else:
            self.text_label.setMaximumHeight(0)

        layout.addWidget(self.text_label, stretch=0)

        self.setStyleSheet("border: none;")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        # Логирование размеров для отладки
        print(
            f"HeroButton для {hero}: icon_label size = {self.icon_label.size().width()}x{self.icon_label.size().height()}, button min size = {self.minimumSize().width()}x{self.minimumSize().height()}"
        )
        print(
            f"HeroButton для {hero}: text_label size = {self.text_label.size().width()}x{self.text_label.size().height()}"
        )

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

    grid_container = QFrame()
    grid = QGridLayout(grid_container)
    grid.setContentsMargins(0, 0, 0, 0)  # Убираем отступы у сетки
    if initial_mode == "max":
        grid.setSpacing(2)  # В "max" режиме оставляем spacing 2
    else:  # "middle" режим
        grid.setSpacing(0)  # В "middle" режиме убираем spacing для компактности

    if initial_mode == "max":
        grid_container.setFixedSize(500, 800)  # Фиксированные размеры для "max" режима
        print(f"Установлены размеры grid_container для режима max: 500x800 пикселей")
    else:  # "middle" режим
        grid_container.setFixedSize(250, 350)  # Фиксированные размеры для "middle" режима
        print(f"Установлены размеры grid_container для режима middle: 250x350 пикселей")

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

    for i, hero in enumerate(heroes):
        icon = parent.right_images.get(hero, None)
        if icon is None or icon.isNull():
            print(f"Предупреждение: Нет валидной иконки для {hero} в режиме '{initial_mode}'")
            continue
        btn = HeroButton(hero, icon, initial_mode)
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
        grid.addWidget(btn, i // 5, i % 5)  # 5 столбцов
        buttons[hero] = btn

    scroll_area.setWidget(grid_container)
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

    grid_width = grid_container.width()
    scrollbar_width = scroll_area.verticalScrollBar().sizeHint().width()
    scroll_area_frame_width = 4

    label_width = selected_heroes_label.sizeHint().width()
    copy_button_width = copy_button.sizeHint().width()
    clear_button_width = clear_button.sizeHint().width()
    extra_elements_width = max(label_width, copy_button_width, clear_button_width)

    total_width = (max(grid_width, extra_elements_width) +
                   layout.contentsMargins().left() + layout.contentsMargins().right() +
                   scrollbar_width + scroll_area_frame_width + 10)
    right_frame.setMinimumWidth(total_width)
    print(f"Минимальная ширина правой панели ({initial_mode}): {total_width} пикселей")

    grid_height = grid_container.height()
    scrollbar_height = scroll_area.horizontalScrollBar().sizeHint().height()
    scroll_area_frame_height = 4

    total_height = (grid_height +
                    selected_heroes_label.sizeHint().height() +
                    copy_button.sizeHint().height() +
                    clear_button.sizeHint().height() +
                    layout.contentsMargins().top() + layout.contentsMargins().bottom() +
                    layout.spacing() * 2 +
                    scroll_area_frame_height +
                    scrollbar_height)
    right_frame.setMinimumHeight(total_height)
    print(f"Минимальная высота правой панели ({initial_mode}): {total_height} пикселей")

    return right_frame, selected_heroes_label, update_counters_wrapper, update_selected_label_wrapper