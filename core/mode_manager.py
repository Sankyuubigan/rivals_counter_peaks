from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from right_panel import create_right_panel
from left_panel import create_left_panel
from images_load import get_images_for_mode
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes

def change_mode(window, mode):
    window.mode = mode
    update_interface_for_mode(window)

def update_interface_for_mode(window):
    if window.mode in window.mode_positions:
        window.mode_positions[window.mode] = window.pos()

    # Clear the buttons dictionary before removing widgets
    window.buttons.clear()

    # Load images for the new mode
    window.right_images, window.left_images, window.small_images, window.horizontal_images = get_images_for_mode(window.mode)

    # Remove old widgets from inner_layout
    while window.inner_layout.count():
        item = window.inner_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    # Recreate icons_frame and its layout
    window.icons_frame = QFrame(window.main_widget)
    window.icons_layout = QHBoxLayout(window.icons_frame)
    window.icons_layout.setContentsMargins(0, 5, 0, 5)
    window.icons_layout.setAlignment(Qt.AlignLeft)

    # Recreate left and right panels
    window.canvas, window.result_frame, window.result_label, window.update_scrollregion = create_left_panel(
        window.main_widget)
    window.right_frame, window.selected_heroes_label, window.update_counters_wrapper, window.update_selected_label_wrapper = create_right_panel(
        window, window.logic, window.buttons, window.copy_to_clipboard, window.result_frame, window.result_label,
        window.canvas, window.update_scrollregion, window.mode
    )

    # Recreate left_container
    window.left_container = QWidget()
    left_layout = QVBoxLayout(window.left_container)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.addWidget(window.icons_frame)
    left_layout.addWidget(window.canvas, stretch=1)

    # Configure the interface based on the mode
    if window.mode == "max":
        window.setMinimumHeight(0)
        window.setMaximumHeight(16777215)
        window.resize(1100, 1000)
        window.left_container.setMinimumWidth(600)
        window.left_container.setMaximumWidth(600)
        window.inner_layout.addWidget(window.left_container)
        window.inner_layout.addWidget(window.right_frame, stretch=0)
        window.canvas.setVisible(True)
        window.icons_frame.setVisible(True)
        window.left_container.setVisible(True)
        window.right_frame.setVisible(True)
        for i, hero in enumerate(heroes):
            btn = window.buttons[hero]
            icon = window.right_images.get(hero)
            if icon is not None and not icon.isNull():
                btn.icon_label.setPixmap(icon)
            else:
                print(f"Предупреждение: Нет валидной иконки для {hero} в режиме 'max'")
            btn.setVisible(True)
        window.author_button.setVisible(True)
        window.rating_button.setVisible(True)
    elif window.mode == "middle":
        window.setMinimumHeight(0)
        window.setMaximumHeight(16777215)
        window.resize(880, 460)
        window.left_container.setMinimumWidth(0)
        window.left_container.setMaximumWidth(16777215)
        window.inner_layout.addWidget(window.left_container, stretch=2)
        window.inner_layout.addWidget(window.right_frame, stretch=0)
        window.canvas.setVisible(True)
        window.icons_frame.setVisible(True)
        window.left_container.setVisible(True)
        window.right_frame.setVisible(True)
        for i, hero in enumerate(heroes):
            btn = window.buttons[hero]
            icon = window.right_images.get(hero)
            if icon is not None and not icon.isNull():
                btn.icon_label.setPixmap(icon)
            else:
                print(f"Предупреждение: Нет валидной иконки для {hero} в режиме 'middle'")
            btn.text_label.setText("")
            btn.setVisible(True)
        window.author_button.setVisible(False)
        window.rating_button.setVisible(False)
    elif window.mode == "min":
        window.left_container.setMinimumWidth(0)
        window.left_container.setMaximumWidth(16777215)
        window.inner_layout.addWidget(window.left_container, stretch=1)
        window.author_button.setVisible(False)
        window.rating_button.setVisible(False)
        window.right_frame.setVisible(False)

        # Dynamically calculate window height
        # 1. Get the height of top_frame
        top_frame_height = window.top_frame.height()
        print(f"Высота top_frame: {top_frame_height}")

        # 2. Call update_horizontal_icon_list to populate icons_frame
        update_horizontal_icon_list(window)

        # 3. Force a layout update to ensure icons_frame has the correct size
        window.icons_layout.invalidate()
        window.icons_frame.updateGeometry()
        window.icons_frame.adjustSize()

        # 4. Get the height of icons_frame (horizontal list)
        icons_layout_margins = window.icons_layout.contentsMargins()
        icon_frame_height = window.icons_frame.height()
        print(f"Высота icons_frame до корректировки: {icon_frame_height}")

        # Ensure the height accounts for the icon size (25) + margins (5 + 5)
        expected_icon_frame_height = 25 + icons_layout_margins.top() + icons_layout_margins.bottom()
        if icon_frame_height < expected_icon_frame_height:
            icon_frame_height = expected_icon_frame_height
            window.icons_frame.setMinimumHeight(icon_frame_height)
            print(f"Установлена минимальная высота icons_frame: {icon_frame_height}")

        icon_height_with_margins = icon_frame_height
        print(f"Высота icons_frame с отступами: {icon_height_with_margins}")

        # 5. Get the height of the canvas (even if empty)
        window.canvas.updateGeometry()
        window.canvas.adjustSize()
        canvas_height = window.canvas.height()
        if canvas_height == 0:
            canvas_height = window.canvas.minimumHeight()
        print(f"Высота canvas: {canvas_height}")

        # 6. Account for left_container's layout margins
        left_layout_margins = window.left_container.layout().contentsMargins()
        left_container_margins = left_layout_margins.top() + left_layout_margins.bottom()
        print(f"Отступы left_container: top={left_layout_margins.top()}, bottom={left_layout_margins.bottom()}")

        # 7. Account for main_layout margins (top and bottom)
        main_layout_margins = window.main_layout.contentsMargins()
        total_margins = main_layout_margins.top() + main_layout_margins.bottom()
        print(f"Отступы main_layout: top={main_layout_margins.top()}, bottom={main_layout_margins.bottom()}")

        # 8. Final window height: top_frame height + icons_frame height + canvas height + all margins + padding
        padding = 10  # Add some padding to account for window decorations
        new_height = (top_frame_height +
                      icon_height_with_margins +
                      canvas_height +
                      left_container_margins +
                      total_margins +
                      padding)
        print(f"Итоговая высота окна: {new_height}")

        # Set the window height
        window.setFixedHeight(new_height)
        window.resize(600, new_height)
        window.icons_frame.setVisible(True)
        print(f"Установлена высота окна: {new_height}")

        # Force a final layout update
        window.left_container.layout().invalidate()
        window.inner_layout.invalidate()
        window.main_widget.updateGeometry()
        window.adjustSize()
        window.update()

    # Force layout update for all modes
    window.inner_layout.invalidate()
    window.main_widget.updateGeometry()
    window.adjustSize()
    window.update()

    window.update_counters_wrapper()
    window.update_result_label_text()
    update_horizontal_icon_list(window)

    if window.mode_positions[window.mode] is not None:
        window.move(window.mode_positions[window.mode])
    else:
        window.mode_positions[window.mode] = window.pos()

    window.restore_hero_selections()