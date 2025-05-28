from PyInstaller.utils.hooks import collect_submodules, copy_metadata
import os
import logging

hiddenimports = []
# datas = [] # datas теперь в основном управляются через .spec
metadatas = []

logging.info("Hook-transformers (фокус на подмодулях): Начало работы хука.")

try:
    # 1. Собираем подмодули transformers, включая все из models
    try:
        # Основные подмодули transformers
        tf_hiddenimports_base = collect_submodules('transformers')
        if tf_hiddenimports_base:
            hiddenimports.extend(tf_hiddenimports_base)
        
        # Явно собираем все подмодули из transformers.models
        # Это может быть избыточно, если collect_submodules('transformers') уже все покрыл,
        # но для ошибки KeyError: frozenset() стоит попробовать.
        tf_models_hiddenimports = collect_submodules('transformers.models')
        if tf_models_hiddenimports:
            for h_import in tf_models_hiddenimports:
                if h_import not in hiddenimports: # Добавляем, только если еще нет
                    hiddenimports.append(h_import)
        
        # Убедимся, что ключевые подпакеты точно есть
        for sub_pkg in ['transformers.models', 'transformers.pipelines', 'transformers.tokenization_utils_base', 'transformers.utils']:
            if sub_pkg not in hiddenimports:
                hiddenimports.append(sub_pkg)
        logging.info(f"Hook-transformers: Hiddenimports после сбора: {hiddenimports}")
    except Exception as e:
        logging.error(f"Hook-transformers: Ошибка при сборе подмодулей: {e}")

    # 2. Файлы данных: основной файл transformers/models/__init__.py добавляется через .spec
    # Другие необходимые файлы данных для transformers должны подхватываться через datas в .spec
    # или, если это специфичные файлы моделей, они должны быть в nn_models и добавляться через .spec

    # 3. Собираем стандартные метаданные transformers
    try:
        tf_metadatas = copy_metadata('transformers')
        if tf_metadatas:
            metadatas.extend(tf_metadatas)
        logging.info(f"Hook-transformers: Собрано метаданных: {len(tf_metadatas)}")
    except Exception as e:
        logging.error(f"Hook-transformers: Ошибка при сборе метаданных transformers: {e}")

    # 4. Обработка .dist-info для transformers остается в .spec файле.

    if 'tqdm' not in hiddenimports: # tqdm обрабатывается своим хуком или .spec файлом
        hiddenimports.append('tqdm')

except Exception as e_main_hook:
    logging.error(f"Hook-transformers: Глобальная ошибка в хуке: {e_main_hook}", exc_info=True)

logging.info(f"Hook-transformers: Итоговые hiddenimports: {hiddenimports}")
logging.info(f"Hook-transformers: Завершение работы хука.")