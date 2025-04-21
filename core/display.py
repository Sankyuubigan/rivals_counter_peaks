# File: display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QScrollArea
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters
from translations import get_text

# --- Вспомогательная функция для очистки layout ---
def clear_layout(layout):
    """Рекурсивно удаляет все виджеты и layout'ы из заданного layout'а."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        else:
            sub_layout = item.layout()
            if sub_layout is not None:
                clear_layout(sub_layout) # Рекурсивно очищаем вложенный layout
                # Удаляем сам layout item после очистки
                # layout.removeItem(item) # Это может быть избыточно, т.к. takeAt уже удалил
                # sub_layout.deleteLater() # Удаляем сам объект layout'а
            else:
                 spacer = item.spacerItem()
                 if spacer is not None:
                     layout.removeItem(item)


def generate_counterpick_display(logic, result_frame, left_images, small_images):
    """
    Генерирует детальное отображение рейтинга контрпиков в result_frame.
    """
    layout = result_frame.layout()
    # Создаем layout, если его нет
    if not layout:
        layout = QVBoxLayout(result_frame)
        layout.setObjectName("result_layout") # Имя для layout'а
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        result_frame.setLayout(layout)

    # Очищаем layout перед заполнением
    clear_layout(layout)

    # --- Находим result_label (предполагаем, что он существует в parent'е result_frame) ---
    result_label_found = None
    if result_frame.parentWidget() and isinstance(result_frame.parentWidget(), QScrollArea):
         canvas = result_frame.parentWidget()
         result_label_found = canvas.findChild(QLabel, "result_label")
    # --- ---

    # Если герои не выбраны, показываем сообщение
    if not logic.selected_heroes:
        if result_label_found:
            result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE))
            result_label_found.show()
            # Добавляем label обратно в layout (на случай, если его удалили)
            if layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
            layout.addStretch(1) # Растяжка, чтобы текст был сверху
        return

    # Скрываем result_label, т.к. сейчас будут отображаться контрпики
    if result_label_found:
        result_label_found.hide()

    # Расчеты
    counter_scores = logic.calculate_counter_scores()
    if not counter_scores:
         # Можно добавить сообщение "Нет данных для расчета"
         return

    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    effective_team = logic.calculate_effective_team(counter_scores)
    selected_heroes_set = set(logic.selected_heroes)

    items_added = 0
    # Добавляем виджеты для каждого контрпика
    for counter, score in sorted_counters:
        # Отображаем только с положительным рейтингом или если это выбранный враг
        if score <= 0 and counter not in selected_heroes_set:
            continue

        # Проверяем наличие картинки
        if counter not in left_images or not left_images.get(counter):
            # print(f"[WARN] No left image for {counter}")
            continue

        # --- Создание строки для героя ---
        counter_frame = QFrame(result_frame) # Родитель - result_frame
        counter_layout = QHBoxLayout(counter_frame)
        counter_layout.setContentsMargins(4, 1, 4, 1); counter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter); counter_layout.setSpacing(5)

        is_effective = counter in effective_team
        is_enemy = counter in selected_heroes_set

        # --- Стилизация строки ---
        bg_color_str = "background-color: transparent;"
        border_style = "border: none;"
        text_color = "color: black;"

        if is_enemy:
            bg_color_str = "background-color: #ffe0e0;" # Светло-красный
            border_style = "border: 1px solid red;"
            text_color = "color: darkred;"
        elif is_effective:
            bg_color_str = "background-color: lightblue;" # Голубой
            border_style = "border: 1px solid darkblue;"
            text_color = "color: darkblue;"

        counter_frame.setStyleSheet(f"QFrame {{ {bg_color_str} {border_style} border-radius: 3px; }}")
        # --- Конец Стилизации ---

        # Иконка героя
        img_label = QLabel(); img_label.setPixmap(left_images[counter]); img_label.setStyleSheet("border: none; padding: 0px; margin: 0px;")
        counter_layout.addWidget(img_label)

        # Текст (Имя: Рейтинг баллов)
        text_label = QLabel(f"{counter}: {score:.1f} {get_text('points', language=logic.DEFAULT_LANGUAGE)}");
        text_label.setStyleSheet(f"QLabel {{ border: none; padding: 0px; margin: 0px; {text_color} }}") # Применяем цвет текста
        counter_layout.addWidget(text_label)

        counter_layout.addStretch(1) # Растяжка перед иконками связей

        # --- Отображение связей с выбранными врагами ---
        enemies_layout = QHBoxLayout(); enemies_layout.setContentsMargins(0, 0, 0, 0); enemies_layout.setSpacing(2)
        enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Враги, которых контрит этот 'counter'
        counter_for_heroes = [h for h in selected_heroes_set if counter in heroes_counters.get(h, [])]
        for hero in counter_for_heroes:
             if hero in small_images and small_images.get(hero):
                 small_img_label = QLabel(); small_img_label.setPixmap(small_images[hero])
                 small_img_label.setStyleSheet("border: 2px solid green; border-radius: 3px; padding: 0px; margin: 0px;")
                 small_img_label.setToolTip(f"{counter} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {hero}")
                 enemies_layout.addWidget(small_img_label)

        # Враги, которые контрят этого 'counter'
        countered_by_heroes = [h for h in selected_heroes_set if h in heroes_counters.get(counter, [])]
        for hero in countered_by_heroes:
             if hero in small_images and small_images.get(hero):
                 small_img_label = QLabel(); small_img_label.setPixmap(small_images[hero])
                 small_img_label.setStyleSheet("border: 2px solid red; border-radius: 3px; padding: 0px; margin: 0px;")
                 small_img_label.setToolTip(f"{hero} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {counter}")
                 enemies_layout.addWidget(small_img_label)

        if enemies_layout.count() > 0:
            counter_layout.addLayout(enemies_layout)
        # --- Конец отображения связей ---

        layout.addWidget(counter_frame)
        items_added += 1
        # --- Конец создания строки ---

    # Добавляем растяжку в конце списка, если есть элементы
    if items_added > 0:
        layout.addStretch(1)
    else:
        # Если после фильтрации не осталось элементов для отображения
        if result_label_found:
            result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE))
            result_label_found.show()
            if layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
            layout.addStretch(1)


# --- generate_minimal_icon_list ---
def generate_minimal_icon_list(logic, result_frame, left_images):
    """
    Генерирует минималистичный список иконок контрпиков в result_frame.
    """
    layout = result_frame.layout()
    # Создаем layout, если его нет
    if not layout:
        layout = QVBoxLayout(result_frame) # Основной layout будет вертикальным
        layout.setObjectName("result_layout_min")
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        result_frame.setLayout(layout)

    # Очищаем layout перед заполнением
    clear_layout(layout)

    # --- Находим result_label ---
    result_label_found = None
    if result_frame.parentWidget() and isinstance(result_frame.parentWidget(), QScrollArea):
         canvas = result_frame.parentWidget()
         result_label_found = canvas.findChild(QLabel, "result_label")
    # --- ---

    # Если герои не выбраны, показываем сообщение
    if not logic.selected_heroes:
        if result_label_found:
            result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE))
            result_label_found.show()
            if layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
            layout.addStretch(1)
        return

    # Скрываем result_label
    if result_label_found:
        result_label_found.hide()

    # Расчеты
    counter_scores = logic.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    selected_heroes_set = set(logic.selected_heroes)
    # Фильтруем: показываем всех врагов + рекомендованных с score >= 0
    filtered_counters = [(hero, score) for hero, score in sorted_counters if score >= 0 or hero in selected_heroes_set]

    if not filtered_counters:
        # Показываем "Нет рекомендаций"
        if result_label_found:
            result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE))
            result_label_found.show()
            if layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
            layout.addStretch(1)
        return

    # --- Создаем горизонтальный layout для иконок внутри вертикального ---
    icons_layout = QHBoxLayout()
    icons_layout.setContentsMargins(2, 2, 2, 2)
    icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    icons_layout.setSpacing(3)
    # --- ---

    effective_team = logic.calculate_effective_team(counter_scores)
    effective_team_set = set(effective_team)

    items_added = 0
    # Добавляем иконки
    for counter, score in filtered_counters:
        if counter in left_images and left_images.get(counter):
            img_label = QLabel()
            pixmap = left_images[counter]
            img_label.setPixmap(pixmap)
            img_label.setFixedSize(pixmap.width(), pixmap.height()) # Фиксируем размер под иконку

            is_effective = counter in effective_team_set
            is_selected = counter in selected_heroes_set

            # --- Стилизация рамки ---
            border_style = "border: 1px solid gray; border-radius: 3px; padding: 0px;" # Серая по умолчанию
            if is_selected:
                border_style = "border: 3px solid orange; border-radius: 3px; padding: 0px;" # Оранжевая для врага
            elif is_effective:
                border_style = "border: 3px solid blue; border-radius: 3px; padding: 0px;" # Синяя для рекомендованного
            # --- ---

            img_label.setStyleSheet(border_style)
            img_label.setToolTip(f"{counter}\nRating: {score:.1f}")

            icons_layout.addWidget(img_label)
            items_added += 1

    if items_added > 0:
         # Добавляем горизонтальный layout с иконками в основной вертикальный layout
         layout.addLayout(icons_layout)
         layout.addStretch(1) # Растяжка в конце основного layout'а
    # else:
        # Если по какой-то причине нет иконок, показываем "Нет рекомендаций"
        # if result_label_found:
        #     result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE))
        #     result_label_found.show()
        #     if layout.indexOf(result_label_found) == -1:
        #         layout.addWidget(result_label_found)
        #     layout.addStretch(1)
