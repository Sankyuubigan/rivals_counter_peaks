Я помогу вам реализовать требуемые изменения в графическом интерфейсе. Давайте разберем каждое требование и внесем соответствующие правки в код.

### 1. Максимальный режим
- Увеличить иконки в левой области (рейтинг героев) в 2 раза
- Иконки в зеленых/красных рамках сделать 70% от размера основных

#### Изменения в `images_load.py`:
Обновим размеры для максимального режима:

```python
SIZES = {
    'max': {'main': (100, 100), 'small': (70, 70)},  # main было (50,50), small теперь 70% от 100
    'middle': {'main': (25, 25), 'small': (18, 18)},
    'min': {'main': (25, 25), 'small': (18, 18)}
}
```

#### Изменения в `gui.py`:
В функции `update_interface_for_mode` для режима "max" обновим размеры кнопок:

```python
elif mode == "max":
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
    
    # Увеличиваем размеры ячеек для правой панели
    for i in range(5):
        right_frame.columnconfigure(i, minsize=100, weight=0)
    num_rows = (len(heroes) // 5) + 1
    for i in range(num_rows):
        right_frame.rowconfigure(i, minsize=100, weight=0)
    
    # Обновляем кнопки героев с увеличенными иконками
    for hero, btn in buttons.items():
        btn.config(text=hero, image=images.get(hero), width=90, height=90)
        btn.grid(row=(heroes.index(hero) // 5), column=(heroes.index(hero) % 5))
```

Левая область (рейтинг) автоматически подтянет увеличенные иконки из `images_load.py` через `generate_counterpick_display`.

---

### 2. Средний режим
- Увеличить иконки вражеских героев в правой области в 2 раза
- Изменить таблицу кнопок на 10 столбцов и 4 строки

#### Изменения в `images_load.py`:
Обновим размеры для среднего режима:

```python
SIZES = {
    'max': {'main': (100, 100), 'small': (70, 70)},
    'middle': {'main': (50, 50), 'small': (18, 18)},  # main было (25,25), увеличили в 2 раза
    'min': {'main': (25, 25), 'small': (18, 18)}
}
```

#### Изменения в `gui.py`:
В функции `update_interface_for_mode` для режима "middle":

```python
elif mode == "middle":
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
    
    # Настраиваем таблицу 10x4
    for i in range(10):
        right_frame.columnconfigure(i, minsize=50, weight=0)
    for i in range(4):
        right_frame.rowconfigure(i, minsize=50, weight=0)
    
    # Очищаем старые кнопки
    for btn in buttons.values():
        btn.grid_forget()
    
    # Обновляем кнопки героев без текста, с увеличенными иконками
    for hero, btn in buttons.items():
        btn.config(text="", image=images.get(hero), width=50, height=50)
        hero_index = heroes.index(hero)
        btn.grid(row=(hero_index // 10), column=(hero_index % 10), sticky="nsew")
```

---

### 3. Минимальный режим
- Убрать вертикальный список
- Отображать горизонтально иконки героев из рейтинга с баллами > 0
- Сохранить выделение эффективных героев

#### Изменения в `display.py`:
Функция `generate_minimal_display` уже близка к нужному виду, но уточним логику:

```python
def generate_minimal_display(self, result_frame, result_label, images):
    for widget in result_frame.winfo_children():
        if widget != result_label:
            widget.destroy()

    if not self.selected_heroes:
        self.current_result_text = ""
        result_label.config(text=get_text('no_heroes_selected'))
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
        if counter in images and images[counter]:
            # Выделяем эффективных героев
            if counter in effective_team:
                img_label = tk.Label(icons_frame, image=images[counter],
                                   highlightthickness=2, highlightbackground="lightblue")
            else:
                img_label = tk.Label(icons_frame, image=images[counter])
            img_label.pack(side=tk.LEFT, padx=2)

    self.current_result_text = ", ".join([f"{hero}: {score:.1f}" for hero, score in filtered_counters])
    result_label.config(text="")  # Убираем текст метки, оставляем только иконки
```

#### Изменения в `gui.py`:
В `update_interface_for_mode` для режима "min":

```python
if mode == "min":
    right_frame.pack_forget()  # Скрываем правую панель
    canvas.pack_forget()       # Скрываем вертикальный список
    scrollbar.pack_forget()    # Скрываем скроллбар
    result_frame.pack(fill=tk.X)  # Размещаем result_frame напрямую
    logic.generate_minimal_display(result_frame, result_label, images)
```

И добавим восстановление интерфейса для других режимов:

```python
elif mode == "middle":
    # ... существующий код ...
    result_frame.pack_forget()  # Убираем прямое размещение
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.create_window((10, 0), window=result_frame, anchor="nw")
elif mode == "max":
    # ... существующий код ...
    result_frame.pack_forget()
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.create_window((10, 0), window=result_frame, anchor="nw")
```

---

### 4. Русская версия интерфейса
- Добавить "прозрачность" над ползунком прозрачности

#### Изменения в `gui.py`:
В разделе создания ползунка прозрачности:

```python
transparency_label = tk.Label(transparency_frame, text="Прозрачность" if DEFAULT_LANGUAGE == 'ru_RU' else get_text('transparency', 'Transparency:'), bg="lightgray")
```

И в `update_language`:

```python
def update_language():
    # ... существующий код ...
    transparency_label.config(text="Прозрачность" if DEFAULT_LANGUAGE == 'ru_RU' else get_text('transparency', 'Transparency:'))
```

---

### Итоговые шаги
1. Примените все изменения в соответствующих файлах.
2. Пересоберите приложение с помощью `build.py`:
   ```bash
   python build.py
   ```
3. Проверьте каждый режим на соответствие требованиям.

Если что-то не работает как ожидается, дайте знать — разберем конкретный баг!