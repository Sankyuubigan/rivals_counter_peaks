from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# Хук для transformers
# Включаем все подмодули и метаданные.
hiddenimports = collect_submodules('transformers')
metadatas = copy_metadata('transformers')
datas = []