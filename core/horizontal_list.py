# File: horizontal_list.py
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QSize, Qt # <--- Добавлен импорт Qt
from translations import get_text # Добавил импорт get_text

def update_horizontal_icon_list(window):
    """
    Обновляет горизонтальный список иконок в icons_frame.
    Отображает рекомендуемую эффективную команду.
    """
    # print("Вызов update_horizontal_icon_list")

    if not window.icons_layout or not window.icons_frame:
        print("[!] Ошибка: icons_layout или icons_frame не найдены.")
        return

    # Очистка текущих иконок
    while window.icons_layout.count():
        item = window.icons_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    # Если нет выбранных героев, показываем пустоту или сообщение
    if not window.logic.selected_heroes:
        # label = QLabel(get_text("select_enemies_for_recommendations", "Выберите врагов для рекомендаций"))
        # window.icons_layout.addWidget(label)
        window.icons_frame.update() # Обновляем вид фрейма
        return

    # Получаем или пересчитываем эффективную команду
    logic = window.logic
    if not hasattr(logic, 'effective_team') or not logic.effective_team:
        counter_scores = logic.calculate_counter_scores()
        logic.calculate_effective_team(counter_scores)

    effective_team = logic.effective_team

    if not effective_team:
        # Можно добавить метку "Нет рекомендаций"
        label = QLabel(get_text("no_recommendations", "Нет рекомендаций"))
        window.icons_layout.addWidget(label)
        window.icons_frame.update()
        return

    icon_size = QSize(25, 25) # Фиксированный размер иконок

    for hero in effective_team:
        if hero in window.horizontal_images and window.horizontal_images[hero]:
            img_label = QLabel()
            # Масштабируем до нужного размера
            pixmap = window.horizontal_images[hero].scaled(icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(pixmap)
            img_label.setFixedSize(icon_size)
            img_label.setToolTip(hero)

            # Подсветка, если герой выбран врагом (желтая/оранжевая)
            style = "border: 1px solid gray; border-radius: 3px; padding: 0px;" # Стиль по умолчанию
            if hero in window.logic.selected_heroes:
                style = "border: 2px solid orange; border-radius: 3px; padding: 0px;" # Выделяем выбранных врагов
                img_label.setToolTip(f"{hero}\n({get_text('enemy_selected_tooltip', 'Выбран врагом')})")

            img_label.setStyleSheet(style)
            window.icons_layout.addWidget(img_label)
        else:
            print(f"Пропущен герой {hero}: нет изображения в horizontal_images")

    # Добавляем растяжение в конец, чтобы иконки не растягивались на всю ширину
    window.icons_layout.addStretch(1)
    window.icons_frame.update() # Обновляем вид фрейма