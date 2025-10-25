# File: core/display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
# ИСПРАВЛЕНО: Исправлен путь импорта
from core.database.heroes_bd import heroes_counters
from info.translations import get_text
from core.images_load import is_invalid_pixmap
import logging
def clear_layout(layout):
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0); widget = item.widget()
        if widget is not None: widget.deleteLater()
        else:
            sub_layout = item.layout()
            if sub_layout is not None:
                clear_layout(sub_layout)
def generate_counterpick_display(logic, result_frame, left_images, small_images, counter_scores=None, effective_team=None):
    layout = result_frame.layout()
    if not layout:
        layout = QVBoxLayout(result_frame)
        layout.setObjectName("result_layout")
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        result_frame.setLayout(layout)
    clear_layout(layout)
    result_label_found = None
    if hasattr(logic, 'main_window') and logic.main_window:
        result_label_found = logic.main_window.findChild(QLabel, "result_label")
    if not logic.selected_heroes:
        if result_label_found:
            result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE))
            result_label_found.show()
            if layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
        if layout: layout.addStretch(1)
        return
    if result_label_found: result_label_found.hide()
    if counter_scores is None: counter_scores = logic.calculate_counter_scores()
    if not counter_scores:
        if result_label_found:
            result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE))
            result_label_found.show()
            if layout.indexOf(result_label_found) == -1:
                layout.addWidget(result_label_found)
            if layout: layout.addStretch(1)
        return
    # ИСПРАВЛЕНИЕ: Сортируем по очкам (x[1]), а не по имени.
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    if effective_team is None: effective_team = logic.calculate_effective_team(counter_scores)
    selected_heroes_set = set(logic.selected_heroes)
    items_added = 0
    current_theme = "light" 
    if hasattr(logic, 'main_window') and logic.main_window and hasattr(logic.main_window, 'appearance_manager'):
        current_theme = logic.main_window.appearance_manager.current_theme
    
    default_text_color = QColor("black") if current_theme == "light" else QColor("#e0e0e0")
    enemy_bg_color = QColor("#ffe0e0") if current_theme == "light" else QColor("#503030")
    enemy_border_color = QColor("red") if current_theme == "light" else QColor("#ff4040")
    enemy_text_color = QColor("darkred") if current_theme == "light" else QColor("#ff8080")
    effective_bg_color = QColor("lightblue") if current_theme == "light" else QColor("#304050")
    effective_border_color = QColor("darkblue") if current_theme == "light" else QColor("#60a0ff")
    effective_text_color = QColor("darkblue") if current_theme == "light" else QColor("#a0c0ff")
    counter_border_good = QColor("green") if current_theme == "light" else QColor("#33cc33")
    counter_border_bad = QColor("red") if current_theme == "light" else QColor("#ff4040")
    for counter, score in sorted_counters:
        if score <= 0 and counter not in selected_heroes_set: continue
        left_pixmap = left_images.get(counter)
        if is_invalid_pixmap(left_pixmap):
            logging.warning(f"[Display] Invalid left image for hero '{counter}'. Skipping.")
            continue
        counter_frame = QFrame(result_frame)
        counter_layout = QHBoxLayout(counter_frame)
        counter_layout.setContentsMargins(4, 1, 4, 1)
        counter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        counter_layout.setSpacing(5)
        
        is_effective = counter in effective_team
        is_enemy = counter in selected_heroes_set
        
        bg_color_str, border_style = "background-color: transparent;", "border: none;"
        text_color_qcolor = default_text_color
        # ИСПРАВЛЕНИЕ: Приоритет у оптимальной команды, а не у врагов.
        if is_effective: 
            bg_color_str, border_style, text_color_qcolor = f"background-color: {effective_bg_color.name()};", f"border: 1px solid {effective_border_color.name()};", effective_text_color
        elif is_enemy: 
            bg_color_str, border_style, text_color_qcolor = f"background-color: {enemy_bg_color.name()};", f"border: 1px solid {enemy_border_color.name()};", enemy_text_color
        
        counter_frame.setStyleSheet(f"QFrame {{ {bg_color_str} {border_style} border-radius: 3px; }}")
        img_label = QLabel()
        img_label.setPixmap(left_pixmap)
        counter_layout.addWidget(img_label)
        
        text_label = QLabel(f"{counter}: {score:.1f} {get_text('points', language=logic.DEFAULT_LANGUAGE)}")
        text_label.setStyleSheet(f"color: {text_color_qcolor.name()}; border: none;")
        counter_layout.addWidget(text_label)
        counter_layout.addStretch(1)
        enemies_icons_layout = QHBoxLayout()
        enemies_icons_layout.setContentsMargins(0, 0, 0, 0)
        enemies_icons_layout.setSpacing(2)
        enemies_icons_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        counter_for_heroes = [enemy for enemy in selected_heroes_set if counter in (heroes_counters.get(enemy, {}).get("hard", []) + heroes_counters.get(enemy, {}).get("soft", []))]
        for hero in counter_for_heroes:
             small_pixmap = small_images.get(hero)
             if is_invalid_pixmap(small_pixmap): continue
             small_img_label = QLabel()
             small_img_label.setPixmap(small_pixmap)
             small_img_label.setStyleSheet(f"border: 2px solid {counter_border_good.name()}; border-radius: 3px;")
             small_img_label.setToolTip(f"{counter} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {hero}")
             enemies_icons_layout.addWidget(small_img_label)
        
        countered_by_heroes = [enemy for enemy in selected_heroes_set if enemy in (heroes_counters.get(counter, {}).get("hard", []) + heroes_counters.get(counter, {}).get("soft", []))]
        for hero in countered_by_heroes: 
             small_pixmap = small_images.get(hero)
             if is_invalid_pixmap(small_pixmap): continue
             small_img_label = QLabel()
             small_img_label.setPixmap(small_pixmap)
             small_img_label.setStyleSheet(f"border: 2px solid {counter_border_bad.name()}; border-radius: 3px;")
             small_img_label.setToolTip(f"{hero} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {counter}")
             enemies_icons_layout.addWidget(small_img_label)
        
        if enemies_icons_layout.count() > 0: counter_layout.addLayout(enemies_icons_layout)
        layout.addWidget(counter_frame)
        items_added += 1
    if items_added == 0 and result_label_found:
        result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE))
        result_label_found.show()
        if layout.indexOf(result_label_found) == -1: 
            layout.addWidget(result_label_found)
    
    layout.addStretch(1)