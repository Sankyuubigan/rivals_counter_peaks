from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_metadata

# Собираем все подмодули transformers
hiddenimports = collect_submodules('transformers')
datas = collect_data_files('transformers', include_py_files=True)

# Добавляем tqdm в скрытые импорты на всякий случай (хотя это можно сделать и в build.py, но здесь тоже не повредит)
hiddenimports.append('tqdm')

# Собираем метаданные для transformers и tqdm
# Это ключевой момент для решения проблемы с PackageNotFoundError
metadatas = collect_metadata('transformers')
metadatas += collect_metadata('tqdm') # Важно добавить это!

# Для отладки можно раскомментировать
# print(f"Hook-transformers: Hidden imports: {hiddenimports}")
# print(f"Hook-transformers: Datas: {datas}")
# print(f"Hook-transformers: Metadatas: {metadatas}")