# File: build.py
import os

version = "3.01" # Или актуальная версия
os.environ["APP_VERSION"] = version

output_name = f"rivals_counter_{os.environ['APP_VERSION']}"
command = (
    f'pyinstaller --onefile --windowed --name "{output_name}" '
    f'--add-data "resources;resources" '
    f'--add-data "heroes_bd.py;." '
    f'--add-data "gui.py;." '
    f'--add-data "top_panel.py;." '
    f'--add-data "right_panel.py;." '
    f'--add-data "left_panel.py;." '
    f'--add-data "dialogs.py;." '
    f'--add-data "utils_gui.py;." '
    f'--add-data "logic.py;." '
    f'--add-data "images_load.py;." '
    f'--add-data "translations.py;." '
    f'--add-data "utils.py;." '
    f'--add-data "display.py;." '
    f'--add-data "horizontal_list.py;." '
    f'--add-data "mode_manager.py;." '
    # Убедитесь, что delegate.py УДАЛЕН или закомментирован
    # f'--add-data "delegate.py;." '
    f'main.py'
)
print(f"Выполняем команду: {command}")
os.system(command)