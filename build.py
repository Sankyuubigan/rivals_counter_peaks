# build.py
import os

# Устанавливаем переменную окружения с версией
version = "1.01"  # Или читай из main.py, как в варианте 1
os.environ["APP_VERSION"] = version

# Генерируем команду
output_name = f"rivals_counter_{os.environ['APP_VERSION']}"
command = f'pyinstaller --onefile --windowed --name "{output_name}" --add-data "resources;resources" main.py'
print(f"Выполняем команду: {command}")
os.system(command)