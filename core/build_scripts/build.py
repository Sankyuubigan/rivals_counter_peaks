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
dist_dir = os.path.join(project_root, 'dist')
build_cache_dir = os.path.join(project_root, "build_cache")
main_script = os.path.join(core_dir, "main.py")
hooks_dir = script_dir
# --- ---

# --- Версия (только для имени файла сборки) ---
now = datetime.datetime.now()
version_for_filename = f"{now.day:02d}.{now.month:02d}.{str(now.year)[2:]}"
output_name = f"rivals_counter_{version_for_filename}"
# Удалена генерация _version.py
spec_file_path = os.path.join(project_root, f"{output_name}.spec")

logging.info(f"Имя выходного файла будет: {output_name}.exe (на основе версии {version_for_filename})")
# --- ---

# <<< --- Принудительная очистка перед сборкой --- >>>
logging.info("Принудительная очистка перед сборкой...")
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
    f'--add-data "{os.path.join(db_dir, "heroes_bd.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(db_dir, "roles_and_groups.py")}{os.pathsep}."',
    f'--add-data "{os.path.join(core_dir, "lang", "information_ru.md")}{os.pathsep}core/lang"',
    f'--add-data "{os.path.join(core_dir, "lang", "information_en.md")}{os.pathsep}core/lang"',
]
# --- ---

# --- Формируем команду PyInstaller ---
command_parts = [
    'pyinstaller', '--noconfirm', '--onefile', '--windowed',
    f'--name "{output_name}"', f'--distpath "{dist_dir}"',
    f'--workpath "{build_cache_dir}"',
    f'--specpath "{project_root}"',
    f'--additional-hooks-dir "{hooks_dir}"',
    '--hidden-import keyboard', '--hidden-import mss', '--hidden-import cv2',
    '--hidden-import numpy', '--hidden-import pyperclip', '--hidden-import ctypes',
    '--hidden-import ctypes.wintypes', '--hidden-import markdown',
    f'--paths "{core_dir}"', f'--paths "{project_root}"'
]
icon_path_ico_logo = os.path.join(project_root, "logo.ico")

if os.path.exists(icon_path_ico_logo):
    command_parts.append(f'--icon="{icon_path_ico_logo}"')
    logging.info(f"Using application icon: {icon_path_ico_logo}")
else:
    logging.warning(f"Icon file 'logo.ico' not found at project root: {project_root}")
    icon_path_ico_resources = os.path.join(resources_dir_abs, "icon.ico")
    icon_path_png_resources = os.path.join(resources_dir_abs, "icon.png")
    if os.path.exists(icon_path_ico_resources):
        command_parts.append(f'--icon="{icon_path_ico_resources}"')
        logging.info(f"Falling back to icon in resources: {icon_path_ico_resources}")
    elif os.path.exists(icon_path_png_resources):
        command_parts.append(f'--icon="{icon_path_png_resources}"')
        logging.info(f"Falling back to icon in resources: {icon_path_png_resources}")
    else:
        logging.warning(f"Fallback icon also not found in {resources_dir_abs}")

manifest_path = os.path.join(script_dir, "manifest.xml")
if platform.system() == "Windows" and os.path.exists(manifest_path): command_parts.append(f'--manifest "{manifest_path}"')
elif platform.system() == "Windows": logging.warning(f"Файл манифеста не найден: {manifest_path}.")
command_parts.extend(data_to_add); command_parts.append(f'"{main_script}"'); command = " ".join(command_parts)
# --- ---

# --- Вывод информации и запуск сборки ---
# Используем version_for_filename для отображения в логе сборки
print("-" * 60); logging.info(f"Версия для имени файла: {version_for_filename}"); logging.info(f"Имя выходного файла: {output_name}.exe");
logging.info(f"Выполняем команду:\n{command}"); print("-" * 60); logging.info("Запуск PyInstaller...")
rc = 1
try:
    build_process = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=project_root, check=False)
    print("--- PyInstaller STDOUT ---"); print(build_process.stdout or "N/A"); print("-" * 26)
    print("--- PyInstaller STDERR ---"); print(build_process.stderr or "N/A"); print("-" * 26)
    rc = build_process.returncode; print("-" * 60)
    if rc == 0:
         logging.info(f"--- PyInstaller УСПЕШНО завершен (Код: {rc}) ---")
         exe_path = os.path.join(dist_dir, output_name + '.exe')
         logging.info(f"Исполняемый файл создан в: {exe_path}")
         if not os.path.exists(exe_path): logging.error("EXE файл не найден!"); rc = -1
    else: logging.error(f"--- PyInstaller ЗАВЕРШЕН С ОШИБКОЙ (Код: {rc}) ---")
except Exception as e: logging.critical(f"Критическая ошибка при запуске PyInstaller: {e}", exc_info=True); rc = -1
# --- ---

# --- Очистка временных файлов ---
if rc == 0:
    logging.info("Очистка временных файлов после успешной сборки...")
    # Удалена очистка _version.py
    if os.path.exists(spec_file_path):
        try: os.remove(spec_file_path); logging.info(f"Удален файл spec: {spec_file_path}")
        except Exception as e: logging.warning(f"Не удалось удалить spec файл {spec_file_path} после сборки: {e}")
    if os.path.exists(build_cache_dir):
        try: shutil.rmtree(build_cache_dir); logging.info(f"Удалена папка build_cache: {build_cache_dir}")
        except Exception as e: logging.warning(f"Не удалось удалить папку {build_cache_dir} после сборки: {e}")
else:
    logging.warning("Сборка завершилась с ошибкой, временные файлы (*.spec, build_cache) не удалены для анализа.")
# --- ---
logging.info("Скрипт сборки завершен."); sys.exit(rc)