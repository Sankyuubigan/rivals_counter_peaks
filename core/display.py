# File: core/display.py
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor # Добавлен QColor
from database.heroes_bd import heroes_counters
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
                # removeItem нужен только если sub_layout это QLayoutItem, а не сам QLayout
                # В данном случае, если sub_layout это QLayout, его нужно удалить из родительского layout
                if layout and hasattr(layout, 'removeItem') and item: # Проверка на None для item
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
    # Пытаемся найти result_label, который теперь может быть дочерним элементом result_frame
    # или его родителя (scroll_area -> left_panel_widget -> main_widget)
    # Проще всего, если result_label всегда создается и добавляется в MainWindow
    # и передается сюда, или ищется по objectName в MainWindow.
    # Пока оставим поиск в родителях result_frame, но это не очень надежно.
    # Наиболее вероятно, что result_label является прямым потомком result_frame,
    # если он добавляется в `create_left_panel`.
    
    # Попробуем найти result_label как прямой потомок MainWindow
    if hasattr(logic, 'main_window') and logic.main_window:
        result_label_found = logic.main_window.findChild(QLabel, "result_label")

    if not logic.selected_heroes:
        if result_label_found: 
            result_label_found.setText(get_text('no_heroes_selected', language=logic.DEFAULT_LANGUAGE)); 
            result_label_found.show()
            # Убедимся, что result_label в layout, если он еще не там
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

    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    effective_team = logic.calculate_effective_team(counter_scores) 
    selected_heroes_set = set(logic.selected_heroes)
    items_added = 0

    current_theme = "light" 
    if hasattr(logic, 'main_window') and logic.main_window and \
       hasattr(logic.main_window, 'appearance_manager') and logic.main_window.appearance_manager:
        current_theme = logic.main_window.appearance_manager.current_theme
    
    logging.debug(f"[Display] Generating counterpick display for theme: {current_theme}")

    default_text_color = QColor("black")
    enemy_bg_color = QColor("#ffe0e0")
    enemy_border_color = QColor("red")
    enemy_text_color = QColor("darkred")
    effective_bg_color = QColor("lightblue")
    effective_border_color = QColor("darkblue")
    effective_text_color = QColor("darkblue")
    counter_border_good = QColor("green")
    counter_border_bad = QColor("red")
    
    if current_theme == "dark":
        default_text_color = QColor("#e0e0e0")
        enemy_bg_color = QColor("#503030") 
        enemy_border_color = QColor("#ff4040") 
        enemy_text_color = QColor("#ff8080") 
        effective_bg_color = QColor("#304050") 
        effective_border_color = QColor("#60a0ff") 
        effective_text_color = QColor("#a0c0ff") 
        counter_border_good = QColor("#33cc33") 
        counter_border_bad = QColor("#ff4040") 

    for counter, score in sorted_counters:
        if score <= 0 and counter not in selected_heroes_set: continue

        left_pixmap = left_images.get(counter)
        if is_invalid_pixmap(left_pixmap):
            logging.warning(f"[Display] Invalid/missing left image for hero '{counter}'. Skipping hero row.")
            continue

        counter_frame = QFrame(result_frame); counter_layout = QHBoxLayout(counter_frame)
        counter_layout.setContentsMargins(4, 1, 4, 1); counter_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter); counter_layout.setSpacing(5)
        is_effective = counter in effective_team; is_enemy = counter in selected_heroes_set
        
        bg_color_str = "background-color: transparent;"; 
        border_style = "border: none;"; 
        text_color_resolved_qcolor = default_text_color # Используем QColor для text_label

        if is_enemy: 
            bg_color_str = f"background-color: {enemy_bg_color.name()};"; 
            border_style = f"border: 1px solid {enemy_border_color.name()};"; 
            text_color_resolved_qcolor = enemy_text_color;
        elif is_effective: 
            bg_color_str = f"background-color: {effective_bg_color.name()};"; 
            border_style = f"border: 1px solid {effective_border_color.name()};"; 
            text_color_resolved_qcolor = effective_text_color;
        
        counter_frame.setStyleSheet(f"QFrame {{ {bg_color_str} {border_style} border-radius: 3px; }}")

        img_label = QLabel(); img_label.setPixmap(left_pixmap); img_label.setStyleSheet("border: none; padding: 0px; margin: 0px;")
        counter_layout.addWidget(img_label)
        
        text_label = QLabel(f"{counter}: {score:.1f} {get_text('points', language=logic.DEFAULT_LANGUAGE)}");
        # Устанавливаем цвет текста напрямую через палитру или setStyleSheet с !important, если QSS конфликтует
        text_label.setStyleSheet(f"QLabel {{ border: none; padding: 0px; margin: 0px; color: {text_color_resolved_qcolor.name()}; }}")
        counter_layout.addWidget(text_label); counter_layout.addStretch(1)

        enemies_layout = QHBoxLayout(); enemies_layout.setContentsMargins(0, 0, 0, 0); enemies_layout.setSpacing(2)
        enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Герои, которых контрит 'counter'
        counter_for_heroes = []
        for enemy_hero_name in selected_heroes_set:
            enemy_data = heroes_counters.get(enemy_hero_name, {})
            if counter in enemy_data.get("hard", []) or counter in enemy_data.get("soft", []):
                counter_for_heroes.append(enemy_hero_name)

        for hero in counter_for_heroes:
             small_pixmap = small_images.get(hero)
             if is_invalid_pixmap(small_pixmap): logging.warning(f"[Display] Invalid/missing small image for countered hero '{hero}' (when checking '{counter}')."); continue
             small_img_label = QLabel(); small_img_label.setPixmap(small_pixmap)
             small_img_label.setStyleSheet(f"border: 2px solid {counter_border_good.name()}; border-radius: 3px; padding: 0px; margin: 0px;")
             small_img_label.setToolTip(f"{counter} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {hero}")
             enemies_layout.addWidget(small_img_label)
        
        # Герои, которые контрят 'counter'
        countered_by_heroes = []
        hero_is_countered_by_data = heroes_counters.get(counter, {})
        hard_countered_by_counter = hero_is_countered_by_data.get("hard", [])
        soft_countered_by_counter = hero_is_countered_by_data.get("soft", [])
        
        for enemy_hero_name in selected_heroes_set:
            if enemy_hero_name in hard_countered_by_counter or enemy_hero_name in soft_countered_by_counter:
                countered_by_heroes.append(enemy_hero_name)

        for hero in countered_by_heroes: 
             small_pixmap = small_images.get(hero)
             if is_invalid_pixmap(small_pixmap): logging.warning(f"[Display] Invalid/missing small image for countering hero '{hero}' (when checking '{counter}')."); continue
             small_img_label = QLabel(); small_img_label.setPixmap(small_pixmap)
             small_img_label.setStyleSheet(f"border: 2px solid {counter_border_bad.name()}; border-radius: 3px; padding: 0px; margin: 0px;")
             small_img_label.setToolTip(f"{hero} {get_text('counters', language=logic.DEFAULT_LANGUAGE)} {counter}")
             enemies_layout.addWidget(small_img_label)
        
        if enemies_layout.count() > 0: counter_layout.addLayout(enemies_layout)
        layout.addWidget(counter_frame); items_added += 1

    if items_added == 0 and result_label_found: # Если ничего не добавили, но были кандидаты
        result_label_found.setText(get_text('no_recommendations', language=logic.DEFAULT_LANGUAGE)); 
        result_label_found.show()
        if layout and layout.indexOf(result_label_found) == -1: 
            layout.addWidget(result_label_found)
    
    if layout: layout.addStretch(1) # Добавляем растяжку в любом случае, чтобы контент был сверху


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