# File: horizontal_list.py
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QSize # Добавил QSize
from heroes_bd import heroes

def update_horizontal_icon_list(window):
    """
    Обновляет горизонтальный список иконок в icons_frame.
    Отображает рекомендуемую эффективную команду.
    """
    # print("Вызов update_horizontal_icon_list")
    # print(f"Текущий режим: {window.mode}")
    # print(f"Текущие selected_heroes: {window.logic.selected_heroes}")

    if not window.icons_layout or not window.icons_frame:
        print("[!] Ошибка: icons_layout или icons_frame не найдены.")
        return

    # Очистка текущих иконок
    while window.icons_layout.count():
        item = window.icons_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    # Если нет выбранных героев, показываем пустоту
    if not window.logic.selected_heroes:
        # print("selected_heroes пуст, горизонтальный список пуст")
        window.icons_frame.update() # Обновляем вид фрейма
        return

    # Получаем или пересчитываем эффективную команду
    if not hasattr(logic := window.logic, 'effective_team') or not logic.effective_team:
        # print("Пересчет effective_team для горизонтального списка...")
        counter_scores = logic.calculate_counter_scores()
        logic.calculate_effective_team(counter_scores)

    effective_team = logic.effective_team
    # print(f"Эффективная команда для отображения: {effective_team}")

    if not effective_team:
        # Можно добавить метку "Нет рекомендаций" или оставить пустым
        # label = QLabel(get_text("no_recommendations", "Нет рекоммендаций"))
        # window.icons_layout.addWidget(label)
        # print("Эффективная команда пуста, горизонтальный список пуст.")
        window.icons_frame.update()
        return

    # print(f"Обновление горизонтального списка. Изображений: {len(window.horizontal_images)}")
    icon_size = QSize(25, 25) # Фиксированный размер иконок в этом списке

    for hero in effective_team:
        if hero in window.horizontal_images and window.horizontal_images[hero]:
            img_label = QLabel()
            # Масштабируем до нужного размера, если он отличается
            pixmap = window.horizontal_images[hero].scaled(icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(pixmap)
            img_label.setFixedSize(icon_size) # Задаем фиксированный размер виджету
            img_label.setToolTip(hero) # Подсказка с именем героя

            # Подсветка, если герой выбран врагом (желтая)
            style = "border: 1px solid gray; border-radius: 3px;" # Стиль по умолчанию
            if hero in window.logic.selected_heroes:
                style = "border: 2px solid orange; border-radius: 3px;" # Выделяем выбранных врагов особо
                img_label.setToolTip(f"{hero}\n({get_text('enemy_selected_tooltip', 'Выбран врагом')})")

            img_label.setStyleSheet(style)
            window.icons_layout.addWidget(img_label)
            # print(f"Добавлен герой {hero} в горизонтальный список")
        else:
            print(f"Пропущен герой {hero}: нет изображения в horizontal_images")

    window.icons_frame.update() # Обновляем вид фрейма
    # print("Завершено обновление горизонтального списка")