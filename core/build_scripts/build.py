# File: build_scripts/build.py
import os
import sys
import datetime
import shutil
import subprocess # Используем subprocess для запуска PyInstaller

# --- Определяем пути ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # На два уровня выше build_scripts
core_dir = os.path.join(project_root, "core") # Папка core
resources_dir_abs = os.path.join(project_root, "resources")
templates_dir_abs = os.path.join(resources_dir_abs, "templates")
dist_dir = os.path.join(project_root, 'dist')
main_script = os.path.join(core_dir, "main.py") # Главный скрипт в core
hooks_dir = script_dir # Хуки лежат рядом с build.py
# --- ---

# --- Версия ---
now = datetime.datetime.now()
version = f"{now.month}.{now.day}" # Формат ММ.ДД
os.environ["APP_VERSION"] = version
output_name = f"rivals_counter_{version}"
# --- ---

# --- Формируем список данных для --add-data ---
# Используем os.pathsep в качестве разделителя для PyInstaller
# Формат: "ПУТЬ_К_ИСХОДНИКУ{os.pathsep}ЦЕЛЕВАЯ_ПАПКА_В_EXE"
data_to_add = [
    # Папка resources копируется целиком в корень EXE
    f'--add-data "{resources_dir_abs}{os.pathsep}resources"',
    # Папка templates копируется внутрь resources в EXE
    # f'--add-data "{templates_dir_abs}{os.pathsep}resources/templates"', # Это уже включено предыдущей строкой

    # Добавляем файлы .py из корня проекта в корень EXE
    f'--add-data "{os.path.join(project_root, "heroes_bd.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(project_root, "delegate.py")}{os.pathsep}."', # Был перемещен? Если да, исправить путь
    f'--add-data "{os.path.join(project_root, "dialogs.py")}{os.pathsep}."', # Был перемещен?
    f'--add-data "{os.path.join(project_root, "display.py")}{os.pathsep}."', # Был перемещен?
    f'--add-data "{os.path.join(project_root, "horizontal_list.py")}{os.pathsep}."', # Был перемещен?
    f'--add-data "{os.path.join(project_root, "translations.py")}{os.pathsep}."', # Был перемещен?
    f'--add-data "{os.path.join(project_root, "utils_gui.py")}{os.pathsep}."', # Был перемещен?
]
# --- ---

# --- Формируем команду PyInstaller ---
command_parts = [
    'pyinstaller',
    '--onefile',
    '--windowed', # '--noconsole' для скрытия консоли в финальной версии
    # '--console', # '--debug=all' для отладки
    f'--name "{output_name}"',
    f'--distpath "{dist_dir}"', # Куда положить EXE
    f'--workpath "{os.path.join(project_root, "build_cache")}"', # Папка для временных файлов сборки
    f'--specpath "{project_root}"', # Куда положить .spec файл
    f'--additional-hooks-dir "{hooks_dir}"', # Путь к хукам
    # Скрытые импорты (важно для библиотек, которые PyInstaller может не найти)
    '--hidden-import keyboard',
    '--hidden-import mss',
    '--hidden-import cv2',
    '--hidden-import numpy',
    '--hidden-import pytesseract', # Добавляем pytesseract
    '--hidden-import pyautogui', # Добавляем pyautogui
    '--hidden-import pyperclip', # Добавляем pyperclip
    # Для WinAPI (может помочь, если PyInstaller не найдет сам)
    '--hidden-import ctypes',
    '--hidden-import ctypes.wintypes',
]
# Добавляем манифест для запроса прав администратора (если он нужен)
manifest_path = os.path.join(script_dir, "manifest.xml")
if os.path.exists(manifest_path):
     command_parts.append(f'--manifest "{manifest_path}"')
# Добавляем данные
command_parts.extend(data_to_add)
# Добавляем главный скрипт
command_parts.append(f'"{main_script}"')

# Собираем финальную строку команды
command = " ".join(command_parts)
# --- ---

# --- Вывод информации и запуск сборки ---
print("-" * 60)
print(f"Папка скрипта build.py (и хуков): {script_dir}")
print(f"Корневая папка проекта: {project_root}")
print(f"Папка ресурсов (абс.): {resources_dir_abs}")
print(f"Папка шаблонов (абс.): {templates_dir_abs}")
print(f"Папка назначения (dist): {dist_dir}")
print(f"Главный скрипт: {main_script}")
print("-" * 60)
print(f"Выполняем команду:\n{command}")
print("-" * 60)

# Переходим в корень проекта перед запуском PyInstaller, чтобы пути в spec-файле были корректными
# Это необязательно, если все пути абсолютные или относительно корня
# os.chdir(project_root)
# print(f"Текущая директория для PyInstaller: {os.getcwd()}")

# Запускаем PyInstaller через subprocess
print("Запуск PyInstaller...")
build_process = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')

print("--- PyInstaller STDOUT ---")
print(build_process.stdout if build_process.stdout else "Нет вывода STDOUT")
print("-" * 26)
print("--- PyInstaller STDERR ---")
print(build_process.stderr if build_process.stderr else "Нет вывода STDERR")
print("-" * 26)

if build_process.returncode == 0:
     print(f"--- PyInstaller УСПЕШНО завершен (Код: {build_process.returncode}) ---")
else:
     print(f"--- PyInstaller ЗАВЕРШЕН С ОШИБКОЙ (Код: {build_process.returncode}) ---")
# --- ---

# --- Очистка временных файлов ---
print("Очистка временных файлов...")
spec_file = os.path.join(project_root, f"{output_name}.spec")
build_dir = os.path.join(project_root, "build_cache") # Папка build теперь называется build_cache

if os.path.exists(spec_file):
    try: os.remove(spec_file); print(f"Удален файл: {spec_file}")
    except Exception as e: print(f"[WARN] Не удалось удалить {spec_file}: {e}")

if os.path.exists(build_dir):
    try: shutil.rmtree(build_dir); print(f"Удалена папка: {build_dir}")
    except Exception as e: print(f"[WARN] Не удалось удалить папку {build_dir}: {e}")
# --- ---

print("Сборка завершена.")
