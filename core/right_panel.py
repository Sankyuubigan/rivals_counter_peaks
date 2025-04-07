from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QGridLayout, QVBoxLayout, QScrollArea, QWidget
from PySide6.QtCore import Qt, Signal
from heroes_bd import heroes
from translations import get_text


class HeroButton(QWidget):
    clicked = Signal()
    customContextMenuRequested = Signal(object)

    def __init__(self, hero, icon, initial_mode):
        super().__init__()
        self.hero = hero
        self.setMinimumSize(90 if initial_mode == "max" else 50, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(hero if initial_mode == "max" else "")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("font-size: 8pt; line-height: 8pt;")
        self.text_label.setWordWrap(True)
        self.text_label.setMaximumHeight(30 if initial_mode == "max" else 0)
        layout.addWidget(self.text_label)

        self.setStyleSheet("border: none;")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

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
    grid.setSpacing(2)

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
            parent.horizontal_images = horizontal_images  # Обновляем horizontal_images
            print(f"Обновлены horizontal_images, размер: {len(parent.horizontal_images)}")
            if current_mode == "min":
                logic.generate_minimal_icon_list(parent.result_frame, parent.result_label, left_images)
            else:
                logic.generate_counterpick_display(parent.result_frame, parent.result_label, left_images, small_images)
        # Удаляем код, связанный с result_label

        update_selected_label_wrapper()
        update_scrollregion()
        parent.result_frame.update()
        parent.canvas.update()
        print("Вызываем update_horizontal_icon_list для обновления горизонтального списка")
        parent.update_horizontal_icon_list()

    def update_selected_label_wrapper():
        if parent.selected_heroes_label and hasattr(parent.selected_heroes_label, 'setText'):
            parent.selected_heroes_label.setText(logic.get_selected_heroes_text())

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
        grid.addWidget(btn, i // 5, i % 5)
        buttons[hero] = btn

    scroll_area.setWidget(grid_container)
    layout.addWidget(scroll_area)

    button_width = 90 if initial_mode == "max" else 50
    right_frame.setMinimumWidth(
        (button_width + grid.spacing()) * 5 + layout.contentsMargins().left() + layout.contentsMargins().right() + 10
    )

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

    return right_frame, selected_heroes_label, update_counters_wrapper, update_selected_label_wrapper