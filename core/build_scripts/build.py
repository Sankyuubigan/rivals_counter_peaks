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
script_dir = os.path.dirname(os.path.abspath(__file__)) # Папка core/build_scripts
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Корень проекта rivals_counter_peaks
dist_dir = os.path.join(project_root, 'dist') 
build_cache_dir = os.path.join(project_root, "build_cache") # PyInstaller создаст папку build здесь

# Имя .spec файла (теперь он в script_dir)
# ВАЖНО: Убедитесь, что имя файла 'rivals_counter_peaks.spec' совпадает с тем, что вы создали.
# Если вы использовали имя с версией, например 'rivals_counter_peaks_25.05.28.spec', укажите его.
spec_file_name = "rivals_counter_peaks.spec" 
spec_file_path_abs = os.path.join(script_dir, spec_file_name) 

logging.info(f"Используется .spec файл: {spec_file_path_abs}")

# --- Принудительная очистка перед сборкой ---
logging.info("Принудительная очистка перед сборкой (кроме папки dist)...")
# .spec файл больше не нужно удалять, так как мы его редактируем вручную и используем.
# Если вы хотите, чтобы build.py всегда генерировал новый .spec из параметров,
# то нужно вернуть старую логику, но тогда ручные правки в .spec будут теряться.
# Сейчас предполагается, что .spec файл уже настроен.

if os.path.exists(build_cache_dir):
    try:
        shutil.rmtree(build_cache_dir)
        logging.info(f"Удалена папка кэша PyInstaller: {build_cache_dir}")
    except Exception as e:
        logging.warning(f"Не удалось удалить папку кэша {build_cache_dir}: {e}")
else:
    logging.info(f"Папка кэша {build_cache_dir} не найдена, удаление не требуется.")

# Очистка папки dist перед новой сборкой (опционально, но рекомендуется)
if os.path.exists(dist_dir):
    logging.info(f"Очистка папки dist: {dist_dir}")
    try:
        shutil.rmtree(dist_dir)
        os.makedirs(dist_dir) # Создаем заново пустую
    except Exception as e:
        logging.warning(f"Не удалось полностью очистить папку dist: {e}")
else:
    os.makedirs(dist_dir) # Создаем, если не было

# --- Определяем путь к python.exe из текущего виртуального окружения ---
python_exe = sys.executable
if not python_exe:
    logging.error("Не удалось определить путь к исполняемому файлу Python (sys.executable пуст). Сборка невозможна.")
    sys.exit(1)
logging.info(f"Используется Python интерпретатор: {python_exe}")

# --- Формируем команду PyInstaller для запуска с .spec файлом ---
# Опции типа --onefile, --windowed, --name, datas, hiddenimports и т.д.
# теперь должны быть определены ВНУТРИ .spec файла.
# build.py просто запускает PyInstaller с этим .spec файлом.

command_parts_pyinstaller = [
    '--noconfirm', 
    # '--clean', # Можно добавить для дополнительной очистки PyInstaller'ом
    f'--distpath "{dist_dir}"', # Куда класть результат
    f'--workpath "{build_cache_dir}"', # Где PyInstaller будет хранить временные файлы сборки
    f'"{spec_file_path_abs}"' # Путь к нашему .spec файлу
]

command_full_list = [f'"{python_exe}"', '-m', 'PyInstaller'] + command_parts_pyinstaller
command = " ".join(command_full_list)

# --- Вывод информации и запуск сборки ---
print("-" * 60)
logging.info(f"Папка для результатов сборки: {dist_dir}")
logging.info(f"Выполняем команду:\n{command}")
print("-" * 60)
logging.info("Запуск PyInstaller...")
rc = 1 
try:
    # Запускаем из корня проекта, чтобы пути в .spec (если они относительные) разрешались правильно
    # Хотя мы используем абсолютный project_root в .spec, это хорошая практика.
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
         # Имя EXE теперь определяется в .spec файле
         # Можно попытаться его найти, если нужно
         # exe_name_in_spec = "rivals_counter_peaks_25.05.28.exe" # Пример
         # exe_path = os.path.join(dist_dir, exe_name_in_spec)
         # logging.info(f"Исполняемый файл должен быть создан в папке dist.")
    else:
         logging.error(f"--- PyInstaller ЗАВЕРШЕН С ОШИБКОЙ (Код: {rc}) ---")
except Exception as e:
    logging.critical(f"Критическая ошибка при запуске PyInstaller: {e}", exc_info=True)
    rc = -1

# --- Очистка временных файлов ---
# .spec файл больше не удаляем.
# build_cache_dir (workpath) PyInstaller должен удалить сам при успешной сборке,
# если не используется опция --noupx (которой у нас нет явно) или если не было ошибок.
if rc == 0:
    if os.path.exists(build_cache_dir): 
        logging.info(f"Папка {build_cache_dir} должна была быть удалена PyInstaller. Проверяем...")
        try:
            shutil.rmtree(build_cache_dir)
            logging.info(f"Принудительно удалена папка build_cache: {build_cache_dir}")
        except Exception as e:
            logging.warning(f"Не удалось принудительно удалить папку {build_cache_dir} после сборки: {e}")
else:
    logging.warning("Сборка завершилась с ошибкой, папка кэша сборки не удалена для анализа.")
    logging.warning(f"Папка кэша сборки: {build_cache_dir}")

logging.info("Скрипт сборки завершен.")
sys.exit(rc)