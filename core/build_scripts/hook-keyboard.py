# File: core/hook-keyboard.py
# Этот файл должен лежать в той же папке, что и build.py

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Собираем все подмодули библиотеки keyboard
hiddenimports = collect_submodules('keyboard')
print(f"[Hook-Keyboard] Found hidden imports: {hiddenimports}")

# На всякий случай попробуем собрать и файлы данных (если они есть)
# datas = collect_data_files('keyboard')
# print(f"[Hook-Keyboard] Found data files: {datas}")