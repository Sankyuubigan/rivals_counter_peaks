# File: build_scripts/build.py
import os
import sys
import datetime
import shutil
import subprocess
import logging
import re
from PIL import Image

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

# --- Определяем пути относительно скрипта ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
dist_dir = os.path.join(project_root, 'dist')
build_cache_dir = os.path.join(project_root, "build_cache")
spec_file_path = os.path.join(script_dir, "rivals_counter_peaks.spec")
analyzer_script_path = os.path.join(script_dir, "analyze_build.py")

# --- Пути к иконкам ---
png_icon_path = os.path.join(project_root, 'resources', 'logo.png')
ico_icon_path = os.path.join(project_root, 'resources', 'logo.ico')

def convert_png_to_ico(png_path, ico_path):
    """Конвертирует PNG в ICO, если ICO не существует или PNG новее."""
    if not os.path.exists(png_path):
        logging.error(f"PNG иконка не найдена: {png_path}")
        return False
    
    if not os.path.exists(ico_path) or os.path.getmtime(png_path) > os.path.getmtime(ico_path):
        try:
            img = Image.open(png_path)
            img.save(ico_path, format='ICO', sizes=[(256, 256)])
            logging.info(f"Иконка успешно сконвертирована: {ico_path}")
        except Exception as e:
            logging.error(f"Ошибка при конвертации иконки: {e}")
            return False
    else:
        logging.info(f"Иконка в актуальном состоянии: {ico_path}")
    return True

def update_spec_file(spec_path, app_name):
    """Обновляет имя приложения в .spec файле."""
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content, count = re.subn(r"name\s*=\s*['\"].*?['\"]", f"name='{app_name}'", content, count=1)
        
        if count > 0:
            with open(spec_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logging.info(f"Имя приложения в {os.path.basename(spec_path)} обновлено на '{app_name}'.")
        else:
            logging.warning(f"Не удалось найти и заменить 'name' в {os.path.basename(spec_path)}.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении .spec файла: {e}")

# --- Основной процесс сборки ---
if __name__ == "__main__":
    # --- Проверка на режим отчета ---
    is_report_mode = 'report' in sys.argv

    # 1. Подготовка иконки
    if not convert_png_to_ico(png_icon_path, ico_icon_path):
        sys.exit(1)

    # 2. Генерация имени с версией
    now = datetime.datetime.now()
    version_date_str = f"{now.year % 100}.{now.month:02d}.{now.day:02d}"
    app_name_with_version = f"rivals_counter_peaks_{version_date_str}"
    logging.info(f"Имя для EXE: {app_name_with_version}.exe")

    # 3. Обновление .spec файла
    if not os.path.exists(spec_file_path):
        logging.error(f".spec файл не найден: {spec_file_path}")
        sys.exit(1)
    update_spec_file(spec_file_path, app_name_with_version)

    # 4. Очистка перед сборкой
    logging.info("Очистка предыдущих сборок...")
    if os.path.exists(build_cache_dir):
        shutil.rmtree(build_cache_dir)
    # Папку dist лучше чистить вручную или с явным флагом, чтобы не потерять результаты

    # Создание подпапки для работы PyInstaller
    os.makedirs(os.path.join(build_cache_dir, app_name_with_version), exist_ok=True)

    # 4.5. Завершение работающих экземпляров приложения перед сборкой
    logging.info("Проверка и завершение работающих экземпляров 'rivals_counter_peaks_*.exe'...")
    try:
        # Используем taskkill для завершения процессов
        result = subprocess.run(
            ['taskkill', '/F', '/IM', 'rivals_counter_peaks_*.exe', '/T'],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            logging.info("Работающие экземпляры приложения успешно завершены.")
            # Выводим подробности о завершенных процессах из stderr
            if result.stderr:
                logging.info(f"Детали завершения: {result.stderr.strip()}")
        elif result.returncode == 128:  # Нет процессов для завершения
            logging.info("Нет работающих экземпляров приложения для завершения.")
        else:
            logging.warning(f"Ошибка при завершении процессов (код {result.returncode}): {result.stderr.strip()}")
    except Exception as e:
        logging.error(f"Не удалось выполнить taskkill: {e}")
        logging.error("Продолжаем сборку без завершения процессов.")

    # 5. Сборка с помощью PyInstaller
    python_exe = sys.executable
    command = [
        python_exe, '-m', 'PyInstaller', '--noconfirm',
        '--distpath', dist_dir,
        '--workpath', build_cache_dir,
        spec_file_path
    ]
    
    logging.info(f"Выполняется команда сборки:\n{' '.join(command)}")
    
    build_env = os.environ.copy()
    build_env["PROJECT_ROOT_FOR_SPEC"] = project_root
    
    try:
        result = subprocess.run(command, check=True, cwd=project_root, text=True, env=build_env)
        logging.info("--- PyInstaller УСПЕШНО завершен ---")
        exe_path = os.path.join(dist_dir, f"{app_name_with_version}.exe")
        if os.path.exists(exe_path):
            logging.info(f"Исполняемый файл готов: {exe_path}")
        else:
            logging.warning(f"Ожидаемый .exe файл не найден: {exe_path}")
        rc = 0
    except subprocess.CalledProcessError as e:
        logging.error(f"--- PyInstaller ЗАВЕРШЕН С ОШИБКОЙ (Код: {e.returncode}) ---")
        logging.error("Логи сборки смотрите выше.")
        rc = e.returncode
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске PyInstaller: {e}", exc_info=True)
        rc = -1

    # 6. Анализ сборки в режиме отчета
    if rc == 0 and is_report_mode:
        logging.info("Запуск анализатора размера сборки...")
        try:
            subprocess.run([python_exe, analyzer_script_path, build_cache_dir], check=True)
        except Exception as e:
            logging.error(f"Не удалось запустить скрипт анализа: {e}")

    # 7. Финальная очистка
    if rc == 0 and not is_report_mode and os.path.exists(build_cache_dir):
        logging.info(f"Удаление временной папки сборки: {build_cache_dir}")
        shutil.rmtree(build_cache_dir)
    elif is_report_mode:
        logging.info(f"РЕЖИМ ОТЧЕТА: Временная папка сборки сохранена для анализа: {build_cache_dir}")
    else:
        logging.warning(f"Сборка завершилась с ошибкой. Временная папка не удалена для анализа: {build_cache_dir}")

    logging.info("Скрипт сборки завершен.")
    sys.exit(rc)