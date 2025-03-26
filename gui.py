import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pyperclip
from build import version
from logic import CounterpickLogic
from images_load import load_images
from heroes_bd import heroes  # Добавляем импорт heroes
from translations import get_text, set_language, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

def create_gui(root):
    root.title(get_text('title'))
    root.geometry("1400x1000")
    root.maxsize(2000, 2000)

    logic = CounterpickLogic()

    def on_mousewheel(event):
        widget = canvas.winfo_containing(event.x_root, event.y_root)
        if widget and (widget == canvas or canvas.winfo_containing(event.x_root, event.y_root) == widget):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    top_frame = tk.Frame(root, bg="lightgray", height=30)
    top_frame.pack(side=tk.TOP, fill=tk.X)

    version_label = tk.Label(top_frame, text=get_text('version').replace('1.01', version), bg="lightgray")
    version_label.pack(side=tk.LEFT, padx=5, pady=5)

    language_frame = tk.Frame(top_frame, bg="lightgray")
    language_frame.pack(side=tk.LEFT, padx=5, pady=5)

    language_label = tk.Label(language_frame, text=get_text('language'), bg="lightgray")
    language_label.pack(side=tk.LEFT)

    language_var = tk.StringVar(value=DEFAULT_LANGUAGE)
    language_menu = tk.OptionMenu(language_frame, language_var, *SUPPORTED_LANGUAGES.keys(), command=lambda lang: switch_language(lang))
    language_menu.pack(side=tk.LEFT)

    author_button = tk.Button(top_frame, text=get_text('about_author'), command=lambda: show_author_info(root))
    author_button.pack(side=tk.RIGHT, padx=5, pady=5)

    rating_button = tk.Button(top_frame, text=get_text('hero_rating'), command=lambda: show_hero_rating(root))
    rating_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def show_author_info(root):
        author_window = tk.Toplevel(root)
        author_window.title(get_text('about_author'))
        author_window.geometry("400x200")
        author_window.resizable(False, False)
        author_window.transient(root)
        author_window.grab_set()

        author_window.update_idletasks()
        width = author_window.winfo_width()
        height = author_window.winfo_height()
        x = (author_window.winfo_screenwidth() // 2) - (width // 2)
        y = (author_window.winfo_screenheight() // 2) - (height // 2)
        author_window.geometry(f"{width}x{height}+{x}+{y}")

        text_widget = tk.Text(author_window, height=10, width=50, wrap=tk.WORD)
        text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        info_text = (f"{get_text('author_info').replace('1.01', version)}\n\n"
                     f"{get_text('donate_info')}")
        text_widget.insert(tk.END, info_text)

        text_widget.config(state=tk.NORMAL)
        text_widget.bind("<Key>", lambda e: "break")

        def copy_text():
            try:
                selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                pyperclip.copy(selected_text)
            except tk.TclError:
                pass

        text_widget.bind("<Control-c>", lambda e: copy_text())
        context_menu = tk.Menu(author_window, tearoff=0)
        context_menu.add_command(label="Copy", command=copy_text)
        text_widget.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

        close_button = tk.Button(author_window, text="OK", width=10, command=author_window.destroy)
        close_button.pack(pady=10)

    def show_hero_rating(root):
        from heroes_bd import heroes_counters, heroes
        rating_window = tk.Toplevel(root)
        rating_window.title(get_text('hero_rating_title'))
        rating_window.geometry("400x600")
        rating_window.transient(root)
        rating_window.grab_set()

        rating_window.update_idletasks()
        width = rating_window.winfo_width()
        height = rating_window.winfo_height()
        x = (rating_window.winfo_screenwidth() // 2) - (width // 2)
        y = (rating_window.winfo_screenheight() // 2) - (height // 2)
        rating_window.geometry(f"{width}x{height}+{x}+{y}")

        canvas = tk.Canvas(rating_window)
        scrollbar = tk.Scrollbar(rating_window, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        rating_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=rating_frame, anchor="nw")

        def update_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        rating_frame.bind("<Configure>", update_scrollregion)

        counter_counts = {hero: len(heroes_counters.get(hero, [])) for hero in heroes}
        sorted_heroes = sorted(counter_counts.items(), key=lambda x: x[1])

        for hero, count in sorted_heroes:
            tk.Label(rating_frame, text=f"{hero} ({count})").pack(anchor=tk.W)

        rating_window.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

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
        rating_button.config(text=get_text('hero_rating'))
        if not logic.selected_heroes:
            result_label.config(text=get_text('no_heroes_selected'))
        logic.update_display_language()

    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    right_frame = tk.Frame(main_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)

    for i in range(5):
        right_frame.columnconfigure(i, minsize=100, weight=0)
    num_rows = (len(heroes) // 5) + 1
    for i in range(num_rows):
        right_frame.rowconfigure(i, minsize=100, weight=0)
    right_frame.rowconfigure(num_rows, minsize=50, weight=0)

    left_frame = tk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    global canvas
    canvas = tk.Canvas(left_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    canvas.bind("<Enter>", lambda e: canvas.focus_set())

    scrollbar = tk.Scrollbar(left_frame, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(yscrollcommand=scrollbar.set)
    result_frame = tk.Frame(canvas)
    canvas.create_window((10, 0), window=result_frame, anchor="nw")  # Отступ слева

    def update_scrollregion(event=None):
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)
        else:
            canvas.configure(scrollregion=(0, 0, 0, 0))

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

    def update_selected_label_wrapper():
        selected_heroes_label.config(text=logic.get_selected_heroes_text())

    for i, hero in enumerate(heroes):
        hero_frame = tk.Frame(right_frame)
        hero_frame.grid(row=i // 5, column=i % 5, padx=0, pady=0, sticky="nsew")
        btn = tk.Button(hero_frame, text=hero, image=images.get(hero), compound=tk.TOP,
                        command=lambda h=hero: logic.toggle_hero(h, buttons, update_counters_wrapper),
                        width=90, height=90, relief="raised", borderwidth=1, highlightthickness=0)
        btn.pack(fill=tk.BOTH, expand=True)
        btn.bind("<Button-3>", lambda event, h=hero, b=btn, f=hero_frame: logic.set_priority(h, b, f, update_counters_wrapper))
        buttons[hero] = btn

    selected_heroes_label = tk.Label(right_frame, text=get_text('selected'), height=2, anchor="w", wraplength=400)
    selected_heroes_label.grid(row=num_rows, column=0, columnspan=5, sticky="w", pady=(10, 5))

    copy_button = tk.Button(right_frame, text=get_text('copy_rating'), command=lambda: copy_to_clipboard(logic))
    copy_button.grid(row=num_rows + 1, column=0, columnspan=5, sticky="ew", pady=(0, 5))

    clear_button = tk.Button(right_frame, text=get_text('clear_all'),
                             command=lambda: logic.clear_all(buttons, update_selected_label_wrapper, update_counters_wrapper))
    clear_button.grid(row=num_rows + 2, column=0, columnspan=5, sticky="ew", pady=(0, 5))

    update_language()

def copy_to_clipboard(logic):
    effective_team = logic.calculate_effective_team(logic.calculate_counter_scores())
    if effective_team:
        text_to_copy = f"Эффективная команда сопротивления:\n{', '.join(effective_team)}"
        pyperclip.copy(text_to_copy)
    else:
        messagebox.showwarning("Ошибка", "Нет данных для копирования.")