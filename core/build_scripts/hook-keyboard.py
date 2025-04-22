# File: build_scripts/hook-keyboard.py
from PyInstaller.utils.hooks import collect_submodules

# Собираем все подмодули библиотеки keyboard
hiddenimports = collect_submodules('keyboard')
print(f"[hook-keyboard.py] Найденные скрытые импорты для 'keyboard': {hiddenimports}")