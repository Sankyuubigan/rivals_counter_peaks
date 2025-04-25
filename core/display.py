# File: core/display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QScrollArea, QMessageBox
from PySide6.QtGui import QPixmap, QIcon # Добавляем QIcon
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters
from translations import get_text
# <<< ИЗМЕНЕНО: Импорт is_invalid_pixmap >>>
from images_load import is_invalid_pixmap, load_default_pixmap
# <<< ---------------------------------- >>>
import logging

def clear_layout(layout):
    """Рекурсивно удаляет все виджеты и layout'ы из заданного layout'а."""
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0); widget = item.widget()
        if widget is not None: widget.deleteLater()
        else:
            sub_layout = item.layout();
            if sub_layout is not None:
                clear_layout(sub_layout)
                # <<< Добавлено: удаление пустого layout из родительского >>>
                layout.removeItem(item)


def generate_counterpick_display(logic, result_frame, left_images, small_images):
    """Генерирует детальное отображение рейтинга контрпиков в result_frame."""
    layout = result_frame.layout()
    if not layout: layout = QVBoxLayout(result_frame); layout.setObjectName("result_layout"); layout.setAlignment(Qt.AlignmentFlag.AlignTop); layout.setContentsMargins(2, 2, 2, 2); layout.setSpacing(1); result_frame.setLayout(layout)
    clear_layout(layout)

    result_label_found = None
    if result_frame.parentWidget() and isinstance(result_frame.parentWidget(), QScrollArea):
         canvas = result_frame.parentWidget(); result_label_found = canvas.findChild(QLabel, "result_label")

    if not logic.selected_heroes:
        if result_label_found: result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE)); result_label_found.show()
        if layout and result_label_found and layout.indexOf(result_label_found) == -1: layout.addWidget(result_label_found) # Добавляем обратно, если удалили
        if layout: layout.addStretch(1)
        return

    if result_label_found: result_label_found.hide()

    counter_scores = logic.calculate_counter_scores()
    if not counter_scores: return

    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    effective_team = logic.calculate_effective_team(counter_scores)
    selected_heroes_set = set(logic.selected_heroes)
    items_added = 0

    for counter, score in sorted_counters:
        if score <= 0 and counter not in selected_heroes_set: continue

        left_pixmap = left_images.get(counter)
        if is_invalid_pixmap(left_pixmap):
            logging.warning(f"[Display] Invalid/missing left image for hero '{counter}'. Skipping hero row.")
            continue

        counter_frame = QFrame(result_frame); counter_layout = QHBoxLayout(counter_frame)
        counter_layout.setContentsMargins(4, 1, 4, 1); counter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter); counter_layout.setSpacing(5)
        is_effective = counter in effective_team; is_enemy = counter in selected_heroes_set
        bg_color_str = "background-color: transparent;"; border_style = "border: none;"; text_color = "color: black;"
        # Стиль рамки и фона для врагов (красный) и эффективных (синий)
        if is_enemy: bg_color_str = "background-color: #ffe0e0;"; border_style = "border: 1px solid red;"; text_color = "color: darkred;"
        elif is_effective: bg_color_str = "background-color: lightblue;"; border_style = "border: 1px solid darkblue;"; text_color = "color: darkblue;"
        counter_frame.setStyleSheet(f"QFrame {{ {bg_color_str} {border_style} border-radius: 3px; }}")

        img_label = QLabel(); img_label.setPixmap(left_pixmap); img_label.setStyleSheet("border: none; padding: 0px; margin: 0px;")
        counter_layout.addWidget(img_label)
        text_label = QLabel(f"{counter}: {score:.1f} {get_text('points', language=logic.DEFAULT_LANGUAGE)}");
        text_label.setStyleSheet(f"QLabel {{ border: none; padding: 0px; margin: 0px; {text_color} }}")
        counter_layout.addWidget(text_label); counter_layout.addStretch(1)

        enemies_layout = QHBoxLayout(); enemies_layout.setContentsMargins(0, 0, 0, 0); enemies_layout.setSpacing(2)
        enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        counter_for_heroes = [h for h in selected_heroes_set if counter in heroes_counters.get(h, [])]
        for hero in counter_for_heroes:
             small_pixmap = small_images.get(hero)
             if is_invalid_pixmap(small_pixmap): logging.warning(f"[Display] Invalid/missing small image for countered hero '{hero}' (when checking '{counter}')."); continue
             small_img_label = QLabel(); small_img_label.setPixmap(small_pixmap)
             # <<< ИЗМЕНЕНО: Толщина рамки увеличена до 3px (Request 4) >>>
             small_img_label.setStyleSheet("border: 3px solid green; border-radius: 3px; padding: 0px; margin: 0px;")
             # <<< END ИЗМЕНЕНО >>>
             small_img_label.setToolTip(f"{counter} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {hero}")
             enemies_layout.addWidget(small_img_label)
        countered_by_heroes = [h for h in selected_heroes_set if h in heroes_counters.get(counter, [])]
        for hero in countered_by_heroes:
             small_pixmap = small_images.get(hero)
             if is_invalid_pixmap(small_pixmap): logging.warning(f"[Display] Invalid/missing small image for countering hero '{hero}' (when checking '{counter}')."); continue
             small_img_label = QLabel(); small_img_label.setPixmap(small_pixmap)
             # <<< ИЗМЕНЕНО: Толщина рамки увеличена до 3px (Request 4) >>>
             small_img_label.setStyleSheet("border: 3px solid red; border-radius: 3px; padding: 0px; margin: 0px;")
             # <<< END ИЗМЕНЕНО >>>
             small_img_label.setToolTip(f"{hero} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {counter}")
             enemies_layout.addWidget(small_img_label)
        if enemies_layout.count() > 0: counter_layout.addLayout(enemies_layout)
        layout.addWidget(counter_frame); items_added += 1

    if items_added > 0: layout.addStretch(1)
    elif result_label_found:
        result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE)); result_label_found.show()
        if layout and layout.indexOf(result_label_found) == -1: layout.addWidget(result_label_found)
        if layout: layout.addStretch(1)


def generate_minimal_icon_list(logic, result_frame, left_images):
    """Генерирует минималистичный список иконок контрпиков в result_frame (для min режима, до разделения)."""
    # Эта функция больше не должна напрямую вызываться для генерации всего списка в min режиме,
    # т.к. теперь у нас два отдельных списка. Оставляем её как есть на случай,
    # если она используется где-то еще, но основная логика теперь в horizontal_list.py
    # и вызывается из main_window.py.
    # Если она больше нигде не нужна, её можно удалить или адаптировать.
    # Пока просто добавим лог, что она вызвана.
    logging.warning("generate_minimal_icon_list called - this might be deprecated for min mode display.")

    layout = result_frame.layout()
    if not layout: layout = QVBoxLayout(result_frame); layout.setObjectName("result_layout_min_deprecated"); layout.setAlignment(Qt.AlignmentFlag.AlignTop); layout.setContentsMargins(2, 2, 2, 2); layout.setSpacing(1); result_frame.setLayout(layout)
    clear_layout(layout)

    result_label_found = None
    if result_frame.parentWidget() and isinstance(result_frame.parentWidget(), QScrollArea):
         canvas = result_frame.parentWidget(); result_label_found = canvas.findChild(QLabel, "result_label")

    if not logic.selected_heroes:
        if result_label_found: result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE)); result_label_found.show()
        if layout and result_label_found and layout.indexOf(result_label_found) == -1: layout.addWidget(result_label_found)
        if layout: layout.addStretch(1)
        return
    if result_label_found: result_label_found.hide()

    counter_scores = logic.calculate_counter_scores()
    # Фильтр для отображения: score >= 1 ИЛИ выбранный враг
    filtered_counters = []
    selected_heroes_set = set(logic.selected_heroes)
    if counter_scores:
        sorted_scores = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
        for hero, score in sorted_scores:
            if score >= 1.0 or hero in selected_heroes_set:
                filtered_counters.append((hero, score))

    if not filtered_counters:
        if result_label_found: result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE)); result_label_found.show()
        if layout and result_label_found and layout.indexOf(result_label_found) == -1: layout.addWidget(result_label_found)
        if layout: layout.addStretch(1)
        return

    icons_layout = QHBoxLayout(); icons_layout.setContentsMargins(2, 2, 2, 2); icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter); icons_layout.setSpacing(3)
    effective_team_set = set(logic.effective_team) # Используем кэшированную команду
    items_added = 0

    for counter, score in filtered_counters:
        pixmap = left_images.get(counter) # Используем left_images для min режима, как и раньше? Или horizontal? Уточнить! Предположим horizontal_images
        # <<< ИСПРАВЛЕНИЕ: Используем horizontal_images для консистентности с верхним списком >>>
        pixmap = logic.main_window.horizontal_images.get(counter) if hasattr(logic, 'main_window') else left_images.get(counter)
        # <<< ---------------------------------------------------------------------------------- >>>

        if is_invalid_pixmap(pixmap):
            logging.warning(f"[Minimal Display - Deprecated?] Invalid/missing image for hero '{counter}'. Skipping icon.")
            continue

        img_label = QLabel(); img_label.setPixmap(pixmap); img_label.setFixedSize(pixmap.width(), pixmap.height())
        is_effective = counter in effective_team_set; is_selected = counter in selected_heroes_set
        border_style = "border: 1px solid gray; border-radius: 3px; padding: 0px;"
        # Рамка для врагов (красная), эффективных (синяя)
        if is_selected: border_style = "border: 2px solid red; border-radius: 3px; padding: 0px;" # Красная для врагов
        elif is_effective: border_style = "border: 2px solid blue; border-radius: 3px; padding: 0px;" # Синяя для эффективных
        img_label.setStyleSheet(border_style); img_label.setToolTip(f"{counter}\nRating: {score:.1f}")
        icons_layout.addWidget(img_label); items_added += 1

    if items_added > 0: layout.addLayout(icons_layout); layout.addStretch(1)
    elif result_label_found:
        result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE)); result_label_found.show()
        if layout and result_label_found and layout.indexOf(result_label_found) == -1: layout.addWidget(result_label_found)
        if layout: layout.addStretch(1)
