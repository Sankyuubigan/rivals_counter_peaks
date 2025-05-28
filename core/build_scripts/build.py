# File: build_scripts/build.py
import os
import sys
import datetime
import shutil
import subprocess
import platform
import logging

# --- Настройка логирования для скрипта сборки ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s', datefmt='%H:%M:%S')

# --- Определяем пути ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
core_dir = os.path.join(project_root, "core")
db_dir = os.path.join(project_root, "database")
resources_dir_abs = os.path.join(project_root, "resources")
dist_dir = os.path.join(project_root, 'dist') # Папка для результатов сборки
build_cache_dir = os.path.join(project_root, "build_cache") # Рабочая папка PyInstaller
main_script = os.path.join(core_dir, "main.py")
hooks_dir = script_dir
# --- ---

# --- Версия для имени файла сборки ---
now = datetime.datetime.now()
# ИЗМЕНЕНО: Формат версии на ГГ.ММ.ДД (год из двух цифр)
version_for_filename = f"{str(now.year)[2:]}.{now.month:02d}.{now.day:02d}"
# Имя выходного файла будет "rivals_counter_peaks_ГГ.ММ.ДД"
output_name = f"rivals_counter_peaks_{version_for_filename}"
spec_file_path = os.path.join(project_root, f"{output_name}.spec") # .spec файл будет в корне проекта

logging.info(f"Имя выходного файла будет: {output_name}.exe (на основе версии {version_for_filename})")
# --- ---


# <<< --- Принудительная очистка перед сборкой (КРОМЕ ПАПКИ DIST) --- >>>
logging.info("Принудительная очистка перед сборкой (кроме папки dist)...")
if os.path.exists(spec_file_path):
    try:
        os.remove(spec_file_path)
        logging.info(f"Удален старый spec файл: {spec_file_path}")
    except Exception as e:
        logging.warning(f"Не удалось удалить старый spec файл {spec_file_path}: {e}")
if os.path.exists(build_cache_dir):
    try:
        shutil.rmtree(build_cache_dir)
        logging.info(f"Удалена папка кэша: {build_cache_dir}")
    except Exception as e:
        logging.warning(f"Не удалось удалить папку кэша {build_cache_dir}: {e}")
# <<< --- КОНЕЦ ОЧИСТКИ --- >>>

# --- Формируем список данных ---
data_to_add = [
    f'--add-data "{resources_dir_abs}{os.pathsep}resources"',
    f'--add-data "{os.path.join(db_dir, "heroes_bd.py")}{os.pathsep}database"',
    f'--add-data "{os.path.join(db_dir, "roles_and_groups.py")}{os.pathsep}database"',
    f'--add-data "{os.path.join(core_dir, "lang", "information_ru.md")}{os.pathsep}core/lang"',
    f'--add-data "{os.path.join(core_dir, "lang", "information_en.md")}{os.pathsep}core/lang"',
    f'--add-data "{os.path.join(core_dir, "lang", "author_ru.md")}{os.pathsep}core/lang"',
    f'--add-data "{os.path.join(core_dir, "lang", "author_en.md")}{os.pathsep}core/lang"',
]
# --- ---

# --- Определяем путь к python.exe из текущего виртуального окружения ---
python_exe = sys.executable
if not python_exe:
    logging.error("Не удалось определить путь к исполняемому файлу Python (sys.executable пуст). Сборка невозможна.")
    sys.exit(1)
logging.info(f"Используется Python интерпретатор: {python_exe}")
# --- ---

# --- Формируем команду PyInstaller ---
command_parts_pyinstaller_options = [
    '--noconfirm', '--onefile', '--windowed', '--log-level=INFO',
    f'--name "{output_name}"', # Используем output_name, который содержит версию
    f'--distpath "{dist_dir}"', 
    f'--workpath "{build_cache_dir}"',
    f'--specpath "{project_root}"',
    f'--additional-hooks-dir "{hooks_dir}"',
    '--hidden-import pynput', '--hidden-import mss', '--hidden-import cv2',
    '--hidden-import numpy', '--hidden-import pyperclip', '--hidden-import ctypes',
    '--hidden-import markdown',
    f'--paths "{core_dir}"',
    f'--paths "{project_root}"'
]
icon_path_ico_logo = os.path.join(project_root, "logo.ico")

if os.path.exists(icon_path_ico_logo):
    command_parts_pyinstaller_options.append(f'--icon="{icon_path_ico_logo}"')
    logging.info(f"Using application icon: {icon_path_ico_logo}")
else:
    logging.warning(f"Icon file 'logo.ico' not found at project root: {project_root}")

manifest_path = os.path.join(script_dir, "manifest.xml")
if platform.system() == "Windows" and os.path.exists(manifest_path):
    command_parts_pyinstaller_options.append(f'--manifest "{manifest_path}"')
elif platform.system() == "Windows":
    logging.warning(f"Файл манифеста не найден: {manifest_path}.")

command_parts_pyinstaller_options.extend(data_to_add)
command_parts_pyinstaller_options.append(f'"{main_script}"')

command_full_list = [f'"{python_exe}"', '-m', 'PyInstaller'] + command_parts_pyinstaller_options
command = " ".join(command_full_list)
# --- ---

# --- Вывод информации и запуск сборки ---
print("-" * 60)
logging.info(f"Версия для имени файла: {version_for_filename}")
logging.info(f"Имя выходного файла: {output_name}.exe") # output_name содержит версию
logging.info(f"Папка для результатов сборки: {dist_dir}")
logging.info(f"Выполняем команду:\n{command}")
print("-" * 60)
logging.info("Запуск PyInstaller...")
rc = 1
try:
    build_process = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=project_root, check=False)
    
    print("--- PyInstaller STDOUT ---")
    print(build_process.stdout or "STDOUT: (empty)")
    print("-" * 26)
    print("--- PyInstaller STDERR ---")
    print(build_process.stderr or "STDERR: (empty)")
    print("-" * 26)
    
    rc = build_process.returncode
    print("-" * 60)
    if rc == 0:
         logging.info(f"--- PyInstaller УСПЕШНО завершен (Код: {rc}) ---")
         exe_path = os.path.join(dist_dir, output_name + '.exe') # output_name содержит версию
         logging.info(f"Исполняемый файл должен быть создан в: {exe_path}")
         if not os.path.exists(exe_path):
             logging.error(f"ОШИБКА: EXE файл не найден по пути {exe_path} после успешной сборки!")
             rc = -1 
    else:
         logging.error(f"--- PyInstaller ЗАВЕРШЕН С ОШИБКОЙ (Код: {rc}) ---")
except Exception as e:
    logging.critical(f"Критическая ошибка при запуске PyInstaller: {e}", exc_info=True)
    rc = -1
# --- ---

# --- Очистка временных файлов (КРОМЕ ПАПКИ DIST) ---
if rc == 0:
    logging.info("Очистка временных файлов после успешной сборки (кроме папки dist)...")
    if os.path.exists(spec_file_path): # spec_file_path также будет с версией в имени
        try:
            os.remove(spec_file_path)
            logging.info(f"Удален файл spec: {spec_file_path}")
        except Exception as e:
            logging.warning(f"Не удалось удалить spec файл {spec_file_path} после сборки: {e}")
    if os.path.exists(build_cache_dir): 
        logging.info(f"Папка {build_cache_dir} должна была быть удалена PyInstaller. Проверяем...")
        if os.path.exists(build_cache_dir): 
            try:
                shutil.rmtree(build_cache_dir)
                logging.info(f"Принудительно удалена папка build_cache: {build_cache_dir}")
            except Exception as e:
                logging.warning(f"Не удалось принудительно удалить папку {build_cache_dir} после сборки: {e}")
else:
    logging.warning("Сборка завершилась с ошибкой, временные файлы (*.spec, build_cache) не удалены для анализа.")
    logging.warning(f"Spec файл: {spec_file_path}")
    logging.warning(f"Папка кэша сборки: {build_cache_dir}")
# --- ---
logging.info("Скрипт сборки завершен.")
sys.exit(rc)
