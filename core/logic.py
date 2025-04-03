from heroes_bd import heroes
from translations import get_text
from display import generate_counterpick_display, generate_minimal_display, generate_minimal_icon_list

MIN_TANKS = 1
MAX_TANKS = 3
MIN_SUPPORTS = 2
MAX_SUPPORTS = 3
TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self):
        self.selected_heroes = []
        self.priority_heroes = []
        self.current_result_text = ""
        self.priority_labels = {}

    def set_priority(self, hero, button, hero_frame, update_counters_callback):
        from PySide6.QtWidgets import QLabel
        if hero not in self.selected_heroes:
            return
        if hero in self.priority_heroes:
            self.priority_heroes.remove(hero)
            if hero in self.priority_labels:
                self.priority_labels[hero].deleteLater()
                del self.priority_labels[hero]
        else:
            self.priority_heroes.append(hero)
            if hero in self.priority_labels:
                self.priority_labels[hero].deleteLater()
            label = QLabel(get_text('strong_player'))
            label.setStyleSheet("font-size: 8pt; color: white; background-color: red; padding: 2px;")
            label.setParent(button)  # Привязываем к кнопке
            label.move((button.width() - label.width()) // 2, 0)  # Центрируем по горизонтали
            label.show()  # Убеждаемся, что метка видима
            self.priority_labels[hero] = label
        update_counters_callback()

    def toggle_hero(self, hero, buttons, update_counters_callback):
        from PySide6.QtGui import QColor
        if hero in self.selected_heroes:
            self.selected_heroes.remove(hero)
            if hero in self.priority_heroes:
                self.priority_heroes.remove(hero)
            buttons[hero].setStyleSheet("")
            if hero in self.priority_labels:
                self.priority_labels[hero].deleteLater()
                del self.priority_labels[hero]
        else:
            if len(self.selected_heroes) >= TEAM_SIZE:
                removed_hero = self.selected_heroes.pop(0)
                buttons[removed_hero].setStyleSheet("")
                if removed_hero in self.priority_heroes:
                    self.priority_heroes.remove(removed_hero)
                if removed_hero in self.priority_labels:
                    self.priority_labels[removed_hero].deleteLater()
                    del self.priority_labels[removed_hero]
            self.selected_heroes.append(hero)
            buttons[hero].setStyleSheet("""
                background-color: lightblue;
                border: 2px solid yellow;  /* Добавляем желтую рамку для выделения */
            """)
        update_counters_callback()

    def clear_all(self, buttons, update_selected_label_callback, update_counters_callback):
        for hero, button in buttons.items():
            button.setStyleSheet("")
            if hero in self.priority_labels:
                self.priority_labels[hero].deleteLater()
                del self.priority_labels[hero]
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        update_selected_label_callback()
        update_counters_callback()

    def get_selected_heroes_text(self):
        return f"{get_text('selected')}{', '.join(self.selected_heroes) if self.selected_heroes else ''}"

    def calculate_counter_scores(self):
        from heroes_bd import heroes_counters
        counter_scores = {hero: 0 for hero in heroes}
        for hero in self.selected_heroes:
            for counter in heroes_counters.get(hero, []):
                score = 2 if hero in self.priority_heroes else 1
                counter_scores[counter] = counter_scores.get(counter, 0) + score
        for hero in self.selected_heroes:
            for counter in heroes_counters.get(hero, []):
                if counter in self.selected_heroes:
                    counter_scores[counter] = counter_scores.get(counter, 0) - 1
        for counter_hero in counter_scores:
            counters_of_hero = heroes_counters.get(counter_hero, [])
            for selected_hero in self.selected_heroes:
                if selected_hero in counters_of_hero:
                    counter_scores[counter_hero] -= 1
        return counter_scores

    def calculate_effective_team(self, counter_scores):
        from heroes_bd import hero_roles, heroes_compositions
        sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
        effective_team = []
        tanks = 0
        supports = 0
        for hero, score in sorted_counters:
            if hero not in effective_team:
                if tanks < MIN_TANKS and hero in hero_roles["tanks"]:
                    effective_team.append(hero)
                    tanks += 1
                elif supports < MIN_SUPPORTS and hero in hero_roles["supports"]:
                    effective_team.append(hero)
                    supports += 1
                if tanks >= MIN_TANKS and supports >= MIN_SUPPORTS:
                    break
        while len(effective_team) < TEAM_SIZE:
            best_score = -float('inf')
            best_hero = None
            for hero, score in sorted_counters:
                if hero not in effective_team:
                    adjusted_score = score
                    for teammate in effective_team:
                        if hero in heroes_compositions.get(teammate, []):
                            adjusted_score += 0.5
                    if adjusted_score > best_score:
                        if (hero in hero_roles["tanks"] and tanks < MAX_TANKS) or \
                           (hero in hero_roles["supports"] and supports < MAX_SUPPORTS) or \
                           (hero in hero_roles["attackers"]):
                            best_score = adjusted_score
                            best_hero = hero
            if best_hero:
                effective_team.append(best_hero)
                if best_hero in hero_roles["tanks"]:
                    tanks += 1
                elif best_hero in hero_roles["supports"]:
                    supports += 1
        return effective_team

    def update_display_language(self):
        for hero, label in self.priority_labels.items():
            label.setText(get_text('strong_player'))

    def generate_minimal_icon_list(self, result_frame, result_label, left_images):
        from display import generate_minimal_icon_list
        generate_minimal_icon_list(self, result_frame, result_label, left_images)

CounterpickLogic.generate_counterpick_display = generate_counterpick_display
CounterpickLogic.generate_minimal_display = generate_minimal_display
CounterpickLogic.generate_minimal_icon_list = generate_minimal_icon_list