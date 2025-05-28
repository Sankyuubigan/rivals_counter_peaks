
import os
import numpy as np
from PIL import Image, ImageOps 
import onnxruntime
from huggingface_hub import hf_hub_download
from transformers import AutoImageProcessor
import logging # Добавлено логирование

# --- Конфигурация ---
# ИЗМЕНЕНО: Пути для nn_models и resources/embeddings_padded
NN_MODELS_DIR = "nn_models" # Новое имя папки для моделей ONNX
INPUT_IMAGES_DIR = "input_images" # Папка с изображениями для создания эмбеддингов
EMBEDDINGS_DIR_OUT = "resources/embeddings_padded" # Эмбеддинги теперь сохраняются сюда

ONNX_MODEL_REPO_ID = "onnx-community/dinov2-small-ONNX"
ONNX_MODEL_FILENAME = "onnx/model.onnx" # Путь внутри папки nn_models

IMAGE_PROCESSOR_ID = "facebook/dinov2-small"
ONNX_PROVIDERS = ['CPUExecutionProvider']
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')


def ensure_dir_exists(dir_path):
    if not os.path.exists(dir_path):
        try: # Добавлена обработка исключений для mkdir
            os.makedirs(dir_path)
            logging.info(f"Создана директория: {dir_path}")
        except OSError as e:
            logging.error(f"Ошибка при создании директории {dir_path}: {e}")
            return False
    return True

def download_model_if_needed(repo_id, filename, target_dir_abs): # target_dir теперь абсолютный
    # Имя файла модели ONNX уже включает подпапку 'onnx'
    # target_dir_abs должен быть путем к 'nn_models'
    # Полный путь к файлу модели будет target_dir_abs / filename (который есть 'onnx/model.onnx')
    model_path_abs = os.path.join(target_dir_abs, filename)
    
    # Убедимся, что подпапка для модели ('nn_models/onnx') существует
    model_subdir_abs = os.path.dirname(model_path_abs)
    if not ensure_dir_exists(model_subdir_abs):
        logging.error(f"Не удалось создать/подтвердить директорию для модели: {model_subdir_abs}")
        return None

    if not os.path.exists(model_path_abs):
        logging.info(f"Скачивание модели {filename} из {repo_id} в {model_subdir_abs}...")
        try:
            # hf_hub_download ожидает имя файла относительно репозитория,
            # а local_dir - куда его положить (сохраняя структуру репо)
            # В нашем случае filename это 'onnx/model.onnx', local_dir это 'nn_models'
            # он скачает в 'nn_models/onnx/model.onnx'
            hf_hub_download(repo_id=repo_id, filename=filename, local_dir=target_dir_abs, local_dir_use_symlinks=False)
            logging.info(f"Модель успешно скачана в: {model_path_abs}")
        except Exception as e:
            logging.error(f"Ошибка при скачивании модели: {e}")
            return None
    else:
        logging.info(f"Модель уже существует: {model_path_abs}")
    return model_path_abs

def pad_image_to_target_size(image_pil, target_height, target_width, padding_color=(0,0,0)):
    original_width, original_height = image_pil.size
    if original_width == target_width and original_height == target_height:
        return image_pil
    
    target_aspect = target_width / target_height if target_height != 0 else 1.0
    original_aspect = original_width / original_height if original_height != 0 else 0.0

    if original_aspect > target_aspect:
        new_width = target_width
        new_height = int(new_width / original_aspect) if original_aspect != 0 else 0
    else: 
        new_height = target_height
        new_width = int(new_height * original_aspect) if original_height != 0 else 0 # Была ошибка, использовался target_aspect
        
    if new_width <= 0 or new_height <= 0:
        logging.warning(f"Рассчитан невалидный размер ({new_width}x{new_height}) для изображения {original_width}x{original_height} при целевом {target_width}x{target_height}. Возвращаем пустое изображение.")
        return Image.new(image_pil.mode, (target_width, target_height), padding_color)
        
    try:
        resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
    except ValueError as e:
        logging.error(f"Ошибка при изменении размера изображения до {new_width}x{new_height}: {e}. Возвращаем пустое изображение.")
        return Image.new(image_pil.mode, (target_width, target_height), padding_color)

    padded_image = Image.new(image_pil.mode, (target_width, target_height), padding_color)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    padded_image.paste(resized_image, (paste_x, paste_y))
    
    return padded_image


def main():
    logging.info("--- Запуск скрипта создания эмбеддингов с паддингом ---")

    # Директории теперь относительно корня проекта
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    nn_models_dir_abs = os.path.join(project_root, NN_MODELS_DIR)
    input_images_dir_abs = os.path.join(project_root, INPUT_IMAGES_DIR)
    embeddings_dir_out_abs = os.path.join(project_root, EMBEDDINGS_DIR_OUT)

    if not ensure_dir_exists(nn_models_dir_abs) or \
       not ensure_dir_exists(input_images_dir_abs) or \
       not ensure_dir_exists(embeddings_dir_out_abs):
        logging.error("Одна или несколько ключевых директорий не существуют и не могут быть созданы. Завершение.")
        return

    # Передаем абсолютный путь к nn_models_dir_abs для скачивания
    onnx_model_path_abs = download_model_if_needed(ONNX_MODEL_REPO_ID, ONNX_MODEL_FILENAME, nn_models_dir_abs)
    if not onnx_model_path_abs:
        logging.error("Не удалось получить модель ONNX. Завершение работы.")
        return

    try:
        ort_session = onnxruntime.InferenceSession(onnx_model_path_abs, providers=ONNX_PROVIDERS)
        input_name = ort_session.get_inputs()[0].name
        image_processor = AutoImageProcessor.from_pretrained(IMAGE_PROCESSOR_ID)
        
        target_h, target_w = 224, 224 # Значения по умолчанию
        if hasattr(image_processor, 'size') and isinstance(image_processor.size, dict):
            if 'height' in image_processor.size and 'width' in image_processor.size:
                target_h = image_processor.size['height']
                target_w = image_processor.size['width']
            elif 'shortest_edge' in image_processor.size: 
                # Для DINOv2 это обычно означает квадратный вход, например 224x224
                # Проверим имя модели, если image_processor.size не дает явных H, W
                edge_size = image_processor.size['shortest_edge']
                if "224" in IMAGE_PROCESSOR_ID or "224" in ONNX_MODEL_FILENAME:
                     target_h, target_w = 224, 224
                elif "256" in IMAGE_PROCESSOR_ID or "256" in ONNX_MODEL_FILENAME: # Пример для другой модели
                     target_h, target_w = 256, 256
                else: # Если не можем определить, используем значение shortest_edge для обеих сторон
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
            logging.info(f"Эмбеддинг для '{image_filename}' уже существует, пропуск: {embedding_path_abs}")
            continue

        try:
            logging.info(f"Обработка эталона: {image_filename}")
            img_pil = Image.open(image_path_abs).convert("RGB")
            
            img_padded_pil = pad_image_to_target_size(img_pil, target_h, target_w)
            
            inputs = image_processor(images=img_padded_pil, return_tensors="np")
            onnx_outputs = ort_session.run(None, {input_name: inputs.pixel_values})
            last_hidden_state = onnx_outputs[0]
            embedding = last_hidden_state[0, 0, :] 

            np.save(embedding_path_abs, embedding)
            logging.info(f"Эмбеддинг сохранен: {embedding_path_abs} (размерность: {embedding.shape})")
        except Exception as e:
            logging.error(f"Ошибка при обработке изображения '{image_filename}': {e}", exc_info=True)

    logging.info("--- Завершение создания эмбеддингов с паддингом ---")

if __name__ == "__main__":
    main()