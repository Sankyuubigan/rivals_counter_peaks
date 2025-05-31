# compare_embeddings.py
import os
import sys # Добавляем sys для манипуляций с путем
import numpy as np
import logging
from pathlib import Path
from collections import defaultdict

# --- Настройка sys.path для корректного импорта ---
# Определяем корень проекта (на три уровня выше текущего скрипта)
# core/build_scripts/compare_embeddings.py -> core/build_scripts -> core -> project_root
SCRIPT_FILE_PATH_COMPARE = Path(__file__).resolve()
PROJECT_ROOT_COMPARE = SCRIPT_FILE_PATH_COMPARE.parent.parent.parent

# Добавляем корень проекта в sys.path, если его там еще нет
if str(PROJECT_ROOT_COMPARE) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_COMPARE))

# Добавляем папку core/build_scripts в sys.path для импорта create_embeddings
BUILD_SCRIPTS_DIR = SCRIPT_FILE_PATH_COMPARE.parent
if str(BUILD_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(BUILD_SCRIPTS_DIR))
# ----------------------------------------------------

# Импортируем main функцию из create_embeddings
try:
    from create_embeddings import main as create_embeddings_main
    CAN_CREATE_EMBEDDINGS = True
except ImportError as e:
    logging.error(f"Не удалось импортировать create_embeddings: {e}. Пересоздание эмбеддингов будет пропущено.")
    CAN_CREATE_EMBEDDINGS = False
# ----------------------------------------------------


# --- Настройка скрипта сравнения ---
EMBEDDINGS_DIR_REL_TO_ROOT = "resources/embeddings_padded"
SIMILARITY_CONFLICT_THRESHOLD = 0.70 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cosine_similarity(vec_a, vec_b):
    if vec_a is None or vec_b is None:
        return 0.0
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def load_embedding(filename_no_ext, base_dir):
    file_path = Path(base_dir) / f"{filename_no_ext}.npy"
    if not file_path.exists():
        logging.error(f"Файл эмбеддинга не найден: {file_path}")
        return None
    try:
        embedding = np.load(file_path)
        if embedding is None or embedding.size == 0:
            logging.error(f"Загружен пустой эмбеддинг из файла: {file_path}")
            return None
        if np.isnan(embedding).any() or np.isinf(embedding).any():
            logging.error(f"Эмбеддинг из файла {file_path} содержит NaN или Inf значения.")
            return None
        return embedding
    except Exception as e:
        logging.error(f"Ошибка загрузки эмбеддинга {file_path}: {e}")
        return None

def main():
    logging.info(f"Определен корень проекта для compare_embeddings: {PROJECT_ROOT_COMPARE}")

    # --- Шаг 1: Пересоздание эмбеддингов ---
    if CAN_CREATE_EMBEDDINGS:
        logging.info("="*50)
        logging.info("НАЧАЛО: Автоматическое пересоздание эмбеддингов...")
        logging.info("="*50)
        try:
            # Важно: create_embeddings.py должен быть написан так, чтобы
            # его функция main() корректно работала при вызове из другого скрипта.
            # В частности, пути внутри create_embeddings.py должны быть абсолютными
            # или корректно вычисляться относительно PROJECT_ROOT, который мы настроили.
            # Наш create_embeddings.py уже использует PROJECT_ROOT.
            
            # Перед вызовом create_embeddings_main, нужно убедиться, что sys.path для него
            # тоже корректен, если он импортирует что-то из core.
            # Это уже сделано выше при настройке sys.path для PROJECT_ROOT_COMPARE.
            
            create_embeddings_main() # Вызываем импортированную функцию
            logging.info("="*50)
            logging.info("ЗАВЕРШЕНО: Автоматическое пересоздание эмбеддингов.")
            logging.info("="*50)
        except Exception as e_create:
            logging.error(f"Ошибка во время автоматического пересоздания эмбеддингов: {e_create}", exc_info=True)
            logging.error("Сравнение будет проводиться на СТАРЫХ эмбеддингах (если они есть).")
    else:
        logging.warning("Пересоздание эмбеддингов пропущено из-за ошибки импорта.")
    # -----------------------------------------

    embeddings_base_path = PROJECT_ROOT_COMPARE / EMBEDDINGS_DIR_REL_TO_ROOT

    if not embeddings_base_path.is_dir():
        logging.error(f"Директория с эмбеддингами не найдена: {embeddings_base_path}")
        return

    logging.info(f"\n--- Анализ попарных сходств всех эталонных эмбеддингов ---")
    logging.info(f"--- Порог для определения 'конфликтного' сходства: {SIMILARITY_CONFLICT_THRESHOLD:.2f} ({(SIMILARITY_CONFLICT_THRESHOLD*100):.0f}%) ---")
    
    all_embedding_files = [f.stem for f in embeddings_base_path.glob('*.npy')]
    if not all_embedding_files:
        logging.warning(f"В директории {embeddings_base_path} не найдено файлов .npy")
        return

    loaded_embeddings = {}
    for hero_file in all_embedding_files:
        emb = load_embedding(hero_file, embeddings_base_path)
        if emb is not None:
            loaded_embeddings[hero_file] = emb
        else:
            logging.warning(f"Пропуск героя {hero_file} из-за ошибки загрузки эмбеддинга.")
    
    if len(loaded_embeddings) < 2:
        logging.info("Недостаточно эмбеддингов для сравнения (нужно хотя бы 2).")
        return

    hero_conflict_scores = defaultdict(lambda: {"count": 0, "conflicts_with": []})
    hero_names = list(loaded_embeddings.keys())

    for i in range(len(hero_names)):
        hero_a_name = hero_names[i]
        embedding_a = loaded_embeddings[hero_a_name]
        for j in range(i + 1, len(hero_names)):
            hero_b_name = hero_names[j]
            embedding_b = loaded_embeddings[hero_b_name]
            similarity = cosine_similarity(embedding_a, embedding_b)
            if similarity > 0.60: # Оставляем детальное логирование для умеренно высоких схожестей
                 logging.debug(f"Сходство между '{hero_a_name}' и '{hero_b_name}': {similarity:.4f} ({(similarity*100):.2f}%)")
            if similarity >= SIMILARITY_CONFLICT_THRESHOLD:
                hero_conflict_scores[hero_a_name]["count"] += 1
                hero_conflict_scores[hero_a_name]["conflicts_with"].append(f"{hero_b_name} ({(similarity*100):.1f}%)")
                hero_conflict_scores[hero_b_name]["count"] += 1
                hero_conflict_scores[hero_b_name]["conflicts_with"].append(f"{hero_a_name} ({(similarity*100):.1f}%)")

    sorted_problematic_heroes = sorted(
        hero_conflict_scores.items(),
        key=lambda item: item[1]["count"],
        reverse=True
    )

    logging.info(f"\n--- Рейтинг 'проблемных' героев (с наибольшим количеством схожестей > {SIMILARITY_CONFLICT_THRESHOLD*100:.0f}% с ДРУГИМИ героями) ---")
    if not sorted_problematic_heroes:
        logging.info("Не найдено героев, превышающих порог конфликтного сходства с другими.")
    else:
        for hero_name, data in sorted_problematic_heroes:
            if data["count"] > 0:
                logging.info(f"Герой: {hero_name}, Конфликтных схожестей: {data['count']}")
                # for conflict in data["conflicts_with"]:
                #     logging.info(f"  - Схож с: {conflict}")
            # else:
            #     logging.info(f"Герой: {hero_name}, Конфликтных схожестей: 0")
    logging.info("--- Анализ завершен ---")

if __name__ == "__main__":
    main()