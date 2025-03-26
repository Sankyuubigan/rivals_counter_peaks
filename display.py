import tkinter as tk
from heroes_bd import heroes_counters
from translations import get_text

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

    effective_team = self.calculate_effective_team(counter_scores)

    for counter, score in sorted_counters:
        if counter in images:
            counter_frame = tk.Frame(result_frame)
            if counter in effective_team:
                counter_frame.config(highlightthickness=5, highlightbackground="blue", relief="solid")
            else:
                counter_frame.config(highlightthickness=0)
            counter_frame.pack(anchor=tk.W, pady=2)

            img_label = tk.Label(counter_frame, image=images[counter])
            img_label.pack(side=tk.LEFT)

            text_label = tk.Label(counter_frame, text=f"{counter}: {score:.1f} {get_text('points')}")
            text_label.pack(side=tk.LEFT, padx=5)

            counter_for_heroes = [hero for hero in self.selected_heroes if counter in heroes_counters.get(hero, [])]
            for hero in counter_for_heroes:
                if hero in small_images:
                    small_img_label = tk.Label(counter_frame, image=small_images[hero],
                                               highlightthickness=3, highlightbackground="green")
                    small_img_label.pack(side=tk.LEFT, padx=2)

            countered_by_heroes = [hero for hero in self.selected_heroes if hero in heroes_counters.get(counter, [])]
            for hero in countered_by_heroes:
                if hero in small_images:
                    small_img_label = tk.Label(counter_frame, image=small_images[hero],
                                               highlightthickness=3, highlightbackground="red")
                    small_img_label.pack(side=tk.LEFT, padx=2)

            self.current_result_text += f"{counter}: {score:.1f} {get_text('points')}\n"

# Привязка осталась для совместимости, но теперь она не нужна здесь, так как перенесена в logic.py
# from logic import CounterpickLogic
# CounterpickLogic.generate_counterpick_display = generate_counterpick_display