# File: display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters
from translations import get_text

# --- ВОССТАНОВЛЕННАЯ ВЕРСИЯ С КРАСНО-ЗЕЛЕНЫМИ РАМКАМИ ---
def generate_counterpick_display(logic, result_frame, left_images, small_images):
    """
    Генерирует детальное отображение рейтинга контрпиков
    с красно-зелеными рамками у маленьких иконок.
    Убраны лишние рамки и отступы.
    """
    print(f"--- Начало generate_counterpick_display (для {logic.selected_heroes}) ---")

    if not logic.selected_heroes:
        print("Нет выбранных героев, отображение не генерируется.")
        return

    print("Расчет counter_scores...")
    counter_scores = logic.calculate_counter_scores()
    if not counter_scores:
         print("Counter_scores пуст.")
         return

    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    print(f"Получено {len(sorted_counters)} записей рейтинга.")

    if not hasattr(logic, 'effective_team') or not logic.effective_team:
         print("Пересчет effective_team для подсветки...")
         logic.calculate_effective_team(counter_scores)
    effective_team = logic.effective_team
    print(f"Эффективная команда для подсветки: {effective_team}")

    items_added = 0
    layout = result_frame.layout()
    if not layout:
         print("[!] Ошибка: layout у result_frame отсутствует.")
         return

    print("Начало добавления виджетов рейтинга...")
    for counter, score in sorted_counters:
        if abs(score) < 0.01 and counter not in logic.selected_heroes : continue # Пропускаем героев с нулевым рейтингом, если они не выбраны

        if counter in left_images and left_images.get(counter):
            counter_frame = QFrame(result_frame)
            counter_layout = QHBoxLayout(counter_frame)

            is_effective = counter in effective_team
            # Устанавливаем фон ТОЛЬКО для эффективной команды, остальное прозрачное
            bg_color_str = "background-color: lightblue;" if is_effective else "background-color: transparent;"
            # УБИРАЕМ рамку по умолчанию, рамка только для выделенных
            border_style = "border: 1px solid darkblue;" if is_effective else "border: none;" # <<< Изменено

            # Применяем стили к фрейму героя
            counter_frame.setStyleSheet(f"{bg_color_str} {border_style} border-radius: 3px;")
            counter_layout.setContentsMargins(4, 2, 4, 2) # Внешние отступы фрейма
            counter_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            counter_layout.setSpacing(4) # Расстояние между иконкой, текстом и маленькими иконками

            # Иконка героя (слева) - без рамки
            img_label = QLabel()
            img_label.setPixmap(left_images[counter])
            # img_label.setStyleSheet("border: none;") # Убедимся что нет рамки
            counter_layout.addWidget(img_label)

            # Текст рейтинга - без рамки
            text_label = QLabel(f"{counter}: {score:.1f} {get_text('points')}")
            # text_label.setStyleSheet("border: none;") # Убедимся что нет рамки
            counter_layout.addWidget(text_label)

            # Добавляем растяжение перед маленькими иконками
            counter_layout.addStretch(1)

            # Иконки врагов, которых контрит этот герой (зеленая рамка, без отступа)
            counter_for_heroes = [h for h in logic.selected_heroes if counter in heroes_counters.get(h, [])]
            for hero in counter_for_heroes:
                 if hero in small_images and small_images.get(hero):
                     small_img_label = QLabel()
                     small_img_label.setPixmap(small_images[hero])
                     # Убрали margin-left, padding не нужен явно
                     small_img_label.setStyleSheet("border: 2px solid green; border-radius: 3px;") # <<< Изменено
                     small_img_label.setToolTip(f"{counter} {get_text('counters')} {hero}")
                     counter_layout.addWidget(small_img_label)

            # Иконки врагов, которые контрят этого героя (красная рамка, без отступа)
            countered_by_heroes = [h for h in logic.selected_heroes if h in heroes_counters.get(counter, [])]
            for hero in countered_by_heroes:
                 if hero in small_images and small_images.get(hero):
                     small_img_label = QLabel()
                     small_img_label.setPixmap(small_images[hero])
                     # Убрали margin-left, padding не нужен явно
                     small_img_label.setStyleSheet("border: 2px solid red; border-radius: 3px;") # <<< Изменено
                     small_img_label.setToolTip(f"{hero} {get_text('counters')} {counter}")
                     counter_layout.addWidget(small_img_label)

            try:
                 layout.addWidget(counter_frame)
                 items_added += 1
            except Exception as e:
                 print(f"[!] Ошибка добавления виджета для {counter}: {e}")
                 if counter_frame: counter_frame.deleteLater()
        else:
             print(f"  [!] Пропуск {counter}: нет иконки в left_images.")

    print(f"Добавлено {items_added} элементов в result_frame.")
    print(f"--- Конец generate_counterpick_display ---")


# --- generate_minimal_icon_list остается как в прошлом ответе ---
def generate_minimal_icon_list(logic, result_frame, left_images):
    """
    Генерирует минималистичный список иконок контрпиков.
    """
    print(f"--- Начало generate_minimal_icon_list (для {logic.selected_heroes}) ---")

    if not logic.selected_heroes:
        print("Нет выбранных героев, отображение не генерируется.")
        return

    print("Расчет counter_scores...")
    counter_scores = logic.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    # Отображаем всех, кроме тех, у кого отрицательный рейтинг И они не выбраны
    filtered_counters = [(hero, score) for hero, score in sorted_counters if score >= 0 or hero in logic.selected_heroes]
    print(f"Получено {len(filtered_counters)} записей с рейтингом >= 0 или выбранных.")

    if not filtered_counters:
        print("Не найдено героев для отображения.")
        return

    layout = result_frame.layout()
    if not layout:
         print("[!] Ошибка: layout у result_frame отсутствует в generate_minimal_icon_list.")
         return

    icons_frame = QFrame(result_frame)
    icons_layout = QHBoxLayout(icons_frame)
    icons_layout.setContentsMargins(0, 2, 0, 2)
    icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    icons_layout.setSpacing(3)

    if not hasattr(logic, 'effective_team') or not logic.effective_team:
         print("Пересчет effective_team для подсветки...")
         logic.calculate_effective_team(counter_scores)
    effective_team = logic.effective_team

    items_added = 0
    print("Начало добавления иконок в icons_frame...")
    for counter, score in filtered_counters:
        if counter in left_images and left_images.get(counter):
            img_label = QLabel()
            pixmap = left_images[counter]
            img_label.setPixmap(pixmap)
            img_label.setFixedSize(pixmap.width(), pixmap.height()) # Используем размер из left_images

            style = "border: 1px solid gray; border-radius: 3px;" # Рамка по умолчанию
            is_effective = counter in effective_team
            is_selected = counter in logic.selected_heroes

            # Приоритет выделения: выбранный (желтый) > эффективный (голубой) > обычный (серый)
            if is_selected: style = "border: 3px solid yellow; border-radius: 3px;"
            elif is_effective: style = "border: 3px solid lightblue; border-radius: 3px;"

            img_label.setStyleSheet(style)
            img_label.setToolTip(f"{counter}\nRating: {score:.1f}")

            icons_layout.addWidget(img_label)
            items_added += 1
        else:
             print(f"  [!] Пропуск {counter}: нет иконки в left_images.")

    if items_added > 0:
         try:
              layout.addWidget(icons_frame)
              print(f"Добавлен icons_frame с {items_added} иконками в result_frame.")
         except Exception as e:
              print(f"[!] Ошибка добавления icons_frame: {e}")
              if icons_frame: icons_frame.deleteLater()
    else:
         print("Ни одна иконка не была добавлена в icons_frame.")
         if icons_frame: icons_frame.deleteLater()

    print(f"--- Конец generate_minimal_icon_list ---")


def generate_minimal_display(self, result_frame, result_label, left_images):
    pass # Оставляем пустым или удаляем, если не используется