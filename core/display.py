# File: display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters
from translations import get_text

def generate_counterpick_display(logic, result_frame, left_images, small_images):
    """
    Генерирует детальное отображение рейтинга контрпиков.
    Убраны рамки у основной иконки/текста, убраны отступы у маленьких иконок.
    """
    # print(f"--- Начало generate_counterpick_display (для {logic.selected_heroes}) ---")

    if not logic.selected_heroes:
        # print("Нет выбранных героев, отображение не генерируется.")
        return

    # print("Расчет counter_scores...")
    counter_scores = logic.calculate_counter_scores()
    if not counter_scores:
         # print("Counter_scores пуст.")
         return

    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    # print(f"Получено {len(sorted_counters)} записей рейтинга.")

    if not hasattr(logic, 'effective_team') or not logic.effective_team:
         # print("Пересчет effective_team для подсветки...")
         logic.calculate_effective_team(counter_scores)
    effective_team = logic.effective_team
    # print(f"Эффективная команда для подсветки: {effective_team}")

    items_added = 0
    layout = result_frame.layout()
    if not layout:
         print("[!] Ошибка: layout у result_frame отсутствует.")
         return

    # print("Начало добавления виджетов рейтинга...")
    for counter, score in sorted_counters:
        # Отображаем всех, включая с отрицательным рейтингом, т.к. они могут быть выбраны
        # Пропуск нулевых, если они не выбраны
        if abs(score) < 0.01 and counter not in logic.selected_heroes: continue

        if counter in left_images and left_images.get(counter):
            # Основной фрейм для строки героя
            counter_frame = QFrame(result_frame)
            counter_layout = QHBoxLayout(counter_frame)
            counter_layout.setContentsMargins(4, 2, 4, 2) # Внешние отступы строки
            counter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter) # Вертикальное выравнивание по центру
            counter_layout.setSpacing(5) # Расстояние между элементами в строке

            is_effective = counter in effective_team
            bg_color_str = "background-color: lightblue;" if is_effective else "background-color: transparent;"
            # Рамка только для эффективной команды
            border_style = "border: 1px solid darkblue;" if is_effective else "border: none;"
            counter_frame.setStyleSheet(f"{bg_color_str} {border_style} border-radius: 3px;")

            # 1. Иконка героя (слева) - БЕЗ РАМКИ
            img_label = QLabel()
            img_label.setPixmap(left_images[counter])
            img_label.setStyleSheet("border: none; padding: 0px; margin: 0px;") # Явно убираем все лишнее
            counter_layout.addWidget(img_label)

            # 2. Текст рейтинга - БЕЗ РАМКИ
            text_label = QLabel(f"{counter}: {score:.1f} {get_text('points')}")
            text_label.setStyleSheet("border: none; padding: 0px; margin: 0px;") # Явно убираем все лишнее
            counter_layout.addWidget(text_label)

            # 3. Растяжение перед маленькими иконками
            counter_layout.addStretch(1)

            # 4. Иконки врагов (маленькие)
            enemies_layout = QHBoxLayout() # Отдельный layout для маленьких иконок
            enemies_layout.setContentsMargins(0, 0, 0, 0)
            enemies_layout.setSpacing(2) # Небольшой отступ между маленькими иконками
            enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter) # Выравнивание справа

            # Враги, которых контрит этот герой (зеленая рамка)
            counter_for_heroes = [h for h in logic.selected_heroes if counter in heroes_counters.get(h, [])]
            for hero in counter_for_heroes:
                 if hero in small_images and small_images.get(hero):
                     small_img_label = QLabel()
                     small_img_label.setPixmap(small_images[hero])
                     # Убираем padding и margin
                     small_img_label.setStyleSheet("border: 2px solid green; border-radius: 3px; padding: 0px; margin: 0px;")
                     small_img_label.setToolTip(f"{counter} {get_text('counters')} {hero}")
                     enemies_layout.addWidget(small_img_label)

            # Враги, которые контрят этого героя (красная рамка)
            countered_by_heroes = [h for h in logic.selected_heroes if h in heroes_counters.get(counter, [])]
            for hero in countered_by_heroes:
                 if hero in small_images and small_images.get(hero):
                     small_img_label = QLabel()
                     small_img_label.setPixmap(small_images[hero])
                     # Убираем padding и margin
                     small_img_label.setStyleSheet("border: 2px solid red; border-radius: 3px; padding: 0px; margin: 0px;")
                     small_img_label.setToolTip(f"{hero} {get_text('counters')} {counter}")
                     enemies_layout.addWidget(small_img_label)

            # Добавляем layout с маленькими иконками в основной layout строки
            if enemies_layout.count() > 0:
                 counter_layout.addLayout(enemies_layout)

            try:
                 layout.addWidget(counter_frame)
                 items_added += 1
            except Exception as e:
                 print(f"[!] Ошибка добавления виджета для {counter}: {e}")
                 if counter_frame: counter_frame.deleteLater()
        # else:
        #      print(f"  [!] Пропуск {counter}: нет иконки в left_images.")

    # print(f"Добавлено {items_added} элементов в result_frame.")
    # print(f"--- Конец generate_counterpick_display ---")


# --- generate_minimal_icon_list ---
def generate_minimal_icon_list(logic, result_frame, left_images):
    """
    Генерирует минималистичный список иконок контрпиков.
    """
    # print(f"--- Начало generate_minimal_icon_list (для {logic.selected_heroes}) ---")

    if not logic.selected_heroes:
        # print("Нет выбранных героев, отображение не генерируется.")
        return

    # print("Расчет counter_scores...")
    counter_scores = logic.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    # Отображаем всех, кроме тех, у кого отрицательный рейтинг И они не выбраны
    filtered_counters = [(hero, score) for hero, score in sorted_counters if score >= 0 or hero in logic.selected_heroes]
    # print(f"Получено {len(filtered_counters)} записей с рейтингом >= 0 или выбранных.")

    if not filtered_counters:
        # print("Не найдено героев для отображения.")
        return

    layout = result_frame.layout()
    if not layout:
         print("[!] Ошибка: layout у result_frame отсутствует в generate_minimal_icon_list.")
         return

    # Используем QHBoxLayout напрямую в result_frame для режима min
    # Очищаем предыдущий layout если он был (например, от QLabel)
    while layout.count():
        item = layout.takeAt(0)
        if item.widget(): item.widget().deleteLater()
        elif item.layout(): # Рекурсивно чистим вложенные layout'ы
            while item.layout().count():
                 sub_item = item.layout().takeAt(0)
                 if sub_item.widget(): sub_item.widget().deleteLater()

    # Создаем горизонтальный layout для иконок
    icons_layout = QHBoxLayout()
    icons_layout.setContentsMargins(2, 2, 2, 2) # Маленькие отступы
    icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    icons_layout.setSpacing(3) # Отступ между иконками

    if not hasattr(logic, 'effective_team') or not logic.effective_team:
         # print("Пересчет effective_team для подсветки...")
         logic.calculate_effective_team(counter_scores)
    effective_team = logic.effective_team

    items_added = 0
    # print("Начало добавления иконок...")
    for counter, score in filtered_counters:
        if counter in left_images and left_images.get(counter):
            img_label = QLabel()
            pixmap = left_images[counter] # Берем pixmap нужного размера для left_panel в min режиме
            img_label.setPixmap(pixmap)
            img_label.setFixedSize(pixmap.width(), pixmap.height()) # Используем его размер

            style = "border: 1px solid gray; border-radius: 3px; padding: 0px;" # Рамка по умолчанию
            is_effective = counter in effective_team
            is_selected = counter in logic.selected_heroes

            # Приоритет выделения: выбранный (желтый) > эффективный (голубой) > обычный (серый)
            if is_selected: style = "border: 3px solid yellow; border-radius: 3px; padding: 0px;"
            elif is_effective: style = "border: 3px solid lightblue; border-radius: 3px; padding: 0px;"

            img_label.setStyleSheet(style)
            img_label.setToolTip(f"{counter}\nRating: {score:.1f}")

            icons_layout.addWidget(img_label)
            items_added += 1
        # else:
        #      print(f"  [!] Пропуск {counter}: нет иконки в left_images.")

    if items_added > 0:
         # Добавляем layout с иконками в основной layout result_frame
         layout.addLayout(icons_layout)
         # Добавляем растяжение в конце основного layout'а
         layout.addStretch(1)
         # print(f"Добавлен icons_layout с {items_added} иконками в result_frame.")
    # else:
         # print("Ни одна иконка не была добавлена.")

    # print(f"--- Конец generate_minimal_icon_list ---")