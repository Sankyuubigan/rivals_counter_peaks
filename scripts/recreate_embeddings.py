import os
import sys
import numpy as np
import logging
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageOps, ImageEnhance
import onnxruntime
import shutil
import hashlib

# *** КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: РАБОТАЕМ В НАСТОЯЩЕМ РАЗМЕРЕ МОДЕЛИ ***
TARGET_SIZE = 224

# --- Конфигурация моделей ---
NN_MODELS_DIR = "vision_models"
INPUT_IMAGES_DIR = "resources/heroes_icons"
EMBEDDINGS_DIR_OUT = "resources/embeddings_padded"

MODEL_CONFIG = {
    "folder_name": "dinov3-vitb16-pretrain-lvd1689m",
    "filename": "model_q4.onnx",
    "target_size": TARGET_SIZE,
    "providers": ['CPUExecutionProvider'],
    "normalize_embedding": True,
    "embedding_extraction": "cls",
    "image_mean": [0.485, 0.456, 0.406],
    "image_std": [0.229, 0.224, 0.225]
}

SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
SIMILARITY_CONFLICT_THRESHOLD = 0.70

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def ensure_dir_exists(dir_path: str, recreate=False) -> bool:
    if recreate and os.path.exists(dir_path):
        logging.info(f"Директория {dir_path} уже существует. Пересоздание...")
        shutil.rmtree(dir_path)
    os.makedirs(dir_path, exist_ok=True)
    return True

def pad_image_to_target_size(image_pil, target_height, target_width, padding_color=(0,0,0)):
    """
    *** ВОЗВРАЩЕНА ВАША ОРИГИНАЛЬНАЯ ЛОГИКА ПАДДИНГА С СОХРАНЕНИЕМ ПРОПОРЦИЙ ***
    Паддинг изображения до целевого размера.
    """
    if image_pil is None: 
        return Image.new("RGB", (target_width, target_height), padding_color) 
    
    original_width, original_height = image_pil.size
    if original_width == target_width and original_height == target_height:
        return image_pil
    
    target_aspect = target_width / target_height if target_height != 0 else 1.0
    original_aspect = original_width / original_height if original_height != 0 else 1.0
    
    if original_aspect > target_aspect: 
        new_width = target_width
        new_height = int(new_width / original_aspect)
    else: 
        new_height = target_height
        new_width = int(new_height * original_aspect)
        
    if new_width <= 0 or new_height <= 0:
        return Image.new("RGB", (target_width, target_height), padding_color)
        
    resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    padded_image = Image.new("RGB", (target_width, target_height), padding_color)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    padded_image.paste(resized_image, (paste_x, paste_y))
    
    return padded_image

def preprocess_image(image_pil: Image.Image, target_size, image_mean, image_std):
    """
    Предобработка изображения: паддинг и нормализация.
    """
    if image_pil.mode != 'RGB':
        image_pil = image_pil.convert('RGB')

    # *** ИСПОЛЬЗУЕМ ПРАВИЛЬНЫЙ ПАДДИНГ ***
    img_padded_pil = pad_image_to_target_size(image_pil, target_size, target_size)
    
    img_array = np.array(img_padded_pil, dtype=np.float32) / 255.0
    
    mean = np.array(image_mean, dtype=np.float32)
    std = np.array(image_std, dtype=np.float32)
    img_array = (img_array - mean) / std
    
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array.astype(np.float32)

def extract_embedding(last_hidden_state):
    return last_hidden_state[0, 0, :]

def normalize_embedding_func(embedding):
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm != 0 else embedding

def cosine_similarity(vec_a, vec_b):
    return np.dot(vec_a, vec_b)

def load_embedding(filename_no_ext, base_dir):
    file_path = Path(base_dir) / f"{filename_no_ext}.npy"
    return np.load(file_path) if file_path.exists() else None

def compare_embeddings():
    PROJECT_ROOT = get_project_root()
    embeddings_base_path = Path(PROJECT_ROOT) / EMBEDDINGS_DIR_OUT
    logging.info(f"\n--- Анализ попарных сходств всех эталонных эмбеддингов ---")
    logging.info(f"--- Порог для определения 'конфликтного' сходства: {SIMILARITY_CONFLICT_THRESHOLD:.2f} ---")
    
    all_embedding_files = [f.stem for f in embeddings_base_path.glob('*.npy')]
    loaded_embeddings = {hero_file: load_embedding(hero_file, embeddings_base_path) for hero_file in all_embedding_files}
    loaded_embeddings = {k: v for k, v in loaded_embeddings.items() if v is not None}
    
    hero_conflict_scores = defaultdict(lambda: {"count": 0, "conflicts_with": []})
    hero_names = list(loaded_embeddings.keys())
    
    for i in range(len(hero_names)):
        for j in range(i + 1, len(hero_names)):
            hero_a, hero_b = hero_names[i], hero_names[j]
            sim = cosine_similarity(loaded_embeddings[hero_a], loaded_embeddings[hero_b])
            if sim >= SIMILARITY_CONFLICT_THRESHOLD:
                hero_conflict_scores[hero_a]["count"] += 1
                hero_conflict_scores[hero_a]["conflicts_with"].append(f"{hero_b} ({(sim*100):.1f}%)")
                hero_conflict_scores[hero_b]["count"] += 1
                hero_conflict_scores[hero_b]["conflicts_with"].append(f"{hero_a} ({(sim*100):.1f}%)")
    
    sorted_problematic_heroes = sorted(hero_conflict_scores.items(), key=lambda item: item[1]["count"], reverse=True)
    
    logging.info(f"\n--- Рейтинг 'проблемных' героев (с наибольшим количеством схожестей > {SIMILARITY_CONFLICT_THRESHOLD*100:.0f}% с ДРУГИМИ героями) ---")
    if not any(data["count"] > 0 for _, data in sorted_problematic_heroes):
        logging.info("Не найдено героев, превышающих порог конфликтного сходства с другими.")
    else:
        for hero_name, data in sorted_problematic_heroes:
            if data["count"] > 0:
                print(f"Герой: {hero_name}, Конфликтных схожестей: {data['count']}")
    
    logging.info("--- Анализ завершен ---")

def create_embeddings():
    logging.info(f"--- Запуск скрипта создания эмбеддингов с моделью {MODEL_CONFIG['folder_name']} ---")
    PROJECT_ROOT = get_project_root()
    nn_models_dir_abs = os.path.join(PROJECT_ROOT, NN_MODELS_DIR)
    input_images_dir_abs = os.path.join(PROJECT_ROOT, INPUT_IMAGES_DIR)
    embeddings_dir_out_abs = os.path.join(PROJECT_ROOT, EMBEDDINGS_DIR_OUT)
    
    if not all(os.path.exists(p) for p in [nn_models_dir_abs, input_images_dir_abs]) or \
       not ensure_dir_exists(embeddings_dir_out_abs, recreate=True):
        logging.error("Одна или несколько ключевых директорий не существуют. Завершение.")
        return
        
    onnx_model_path_abs = os.path.join(nn_models_dir_abs, MODEL_CONFIG['folder_name'], MODEL_CONFIG['filename'])
    if not os.path.exists(onnx_model_path_abs):
        logging.error(f"Модель не найдена: {onnx_model_path_abs}")
        return

    try:
        ort_session = onnxruntime.InferenceSession(onnx_model_path_abs, providers=MODEL_CONFIG['providers'])
        input_info = ort_session.get_inputs()[0]
    except Exception as e:
        logging.error(f"Ошибка при загрузке ONNX: {e}", exc_info=True)
        return
    
    image_files = [f for f in os.listdir(input_images_dir_abs) if f.lower().endswith(SUPPORTED_EXTENSIONS)]
    logging.info(f"Найдено изображений для обработки: {len(image_files)}")
    
    for image_filename in image_files:
        try:
            logging.info(f"Обработка: {image_filename}")
            img_pil = Image.open(os.path.join(input_images_dir_abs, image_filename))
            inputs = preprocess_image(img_pil, MODEL_CONFIG['target_size'], MODEL_CONFIG['image_mean'], MODEL_CONFIG['image_std'])
            
            onnx_outputs = ort_session.run(None, {input_info.name: inputs})
            embedding = extract_embedding(onnx_outputs[0])
            
            if MODEL_CONFIG['normalize_embedding']:
                embedding = normalize_embedding_func(embedding)
            
            embedding_path_abs = os.path.join(embeddings_dir_out_abs, os.path.splitext(image_filename)[0] + ".npy")
            np.save(embedding_path_abs, embedding)
            logging.info(f"Эмбеддинг сохранен: {embedding_path_abs}")
        except Exception as e:
            logging.error(f"Ошибка при обработке '{image_filename}': {e}", exc_info=True)
    
    logging.info("--- Завершение создания эмбеддингов ---")
    compare_embeddings()

if __name__ == "__main__":
    create_embeddings()