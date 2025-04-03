from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QGridLayout, QVBoxLayout
from PySide6.QtCore import Qt
from heroes_bd import heroes
from translations import get_text

def create_right_panel(parent, logic, buttons, copy_to_clipboard, result_frame, result_label, canvas,
                       update_scrollregion, initial_mode="middle"):
    right_frame = QFrame(parent)
    layout = QVBoxLayout(right_frame)
    layout.setContentsMargins(5, 5, 5, 5)

    grid = QGridLayout()
    grid.setSpacing(2)  # Уменьшаем расстояние между кнопками
    layout.addLayout(grid)

    def update_counters_wrapper(result_label, selected_heroes_label):
        current_mode = parent.mode
        if logic.selected_heroes:
            from images_load import get_images_for_mode
            right_images, left_images, small_images = get_images_for_mode(current_mode)
            if current_mode == "min":
                logic.generate_minimal_icon_list(result_frame, result_label, left_images)
            else:
                logic.generate_counterpick_display(result_frame, result_label, left_images, small_images)
            if result_label and hasattr(result_label, 'isVisible') and result_label.isVisible():
                result_label.setText("")
        else:
            for widget in result_frame.findChildren(QFrame):
                widget.deleteLater()
            if result_label and hasattr(result_label, 'isVisible') and result_label.isVisible():
                result_label.setText(get_text('no_heroes_selected'))
        update_selected_label_wrapper(selected_heroes_label)
        update_scrollregion()

    def update_selected_label_wrapper(selected_heroes_label):
        if selected_heroes_label and hasattr(selected_heroes_label, 'setText'):
            selected_heroes_label.setText(logic.get_selected_heroes_text())

    for i, hero in enumerate(heroes):
        btn = QPushButton()
        btn_layout = QVBoxLayout(btn)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(2)
        btn_layout.setAlignment(Qt.AlignCenter)  # Выравниваем содержимое по центру

        # Добавляем текст только в режиме "max"
        if initial_mode == "max":
            label = QLabel(hero)
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            btn_layout.addWidget(label)

        btn.clicked.connect(lambda checked, h=hero: logic.toggle_hero(h, buttons, lambda: update_counters_wrapper(parent.result_label, parent.selected_heroes_label)))
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, h=hero, b=btn: logic.set_priority(h, b, b.parent(), lambda: update_counters_wrapper(parent.result_label, parent.selected_heroes_label)))
        grid.addWidget(btn, i // 5, i % 5)
        buttons[hero] = btn

    # Устанавливаем максимальную ширину правой панели на основе количества кнопок в ряду
    button_width = 70 if initial_mode == "max" else 40
    right_frame.setMaximumWidth(
        (button_width + grid.spacing()) * 5 + layout.contentsMargins().left() + layout.contentsMargins().right())

    selected_heroes_label = QLabel(get_text('selected'))
    selected_heroes_label.setWordWrap(True)
    layout.addWidget(selected_heroes_label)

    copy_button = QPushButton(get_text('copy_rating'))
    copy_button.clicked.connect(lambda: copy_to_clipboard(logic))
    layout.addWidget(copy_button)

    clear_button = QPushButton(get_text('clear_all'))
    clear_button.clicked.connect(
        lambda: logic.clear_all(buttons, lambda: update_selected_label_wrapper(parent.selected_heroes_label), lambda: update_counters_wrapper(parent.result_label, parent.selected_heroes_label)))
    layout.addWidget(clear_button)

    return right_frame, selected_heroes_label, update_counters_wrapper, update_selected_label_wrapper