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
    # Устанавливаем заголовок окна с версией
    window_title = f"{get_text('title')} v{version}"
    root.title(window_title)
    # Уменьшаем размер окна в 2 раза
    root.geometry("700x500")
    root.maxsize(2000, 2000) # Оставим максимальный размер прежним

    logic = CounterpickLogic()

    def on_mousewheel(event):
        widget = canvas.winfo_containing(event.x_root, event.y_root)
        if widget and (widget == canvas or canvas.winfo_containing(event.x_root, event.y_root) == widget):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    top_frame = tk.Frame(root, bg="lightgray") # Убрал height=30
    top_frame.pack(side=tk.TOP, fill=tk.X)

    # --- Ползунок прозрачности ---
    def update_transparency(val):
        # Значение ползунка от 10 до 100, преобразуем в 0.1 - 1.0
        alpha_value = float(val) / 100.0
        root.attributes('-alpha', alpha_value) # Убрал max(..., 0.1), т.к. from_=10

    # --- Группа ползунка прозрачности ---
    transparency_frame = tk.Frame(top_frame, bg="lightgray")
    transparency_frame.pack(side=tk.LEFT, padx=(10, 10), pady=2) # Уменьшил pady

    transparency_label = tk.Label(transparency_frame, text=get_text('transparency', 'Прозрачность:'), bg="lightgray") # Добавил fallback текст
    transparency_label.pack(side=tk.TOP) # Метка сверху

    # Начальное значение ползунка соответствует начальной прозрачности (20%)
    transparency_slider = tk.Scale(transparency_frame, from_=10, to=100, orient=tk.HORIZONTAL,
                                   command=update_transparency, showvalue=0, length=100, 
                                   bg="lightgray", troughcolor='#d3d3d3', sliderrelief=tk.RAISED,
                                   highlightthickness=1, highlightbackground='white')
    transparency_slider.set(100) # Устанавливаем начальное значение 100 (максимум)
    transparency_slider.pack(side=tk.TOP) # Ползунок под меткой
    # --- Конец группы ползунка прозрачности ---

    # Убираем метку версии отсюда
    # version_label = tk.Label(top_frame, text=get_text('version').replace('1.01', version), bg="lightgray")
    # version_label.pack(side=tk.LEFT, padx=5, pady=5)

    language_frame = tk.Frame(top_frame, bg="lightgray")
    language_frame.pack(side=tk.LEFT, padx=5, pady=5)

    language_label = tk.Label(language_frame, text=get_text('language'), bg="lightgray")
    language_label.pack(side=tk.LEFT)

    language_var = tk.StringVar(value=DEFAULT_LANGUAGE)
    language_menu = tk.OptionMenu(language_frame, language_var, *SUPPORTED_LANGUAGES.keys(), command=lambda lang: switch_language(lang))
    language_menu.pack(side=tk.LEFT)

    # Добавляем переключатель режимов
    mode_frame = tk.Frame(top_frame, bg="lightgray")
    mode_frame.pack(side=tk.LEFT, padx=(10, 0), pady=2)

    # Метка над переключателем
    mode_label = tk.Label(mode_frame, text="Режим:", bg="lightgray")
    mode_label.pack(side=tk.TOP)

    # Кнопки переключения режимов
    mode_buttons_frame = tk.Frame(mode_frame, bg="lightgray")
    mode_buttons_frame.pack(side=tk.TOP)

    mode_var = tk.StringVar(value="middle")  # По умолчанию средний режим

    def switch_mode(mode):
        mode_var.set(mode)
        
        # Устанавливаем размеры окна в зависимости от режима
        if mode == "min":
            root.geometry("600x110")
            author_button.pack_forget()
            rating_button.pack_forget()
        elif mode == "middle":
            root.geometry("950x270") 
            author_button.pack_forget()
            rating_button.pack_forget()
        elif mode == "max":
            root.geometry("1700x1000")
            author_button.pack(side=tk.RIGHT, padx=5, pady=5)
            rating_button.pack(side=tk.RIGHT, padx=5, pady=5)
            
        update_interface_for_mode(mode)

    min_button = tk.Button(mode_buttons_frame, text="Компактный", width=10,
                          command=lambda: switch_mode("min"))
    min_button.pack(side=tk.LEFT, padx=2)

    middle_button = tk.Button(mode_buttons_frame, text="Средний", width=10,
                            command=lambda: switch_mode("middle"))
    middle_button.pack(side=tk.LEFT, padx=2)

    max_button = tk.Button(mode_buttons_frame, text="Большой", width=10,
                          command=lambda: switch_mode("max"))
    max_button.pack(side=tk.LEFT, padx=2)

    author_button = tk.Button(top_frame, text=get_text('about_author'), command=lambda: show_author_info(root))
    author_button.pack(side=tk.RIGHT, padx=5, pady=5)

    rating_button = tk.Button(top_frame, text=get_text('hero_rating'), command=lambda: show_hero_rating(root))
    rating_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def update_interface_for_mode(mode):
        """Обновляет интерфейс в соответствии с выбранным режимом"""
        from images_load import get_images_for_mode
        
        # Получаем изображения для текущего режима
        images, small_images = get_images_for_mode(mode)
        
        # Обновляем размеры и видимость элементов
        if mode == "min":
            right_frame.pack_forget()  # Скрываем правую панель
            # Используем минимальный режим отображения
            logic.generate_minimal_display(result_frame, result_label, images)
        elif mode == "middle":
            right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
            
            # Обновляем правую панель - 10 колонок x 4 строки, иконки без текста
            for i in range(10):  # Настраиваем 10 колонок
                right_frame.columnconfigure(i, minsize=50, weight=0)
            
            # Настраиваем 4 строки
            for i in range(4):
                right_frame.rowconfigure(i, minsize=50, weight=0)
            
            # Очищаем старые кнопки
            for btn in buttons.values():
                btn.grid_forget()
            
            # Обновляем кнопки героев
            for hero, btn in buttons.items():
                btn.config(text="", image=images.get(hero), width=50, height=50)
                hero_index = heroes.index(hero)
                btn.grid(row=(hero_index // 10), column=(hero_index % 10), sticky="nsew")
            
            # Обновляем левую панель - одинаковый размер иконок
            # Это будет обработано в generate_counterpick_display через small_images
            
        elif mode == "max":
            right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
            
            # Возвращаем оригинальные размеры (в 2 раза больше текущих)
            for i in range(5):
                right_frame.columnconfigure(i, minsize=100, weight=0) # minsize 50 -> 100
            num_rows = (len(heroes) // 5) + 1
            for i in range(num_rows):
                right_frame.rowconfigure(i, minsize=100, weight=0) # minsize 50 -> 100
            
            # Обновляем кнопки героев с текстом и увеличенными иконками
            for hero, btn in buttons.items():
                btn.config(text=hero, image=images.get(hero), width=90, height=90) # width/height 45 -> 90
                btn.grid(row=(heroes.index(hero) // 5), column=(heroes.index(hero) % 5))
        
        # Обновляем отображение героев
        if hasattr(logic, 'selected_heroes'):
            update_counters_wrapper()

    def show_author_info(root):
        author_window = tk.Toplevel(root)
        author_window.title(get_text('about_author'))
        author_window.geometry("400x200")
        author_window.resizable(True, True) # Разрешаем изменение размера
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

        def copy_text():
            try:
                selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                pyperclip.copy(selected_text)
            except tk.TclError:
                pass

        # Привязываем Ctrl+C напрямую к виджету текста
        text_widget.bind("<Control-c>", lambda e: copy_text())

        # Контекстное меню для правой кнопки мыши
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
        transparency_label.config(text=get_text('transparency', 'Прозрачность:')) # Обновляем текст метки ползунка
        # Обновляем заголовок окна при смене языка
        root.title(f"{get_text('title')} v{version}")
        rating_button.config(text=get_text('hero_rating'))
        if not logic.selected_heroes:
            result_label.config(text=get_text('no_heroes_selected'))
        logic.update_display_language()

    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    right_frame = tk.Frame(main_frame)
    # Уменьшаем ширину правой панели, делая ее нерасширяемой по X
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=False) # Изменил fill и expand

    # Уменьшаем размеры ячеек в правой панели в 2 раза
    for i in range(5):
        right_frame.columnconfigure(i, minsize=50, weight=0) # minsize 100 -> 50
    num_rows = (len(heroes) // 5) + 1
    for i in range(num_rows):
        right_frame.rowconfigure(i, minsize=50, weight=0) # minsize 100 -> 50
    # Уменьшаем высоту строк для доп. элементов
    right_frame.rowconfigure(num_rows, minsize=25, weight=0) # Строка для selected_heroes_label
    right_frame.rowconfigure(num_rows + 1, minsize=25, weight=0) # Строка для copy_button
    right_frame.rowconfigure(num_rows + 2, minsize=25, weight=0) # Строка для clear_button


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
        # Уменьшаем размер кнопок героев в 2 раза
        btn = tk.Button(hero_frame, text=hero, image=images.get(hero), compound=tk.TOP,
                        command=lambda h=hero: logic.toggle_hero(h, buttons, update_counters_wrapper),
                        width=45, height=45, relief="raised", borderwidth=1, highlightthickness=0) # width/height 90 -> 45
        btn.pack(fill=tk.BOTH, expand=True)
        btn.bind("<Button-3>", lambda event, h=hero, b=btn, f=hero_frame: logic.set_priority(h, b, f, update_counters_wrapper))
        buttons[hero] = btn

    # Уменьшаем wraplength и паддинги для метки выбранных героев
    selected_heroes_label = tk.Label(right_frame, text=get_text('selected'), height=2, anchor="w", wraplength=250) # wraplength 400 -> 250 (по ширине 5 кнопок по 50)
    selected_heroes_label.grid(row=num_rows, column=0, columnspan=5, sticky="nsew", pady=(5, 2)) # Уменьшил pady, sticky="w" -> "nsew"

    # Добавляем возможность копирования текста из selected_heroes_label
    def copy_selected_text():
        try:
            pyperclip.copy(selected_heroes_label.cget("text"))
        except Exception as e:
            print(f"Ошибка при копировании: {e}")

    selected_heroes_label.bind("<Control-c>", lambda e: copy_selected_text())
    context_menu_selected = tk.Menu(right_frame, tearoff=0)
    context_menu_selected.add_command(label="Copy", command=copy_selected_text)
    selected_heroes_label.bind("<Button-3>", lambda event: context_menu_selected.post(event.x_root, event.y_root))

    # Уменьшаем паддинги для кнопок
    copy_button = tk.Button(right_frame, text=get_text('copy_rating'), command=lambda: copy_to_clipboard(logic))
    copy_button.grid(row=num_rows + 1, column=0, columnspan=5, sticky="nsew", pady=(0, 2)) # sticky="ew" -> "nsew", pady=(0, 5) -> (0, 2)

    clear_button = tk.Button(right_frame, text=get_text('clear_all'),
                             command=lambda: logic.clear_all(buttons, update_selected_label_wrapper, update_counters_wrapper))
    clear_button.grid(row=num_rows + 2, column=0, columnspan=5, sticky="nsew", pady=(0, 5)) # sticky="ew" -> "nsew", pady=(0, 5) -> (0, 5) - оставим нижний отступ

    update_language() # Вызываем до update_counters_wrapper, чтобы метки обновились
    update_counters_wrapper() # Вызываем один раз в конце для инициализации левой панели

def copy_to_clipboard(logic):
    effective_team = logic.calculate_effective_team(logic.calculate_counter_scores())
    if effective_team:
        text_to_copy = f"we need to get these heroes:\n{', '.join(effective_team)}"
        pyperclip.copy(text_to_copy)
    else:
        messagebox.showwarning("Ошибка", "Нет данных для копирования.")
