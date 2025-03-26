import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pyperclip

from build import version
from logic import CounterpickLogic
from images_load import load_images, resource_path
from heroes_bd import heroes, heroes_counters
from translations import get_text, set_language, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

def validate_heroes():
    invalid_heroes = []
    for hero, counters in heroes_counters.items():
        if hero not in heroes:
            invalid_heroes.append(hero)
        for counter in counters:
            if counter not in heroes:
                invalid_heroes.append(counter)

    if invalid_heroes:
        error_message = f"Ошибка: В hero_counters найдены герои, которых нет в списке heroes:\n{', '.join(set(invalid_heroes))}"
        print(error_message)

def create_gui():
    root = tk.Tk()
    root.title(get_text('title'))
    root.geometry("1400x1000")
    root.maxsize(2000, 2000)

    logic = CounterpickLogic()

    def on_mousewheel(event):
        print(f"Mouse wheel event at ({event.x_root}, {event.y_root})")
        widget = canvas.winfo_containing(event.x_root, event.y_root)
        print(f"Widget under cursor: {widget}")
        if widget and (widget == canvas or canvas.winfo_containing(event.x_root, event.y_root) == widget):
            print("Scrolling canvas")
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            print("Cursor not over canvas or its children")

    # Верхняя панель
    top_frame = tk.Frame(root, bg="lightgray", height=30)
    top_frame.pack(side=tk.TOP, fill=tk.X)

    # Метка версии слева
    version_label = tk.Label(top_frame, text=get_text('version').replace('1.01', version), bg="lightgray")
    version_label.pack(side=tk.LEFT, padx=5, pady=5)

    # Фрейм для кнопки языка
    language_frame = tk.Frame(top_frame, bg="lightgray")
    language_frame.pack(side=tk.LEFT, padx=5, pady=5)

    # Метка "Язык"
    language_label = tk.Label(language_frame, text=get_text('language'), bg="lightgray")
    language_label.pack(side=tk.LEFT)

    # Выпадающий список
    language_var = tk.StringVar(value=DEFAULT_LANGUAGE)
    language_menu = tk.OptionMenu(language_frame, language_var, *SUPPORTED_LANGUAGES.keys(), command=lambda lang: switch_language(lang))
    language_menu.pack(side=tk.LEFT)

    # Информация об авторе (справа)
    author_button = tk.Button(top_frame, text=get_text('about_author'), command=lambda: show_author_info())
    author_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def show_author_info():
        messagebox.showinfo(get_text('about_author'), get_text('author_info').replace('1.01', version))

    def switch_language(lang):
        set_language(lang)
        update_language()
        update_counters_wrapper()

    def update_language():
        root.title(get_text('title'))
        result_label.config(text=get_text('select_heroes'))
        selected_heroes_label.config(text=get_text('selected'))
        copy_button.config(text=get_text('copy_rating'))
        clear_button.config(text=get_text('clear_all'))
        author_button.config(text=get_text('about_author'))
        language_label.config(text=get_text('language'))
        version_label.config(text=get_text('version').replace('1.01', version))
        if not logic.selected_heroes:
            result_label.config(text=get_text('no_heroes_selected'))
        logic.update_display_language()

    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    left_frame = tk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

    for i in range(5):
        left_frame.columnconfigure(i, minsize=100, weight=0)
    num_rows = (len(heroes) // 5) + 1
    for i in range(num_rows):
        left_frame.rowconfigure(i, minsize=100, weight=0)
    left_frame.rowconfigure(num_rows, minsize=50, weight=0)

    right_frame = tk.Frame(main_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(right_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    canvas.bind("<Enter>", lambda e: canvas.focus_set())

    scrollbar = tk.Scrollbar(right_frame, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(yscrollcommand=scrollbar.set)
    result_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=result_frame, anchor="nw")

    def update_scrollregion(event=None):
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)
        else:
            canvas.configure(scrollregion=(0, 0, 0, 0))
        print(f"Scrollregion updated to: {canvas.bbox('all')}")

    result_frame.bind("<Configure>", update_scrollregion)
    canvas.configure(scrollregion=(0, 0, 0, 0))

    root.bind_all("<MouseWheel>", on_mousewheel)

    try:
        images, small_images = load_images()
    except Exception as e:
        messagebox.showerror("Ошибка загрузки изображений", f"Произошла ошибка: {e}")
        root.destroy()
        return

    buttons = {}
    result_label = tk.Label(result_frame, text=get_text('select_heroes'))
    result_label.pack(anchor=tk.W)

    def update_counters_wrapper():
        if logic.selected_heroes:
            logic.generate_counterpick_display(result_frame, result_label, images, small_images)
            if result_label.winfo_exists():
                result_label.config(text="")
        else:
            for widget in result_frame.winfo_children():
                if widget != result_label:
                    widget.destroy()
            if result_label.winfo_exists():
                result_label.config(text=get_text('no_heroes_selected'))
        update_selected_label_wrapper()
        canvas.update_idletasks()
        update_scrollregion()
        print(f"Scrollregion after update: {canvas.bbox('all')}")

    def update_selected_label_wrapper():
        selected_heroes_label.config(text=logic.get_selected_heroes_text())

    for i, hero in enumerate(heroes):
        hero_frame = tk.Frame(left_frame)
        hero_frame.grid(row=i // 5, column=i % 5, padx=0, pady=0, sticky="nsew")
        btn = tk.Button(hero_frame, text=hero, image=images.get(hero), compound=tk.TOP,
                        command=lambda h=hero: logic.toggle_hero(h, buttons, update_counters_wrapper),
                        width=90, height=90, relief="raised", borderwidth=1, highlightthickness=0)
        btn.pack(fill=tk.BOTH, expand=True)
        btn.bind("<Button-3>", lambda event, h=hero, b=btn, f=hero_frame: logic.set_priority(h, b, f, update_counters_wrapper))
        buttons[hero] = btn

    selected_heroes_label = tk.Label(left_frame, text=get_text('selected'), height=2, anchor="w", wraplength=400)
    selected_heroes_label.grid(row=num_rows, column=0, columnspan=5, sticky="w", pady=(10, 5))

    copy_button = tk.Button(left_frame, text=get_text('copy_rating'), command=lambda: copy_to_clipboard(logic))
    copy_button.grid(row=num_rows + 1, column=0, columnspan=5, sticky="ew", pady=(0, 5))

    clear_button = tk.Button(left_frame, text=get_text('clear_all'),
                             command=lambda: logic.clear_all(buttons, update_selected_label_wrapper, update_counters_wrapper))
    clear_button.grid(row=num_rows + 2, column=0, columnspan=5, sticky="ew", pady=(0, 5))

    # Инициализация языка
    update_language()

    root.mainloop()

def copy_to_clipboard(logic):
    if logic.current_result_text:
        pyperclip.copy(logic.current_result_text)
    else:
        messagebox.showwarning("Ошибка", "Нет данных для копирования.")

if __name__ == "__main__":
    validate_heroes()
    create_gui()