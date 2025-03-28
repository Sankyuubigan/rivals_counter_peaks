import os

# Устанавливаем переменную окружения с версией
version = "2.02"
os.environ["APP_VERSION"] = version

# Генерируем команду
output_name = f"rivals_counter_{os.environ['APP_VERSION']}"
command = (
    f'pyinstaller --onefile --windowed --name "{output_name}" '
    f'--add-data "resources;resources" '  # Для изображений
    f'--add-data "heroes_bd.py;." '      # Добавляем heroes_bd.py
    f'--add-data "gui.py;." '            # Добавляем gui.py
    f'--add-data "logic.py;." '          # Добавляем logic.py
    f'--add-data "images_load.py;." '    # Добавляем images_load.py
    f'--add-data "translations.py;." '   # Добавляем translations.py
    f'--add-data "utils.py;." '          # Добавляем utils.py
    f'--add-data "display.py;." '        # Добавляем display.py
    f'main.py'
)
print(f"Выполняем команду: {command}")
os.system(command)