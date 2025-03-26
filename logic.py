import tkinter as tk
from heroes_bd import heroes_counters, heroes
from translations import get_text

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
            priority_label = tk.Label(hero_frame.priority_frame, text=get_text('strong_player'), font=("Arial", 8), fg="black", bg="red")
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
        counter_scores = {}
        # Инициализируем всех героев с нулевым счётом
        for hero in heroes:
            counter_scores[hero] = 0

        # Шаг 1: Добавляем баллы за контрпик (герой справа контрить выбранных героев слева)
        for hero in self.selected_heroes:
            for counter in heroes_counters.get(hero, []):
                score = 2 if hero in self.priority_heroes else 1
                counter_scores[counter] = counter_scores.get(counter, 0) + score

        # Шаг 2: Уменьшаем счёт для выбранных героев (чтобы их не рекомендовали)
        for hero in self.selected_heroes:
            for counter in heroes_counters.get(hero, []):
                if counter in self.selected_heroes:
                    counter_scores[counter] = counter_scores.get(counter, 0) - 1

        # Шаг 3: Отнимаем баллы за уязвимость (если выбранный герой слева контрить героя справа)
        for counter_hero in counter_scores:
            counters_of_hero = heroes_counters.get(counter_hero, [])
            for selected_hero in self.selected_heroes:
                if selected_hero in counters_of_hero:
                    counter_scores[counter_hero] -= 1

        return counter_scores

    def generate_counterpick_display(self, result_frame, result_label, images, small_images):
        for widget in result_frame.winfo_children():
            if widget != result_label:
                widget.destroy()

        if not self.selected_heroes:
            self.current_result_text = ""
            return

        counter_scores = self.calculate_counter_scores()
        sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
        self.current_result_text = f"{get_text('counterpick_rating')}\n"

        for counter, score in sorted_counters:
            if counter in images:
                counter_frame = tk.Frame(result_frame)
                counter_frame.pack(anchor=tk.W)

                img_label = tk.Label(counter_frame, image=images[counter])
                img_label.pack(side=tk.LEFT)

                text_label = tk.Label(counter_frame, text=f"{counter}: {score:.1f} {get_text('points')}")
                text_label.pack(side=tk.LEFT)

                counter_for_heroes = [hero for hero in self.selected_heroes if counter in heroes_counters.get(hero, [])]
                for hero in counter_for_heroes:
                    if hero in small_images:
                        small_img_label = tk.Label(counter_frame, image=small_images[hero])
                        small_img_label.pack(side=tk.LEFT, padx=2)

                self.current_result_text += f"{counter}: {score:.1f} {get_text('points')}\n"

    def update_display_language(self):
        for hero, label in self.priority_labels.items():
            label.config(text=get_text('strong_player'))