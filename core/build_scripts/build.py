# File: build.py
import os
import sys
import datetime
import shutil
# import importlib.util # Убираем, т.к. --paths не помог

# --- Определяем пути ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
resources_dir_abs = os.path.join(project_root, "resources") # Папка ресурсов в корне
# <<< ДОБАВЛЕНО: Путь к папке шаблонов >>>
templates_dir_abs = os.path.join(resources_dir_abs, "templates")
# <<< ---------------------------------- >>>
dist_dir = os.path.join(project_root, 'dist') # Папка назначения в корне
main_script = os.path.join(project_root, "main.py") # Главный скрипт в КОРНЕ проекта
# <<< ИЗМЕНЕНИЕ: Папка с хуками - это папка со скриптом build.py >>>
hooks_dir = script_dir
# ------------------------------------------------------------------

now = datetime.datetime.now()
version = f"{now.month}.{now.day}"

os.environ["APP_VERSION"] = version

output_name = f"rivals_counter_{os.environ['APP_VERSION']}"

# --- Формируем список данных для --add-data ---
# Используем os.pathsep в качестве разделителя для --add-data
data_to_add = [
    f'--add-data "{resources_dir_abs}{os.pathsep}resources"',
    # <<< ДОБАВЛЕНО: Добавляем папку с шаблонами >>>
    f'--add-data "{templates_dir_abs}{os.pathsep}resources/templates"',
    # <<< --------------------------------------- >>>
    # Добавляем файлы из корня проекта, указывая путь к ним относительно build.py
    # и целевую папку '.' в собранном приложении
    f'--add-data "{os.path.join(project_root, "heroes_bd.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "gui.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "top_panel.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "right_panel.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "left_panel.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "dialogs.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "utils_gui.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "logic.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "images_load.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "translations.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "utils.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "display.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "horizontal_list.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "mode_manager.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "delegate.py")}{os.pathsep}."',
]
# ---------------------------------------------

# --- Формируем команду ---
command_parts = [
    'pyinstaller',
    '--onefile',
    '--windowed',
    f'--name "{output_name}"',
    f'--distpath "{dist_dir}"',
    # <<< Указываем путь к папке с хуками (текущая директория build.py) >>>
    f'--additional-hooks-dir "{hooks_dir}"',
    # <<< Оставляем --hidden-import как подстраховку >>>
    '--hidden-import keyboard',
    # <<< ДОБАВЛЕНО: Скрытые импорты для новых библиотек >>>
    '--hidden-import mss',
    '--hidden-import cv2',
    '--hidden-import numpy',
    # <<< Для WinAPI (на всякий случай, если PyInstaller не найдет сам) >>>
    '--hidden-import ctypes',
    '--hidden-import ctypes.wintypes'
    # <<< ----------------------------------------------- >>>
]

# Добавляем данные
command_parts.extend(data_to_add)

# Добавляем главный скрипт (путь к нему из корня)
command_parts.append(f'"{main_script}"')

# Собираем финальную строку команды
command = " ".join(command_parts)
# -------------------------

print(f"Папка скрипта build.py (и хуков): {script_dir}")
print(f"Корневая папка проекта: {project_root}")
print(f"Папка ресурсов (абс.): {resources_dir_abs}")
print(f"Папка шаблонов (абс.): {templates_dir_abs}")
print(f"Папка назначения (dist): {dist_dir}")
print(f"Выполняем команду: {command}")

# Выполняем команду сборки
# Используем sys.executable для гарантии вызова нужного python/pyinstaller
# >>> ВАЖНО: Запускать сборку нужно находясь в директории build_scripts <<<
# Перейти в build_scripts: cd path/to/build_scripts
# Запустить: python build.py
os.chdir(project_root) # Переходим в корень проекта перед запуском PyInstaller
print(f"Текущая директория для PyInstaller: {os.getcwd()}")
build_process = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
print("--- PyInstaller STDOUT ---")
print(build_process.stdout)
print("--- PyInstaller STDERR ---")
print(build_process.stderr)
print("--- PyInstaller Завершен ---")


# Очистка временных файлов (ищем их относительно project_root)
print("Очистка временных файлов...")
spec_file = os.path.join(project_root, f"{output_name}.spec")
build_dir = os.path.join(project_root, "build") # Папка build создается в корне

if os.path.exists(spec_file):
    try: os.remove(spec_file); print(f"Удален файл: {spec_file}")
    except Exception as e: print(f"[WARN] Не удалось удалить {spec_file}: {e}")

if os.path.exists(build_dir):
    try: shutil.rmtree(build_dir); print(f"Удалена папка: {build_dir}")
    except Exception as e: print(f"[WARN] Не удалось удалить папку {build_dir}: {e}")

print("Сборка завершена.")