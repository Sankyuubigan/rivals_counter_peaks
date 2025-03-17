# код файла logic.py

import tkinter as tk
from heroes_bd import hero_counters

# Глобальные переменные для хранения состояния
selected_heroes = []
priority_heroes = []
current_result_text = ""

# Функция для добавления/удаления героя из списка выбранных
def toggle_hero(hero, button, selected_heroes_label, buttons, update_counters):
    if hero in selected_heroes:
        # Если герой уже выбран, удаляем его
        selected_heroes.remove(hero)
        if hero in priority_heroes:
            priority_heroes.remove(hero)  # Удаляем из приоритетных, если был
        button.config(relief=tk.RAISED, bg="SystemButtonFace")  # Снимаем выделение
        for widget in button.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("text") == "сильный игрок":
                widget.destroy()  # Удаляем надпись "сильный игрок"
    else:
        if len(selected_heroes) >= 6:
            # Если уже выбрано 6 героев, заменяем последнего
            removed_hero = selected_heroes.pop()
            removed_button = buttons[removed_hero]
            removed_button.config(relief=tk.RAISED, bg="SystemButtonFace")  # Снимаем выделение
            if removed_hero in priority_heroes:
                priority_heroes.remove(removed_hero)  # Удаляем из приоритетных
            # Удаляем надпись "сильный игрок" у удалённого героя
            for widget in removed_button.winfo_children():
                if isinstance(widget, tk.Label) and widget.cget("text") == "сильный игрок":
                    widget.destroy()  # Удаляем надпись "сильный игрок"
        selected_heroes.append(hero)
        button.config(relief=tk.SUNKEN, bg="lightblue")  # Выделяем кнопку синим цветом
    update_selected_heroes_label(selected_heroes_label)
    update_counters()  # Обновляем рейтинг контрпиков

# Функция для выделения героя правой кнопкой мыши
def set_priority(event, hero, button, update_counters):
    if hero not in selected_heroes:
        return  # Правая кнопка работает только на выбранных героях

    if hero in priority_heroes:
        # Если герой уже приоритетный, снимаем выделение
        priority_heroes.remove(hero)
        for widget in button.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("text") == "сильный игрок":
                widget.destroy()  # Удаляем надпись "сильный игрок"
    else:
        # Если герой не приоритетный, добавляем его
        priority_heroes.append(hero)
        # Добавляем надпись "сильный игрок" с красным фоном
        priority_label = tk.Label(button, text="сильный игрок", font=("Arial", 8), fg="black", bg="red")
        priority_label.pack(side=tk.TOP)
    update_counters()  # Обновляем рейтинг

# Функция для обновления отображения выбранных героев
def update_selected_heroes_label(selected_heroes_label):
    selected_heroes_label.config(text=f"Выбрано: {', '.join(selected_heroes)}")

# Функция для обновления рейтинга контрпиков
def update_counters(result_label, result_frame, canvas, images, small_images):
    global current_result_text
    if len(selected_heroes) == 0:
        if result_label.winfo_exists():  # Проверяем, существует ли result_label
            result_label.config(text="Выберите героев вражеской команды, чтобы увидеть контрпики.")
        current_result_text = ""  # Очищаем текст рейтинга
        # Очищаем предыдущий рейтинг
        for widget in result_frame.winfo_children():
            widget.destroy()
        return

    counter_scores = {}
    for hero in selected_heroes:
        for counter in hero_counters.get(hero, []):
            if counter in counter_scores:
                # Если герой приоритетный, добавляем 2 балла, иначе 1
                counter_scores[counter] += 2 if hero in priority_heroes else 1
            else:
                counter_scores[counter] = 2 if hero in priority_heroes else 1

    # Штраф за уязвимость
    for hero in selected_heroes:
        for counter in hero_counters.get(hero, []):
            if counter in selected_heroes:  # Если контрпик также выбран в команде врага
                counter_scores[counter] -= 1  # Отнимаем 1 балл за уязвимость

    # Убираем героев с 0 баллами
    counter_scores = {k: v for k, v in counter_scores.items() if v > 0}

    # Сортируем контрпики по количеству баллов
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)

    # Очищаем предыдущий рейтинг
    for widget in result_frame.winfo_children():
        widget.destroy()

    # Выводим результат с картинками
    result_text = "Counterpick rating for a given enemy team's lineup:\n"
    for counter, score in sorted_counters:
        if counter in images:
            # Создаем фрейм для каждого контрпика
            counter_frame = tk.Frame(result_frame)
            counter_frame.pack(anchor=tk.W)

            # Добавляем изображение
            img_label = tk.Label(counter_frame, image=images[counter])
            img_label.pack(side=tk.LEFT)

            # Добавляем текст (имя и баллы)
            text_label = tk.Label(counter_frame, text=f"{counter}: {score:.1f} балл(ов)")
            text_label.pack(side=tk.LEFT)

            # Добавляем мелкие иконки героев, для которых данный герой является контрпиком
            counter_for_heroes = [hero for hero in selected_heroes if counter in hero_counters.get(hero, [])]
            for hero in counter_for_heroes:
                if hero in small_images:
                    small_img_label = tk.Label(counter_frame, image=small_images[hero])
                    small_img_label.pack(side=tk.LEFT, padx=2)

            # Добавляем текст в результат для копирования
            result_text += f"{counter}: {score:.1f} points\n"

    # Сохраняем текст рейтинга для копирования
    current_result_text = result_text

    # Обновляем scrollregion после добавления нового контента
    canvas.configure(scrollregion=canvas.bbox("all"))

# Функция для копирования текста рейтинга в буфер обмена
def copy_to_clipboard():
    if current_result_text:
        pyperclip.copy(current_result_text)
        # messagebox.showinfo("Успех", "Текст рейтинга скопирован в буфер обмена!")
    else:
        messagebox.showwarning("Ошибка", "Нет данных для копирования.")

# Функция для очистки всех выбранных героев
def clear_all(buttons, update_selected_heroes_label, update_counters):
    global selected_heroes, priority_heroes
    selected_heroes.clear()
    priority_heroes.clear()
    for button in buttons.values():
        button.config(relief=tk.RAISED, bg="SystemButtonFace")  # Сбрасываем выделение
        for widget in button.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("text") == "сильный игрок":
                widget.destroy()  # Удаляем надпись "сильный игрок"
    update_selected_heroes_label()
    update_counters()