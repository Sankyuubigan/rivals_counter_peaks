# код файла main.py

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pyperclip
from logic import toggle_hero, set_priority, update_selected_heroes_label, update_counters, copy_to_clipboard, clear_all
from images_load import load_images, resource_path  # Обновлённый импорт
from heroes_bd import heroes, hero_counters


def validate_heroes():
    # Проверяем, что все герои из hero_counters есть в списке heroes
    invalid_heroes = []
    for hero, counters in hero_counters.items():
        if hero not in heroes:
            invalid_heroes.append(hero)
        for counter in counters:
            if counter not in heroes:
                invalid_heroes.append(counter)

    if invalid_heroes:
        # Если найдены невалидные герои, выводим ошибку и завершаем программу
        error_message = f"Ошибка: В hero_counters найдены герои, которых нет в списке heroes:\n{', '.join(set(invalid_heroes))}"
        print(error_message)


def create_gui():
    # Создаем главное окно
    root = tk.Tk()
    root.title("Подбор контрпиков")
    root.geometry("1400x1000")  # Устанавливаем начальный размер окна
    root.maxsize(2000, 2000)  # Ограничиваем максимальную высоту окна

    # Функция для прокрутки колесом мыши
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Создаем основной фрейм для разделения на левую и правую области
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Левая область (выбор героев)
    left_frame = tk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)  # Левая область не расширяется

    # Устанавливаем фиксированные размеры для столбцов и строк
    for i in range(5):
        left_frame.columnconfigure(i, minsize=100, weight=0)  # Отключаем растягивание столбцов
    for i in range((len(heroes) // 5) + 1):  # Уменьшаем количество строк до необходимого
        left_frame.rowconfigure(i, minsize=100, weight=0)  # Отключаем растягивание строк

    # Правая область (рейтинг)
    right_frame = tk.Frame(main_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Canvas и Scrollbar для правой области
    canvas = tk.Canvas(right_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(right_frame, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(yscrollcommand=scrollbar.set)

    # Фрейм для размещения рейтинга внутри Canvas
    result_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=result_frame, anchor="nw")

    # Привязка прокрутки колесом мыши
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    # Обновление scrollregion при изменении содержимого
    def update_scrollregion(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    result_frame.bind("<Configure>", update_scrollregion)

    # Загрузка изображений
    images, small_images = load_images()

    # Создаем кнопки для выбора героев
    buttons = {}
    for i, hero in enumerate(heroes):
        btn = tk.Button(left_frame, text=hero, image=images.get(hero), compound=tk.TOP,
                        command=lambda h=hero, b=buttons: toggle_hero(h, b[h], selected_heroes_label, buttons, lambda: update_counters(result_label, result_frame, canvas, images, small_images)),
                        width=90, height=90, relief="raised", borderwidth=1, highlightthickness=0)  # Отключаем изменение состояния при наведении
        btn.grid(row=i // 5, column=i % 5, padx=0, pady=0, sticky="nsew")  # Убираем отступы
        btn.bind("<Button-3>", lambda event, h=hero, b=btn: set_priority(event, h, b, lambda: update_counters(result_label, result_frame, canvas, images, small_images)))  # Привязка правой кнопки мыши
        buttons[hero] = btn  # Сохраняем ссылку на кнопку

    # Создаем отдельный фрейм для кнопок и надписи
    control_frame = tk.Frame(main_frame)
    control_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, pady=10)  # Размещаем слева от left_frame

    # Метка для отображения выбранных героев
    selected_heroes_label = tk.Label(control_frame, text="Выбрано: ")
    selected_heroes_label.pack(anchor="w", pady=(0, 5))  # Убираем лишние отступы

    # Кнопка для копирования текста рейтинга
    copy_button = tk.Button(control_frame, text="Копировать рейтинг", command=copy_to_clipboard)
    copy_button.pack(fill=tk.X, pady=(0, 5))  # Убираем лишние отступы

    # Кнопка для очистки всех выбранных героев
    clear_button = tk.Button(control_frame, text="Очистить всё", command=lambda: clear_all(buttons, lambda: update_selected_heroes_label(selected_heroes_label), lambda: update_counters(result_label, result_frame, canvas, images, small_images)))
    clear_button.pack(fill=tk.X)  # Убираем лишние отступы

    # Метка для заголовка рейтинга
    result_label = tk.Label(result_frame, text="Выберите героев, чтобы увидеть контрпики.")
    result_label.pack(anchor=tk.W)

    # Запуск главного цикла
    root.mainloop()

if __name__ == "__main__":
    # Вызываем проверку перед запуском программы
    validate_heroes()
    create_gui()