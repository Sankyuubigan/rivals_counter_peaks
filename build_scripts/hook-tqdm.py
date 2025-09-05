from PyInstaller.utils.hooks import copy_metadata

# Хук для tqdm, просто копируем метаданные.
# Это помогает transformers найти версию tqdm при запуске.
datas = []
metadatas = copy_metadata('tqdm')
hiddenimports = []