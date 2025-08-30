# File: core/display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from core.lang.translations import get_text
from images_load import is_invalid_pixmap
import logging

def clear_layout(layout):
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0); widget = item.widget()
        if widget is not None: widget.deleteLater()
        else:
            sub_layout = item.layout();
            if sub_layout is not None:
                clear_layout(sub_layout)
                if layout and hasattr(layout, 'removeItem') and item:
                    layout.removeItem(item)


def generate_counterpick_display(logic, result_frame, left_images, small_images):
    layout = result_frame.layout()
    if not layout: 
        layout = QVBoxLayout(result_frame); 
        layout.setObjectName("result_layout"); 
        layout.setAlignment(Qt.AlignmentFlag.AlignTop); 
        layout.setContentsMargins(2, 2, 2, 2); 
        layout.setSpacing(1); 
        result_frame.setLayout(layout)
    clear_layout(layout)

    result_label_found = None
    if hasattr(logic, 'main_window') and logic.main_window:
        result_label_found = logic.main_window.findChild(QLabel, "result_label")

    if not logic.selected_heroes:
        if result_label_found: 
            result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE)); 
            result_label_found.show()
            if layout and layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
        if layout: layout.addStretch(1)
        return

    if result_label_found: result_label_found.hide()

    counter_scores = logic.calculate_counter_scores()
    if not counter_scores: 
        if result_label_found:
            result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE))
            result_label_found.show()
            if layout and layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
            if layout: layout.addStretch(1)
        return

    # --- ИЗМЕНЕНИЕ: Сортируем по абсолютному значению, а не по difference ---
    scores_with_context = logic._absolute_with_context(counter_scores.items(), logic.hero_stats)
    scores_with_context.sort(key=lambda x: x, reverse=True)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    effective_team = logic.calculate_effective_team(counter_scores) 
    selected_heroes_set = set(logic.selected_heroes)
    items_added = 0

    current_theme = "light" 
    if hasattr(logic, 'main_window') and logic.main_window and \
       hasattr(logic.main_window, 'appearance_manager') and logic.main_window.appearance_manager:
        current_theme = logic.main_window.appearance_manager.current_theme
    
    logging.debug(f"[Display] Generating counterpick display for theme: {current_theme}")

    default_text_color = QColor("black"); enemy_bg_color = QColor("#ffe0e0"); enemy_border_color = QColor("red")
    enemy_text_color = QColor("darkred"); effective_bg_color = QColor("lightblue"); effective_border_color = QColor("darkblue")
    effective_text_color = QColor("darkblue"); counter_border_good = QColor("green"); counter_border_bad = QColor("red")
    
    if current_theme == "dark":
        default_text_color = QColor("#e0e0e0"); enemy_bg_color = QColor("#503030"); enemy_border_color = QColor("#ff4040")
        enemy_text_color = QColor("#ff8080"); effective_bg_color = QColor("#304050"); effective_border_color = QColor("#60a0ff")
        effective_text_color = QColor("#a0c0ff"); counter_border_good = QColor("#33cc33"); counter_border_bad = QColor("#ff4040")

    # Порог для определения "контрпика" по значению difference
    COUNTER_DIFFERENCE_THRESHOLD = 2.0

    for counter, score in scores_with_context:
        # Отображаем только героев с положительным рейтингом или выбранных врагов
        if score < 0 and counter not in selected_heroes_set: continue

        left_pixmap = left_images.get(counter)
        if is_invalid_pixmap(left_pixmap): continue

        counter_frame = QFrame(result_frame); counter_layout = QHBoxLayout(counter_frame)
        counter_layout.setContentsMargins(4, 1, 4, 1); counter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter); counter_layout.setSpacing(5)
        is_effective = counter in effective_team; is_enemy = counter in selected_heroes_set
        
        bg_color_str = "background-color: transparent;"; border_style = "border: none;"
        text_color_resolved_qcolor = default_text_color

        if is_enemy: 
            bg_color_str = f"background-color: {enemy_bg_color.name()};"; border_style = f"border: 1px solid {enemy_border_color.name()};"
            text_color_resolved_qcolor = enemy_text_color;
        elif is_effective: 
            bg_color_str = f"background-color: {effective_bg_color.name()};"; border_style = f"border: 1px solid {effective_border_color.name()};"
            text_color_resolved_qcolor = effective_text_color;
        
        counter_frame.setStyleSheet(f"QFrame {{ {bg_color_str} {border_style} border-radius: 3px; }}")

        img_label = QLabel(); img_label.setPixmap(left_pixmap); img_label.setStyleSheet("border: none; padding: 0px; margin: 0px;")
        counter_layout.addWidget(img_label)
        
        text_label = QLabel(f"{counter}: {score:.0f} {get_text('points', language=logic.DEFAULT_LANGUAGE)}")
        text_label.setStyleSheet(f"QLabel {{ border: none; padding: 0px; margin: 0px; color: {text_color_resolved_qcolor.name()}; }}")
        counter_layout.addWidget(text_label); counter_layout.addStretch(1)

        enemies_layout = QHBoxLayout(); enemies_layout.setContentsMargins(0, 0, 0, 0); enemies_layout.setSpacing(2)
        enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # --- Новая логика для иконок контрпиков ---
        counter_matchups = logic.matchups_data.get(counter, [])
        for enemy_hero in selected_heroes_set:
            for matchup in counter_matchups:
                if matchup.get("opponent") == enemy_hero:
                    try:
                        diff = -float(matchup.get("difference", "0%").replace('%',''))
                        if diff > COUNTER_DIFFERENCE_THRESHOLD:
                            small_pixmap = small_images.get(enemy_hero)
                            if not is_invalid_pixmap(small_pixmap):
                                small_img_label = QLabel(); small_img_label.setPixmap(small_pixmap)
                                small_img_label.setStyleSheet(f"border: 2px solid {counter_border_good.name()}; border-radius: 3px;")
                                small_img_label.setToolTip(f"{counter} {get_text('counters')} {enemy_hero} ({diff:+.1f}%)")
                                enemies_layout.addWidget(small_img_label)
                    except (ValueError, TypeError): pass
                    break

        for enemy_hero in selected_heroes_set:
            enemy_matchups = logic.matchups_data.get(enemy_hero, [])
            for matchup in enemy_matchups:
                if matchup.get("opponent") == counter:
                    try:
                        diff = -float(matchup.get("difference", "0%").replace('%',''))
                        if diff > COUNTER_DIFFERENCE_THRESHOLD:
                             small_pixmap = small_images.get(enemy_hero)
                             if not is_invalid_pixmap(small_pixmap):
                                small_img_label = QLabel(); small_img_label.setPixmap(small_pixmap)
                                small_img_label.setStyleSheet(f"border: 2px solid {counter_border_bad.name()}; border-radius: 3px;")
                                small_img_label.setToolTip(f"{enemy_hero} {get_text('counters')} {counter} ({diff:+.1f}%)")
                                enemies_layout.addWidget(small_img_label)
                    except (ValueError, TypeError): pass
                    break
        # --- Конец новой логики ---
        
        if enemies_layout.count() > 0: counter_layout.addLayout(enemies_layout)
        layout.addWidget(counter_frame); items_added += 1

    if items_added == 0 and result_label_found:
        result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE)); 
        result_label_found.show()
        if layout and layout.indexOf(result_label_found) == -1: 
            layout.addWidget(result_label_found)
    
    if layout: layout.addStretch(1)


def generate_minimal_icon_list(logic, result_frame, left_images):
    logging.warning("generate_minimal_icon_list called - this might be deprecated for min mode display.")
    layout = result_frame.layout()
    if not layout: layout = QVBoxLayout(result_frame); layout.setObjectName("result_layout_min_deprecated"); layout.setAlignment(Qt.AlignmentFlag.AlignTop); layout.setContentsMargins(2, 2, 2, 2); layout.setSpacing(1); result_frame.setLayout(layout)
    clear_layout(layout)

    result_label_found = None
    if hasattr(logic, 'main_window') and logic.main_window:
        result_label_found = logic.main_window.findChild(QLabel, "result_label")

    if not logic.selected_heroes:
        if result_label_found: result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE)); result_label_found.show()
        if layout and result_label_found and layout.indexOf(result_label_found) == -1: layout.addWidget(result_label_found)
        if layout: layout.addStretch(1)
        return
    if result_label_found: result_label_found.hide()