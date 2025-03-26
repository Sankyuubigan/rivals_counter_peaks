import tkinter as tk
from heroes_bd import heroes
from translations import get_text
from display import generate_counterpick_display  # Импортируем функцию

class CounterpickLogic:
    def __init__(self):
        self.selected_heroes = []
        self.priority_heroes = []
        self.current_result_text = ""
        self.priority_labels = {}

    def set_priority(self, hero, button, hero_frame, update_counters_callback):
        print(f"set_priority called for hero: {hero}, button text: {button.cget('text')}")
        if hero not in self.selected_heroes:
            print(f"Hero {hero} not in selected_heroes, exiting")
            return

        if hero in self.priority_heroes:
            print(f"Removing priority from {hero}")
            self.priority_heroes.remove(hero)
            self._remove_priority_label(button, hero_frame)
        else:
            print(f"Adding priority to {hero}")
            self.priority_heroes.append(hero)
            if hero in self.priority_labels:
                self._remove_priority_label(button, hero_frame)
            if not hasattr(hero_frame, 'priority_frame'):
                hero_frame.priority_frame = tk.Frame(hero_frame, bg=button.cget('bg'))
                hero_frame.priority_frame.place(relx=0.5, rely=0.0, anchor="n")
            priority_label = tk.Label(hero_frame.priority_frame, text=get_text('strong_player'), font=("Arial", 8),
                                      fg="black", bg="red")
            priority_label.pack(side=tk.TOP, anchor="center")
            self.priority_labels[hero] = priority_label
            print(f"Label added to {hero}, priority_labels: {list(self.priority_labels.keys())}")

        update_counters_callback()

    def _remove_priority_label(self, button, hero_frame):
        hero = button.cget("text")
        if hero in self.priority_labels:
            print(f"Removing label for {hero}")
            label = self.priority_labels.pop(hero)
            label.destroy()
            if hasattr(hero_frame, 'priority_frame') and not hero_frame.priority_frame.winfo_children():
                hero_frame.priority_frame.destroy()
                delattr(hero_frame, 'priority_frame')

    def _reset_button(self, button):
        hero = button.cget("text")
        button.config(relief=tk.RAISED, bg="SystemButtonFace")

    def toggle_hero(self, hero, buttons, update_counters_callback):
        if hero in self.selected_heroes:
            self.selected_heroes.remove(hero)
            if hero in self.priority_heroes:
                self.priority_heroes.remove(hero)
            self._reset_button(buttons[hero])
            hero_frame = buttons[hero].master
            self._remove_priority_label(buttons[hero], hero_frame)
        else:
            if len(self.selected_heroes) >= 6:
                removed_hero = self.selected_heroes.pop(0)
                self._reset_button(buttons[removed_hero])
                if removed_hero in self.priority_heroes:
                    self.priority_heroes.remove(removed_hero)
                hero_frame = buttons[removed_hero].master
                self._remove_priority_label(buttons[removed_hero], hero_frame)
            self.selected_heroes.append(hero)
            buttons[hero].config(relief=tk.SUNKEN, bg="lightblue")
        update_counters_callback()

    def clear_all(self, buttons, update_selected_label_callback, update_counters_callback):
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        for hero, button in buttons.items():
            self._reset_button(button)
            hero_frame = button.master
            if hero in self.priority_labels:
                self._remove_priority_label(button, hero_frame)
        update_selected_label_callback()
        update_counters_callback()

    def get_selected_heroes_text(self):
        return f"{get_text('selected')}{', '.join(self.selected_heroes) if self.selected_heroes else ''}"

    def calculate_counter_scores(self):
        from heroes_bd import heroes_counters
        counter_scores = {}
        for hero in heroes:
            counter_scores[hero] = 0

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
                if tanks < 1 and hero in hero_roles["tanks"]:
                    effective_team.append(hero)
                    tanks += 1
                elif supports < 1 and hero in hero_roles["supports"]:
                    effective_team.append(hero)
                    supports += 1
                if tanks >= 1 and supports >= 1:
                    break

        while len(effective_team) < 6:
            best_score = -float('inf')
            best_hero = None
            for hero, score in sorted_counters:
                if hero not in effective_team:
                    adjusted_score = score
                    for teammate in effective_team:
                        if hero in heroes_compositions.get(teammate, []):
                            adjusted_score += 0.5
                    if adjusted_score > best_score:
                        if (hero in hero_roles["tanks"] and tanks < 2) or \
                                (hero in hero_roles["supports"] and supports < 3) or \
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
            label.config(text=get_text('strong_player'))

# Привязываем метод generate_counterpick_display к классу
CounterpickLogic.generate_counterpick_display = generate_counterpick_display