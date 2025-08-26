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
    "dinov2-small": {
        "folder_name": "dinov2-small-ONNX",
        "filename": "onnx/model.onnx",
        "target_size": TARGET_SIZE,  # Используем переменную
        "providers": ['CUDAExecutionProvider', 'CPUExecutionProvider'],
        "preprocessing_type": "pad",
        "normalize_embedding": False,
        "embedding_extraction": "cls"
    },
    "dinov2-base": {
        "folder_name": "dinov2-base",
        "filename": "model_q4.onnx",
        "target_size": TARGET_SIZE,  # Используем переменную
        "providers": ['CUDAExecutionProvider', 'CPUExecutionProvider'],
        "preprocessing_type": "crop",
        "normalize_embedding": False,
        "embedding_extraction": "cls"
    },
    "dinov3-vitb16-pretrain-lvd1689m": {
        "folder_name": "dinov3-vitb16-pretrain-lvd1689m",
        "filename": "model_q4.onnx",
        "target_size": TARGET_SIZE,  # Используем переменную
        "providers": ['CUDAExecutionProvider', 'CPUExecutionProvider'],
        "preprocessing_type": "resize",
        "normalize_embedding": False,
        "embedding_extraction": "cls"
    },
    "nomic-embed-vision": {
        "folder_name": "nomic-embed-vision-v1.5",
        "filename": "model_q4.onnx",
        "target_size": TARGET_SIZE,  # Используем переменную
        "providers": ['CUDAExecutionProvider', 'CPUExecutionProvider'],
        "preprocessing_type": "clip",
        "normalize_embedding": False,
        "embedding_extraction": "nomic"
    }
}

# Установка параметров по умолчанию для всех моделей
DEFAULT_PARAMS = {
    "image_mean": [0.485, 0.456, 0.406],
    "image_std": [0.229, 0.224, 0.225]
}

# Добавляем параметры по умолчанию ко всем моделям
for model_config in MODEL_CONFIGS.values():
    model_config.update(DEFAULT_PARAMS)

# Специальные параметры для nomic
MODEL_CONFIGS["nomic-embed-vision"].update({
    "image_mean": [0.48145466, 0.4578275, 0.40821073],
    "image_std": [0.26862954, 0.26130258, 0.27577711]
})

CURRENT_MODEL = "dinov3-vitb16-pretrain-lvd1689m"
MODEL_CONFIG = MODEL_CONFIGS[CURRENT_MODEL]

# Извлекаем параметры
ONNX_MODEL_FILENAME = MODEL_CONFIG["filename"]
ONNX_MODEL_FOLDER = MODEL_CONFIG["folder_name"]
ONNX_PROVIDERS = MODEL_CONFIG["providers"]
TARGET_SIZE = MODEL_CONFIG["target_size"]  # Используем переменную из конфига
PREPROCESSING_TYPE = MODEL_CONFIG["preprocessing_type"]
NORMALIZE_EMBEDDING = MODEL_CONFIG["normalize_embedding"]
EMBEDDING_EXTRACTION = MODEL_CONFIG["embedding_extraction"]
IMAGE_MEAN = MODEL_CONFIG["image_mean"]
IMAGE_STD = MODEL_CONFIG["image_std"]

SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
SIMILARITY_CONFLICT_THRESHOLD = 0.70

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

def is_symbolic_dimension(dim):
    """Проверяет, является ли размерность символьной"""
    return isinstance(dim, str) and dim.startswith('s')

def get_file_hash(file_path):
    """Получить хеш файла"""
    if not os.path.exists(file_path):
        return None
    
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def find_project_root(current_path=None, markers=None):
    """Найти корень проекта по маркерным файлам/директориям"""
    if markers is None:
        markers = ['.git', 'pyproject.toml', 'setup.py', 'requirements.txt', 'src', 'core', 'resources']
    
    if current_path is None:
        current_path = os.path.dirname(os.path.abspath(__file__))
    
    current_path = os.path.abspath(current_path)
    logging.info(f"Начальный путь для поиска корня проекта: {current_path}")
    
    while current_path != os.path.dirname(current_path):
        for marker in markers:
            marker_path = os.path.join(current_path, marker)
            if os.path.exists(marker_path):
                logging.info(f"Найден маркер проекта '{marker}' в: {current_path}")
                return current_path
        
        current_path = os.path.dirname(current_path)
    
    fallback_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logging.warning(f"Маркеры проекта не найдены, используем запасной путь: {fallback_path}")
    return fallback_path

def get_project_root():
    """Получить корень проекта"""
    env_root = os.environ.get('PROJECT_ROOT')
    if env_root and os.path.exists(env_root):
        logging.info(f"PROJECT_ROOT из переменных окружения: {env_root}")
        return env_root
    
    marker_root = find_project_root()
    if marker_root:
        return marker_root
    
    cwd = os.getcwd()
    if os.path.basename(cwd) == 'test':
        cwd_root = os.path.dirname(cwd)
        logging.info(f"PROJECT_ROOT из рабочего каталога: {cwd_root}")
        return cwd_root
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fallback_root = os.path.dirname(script_dir)
    logging.info(f"PROJECT_ROOT (запасной вариант): {fallback_root}")
    return fallback_root

def ensure_dir_exists(dir_path: str, recreate=False) -> bool:
    """Проверка и создание директории"""
    if recreate and os.path.exists(dir_path):
        logging.info(f"Директория {dir_path} уже существует. Пересоздание...")
        try:
            shutil.rmtree(dir_path)
            logging.info(f"Удалена существующая директория: {dir_path}")
        except OSError as e:
            logging.error(f"Ошибка при удалении директории {dir_path}: {e}")
            return False
    
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

def get_local_model_path(target_dir_abs, folder_name, filename):
    """Получить путь к локальной модели"""
    model_path_abs = os.path.join(target_dir_abs, folder_name, filename)
    
    if os.path.exists(model_path_abs):
        file_hash = get_file_hash(model_path_abs)
        logging.info(f"Найдена локальная модель: {model_path_abs}")
        logging.info(f"Хеш файла: {file_hash}")
        return model_path_abs
    else:
        logging.error(f"Модель не найдена в ожидаемом месте: {model_path_abs}")
        return None

def enhance_image_for_embedding(image_pil: Image.Image) -> Image.Image:
    """Улучшение изображения перед созданием эмбеддинга"""
    try:
        # Убедимся, что изображение в RGB
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
        
        # Улучшаем резкость
        enhancer = ImageEnhance.Sharpness(image_pil)
        image_pil = enhancer.enhance(1.5)
        
        # Улучшаем контрастность
        enhancer = ImageEnhance.Contrast(image_pil)
        image_pil = enhancer.enhance(1.3)
        
        # Улучшаем цветность
        enhancer = ImageEnhance.Color(image_pil)
        image_pil = enhancer.enhance(1.2)
        
        return image_pil
    except Exception as e:
        logging.error(f"Ошибка в enhance_image_for_embedding: {e}")
        return image_pil

def pad_image_to_target_size(image_pil, target_height, target_width, padding_color=(0,0,0)):
    """Паддинг изображения до целевого размера (для обратной совместимости)"""
    if image_pil is None: 
        return Image.new("RGB", (target_width, target_height), padding_color) 
    
    original_width, original_height = image_pil.size
    if original_width == target_width and original_height == target_height:
        return image_pil
    
    # Рассчитываем новые размеры с сохранением пропорций
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
        
    try:
        resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
    except ValueError as e:
        logging.error(f"Ошибка при изменении размера изображения: {e}")
        return Image.new("RGB", (target_width, target_height), padding_color)
    
    # Центрируем изображение
    padded_image = Image.new("RGB", (target_width, target_height), padding_color)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    padded_image.paste(resized_image, (paste_x, paste_y))
    
    return padded_image

def crop_image_to_target_size(image_pil, target_size=224):
    """Crop изображения до целевого размера"""
    # Предобработка изображения
    img_pil_preprocessed = enhance_image_for_embedding(image_pil)
    
    # Resize до кратного размера
    width, height = img_pil_preprocessed.size
    if width < height:
        new_width = 256
        new_height = int(height * 256 / width)
    else:
        new_height = 256
        new_width = int(width * 256 / height)
    
    img_resized = img_pil_preprocessed.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Center crop
    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    right = left + target_size
    bottom = top + target_size
    
    img_cropped = img_resized.crop((left, top, right, bottom))
    
    # Конвертируем в numpy array и нормализуем
    img_array = np.array(img_cropped, dtype=np.float32) / 255.0
    
    # ImageNet нормализация
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_array = (img_array - mean) / std
    
    # Транспонирование HWC -> CHW и добавление batch dimension
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array.astype(np.float32)

def clip_preprocess_image(image_pil, target_size=224, image_mean=None, image_std=None):
    """Предобработка в стиле CLIP"""
    if image_pil.mode != 'RGB':
        image_pil = image_pil.convert('RGB')
    
    # Увеличиваем маленькие изображения
    width, height = image_pil.size
    min_dimension = min(width, height)
    
    if min_dimension < 256:
        scale = 256 / min_dimension
        new_width = int(width * scale)
        new_height = int(height * scale)
        image_pil = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        width, height = new_width, new_height
    
    # Resize до кратного размера
    if width < height:
        new_width = 256
        new_height = int(height * 256 / width)
    else:
        new_height = 256
        new_width = int(width * 256 / height)
    
    img_resized = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Center crop
    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    right = left + target_size
    bottom = top + target_size
    
    img_cropped = img_resized.crop((left, top, right, bottom))
    
    # Конвертируем в numpy array и нормализуем
    img_array = np.array(img_cropped, dtype=np.float32) / 255.0
    
    # CLIP нормализация
    if image_mean is None:
        image_mean = [0.48145466, 0.4578275, 0.40821073]
    if image_std is None:
        image_std = [0.26862954, 0.26130258, 0.27577711]
        
    mean = np.array(image_mean, dtype=np.float32)
    std = np.array(image_std, dtype=np.float32)
    img_array = (img_array - mean) / std
    
    # Транспонирование HWC -> CHW и добавление batch dimension
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array.astype(np.float32)

def dynamic_resize_preprocess(image_pil: Image.Image, target_size=224, image_mean=None, image_std=None):
    """
    Динамическая предобработка изображений любого размера для DINOv3
    Оптимальный подход для максимальной точности
    """
    try:
        # 1. Улучшаем качество изображения
        img_enhanced = enhance_image_for_embedding(image_pil)
        
        # 2. Конвертируем в RGB если нужно
        if img_enhanced.mode != 'RGB':
            img_enhanced = img_enhanced.convert('RGB')
        
        # 3. Получаем оригинальные размеры для логирования
        original_width, original_height = img_enhanced.size
        logging.debug(f"Обработка изображения: {original_width}x{original_height} -> {target_size}x{target_size}")
        
        # 4. Динамический выбор стратегии обработки в зависимости от размера изображения
        max_dimension = max(original_width, original_height)
        
        if max_dimension <= target_size:
            # Для маленьких изображений: upscale + resize
            intermediate_size = int(target_size * 1.5)  # Увеличиваем до 336px для 224 target
            
            # Сначала upscale с сохранением пропорций
            scale = intermediate_size / max_dimension
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            img_intermediate = img_enhanced.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Затем финальный resize до целевого размера
            img_resized = img_intermediate.resize((target_size, target_size), Image.Resampling.LANCZOS)
            
        elif max_dimension <= target_size * 2:
            # Для средних изображений: прямой resize с высококачественной интерполяцией
            img_resized = img_enhanced.resize((target_size, target_size), Image.Resampling.LANCZOS)
            
        else:
            # Для больших изображений: сначала уменьшаем с сохранением пропорций, затем resize
            scale = (target_size * 1.5) / max_dimension
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            img_intermediate = img_enhanced.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img_resized = img_intermediate.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # 5. Конвертируем в numpy array
        img_array = np.array(img_resized, dtype=np.float32) / 255.0
        
        # 6. Нормализация (используем переданные параметры или значения по умолчанию)
        if image_mean is None:
            image_mean = [0.485, 0.456, 0.406]
        if image_std is None:
            image_std = [0.229, 0.224, 0.225]
            
        mean = np.array(image_mean, dtype=np.float32)
        std = np.array(image_std, dtype=np.float32)
        img_array = (img_array - mean) / std
        
        # 7. Транспонирование HWC -> CHW и добавление batch dimension
        img_array = np.transpose(img_array, (2, 0, 1))
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array.astype(np.float32)
        
    except Exception as e:
        logging.error(f"Ошибка в dynamic_resize_preprocess: {e}")
        # Возвращаем нулевой тензор в случае ошибки
        return np.zeros((1, 3, target_size, target_size), dtype=np.float32)

def preprocess_image(image_pil: Image.Image, target_size=224, preprocessing_type="resize", image_mean=None, image_std=None):
    """
    Унифицированная предобработка изображения с динамической обработкой
    """
    try:
        if preprocessing_type == "crop":
            return crop_image_to_target_size(image_pil, target_size)
        elif preprocessing_type == "clip":
            return clip_preprocess_image(image_pil, target_size, image_mean, image_std)
        elif preprocessing_type == "pad":
            # Для обратной совместимости, но рекомендуется использовать "resize"
            img_pil_preprocessed = enhance_image_for_embedding(image_pil)
            img_padded_pil = pad_image_to_target_size(img_pil_preprocessed, target_size, target_size)
            
            img_array = np.array(img_padded_pil, dtype=np.float32) / 255.0
            
            if image_mean is None:
                image_mean = [0.485, 0.456, 0.406]
            if image_std is None:
                image_std = [0.229, 0.224, 0.225]
                
            mean = np.array(image_mean, dtype=np.float32)
            std = np.array(image_std, dtype=np.float32)
            img_array = (img_array - mean) / std
            
            img_array = np.transpose(img_array, (2, 0, 1))
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array.astype(np.float32)
        else:  # resize - новый подход для DINOv3
            return dynamic_resize_preprocess(image_pil, target_size, image_mean, image_std)
    except Exception as e:
        logging.error(f"Ошибка в preprocess_image: {e}")
        return np.zeros((1, 3, target_size, target_size), dtype=np.float32)

def extract_embedding(last_hidden_state, method="cls"):
    """Извлечение эмбеддинга из выходного тензора модели"""
    if method == "nomic":
        # Взвешенное среднее для nomic
        tokens = last_hidden_state[0, 1:, :]  # исключаем CLS токен
        num_tokens = tokens.shape[0]
        weights = np.linspace(0.5, 1.5, num_tokens)  # линейно увеличивающиеся веса
        weights = weights / weights.sum()  # нормализация
        weighted_sum = np.sum(tokens * weights[:, np.newaxis], axis=0)
        return weighted_sum
    elif method == "mean":
        # Mean pooling всех токенов
        return np.mean(last_hidden_state[0], axis=0)
    elif method == "mean_no_cls":
        # Mean pooling всех токенов кроме CLS
        return np.mean(last_hidden_state[0, 1:], axis=0)
    elif method == "max":
        # Max pooling всех токенов
        return np.max(last_hidden_state[0], axis=0)
    else:
        # По умолчанию используем [CLS] токен
        return last_hidden_state[0, 0, :]

def normalize_embedding(embedding):
    """L2 нормализация эмбеддинга"""
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm

def cosine_similarity(vec_a, vec_b):
    """Вычисление косинусного сходства"""
    if vec_a is None or vec_b is None:
        return 0.0
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def load_embedding(filename_no_ext, base_dir):
    """Загрузка эмбеддинга из файла"""
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

def compare_embeddings():
    """Сравнение эмбеддингов между собой"""
    PROJECT_ROOT = get_project_root()
    embeddings_base_path = Path(PROJECT_ROOT) / EMBEDDINGS_DIR_OUT
    
    if not embeddings_base_path.is_dir():
        logging.error(f"Директория с эмбеддингами не найдена: {embeddings_base_path}")
        return
    
    logging.info(f"\n--- Анализ попарных сходств всех эталонных эмбеддингов ---")
    logging.info(f"--- Порог для определения 'конфликтного' сходства: {SIMILARITY_CONFLICT_THRESHOLD:.2f} ---")
    
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
                print(f"Герой: {hero_name}, Конфликтных схожестей: {data['count']}")
    
    logging.info("--- Анализ завершен ---")

def validate_input_dimensions(input_shape, actual_shape):
    """Валидация размерностей входных данных с поддержкой символьных размерностей"""
    if len(input_shape) != len(actual_shape):
        return False, f"Несоответствие количества размерностей: ожидается {len(input_shape)}, получено {len(actual_shape)}"
    
    for i, (expected, actual) in enumerate(zip(input_shape, actual_shape)):
        if is_symbolic_dimension(expected):
            # Для символьных размерностей пропускаем проверку
            continue
        elif isinstance(expected, int) and expected != actual:
            return False, f"Несоответствие размерности {i}: ожидается {expected}, получено {actual}"
    
    return True, "Размерности совпадают"

def create_embeddings():
    """Создание эмбеддингов с использованием локальных моделей"""
    logging.info(f"--- Запуск скрипта создания эмбеддингов с моделью {CURRENT_MODEL} ---")
    logging.info(f"--- Используется размер изображения: {TARGET_SIZE}x{TARGET_SIZE} ---")
    logging.info(f"--- Тип предобработки: {PREPROCESSING_TYPE} ---")
    logging.info(f"--- Извлечение эмбеддинга: {EMBEDDING_EXTRACTION} ---")
    logging.info(f"--- Нормализация эмбеддингов: {NORMALIZE_EMBEDDING} ---")
    
    # Определяем корень проекта
    PROJECT_ROOT = get_project_root()
    logging.info(f"Определенный PROJECT_ROOT: {PROJECT_ROOT}")
    
    # Формируем абсолютные пути
    nn_models_dir_abs = os.path.join(PROJECT_ROOT, NN_MODELS_DIR)
    input_images_dir_abs = os.path.join(PROJECT_ROOT, INPUT_IMAGES_DIR)
    embeddings_dir_out_abs = os.path.join(PROJECT_ROOT, EMBEDDINGS_DIR_OUT)
    
    logging.info(f"Модели: {nn_models_dir_abs}")
    logging.info(f"Входные изображения: {input_images_dir_abs}")
    logging.info(f"Выходные эмбеддинги: {embeddings_dir_out_abs}")
    
    # Проверка существования директории с изображениями
    if not os.path.exists(input_images_dir_abs):
        logging.error(f"Директория с изображениями не найдена: {input_images_dir_abs}")
        possible_paths = [
            os.path.join(PROJECT_ROOT, "resources", "templates"),
            os.path.join(PROJECT_ROOT, "resources"),
            os.path.join(PROJECT_ROOT, "templates"),
            os.path.join(PROJECT_ROOT, "..", "resources", "templates"),
            os.path.join(PROJECT_ROOT, "..", "templates"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logging.info(f"Найдена альтернативная директория: {path}")
                input_images_dir_abs = path
                break
        else:
            logging.error("Не найдена директория с изображениями!")
            return
    
    # Проверка директорий
    if not ensure_dir_exists(nn_models_dir_abs) or \
       not ensure_dir_exists(input_images_dir_abs) or \
       not ensure_dir_exists(embeddings_dir_out_abs, recreate=True):
        logging.error("Одна или несколько ключевых директорий не существуют и не могут быть созданы. Завершение.")
        return
    
    # Получаем путь к локальной модели
    onnx_model_path_abs = get_local_model_path(nn_models_dir_abs, ONNX_MODEL_FOLDER, ONNX_MODEL_FILENAME)
    if not onnx_model_path_abs: 
        logging.error("Не удалось найти локальную модель. Завершение работы.")
        return
    
    try:
        # Создаем сессию с указанием провайдеров
        ort_session = onnxruntime.InferenceSession(
            onnx_model_path_abs, 
            providers=ONNX_PROVIDERS
        )
        
        # Проверяем, какой провайдер реально используется
        actual_providers = ort_session.get_providers()
        logging.info(f"Используются провайдеры: {actual_providers}")
        
        # Получаем информацию о входах и выходах
        input_info = ort_session.get_inputs()[0]
        output_info = ort_session.get_outputs()[0]
        
        logging.info(f"Входной тензор: {input_info.name}, форма: {input_info.shape}, тип: {input_info.type}")
        logging.info(f"Выходной тензор: {output_info.name}, форма: {output_info.shape}, тип: {output_info.type}")
        
    except Exception as e:
        logging.error(f"Ошибка при загрузке ONNX: {e}", exc_info=True)
        return
    
    logging.info(f"Целевой размер изображения для предобработки: {TARGET_SIZE}x{TARGET_SIZE}")
    
    # Поиск изображений
    image_files = [f for f in os.listdir(input_images_dir_abs) if f.lower().endswith(SUPPORTED_EXTENSIONS)]
    if not image_files:
        logging.warning(f"В директории '{input_images_dir_abs}' не найдено изображений.")
        return
    
    logging.info(f"Найдено изображений для обработки: {len(image_files)}")
    
    # Обработка изображений
    for image_filename in image_files:
        image_path_abs = os.path.join(input_images_dir_abs, image_filename)
        embedding_filename = os.path.splitext(image_filename)[0] + ".npy"
        embedding_path_abs = os.path.join(embeddings_dir_out_abs, embedding_filename)
        
        try:
            logging.info(f"Обработка: {image_filename}")
            
            # Загружаем изображение
            img_pil_original = Image.open(image_path_abs) 
            original_width, original_height = img_pil_original.size
            logging.debug(f"Оригинальный размер изображения: {original_width}x{original_height}")
            
            # Используем правильную предобработку для текущей модели
            inputs = preprocess_image(img_pil_original, TARGET_SIZE, PREPROCESSING_TYPE, IMAGE_MEAN, IMAGE_STD)
            logging.debug(f"Форма входного тензора: {inputs.shape}, тип: {inputs.dtype}")
            
            # Валидация размерностей с поддержкой символьных размерностей
            is_valid, message = validate_input_dimensions(input_info.shape, inputs.shape)
            if not is_valid:
                logging.error(f"{message}")
                continue
            
            # Получаем выход модели
            onnx_outputs = ort_session.run(None, {input_info.name: inputs})
            last_hidden_state = onnx_outputs[0]
            
            # Извлекаем эмбеддинг
            embedding = extract_embedding(last_hidden_state, EMBEDDING_EXTRACTION)
            logging.debug(f"Извлечен эмбеддинг методом {EMBEDDING_EXTRACTION}, размерность: {embedding.shape}")
            
            # Применяем L2 нормализацию если нужно
            if NORMALIZE_EMBEDDING:
                embedding = normalize_embedding(embedding)
                logging.debug(f"Применена L2 нормализация эмбеддинга")
            
            np.save(embedding_path_abs, embedding) 
            logging.info(f"Эмбеддинг сохранен: {embedding_path_abs} (размерность: {embedding.shape})")
            
        except Exception as e:
            logging.error(f"Ошибка при обработке изображения '{image_filename}': {e}", exc_info=True)
    
    logging.info("--- Завершение создания эмбеддингов ---")
    
    # Запускаем тест сравнения эмбеддингов
    compare_embeddings()

if __name__ == "__main__":
    create_embeddings()