# logic.py
import tkinter as tk
from heroes_bd import hero_counters

class CounterpickLogic:
    def __init__(self):
        self.selected_heroes = []
        self.priority_heroes = []
        self.current_result_text = ""
        self.priority_labels = {}  # Словарь для хранения ссылок на priority_label

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
                hero_frame.priority_frame.place(relx=0.5, rely=0.0, anchor="n")  # Сверху посередине
            priority_label = tk.Label(hero_frame.priority_frame, text="сильный игрок", font=("Arial", 8), fg="black",
                                      bg="red")
            priority_label.pack(side=tk.TOP, anchor="center")  # Центрируем метку
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
            self._remove_priority_label(buttons[hero], hero_frame)  # Удаляем метку
        else:
            if len(self.selected_heroes) >= 6:
                removed_hero = self.selected_heroes.pop(0)
                self._reset_button(buttons[removed_hero])
                if removed_hero in self.priority_heroes:
                    self.priority_heroes.remove(removed_hero)
                hero_frame = buttons[removed_hero].master
                self._remove_priority_label(buttons[removed_hero], hero_frame)  # Удаляем метку с последнего
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
        return f"Выбрано: {', '.join(self.selected_heroes)}"

    def calculate_counter_scores(self):
        counter_scores = {}
        for hero in self.selected_heroes:
            for counter in hero_counters.get(hero, []):
                score = 2 if hero in self.priority_heroes else 1
                counter_scores[counter] = counter_scores.get(counter, 0) + score

        for hero in self.selected_heroes:
            for counter in hero_counters.get(hero, []):
                if counter in self.selected_heroes:
                    counter_scores[counter] = max(0, counter_scores.get(counter, 0) - 1)

        return {k: v for k, v in counter_scores.items() if v > 0}

    def generate_counterpick_display(self, result_frame, images, small_images):
        # Preserve the result_label by only destroying non-label widgets or widgets that aren’t the default text
        for widget in result_frame.winfo_children():
            if not (isinstance(widget, tk.Label) and widget.cget('text') in [
                "Выберите героев, чтобы увидеть контрпики.", ""]):
                widget.destroy()

        sorted_counters = sorted(self.calculate_counter_scores().items(), key=lambda x: x[1], reverse=True)
        self.current_result_text = "Counterpick rating for a given enemy team's lineup:\n"

        for counter, score in sorted_counters:
            if counter in images:
                counter_frame = tk.Frame(result_frame)
                counter_frame.pack(anchor=tk.W)

                img_label = tk.Label(counter_frame, image=images[counter])
                img_label.pack(side=tk.LEFT)

                text_label = tk.Label(counter_frame, text=f"{counter}: {score:.1f} балл(ов)")
                text_label.pack(side=tk.LEFT)

                counter_for_heroes = [hero for hero in self.selected_heroes if counter in hero_counters.get(hero, [])]
                for hero in counter_for_heroes:
                    if hero in small_images:
                        small_img_label = tk.Label(counter_frame, image=small_images[hero])
                        small_img_label.pack(side=tk.LEFT, padx=2)

                self.current_result_text += f"{counter}: {score:.1f} points\n"


