from PyInstaller.utils.hooks import copy_metadata, get_package_paths
import os
import logging # Используем logging для вывода информации

# Инициализируем переменные для данных и метаданных
datas = []
metadatas = []
hiddenimports = [] # tqdm обычно не требует скрытых импортов, но на всякий случай

# 1. Собираем стандартные метаданные
# copy_metadata вернет список кортежей (имя_файла_метаданных, None, 'PKG-INFO')
# или пустой список, если метаданные не найдены
try:
    tqdm_metadatas = copy_metadata('tqdm')
    if tqdm_metadatas:
        metadatas.extend(tqdm_metadatas)
        logging.info(f"Hook-tqdm: Успешно собраны метаданные через copy_metadata: {tqdm_metadatas}")
    else:
        logging.warning("Hook-tqdm: copy_metadata('tqdm') не вернул метаданных.")
except Exception as e:
    logging.error(f"Hook-tqdm: Ошибка при вызове copy_metadata('tqdm'): {e}")


# 2. Явно копируем всю папку .dist-info
# Это самый надёжный способ убедиться, что все метаданные на месте.
# PyInstaller должен поместить эту папку в корень сборки.
try:
    # get_package_paths возвращает (путь_к_пакету, путь_к_dist_info)
    pkg_base_path, pkg_dist_info_path = get_package_paths('tqdm')
    
    if pkg_dist_info_path and os.path.isdir(pkg_dist_info_path):
        # Имя папки .dist-info (например, "tqdm-4.66.1.dist-info")
        dist_info_dir_name = os.path.basename(pkg_dist_info_path)
        
        # Мы хотим, чтобы папка <tqdm.dist-info> была в корне сборки.
        # PyInstaller копирует содержимое источника в папку назначения.
        # (source_path, destination_in_bundle_relative_to_root)
        # Если destination_in_bundle_relative_to_root это '.', то папка-источник копируется в корень.
        datas.append((pkg_dist_info_path, '.')) 
        logging.info(f"Hook-tqdm: Папка {pkg_dist_info_path} будет скопирована в корень сборки как {dist_info_dir_name}.")
    else:
        logging.warning(f"Hook-tqdm: Не удалось найти папку .dist-info для tqdm. Путь: {pkg_dist_info_path}")
except ImportError:
    logging.warning("Hook-tqdm: Пакет tqdm не найден через get_package_paths. Возможно, он не установлен.")
except Exception as e:
    logging.error(f"Hook-tqdm: Ошибка при явном добавлении папки .dist-info для tqdm: {e}")

# Логирование для отладки (будет видно в DEBUG логе PyInstaller)
logging.debug(f"Hook-tqdm: Итоговые hiddenimports: {hiddenimports}")
logging.debug(f"Hook-tqdm: Итоговые datas: {datas}")
logging.debug(f"Hook-tqdm: Итоговые metadatas: {metadatas}")