from PySide6.QtWidgets import QLabel
from heroes_bd import heroes

def update_horizontal_icon_list(window):
    """
    Updates the horizontal icon list based on the current state of selected heroes.
    If no heroes are selected, the list should be empty.
    """
    print("Вызов update_horizontal_icon_list")
    print(f"Текущий режим: {window.mode}")
    print(f"Текущие selected_heroes: {window.logic.selected_heroes}")
    print(f"Текущие effective_team: {window.logic.effective_team}")

    # Clear the current icons in the horizontal list
    while window.icons_layout.count():
        item = window.icons_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    # If no heroes are selected, keep the list empty
    if not window.logic.selected_heroes:
        print("selected_heroes пуст, горизонтальный список остаётся пустым")
        window.icons_frame.update()
        window.left_container.update()
        window.main_widget.update()
        print(f"Видимость icons_frame: {window.icons_frame.isVisible()}")
        print(f"Количество элементов в icons_layout: {window.icons_layout.count()}")
        print("Завершено обновление горизонтального списка")
        return

    # Calculate counterpick ratings
    counter_scores = window.logic.calculate_counter_scores()
    print(f"Рассчитанные counter_scores: {counter_scores}")
    window.logic.calculate_effective_team(counter_scores)
    print(f"Обновлённый effective_team: {window.logic.effective_team}")

    # Filter heroes: only include those with a rating > 0
    filtered_heroes = [(hero, score) for hero, score in counter_scores.items() if score > 0]
    # Sort by rating in descending order
    filtered_heroes.sort(key=lambda x: x[1], reverse=True)
    print(f"Отфильтрованные герои с рейтингом > 0: {filtered_heroes}")

    if not filtered_heroes:
        print("Нет героев для отображения в горизонтальном списке.")
        window.icons_frame.update()
        window.left_container.update()
        window.main_widget.update()
        return

    print(f"Обновление горизонтального списка с selected_heroes: {window.logic.selected_heroes}")
    print(f"Размер horizontal_images: {len(window.horizontal_images)}")
    for hero, score in filtered_heroes:
        if hero in window.horizontal_images and window.horizontal_images[hero]:
            img_label = QLabel()
            img_label.setPixmap(window.horizontal_images[hero])
            img_label.setFixedSize(25, 25)  # Fixed size to prevent compression
            if hero in window.logic.selected_heroes:
                img_label.setStyleSheet("border: 2px solid yellow;")
                print(f"Герой {hero} выделен жёлтым (выбран)")
            if hero in window.logic.effective_team:
                img_label.setStyleSheet("border: 2px solid lightblue;")
                print(f"Герой {hero} выделен голубым (эффективная команда)")
            window.icons_layout.addWidget(img_label)
            print(f"Добавлен герой {hero} с рейтингом {score} в горизонтальный список")
        else:
            print(f"Пропущен герой {hero}: нет изображения в horizontal_images")

    window.icons_frame.update()
    window.left_container.update()
    window.main_widget.update()
    print(f"Видимость icons_frame: {window.icons_frame.isVisible()}")
    print(f"Количество элементов в icons_layout: {window.icons_layout.count()}")
    print("Завершено обновление горизонтального списка")