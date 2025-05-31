import os
import sys # <--- Добавлено
import numpy as np
from PIL import Image, ImageOps 
import onnxruntime
from huggingface_hub import hf_hub_download
from transformers import AutoImageProcessor
import logging

# --- Начало блока для настройки sys.path ---
# Определяем корень проекта (на два уровня выше текущего скрипта)
# core/build_scripts/create_embeddings.py -> core/ -> project_root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

# Добавляем корень проекта в sys.path, если его там еще нет
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --- Конец блока для настройки sys.path ---

# --- Добавляем импорт функции предобработки ---
# Теперь Python должен найти 'core'
from core.image_processing_utils import preprocess_image_for_dino
# ---------------------------------------------

# --- Конфигурация ---
NN_MODELS_DIR = "nn_models" 
INPUT_IMAGES_DIR = "resources/templates" 
EMBEDDINGS_DIR_OUT = "resources/embeddings_padded" 

ONNX_MODEL_REPO_ID = "onnx-community/dinov2-small-ONNX"
ONNX_MODEL_FILENAME = "onnx/model.onnx" 

IMAGE_PROCESSOR_ID = "facebook/dinov2-small"
ONNX_PROVIDERS = ['CPUExecutionProvider']
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')


def ensure_dir_exists(dir_path: str) -> bool:
    if not os.path.exists(dir_path):
        logging.info(f"Директория {dir_path} не существует. Попытка создать...")
        try:
            os.makedirs(dir_path, exist_ok=True) 
            logging.info(f"Создана директория: {dir_path}")
            return True
        except OSError as e:
            logging.error(f"Ошибка при создании директории {dir_path}: {e}")
            return False
    elif not os.path.isdir(dir_path):
        logging.error(f"Путь {dir_path} существует, но не является директорией.")
        return False
    return True


def download_model_if_needed(repo_id, filename, target_dir_abs): 
    model_path_abs = os.path.join(target_dir_abs, filename)
    model_subdir_abs = os.path.dirname(model_path_abs)
    if not ensure_dir_exists(model_subdir_abs):
        logging.error(f"Не удалось создать/подтвердить директорию для модели: {model_subdir_abs}")
        return None

    if not os.path.exists(model_path_abs):
        logging.info(f"Скачивание модели {filename} из {repo_id} в {model_subdir_abs}...")
        try:
            hf_hub_download(repo_id=repo_id, filename=filename, local_dir=target_dir_abs, local_dir_use_symlinks=False)
            logging.info(f"Модель успешно скачана в: {model_path_abs}")
        except Exception as e: 
            logging.error(f"Ошибка при скачивании модели: {e}")
            return None
    else:
        logging.info(f"Модель уже существует: {model_path_abs}")
    return model_path_abs

def pad_image_to_target_size(image_pil, target_height, target_width, padding_color=(0,0,0)):
    if image_pil is None: 
        logging.warning("pad_image_to_target_size получило None изображение.")
        return Image.new("RGB", (target_width, target_height), padding_color) 

    original_width, original_height = image_pil.size
    if original_width == target_width and original_height == target_height:
        return image_pil
    
    target_aspect = 1.0 
    if target_height != 0:
        target_aspect = target_width / target_height
    
    original_aspect = 0.0 
    if original_height != 0:
        original_aspect = original_width / original_height

    new_width = 0
    new_height = 0

    if original_aspect > target_aspect: 
        if original_aspect != 0: 
            new_width = target_width
            new_height = int(new_width / original_aspect)
        else: 
            new_width = target_width
            new_height = 0 
    else: 
        new_height = target_height
        new_width = int(new_height * original_aspect)
        
    if new_width <= 0 or new_height <= 0:
        logging.warning(f"Рассчитан невалидный размер ({new_width}x{new_height}) для изображения {original_width}x{original_height} при целевом {target_width}x{target_height}. Возвращаем пустое изображение.")
        return Image.new(image_pil.mode if hasattr(image_pil, 'mode') else "RGB", (target_width, target_height), padding_color)
        
    try:
        resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
    except ValueError as e:
        logging.error(f"Ошибка при изменении размера изображения до {new_width}x{new_height}: {e}. Возвращаем пустое изображение.")
        return Image.new(image_pil.mode if hasattr(image_pil, 'mode') else "RGB", (target_width, target_height), padding_color)

    padded_image = Image.new(image_pil.mode if hasattr(image_pil, 'mode') else "RGB", (target_width, target_height), padding_color)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    padded_image.paste(resized_image, (paste_x, paste_y))
    
    return padded_image


def main():
    logging.info("--- Запуск скрипта создания эмбеддингов с паддингом (с предобработкой) ---")
    logging.info(f"PROJECT_ROOT установлен в: {PROJECT_ROOT}") # Логируем для проверки

    # Используем PROJECT_ROOT для формирования абсолютных путей
    nn_models_dir_abs = os.path.join(PROJECT_ROOT, NN_MODELS_DIR)
    input_images_dir_abs = os.path.join(PROJECT_ROOT, INPUT_IMAGES_DIR)
    embeddings_dir_out_abs = os.path.join(PROJECT_ROOT, EMBEDDINGS_DIR_OUT)

    if not ensure_dir_exists(nn_models_dir_abs) or \
       not ensure_dir_exists(input_images_dir_abs) or \
       not ensure_dir_exists(embeddings_dir_out_abs):
        logging.error("Одна или несколько ключевых директорий не существуют и не могут быть созданы. Завершение.")
        return

    onnx_model_path_abs = download_model_if_needed(ONNX_MODEL_REPO_ID, ONNX_MODEL_FILENAME, nn_models_dir_abs)
    if not onnx_model_path_abs: 
        logging.error("Не удалось получить модель ONNX. Завершение работы.")
        return

    try:
        ort_session = onnxruntime.InferenceSession(onnx_model_path_abs, providers=ONNX_PROVIDERS)
        input_name = ort_session.get_inputs()[0].name
        image_processor = AutoImageProcessor.from_pretrained(IMAGE_PROCESSOR_ID)
        
        target_h, target_w = 224, 224 
        if hasattr(image_processor, 'size') and isinstance(image_processor.size, dict):
            if 'height' in image_processor.size and 'width' in image_processor.size:
                target_h = image_processor.size['height']
                target_w = image_processor.size['width']
            elif 'shortest_edge' in image_processor.size: 
                edge_size = image_processor.size['shortest_edge']
                if "224" in IMAGE_PROCESSOR_ID or "224" in ONNX_MODEL_FILENAME:
                     target_h, target_w = 224, 224
                elif "256" in IMAGE_PROCESSOR_ID or "256" in ONNX_MODEL_FILENAME:
                     target_h, target_w = 256, 256
                else:
                     logging.warning(f"Не удалось определить точный квадратный размер из image_processor.size['shortest_edge']={edge_size}. Используется {edge_size}x{edge_size}.")
                     target_h, target_w = edge_size, edge_size
            else:
                logging.warning("Не удалось определить target_size из image_processor.size. Используется 224x224.")
        else:
            logging.warning("Атрибут image_processor.size не найден или имеет неверный формат. Используется 224x224.")

        logging.info(f"ONNX сессия и процессор загружены. Целевой размер для паддинга: {target_w}x{target_h}")

    except Exception as e: 
        logging.error(f"Ошибка при загрузке ONNX или процессора: {e}", exc_info=True)
        return

    image_files = [f for f in os.listdir(input_images_dir_abs) if f.lower().endswith(SUPPORTED_EXTENSIONS)]
    if not image_files:
        logging.warning(f"В директории '{input_images_dir_abs}' не найдено изображений.")
        return

    logging.info(f"Найдено изображений для обработки: {len(image_files)}")
    for image_filename in image_files:
        image_path_abs = os.path.join(input_images_dir_abs, image_filename)
        embedding_filename = os.path.splitext(image_filename)[0] + ".npy"
        embedding_path_abs = os.path.join(embeddings_dir_out_abs, embedding_filename)

        if os.path.exists(embedding_path_abs):
            logging.info(f"Эмбеддинг для '{image_filename}' уже существует. Перезапись для эксперимента с предобработкой.")
            try:
                os.remove(embedding_path_abs)
            except OSError as e_rem:
                logging.warning(f"Не удалось удалить существующий эмбеддинг {embedding_path_abs}: {e_rem}. Попытка перезаписать.")


        try:
            logging.info(f"Обработка эталона: {image_filename}")
            img_pil_original = Image.open(image_path_abs).convert("RGB") 
            
            img_pil_preprocessed = preprocess_image_for_dino(img_pil_original)
            if img_pil_preprocessed is None:
                logging.error(f"Предобработка для '{image_filename}' вернула None. Пропуск.")
                continue
            
            img_padded_pil = pad_image_to_target_size(img_pil_preprocessed, target_h, target_w)
            if img_padded_pil is None or img_padded_pil.size != (target_w, target_h): 
                logging.error(f"Паддинг для '{image_filename}' вернул некорректный результат. Пропуск.")
                continue

            inputs = image_processor(images=img_padded_pil, return_tensors="np")
            onnx_outputs = ort_session.run(None, {input_name: inputs.pixel_values})
            last_hidden_state = onnx_outputs[0]
            embedding = last_hidden_state[0, 0, :] 

            np.save(embedding_path_abs, embedding) 
            logging.info(f"Эмбеддинг сохранен: {embedding_path_abs} (размерность: {embedding.shape})")
        except Exception as e:
            logging.error(f"Ошибка при обработке изображения '{image_filename}': {e}", exc_info=True)

    logging.info("--- Завершение создания эмбеддингов с паддингом (с предобработкой) ---")

if __name__ == "__main__":
    main()