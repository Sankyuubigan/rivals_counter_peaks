# File: build_scripts/build.py
import os
import sys
import datetime
import shutil
import subprocess
import platform

# --- Определяем пути ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Корень проекта
core_dir = os.path.join(project_root, "core") # Папка core
resources_dir_abs = os.path.join(project_root, "resources")
templates_dir_abs = os.path.join(resources_dir_abs, "templates")
dist_dir = os.path.join(project_root, 'dist')
main_script = os.path.join(core_dir, "main.py") # Главный скрипт в core
hooks_dir = script_dir # Хуки рядом с build.py
# --- ---

# --- Версия ---
now = datetime.datetime.now()
# <<< ИЗМЕНЕНО: Формат версии М.Д >>>
version = f"{now.month}.{now.day}"
# <<< ------------------------ >>>
os.environ["APP_VERSION"] = version # Устанавливаем переменную окружения
output_name = f"rivals_counter_{version}"
# --- ---

# --- Формируем список данных для --add-data ---
# Формат: "ПУТЬ_К_ИСХОДНИКУ{os.pathsep}ЦЕЛЕВАЯ_ПАПКА_В_EXE"
# os.pathsep - это ';' для Windows, ':' для Linux/macOS
# Целевая папка '.' означает корень внутри EXE.
data_to_add = [
    # Папка resources копируется целиком в корень EXE -> resources
    # Убедимся, что используется правильный разделитель путей для PyInstaller
    f'--add-data "{resources_dir_abs}{os.pathsep}resources"',

    # Добавляем .py файлы из корня проекта в корень EXE
    # Важно: эти файлы НЕ должны быть в `core`, иначе PyInstaller может их неправильно обработать
    f'--add-data "{os.path.join(project_root, "heroes_bd.py")}{os.pathsep}."',
    # Остальные .py файлы теперь в core и будут включены автоматически через --paths
]
# --- ---

# --- Формируем команду PyInstaller ---
command_parts = [
    'pyinstaller',
    '--noconfirm', # Не спрашивать подтверждение перезаписи
    '--onefile',   # Создать один .exe файл
    '--windowed',  # Приложение без консоли
    f'--name "{output_name}"', # Имя выходного файла
    f'--distpath "{dist_dir}"', # Папка для .exe
    f'--workpath "{os.path.join(project_root, "build_cache")}"', # Папка для временных файлов сборки
    f'--specpath "{project_root}"', # Папка для .spec файла
    f'--additional-hooks-dir "{hooks_dir}"', # Папка с пользовательскими хуками
    # Иконка приложения
    f'--icon="{os.path.join(resources_dir_abs, "icon.ico")}"', # Путь к иконке .ico

    # Скрытые импорты (модули, которые PyInstaller может не найти автоматически)
    '--hidden-import keyboard',
    '--hidden-import mss',
    '--hidden-import cv2',
    '--hidden-import numpy',
    # '--hidden-import pytesseract', # Раскомментировать, если используется Tesseract OCR
    # '--hidden-import pyautogui',   # Раскомментировать, если используется
    '--hidden-import pyperclip',   # Для работы с буфером обмена
    '--hidden-import ctypes',      # Для WinAPI
    '--hidden-import ctypes.wintypes', # Для WinAPI

    # Добавляем 'core' как путь для поиска модулей PyInstaller'ом
    # Это должно помочь ему найти модули внутри core при использовании абсолютных импортов
    f'--paths "{core_dir}"',
    # Добавляем корень проекта тоже, на всякий случай
    f'--paths "{project_root}"'
]

# Добавляем манифест для Windows (управляет правами доступа, стилями и т.д.)
manifest_path = os.path.join(script_dir, "manifest.xml")
if platform.system() == "Windows" and os.path.exists(manifest_path):
     command_parts.append(f'--manifest "{manifest_path}"')
     print(f"Using manifest: {manifest_path}")
elif platform.system() == "Windows":
     print(f"[WARN] Manifest file not found at: {manifest_path}. Admin rights prompt may not appear correctly.")


# Добавляем данные (--add-data)
command_parts.extend(data_to_add)

# Добавляем главный скрипт
command_parts.append(f'"{main_script}"')

# Собираем команду в строку
command = " ".join(command_parts)
# --- ---

# --- Вывод информации и запуск сборки ---
print("-" * 60)
print(f"Папка скрипта build.py (и хуков): {script_dir}")
print(f"Корневая папка проекта: {project_root}")
print(f"Папка core: {core_dir}")
print(f"Папка ресурсов (абс.): {resources_dir_abs}")
print(f"Папка шаблонов (абс.): {templates_dir_abs}")
print(f"Папка назначения (dist): {dist_dir}")
print(f"Главный скрипт: {main_script}")
print(f"Версия приложения: {version}")
print(f"Имя выходного файла: {output_name}.exe")
print(f"Используемая иконка: {os.path.join(resources_dir_abs, 'icon.ico')}")
print(f"Используемый манифест: {manifest_path if platform.system() == 'Windows' and os.path.exists(manifest_path) else 'N/A'}")
print("-" * 60)
print(f"Выполняем команду:\n{command}")
print("-" * 60)

print("Запуск PyInstaller...")
# Запускаем из корня проекта для корректной работы путей в spec и --add-data
rc = 1 # По умолчанию - ошибка
try:
    # Используем subprocess.run для простоты, т.к. потоковый вывод уже есть
    build_process = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=project_root, check=False) # check=False чтобы не выбрасывать исключение при ошибке

    # Выводим stdout и stderr
    print("--- PyInstaller STDOUT ---")
    print(build_process.stdout if build_process.stdout else "Нет вывода STDOUT")
    print("-" * 26)
    print("--- PyInstaller STDERR ---")
    print(build_process.stderr if build_process.stderr else "Нет вывода STDERR")
    print("-" * 26)

    rc = build_process.returncode # Получаем код возврата

    print("-" * 60)
    if rc == 0:
         print(f"--- PyInstaller УСПЕШНО завершен (Код: {rc}) ---")
         exe_path = os.path.join(dist_dir, output_name + '.exe')
         print(f"Исполняемый файл создан в: {exe_path}")
         if not os.path.exists(exe_path):
              print("[ERROR] Исполняемый файл не найден после успешной сборки!")
              rc = -1 # Устанавливаем код ошибки
    else:
         print(f"--- PyInstaller ЗАВЕРШЕН С ОШИБКОЙ (Код: {rc}) ---")
         print("Проверьте лог выше на наличие ошибок.")

except Exception as e:
    print(f"Критическая ошибка при запуске PyInstaller: {e}")
    import traceback
    traceback.print_exc()
    rc = -1 # Устанавливаем код ошибки
# --- ---

# --- Очистка временных файлов ---
# Очищаем только если сборка прошла успешно (или если нужно принудительно)
force_clean = False # Поставить True для очистки даже при ошибке
if rc == 0 or force_clean:
    print("Очистка временных файлов...")
    spec_file = os.path.join(project_root, f"{output_name}.spec")
    build_dir = os.path.join(project_root, "build_cache") # Используем build_cache

    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"Удален файл: {spec_file}")
        except Exception as e:
            print(f"[WARN] Не удалось удалить {spec_file}: {e}")

    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir)
            print(f"Удалена папка: {build_dir}")
        except Exception as e:
            print(f"[WARN] Не удалось удалить папку {build_dir}: {e}")
else:
    print("Сборка завершилась с ошибкой, временные файлы не удалены для анализа.")
# --- ---

print("Сборка завершена.")
sys.exit(rc) # Возвращаем код ошибки PyInstaller
