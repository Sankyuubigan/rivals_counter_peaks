# File: display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters
from translations import get_text

def generate_counterpick_display(logic, result_frame, left_images, small_images):
    """
    Генерирует детальное отображение рейтинга контрпиков.
    """
    # print("[LOG] generate_counterpick_display called") # LOG
    if not logic.selected_heroes: print("[LOG] -> No selected heroes, returning"); return

    counter_scores = logic.calculate_counter_scores()
    if not counter_scores: print("[LOG] -> No counter scores, returning"); return

    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    effective_team = logic.calculate_effective_team(counter_scores)
    # print(f"[LOG] -> Effective team for highlight: {effective_team}") # LOG

    items_added = 0
    layout = result_frame.layout()
    # Убедимся, что layout существует и это QVBoxLayout
    if not layout or not isinstance(layout, QVBoxLayout):
        # print("[LOG] -> Layout invalid or missing, creating new QVBoxLayout") # LOG
        while layout and layout.count():
             item = layout.takeAt(0)
             if item is None: continue
             widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem()
             if widget: widget.deleteLater()
             elif layout_item: layout.removeItem(item) # Удаляем сам layout item
             elif spacer: layout.removeItem(item) # Удаляем spacer item
        layout = QVBoxLayout(result_frame); layout.setAlignment(Qt.AlignmentFlag.AlignTop); layout.setSpacing(1)
        result_frame.setLayout(layout)
    else: # Если layout уже есть, очистим его перед добавлением
        # print("[LOG] -> Clearing existing layout") # LOG
        while layout.count():
            item = layout.takeAt(0)
            if item is None: continue
            widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem()
            if widget: widget.deleteLater() # Удаляем старые виджеты
            # --- ИСПРАВЛЕНИЕ СИНТАКСИСА ---
            elif layout_item: # elif на новой строке
                while layout_item.count():
                    sub_item = layout_item.takeAt(0)
                    if sub_item and sub_item.widget(): sub_item.widget().deleteLater()
                layout.removeItem(item)
            elif spacer: # elif на новой строке
                layout.removeItem(item)
            # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    # print(f"[LOG] -> Adding {len(sorted_counters)} counter widgets...") # LOG
    for counter, score in sorted_counters:
        if abs(score) < 0.01 and counter not in logic.selected_heroes: continue

        if counter in left_images and left_images.get(counter):
            counter_frame = QFrame(result_frame)
            counter_layout = QHBoxLayout(counter_frame)
            counter_layout.setContentsMargins(4, 1, 4, 1); counter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter); counter_layout.setSpacing(5)

            is_effective = counter in effective_team
            bg_color_str = "background-color: lightblue;" if is_effective else "background-color: transparent;"
            border_style = "border: 1px solid darkblue;" if is_effective else "border: none;"
            counter_frame.setStyleSheet(f"{bg_color_str} {border_style} border-radius: 3px;")

            img_label = QLabel(); img_label.setPixmap(left_images[counter]); img_label.setStyleSheet("border: none; padding: 0px; margin: 0px;")
            counter_layout.addWidget(img_label)

            text_label = QLabel(f"{counter}: {score:.1f} {get_text('points')}"); text_label.setStyleSheet("border: none; padding: 0px; margin: 0px;")
            counter_layout.addWidget(text_label)

            counter_layout.addStretch(1)

            enemies_layout = QHBoxLayout(); enemies_layout.setContentsMargins(0, 0, 0, 0); enemies_layout.setSpacing(2)
            enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            counter_for_heroes = [h for h in logic.selected_heroes if counter in heroes_counters.get(h, [])]
            for hero in counter_for_heroes:
                 if hero in small_images and small_images.get(hero):
                     small_img_label = QLabel(); small_img_label.setPixmap(small_images[hero])
                     small_img_label.setStyleSheet("border: 2px solid green; border-radius: 3px; padding: 0px; margin: 0px;")
                     small_img_label.setToolTip(f"{counter} {get_text('counters')} {hero}")
                     enemies_layout.addWidget(small_img_label)

            countered_by_heroes = [h for h in logic.selected_heroes if h in heroes_counters.get(counter, [])]
            for hero in countered_by_heroes:
                 if hero in small_images and small_images.get(hero):
                     small_img_label = QLabel(); small_img_label.setPixmap(small_images[hero])
                     small_img_label.setStyleSheet("border: 2px solid red; border-radius: 3px; padding: 0px; margin: 0px;")
                     small_img_label.setToolTip(f"{hero} {get_text('counters')} {counter}")
                     enemies_layout.addWidget(small_img_label)

            if enemies_layout.count() > 0: counter_layout.addLayout(enemies_layout)

            try: layout.addWidget(counter_frame); items_added += 1
            except Exception as e: print(f"[!] Ошибка добавления виджета для {counter}: {e}");
            if counter_frame: counter_frame.deleteLater()
        # else:
             # print(f"[LOG] -> Skipping {counter} (no image)") # DEBUG LOG

    # print(f"[LOG] -> Finished adding widgets. Items added: {items_added}") # LOG
    # Добавляем растяжку в конце списка, только если есть элементы
    if items_added > 0:
        layout.addStretch(1)


# --- generate_minimal_icon_list ---
def generate_minimal_icon_list(logic, result_frame, left_images):
    """
    Генерирует минималистичный список иконок контрпиков.
    """
    # print("[LOG] generate_minimal_icon_list called") # LOG
    if not logic.selected_heroes: print("[LOG] -> No selected heroes, returning"); return

    counter_scores = logic.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    filtered_counters = [(hero, score) for hero, score in sorted_counters if score >= 0 or hero in logic.selected_heroes]

    if not filtered_counters: print("[LOG] -> No counters to display, returning"); return

    layout = result_frame.layout()
    if not layout: print("[!] Ошибка: layout у result_frame отсутствует в generate_minimal_icon_list."); return

    # Очищаем layout
    # print("[LOG] -> Clearing minimal icon list layout") # LOG
    while layout.count():
        item = layout.takeAt(0)
        if item is None: continue
        widget = item.widget(); layout_item = item.layout(); spacer = item.spacerItem()
        if widget: widget.deleteLater()
        elif layout_item:
            while layout_item.count(): sub_item = layout_item.takeAt(0)
            if sub_item and sub_item.widget(): sub_item.widget().deleteLater()
            layout.removeItem(layout_item)
        elif spacer: layout.removeItem(spacer)


    # Создаем горизонтальный layout для иконок
    icons_layout = QHBoxLayout()
    icons_layout.setContentsMargins(2, 2, 2, 2)
    icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    icons_layout.setSpacing(3)

    effective_team = logic.calculate_effective_team(counter_scores)
    # print(f"[LOG] -> Effective team for minimal list: {effective_team}") # LOG

    items_added = 0
    for counter, score in filtered_counters:
        if counter in left_images and left_images.get(counter):
            img_label = QLabel()
            pixmap = left_images[counter]
            img_label.setPixmap(pixmap)
            img_label.setFixedSize(pixmap.width(), pixmap.height())

            style = "border: 1px solid gray; border-radius: 3px; padding: 0px;"
            is_effective = counter in effective_team
            is_selected = counter in logic.selected_heroes

            # Оранжевая рамка для врагов, синяя для рекомендованных
            if is_selected: style = "border: 3px solid orange; border-radius: 3px; padding: 0px;"
            elif is_effective: style = "border: 3px solid blue; border-radius: 3px; padding: 0px;"

            img_label.setStyleSheet(style)
            img_label.setToolTip(f"{counter}\nRating: {score:.1f}")

            icons_layout.addWidget(img_label)
            items_added += 1

    if items_added > 0:
         # print(f"[LOG] -> Adding minimal icons layout with {items_added} items") # LOG
         layout.addLayout(icons_layout)
         layout.addStretch(1) # Растяжка в конце
    # else:
        # print("[LOG] -> No minimal icons added") # LOG