# File: build_scripts/build.py
import os
import sys
import datetime
import shutil
import subprocess
import platform
import logging
import re # <--- Добавлено для работы с регулярными выражениями

# --- Настройка логирования для скрипта сборки ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s', datefmt='%H:%M:%S')

# --- Определяем пути ---
script_dir = os.path.dirname(os.path.abspath(__file__)) # Папка core/build_scripts
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Корень проекта rivals_counter_peaks
dist_dir = os.path.join(project_root, 'dist')
build_cache_dir = os.path.join(project_root, "build_cache") # PyInstaller создаст папку build здесь

# Имя .spec файла (теперь он в script_dir)
spec_file_name_base = "rivals_counter_peaks.spec" # Базовое имя .spec
spec_file_path_abs = os.path.join(script_dir, spec_file_name_base)

logging.info(f"Используется .spec файл: {spec_file_path_abs}")

# --- Генерация имени с текущей датой ---
now = datetime.datetime.now()
version_date_str = f"{str(now.year)[2:]}.{now.month:02d}.{now.day:02d}"
# Имя приложения без расширения
app_name_with_version = f"rivals_counter_peaks_{version_date_str}"
# Полное имя .exe файла
exe_name_with_version = f"{app_name_with_version}.exe"
logging.info(f"Сгенерированное имя для EXE: {exe_name_with_version}")

# --- Модификация .spec файла для установки нового имени ---
if os.path.exists(spec_file_path_abs):
    try:
        with open(spec_file_path_abs, 'r', encoding='utf-8') as f_spec_read:
            spec_content = f_spec_read.read()

        # Ищем строку name='...' и заменяем значение
        # name\s*=\s*['"]([^'"]+)['"]
        # Это регулярное выражение найдет name = '...', name="...", name= '...' и т.д.
        new_spec_content, num_replacements = re.subn(
            r"name\s*=\s*['\"]([^'\"]+)['\"]", # Шаблон для поиска
            f"name='{app_name_with_version}'",    # Строка для замены
            spec_content,                         # Содержимое файла
            count=1                               # Заменить только первое вхождение
        )

        if num_replacements > 0:
            with open(spec_file_path_abs, 'w', encoding='utf-8') as f_spec_write:
                f_spec_write.write(new_spec_content)
            logging.info(f"Файл {spec_file_name_base} успешно обновлен. Новое имя приложения: {app_name_with_version}")
        else:
            logging.warning(f"Не удалось найти строку 'name='...' в файле {spec_file_name_base} для обновления. Сборка будет использовать имя из .spec файла.")
            # В этом случае имя EXE может не соответствовать ожидаемому, если оно жестко задано в .spec

    except Exception as e_spec_mod:
        logging.error(f"Ошибка при модификации .spec файла: {e_spec_mod}. Сборка будет использовать имя из .spec файла.")
else:
    logging.error(f".spec файл {spec_file_path_abs} не найден. Сборка невозможна.")
    sys.exit(1)


# --- Принудительная очистка перед сборкой ---
logging.info("Принудительная очистка перед сборкой (кроме папки dist)...")
if os.path.exists(build_cache_dir):
    try:
        shutil.rmtree(build_cache_dir)
        logging.info(f"Удалена папка кэша PyInstaller: {build_cache_dir}")
    except Exception as e:
        logging.warning(f"Не удалось удалить папку кэша {build_cache_dir}: {e}")
else:
    logging.info(f"Папка кэша {build_cache_dir} не найдена, удаление не требуется.")

# --- Определяем путь к python.exe из текущего виртуального окружения ---
python_exe = sys.executable
if not python_exe:
    logging.error("Не удалось определить путь к исполняемому файлу Python (sys.executable пуст). Сборка невозможна.")
    sys.exit(1)
logging.info(f"Используется Python интерпретатор: {python_exe}")

# --- Формируем команду PyInstaller для запуска с .spec файлом ---
command_parts_pyinstaller = [
    '--noconfirm',
    f'--distpath "{dist_dir}"',
    f'--workpath "{build_cache_dir}"',
    # Имя приложения теперь должно браться из модифицированного .spec файла
    # Поэтому опцию --name здесь указывать не нужно, если она есть в .spec
    f'"{spec_file_path_abs}"'
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
         # Теперь имя EXE будет app_name_with_version + ".exe"
         exe_path_expected = os.path.join(dist_dir, exe_name_with_version)
         logging.info(f"Ожидаемый исполняемый файл: {exe_path_expected}")
         if os.path.exists(exe_path_expected):
             logging.info("Исполняемый файл найден.")
         else:
             # Если имя в .spec не было обновлено, PyInstaller мог использовать старое.
             # Попробуем найти любой .exe в dist_dir, если ожидаемый не найден.
             found_exes = [f for f in os.listdir(dist_dir) if f.lower().endswith(".exe")]
             if found_exes:
                 logging.warning(f"Ожидаемый файл {exe_path_expected} НЕ НАЙДЕН, но найдены другие .exe: {found_exes}. Возможно, имя в .spec не обновилось.")
             else:
                 logging.error(f"Ожидаемый файл {exe_path_expected} НЕ НАЙДEN, и других .exe в dist не найдено.")
    else:
         logging.error(f"--- PyInstaller ЗАВЕРШЕН С ОШИБКОЙ (Код: {rc}) ---")
except Exception as e:
    logging.critical(f"Критическая ошибка при запуске PyInstaller: {e}", exc_info=True)
    rc = -1

# --- Очистка временных файлов ---
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
