# File: build.py
import os
import sys
import shutil
# import importlib.util # Убираем, т.к. --paths не помог

# --- Определяем пути ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
resources_dir_abs = os.path.join(project_root, "resources") # Папка ресурсов в корне
dist_dir = os.path.join(project_root, 'dist') # Папка назначения в корне
main_script = "main.py" # Главный скрипт в папке core
# <<< ИЗМЕНЕНИЕ: Папка с хуками - это папка со скриптом build.py >>>
hooks_dir = script_dir
# ------------------------------------------------------------------

version = "4.14" # Актуальная версия
os.environ["APP_VERSION"] = version

output_name = f"rivals_counter_{os.environ['APP_VERSION']}"

# --- Формируем список данных для --add-data ---
data_to_add = [
    f'--add-data "{resources_dir_abs}{os.pathsep}resources"',
    f'--add-data "heroes_bd.py{os.pathsep}."',
    f'--add-data "gui.py{os.pathsep}."',
    f'--add-data "top_panel.py{os.pathsep}."',
    f'--add-data "right_panel.py{os.pathsep}."',
    f'--add-data "left_panel.py{os.pathsep}."',
    f'--add-data "dialogs.py{os.pathsep}."',
    f'--add-data "utils_gui.py{os.pathsep}."',
    f'--add-data "logic.py{os.pathsep}."',
    f'--add-data "images_load.py{os.pathsep}."',
    f'--add-data "translations.py{os.pathsep}."',
    f'--add-data "utils.py{os.pathsep}."',
    f'--add-data "display.py{os.pathsep}."',
    f'--add-data "horizontal_list.py{os.pathsep}."',
    f'--add-data "mode_manager.py{os.pathsep}."',
    f'--add-data "delegate.py{os.pathsep}."',
    # <<< ИЗМЕНЕНИЕ: Добавляем сам hook-файл как данные, если он лежит рядом >>>
    # Это может помочь PyInstaller его "увидеть" при запуске --onefile
    # f'--add-data "hook-keyboard.py{os.pathsep}."',
    # --------------------------------------------------------------------
]
# ---------------------------------------------

# --- Формируем команду ---
command_parts = [
    'pyinstaller',
    '--onefile',
    '--windowed',
    f'--name "{output_name}"',
    f'--distpath "{dist_dir}"',
    # <<< Указываем путь к папке с хуками (текущая директория) >>>
    f'--additional-hooks-dir "{hooks_dir}"',
    # <<< Оставляем --hidden-import как подстраховку >>>
    '--hidden-import keyboard'
]

# Добавляем данные
command_parts.extend(data_to_add)

# Добавляем главный скрипт
command_parts.append(f'"{main_script}"')

# Собираем финальную строку команды
command = " ".join(command_parts)
# -------------------------

print(f"Папка скрипта (и хуков): {script_dir}")
print(f"Корневая папка проекта: {project_root}")
print(f"Папка ресурсов (абс.): {resources_dir_abs}")
print(f"Папка назначения (dist): {dist_dir}")
print(f"Выполняем команду: {command}")

# Выполняем команду сборки
os.system(command)

# Очистка временных файлов
print("Очистка временных файлов...")
spec_file = os.path.join(script_dir, f"{output_name}.spec")
build_dir = os.path.join(script_dir, "build")

if os.path.exists(spec_file):
    try: os.remove(spec_file); print(f"Удален файл: {spec_file}")
    except Exception as e: print(f"[WARN] Не удалось удалить {spec_file}: {e}")

if os.path.exists(build_dir):
    try: shutil.rmtree(build_dir); print(f"Удалена папка: {build_dir}")
    except Exception as e: print(f"[WARN] Не удалось удалить папку {build_dir}: {e}")

print("Сборка завершена.")