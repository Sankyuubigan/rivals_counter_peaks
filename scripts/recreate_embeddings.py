# 150 - размер изображения для эмбеддингов (измени эту цифру для другого размера)
TARGET_SIZE = 95
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

# --- Конфигурация моделей ---
NN_MODELS_DIR = "vision_models"
INPUT_IMAGES_DIR = "resources/heroes_icons"
EMBEDDINGS_DIR_OUT = "resources/embeddings_padded"

# Упрощенные конфигурации моделей
MODEL_CONFIGS = {
    "dinov3-vitb16-pretrain-lvd1689m": {
        "folder_name": "dinov3-vitb16-pretrain-lvd1689m",
        "filename": "model_q4.onnx",
        "target_size": TARGET_SIZE,
        "providers": ['CPUExecutionProvider'],
        "preprocessing_type": "resize",
        "normalize_embedding": True, # Включаем нормализацию для стабильности
        "embedding_extraction": "cls"
    }
}

DEFAULT_PARAMS = {
    "image_mean": [0.485, 0.456, 0.406],
    "image_std": [0.229, 0.224, 0.225]
}

for model_config in MODEL_CONFIGS.values():
    model_config.update(DEFAULT_PARAMS)

CURRENT_MODEL = "dinov3-vitb16-pretrain-lvd1689m"
MODEL_CONFIG = MODEL_CONFIGS[CURRENT_MODEL]

ONNX_MODEL_FILENAME = MODEL_CONFIG["filename"]
ONNX_MODEL_FOLDER = MODEL_CONFIG["folder_name"]
ONNX_PROVIDERS = MODEL_CONFIG["providers"]
TARGET_SIZE = MODEL_CONFIG["target_size"]
PREPROCESSING_TYPE = MODEL_CONFIG["preprocessing_type"]
NORMALIZE_EMBEDDING = MODEL_CONFIG["normalize_embedding"]
EMBEDDING_EXTRACTION = MODEL_CONFIG["embedding_extraction"]
IMAGE_MEAN = MODEL_CONFIG["image_mean"]
IMAGE_STD = MODEL_CONFIG["image_std"]

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

def enhance_image_for_embedding(image_pil: Image.Image) -> Image.Image:
    # Эта функция больше не используется, но оставлена на случай, если захотите вернуть
    if image_pil.mode != 'RGB':
        image_pil = image_pil.convert('RGB')
    enhancer = ImageEnhance.Sharpness(image_pil)
    image_pil = enhancer.enhance(1.5)
    enhancer = ImageEnhance.Contrast(image_pil)
    image_pil = enhancer.enhance(1.3)
    enhancer = ImageEnhance.Color(image_pil)
    image_pil = enhancer.enhance(1.2)
    return image_pil

def dynamic_resize_preprocess(image_pil: Image.Image, target_size=224, image_mean=None, image_std=None):
    try:
        # *** КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: ОТКЛЮЧАЕМ АГРЕССИВНОЕ УЛУЧШЕНИЕ ***
        # img_enhanced = enhance_image_for_embedding(image_pil) # СТАРАЯ ВЕРСИЯ
        img_enhanced = image_pil # НОВАЯ ВЕРСИЯ - ИСПОЛЬЗУЕМ ОРИГИНАЛ

        if img_enhanced.mode != 'RGB':
            img_enhanced = img_enhanced.convert('RGB')
        
        img_resized = img_enhanced.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        img_array = np.array(img_resized, dtype=np.float32) / 255.0
        
        if image_mean is None: image_mean = [0.485, 0.456, 0.406]
        if image_std is None: image_std = [0.229, 0.224, 0.225]
        mean = np.array(image_mean, dtype=np.float32)
        std = np.array(image_std, dtype=np.float32)
        img_array = (img_array - mean) / std
        
        img_array = np.transpose(img_array, (2, 0, 1))
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array.astype(np.float32)
        
    except Exception as e:
        logging.error(f"Ошибка в dynamic_resize_preprocess: {e}")
        return np.zeros((1, 3, target_size, target_size), dtype=np.float32)

def extract_embedding(last_hidden_state, method="cls"):
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
    logging.info(f"--- Запуск скрипта создания эмбеддингов с моделью {CURRENT_MODEL} ---")
    PROJECT_ROOT = get_project_root()
    nn_models_dir_abs = os.path.join(PROJECT_ROOT, NN_MODELS_DIR)
    input_images_dir_abs = os.path.join(PROJECT_ROOT, INPUT_IMAGES_DIR)
    embeddings_dir_out_abs = os.path.join(PROJECT_ROOT, EMBEDDINGS_DIR_OUT)
    
    if not all(os.path.exists(p) for p in [nn_models_dir_abs, input_images_dir_abs]) or \
       not ensure_dir_exists(embeddings_dir_out_abs, recreate=True):
        logging.error("Одна или несколько ключевых директорий не существуют. Завершение.")
        return
        
    onnx_model_path_abs = os.path.join(nn_models_dir_abs, ONNX_MODEL_FOLDER, ONNX_MODEL_FILENAME)
    if not os.path.exists(onnx_model_path_abs):
        logging.error(f"Модель не найдена: {onnx_model_path_abs}")
        return

    try:
        ort_session = onnxruntime.InferenceSession(onnx_model_path_abs, providers=ONNX_PROVIDERS)
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
            inputs = dynamic_resize_preprocess(img_pil, TARGET_SIZE, IMAGE_MEAN, IMAGE_STD)
            
            onnx_outputs = ort_session.run(None, {input_info.name: inputs})
            embedding = extract_embedding(onnx_outputs[0], EMBEDDING_EXTRACTION)
            
            if NORMALIZE_EMBEDDING:
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