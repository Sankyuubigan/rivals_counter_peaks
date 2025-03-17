# код файла images_load.py

from PIL import Image, ImageTk
import os
import sys

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу. """
    try:
        base_path = sys._MEIPASS  # Папка с ресурсами при запуске из .exe
    except AttributeError:
        base_path = os.path.abspath(".")  # Папка с проектом при запуске из .py
    return os.path.join(base_path, relative_path)

def load_images():
    from heroes_bd import heroes
    images = {}
    small_images = {}  # Мелкие иконки для отображения в рейтинге

    for hero in heroes:
        try:
            img = Image.open(resource_path(f"resources/{hero.lower().replace(' ', '_')}.png"))  # Основные иконки
            img = img.resize((50, 50), Image.Resampling.LANCZOS)
            images[hero] = ImageTk.PhotoImage(img)

            small_img = img.resize((35, 35), Image.Resampling.LANCZOS)  # Мелкие иконки
            small_images[hero] = ImageTk.PhotoImage(small_img)
        except FileNotFoundError:
            print(f"Изображение для {hero} не найдено!")
            images[hero] = None
            small_images[hero] = None

    return images, small_images