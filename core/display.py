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
            # Определяем цвет фона в зависимости от того, входит ли герой в эффективную команду
            bg_color = "lightblue" if counter in effective_team else result_frame.cget("bg") # Используем фон родителя для невыделенных

            # Создаем фрейм с нужным фоном
            counter_frame = tk.Frame(result_frame, bg=bg_color)
            # Убираем рамку, используем фон для выделения
            counter_frame.pack(anchor=tk.W, pady=1, fill=tk.X, padx=2) # Уменьшил pady, добавил fill=X и padx

            # Устанавливаем фон для всех дочерних виджетов
            img_label = tk.Label(counter_frame, image=images[counter], bg=bg_color)
            img_label.pack(side=tk.LEFT)

            text_label = tk.Label(counter_frame, text=f"{counter}: {score:.1f} {get_text('points')}", bg=bg_color)
            text_label.pack(side=tk.LEFT, padx=5)

            counter_for_heroes = [hero for hero in self.selected_heroes if counter in heroes_counters.get(hero, [])]
            for hero in counter_for_heroes:
                if hero in small_images and small_images[hero]: # Добавил проверку на None
                    # Возвращаем зеленую рамку
                    small_img_label = tk.Label(counter_frame, image=small_images[hero], bg=bg_color,
                                               highlightthickness=2, highlightbackground="green")
                    small_img_label.pack(side=tk.LEFT, padx=2)

            countered_by_heroes = [hero for hero in self.selected_heroes if hero in heroes_counters.get(counter, [])]
            for hero in countered_by_heroes:
                if hero in small_images and small_images[hero]: # Добавил проверку на None
                    # Возвращаем красную рамку
                    small_img_label = tk.Label(counter_frame, image=small_images[hero], bg=bg_color,
                                               highlightthickness=2, highlightbackground="red")
                    small_img_label.pack(side=tk.LEFT, padx=2)

            self.current_result_text += f"{counter}: {score:.1f} {get_text('points')}\n"

def generate_minimal_display(self, result_frame, result_label, images):
    for widget in result_frame.winfo_children():
        if widget != result_label:
            widget.destroy()

    if not self.selected_heroes:
        self.current_result_text = ""
        return

    counter_scores = self.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Фильтруем героев с баллами > 0
    filtered_counters = [(hero, score) for hero, score in sorted_counters if score > 0]
    
    if not filtered_counters:
        result_label.config(text=get_text('no_counters_found'))
        return

    # Создаем горизонтальный фрейм для иконок
    icons_frame = tk.Frame(result_frame)
    icons_frame.pack(fill=tk.X, pady=5)

    effective_team = self.calculate_effective_team(counter_scores)
    
    for counter, score in filtered_counters:
        if counter in images:
            # Определяем стиль в зависимости от эффективности
            if counter in effective_team:
                img_label = tk.Label(icons_frame, image=images[counter],
                                   highlightthickness=2, highlightbackground="lightblue")
            else:
                img_label = tk.Label(icons_frame, image=images[counter])
            
            img_label.pack(side=tk.LEFT, padx=2)

    self.current_result_text = ", ".join([f"{hero}: {score:.1f}" for hero, score in filtered_counters])

# Привязка осталась для совместимости, но теперь она не нужна здесь, так как перенесена в logic.py
# from logic import CounterpickLogic
# CounterpickLogic.generate_counterpick_display = generate_counterpick_display
