import os
import sys
import time
import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import Counter, defaultdict
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageGrab
import onnxruntime
import shutil

# Установка Numba (если еще не установлена)
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("Numba не установлена. Установите: pip install numba")

# =============================================================================
# ПУТИ К РЕСУРСАМ
# =============================================================================
VISION_MODELS_DIR = "vision_models"
MODEL_PATH = "vision_models/dinov3-vitb16-pretrain-lvd1689m/model_q4.onnx"
EMBEDDINGS_DIR = "resources/embeddings_padded"
SCREENSHOTS_DIR = "tests/for_recogn/screenshots"
CORRECT_ANSWERS_FILE = "tests/for_recogn/correct_answers.json"
DEBUG_DIR = "tests/debug"

# Создаем директорию для отладки
os.makedirs(DEBUG_DIR, exist_ok=True)
LOG_FILENAME = "recognition_test.log"
log_file_path = os.path.join(DEBUG_DIR, LOG_FILENAME)

# Очищаем лог и папку debug
if os.path.exists(log_file_path):
    open(log_file_path, 'w').close()
for item in os.listdir(DEBUG_DIR):
    item_path = os.path.join(DEBUG_DIR, item)
    if os.path.isfile(item_path) and item != LOG_FILENAME: 
        os.unlink(item_path)
    elif os.path.isdir(item_path): 
        shutil.rmtree(item_path)

# Настройка логирования
logger = logging.getLogger()
logger.setLevel(logging.INFO)
for handler in logger.handlers[:]: 
    logger.removeHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# =============================================================================
# ОСНОВНЫЕ НАСТРОЙКИ
# =============================================================================
TARGET_SIZE = 224
LEFT_OFFSET = 45

# =============================================================================
# КОНСТАНТЫ
# =============================================================================
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]

# Параметры для распознавания - УВЕЛИЧЕН ПОРОГ УВЕРЕННОСТИ
CONFIDENCE_THRESHOLD = 0.70  # Было 0.65
MAX_HEROES = 6
BATCH_SIZE_SLIDING_WINDOW_DINO = 32

# Параметры для поиска квадратов
HERO_SQUARE_SIZE = 95
MIN_SQUARE_SIZE = 85
MAX_SQUARE_SIZE = 105
STEP_SIZE = HERO_SQUARE_SIZE // 4  # Шаг как в Rust коде

RECOGNITION_AREA = {
    'monitor': 1, 'left_pct': 50, 'top_pct': 20, 'width_pct': 20, 'height_pct': 50
}

# =============================================================================
# НОВЫЕ ФУНКЦИИ ДЛЯ NMS
# =============================================================================

def box_area(box):
    """Вычислить площадь bounding box"""
    return (box[2] - box[0]) * (box[3] - box[1])

def box_iou_batch(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """Векторизованный расчет IoU для двух наборов bounding boxes"""
    area_a = box_area(boxes_a.T)
    area_b = box_area(boxes_b.T)
    
    top_left = np.maximum(boxes_a[:, None, :2], boxes_b[:, :2])
    bottom_right = np.minimum(boxes_a[:, None, 2:], boxes_b[:, 2:])
    
    area_inter = np.prod(
        np.clip(bottom_right - top_left, a_min=0, a_max=None), axis=2
    )
    
    return area_inter / (area_a[:, None] + area_b - area_inter)

def non_max_suppression(detections: List[Dict], iou_threshold: float = 0.4) -> List[Dict]:
    """Non-Maximum Suppression для удаления пересекающихся детекций"""
    if not detections:
        return []
    
    # Сортируем детекции по уверенности (по убыванию)
    detections_sorted = sorted(detections, key=lambda x: x['confidence'], reverse=True)
    
    # Преобразуем в формат для NMS
    boxes = []
    scores = []
    for det in detections_sorted:
        x, y = det['position']
        w, h = det['size']
        boxes.append([x, y, x + w, y + h])  # [x1, y1, x2, y2]
        scores.append(det['confidence'])
    
    boxes = np.array(boxes)
    scores = np.array(scores)
    
    # Рассчитываем IoU для всех пар
    ious = box_iou_batch(boxes, boxes)
    np.fill_diagonal(ious, 0)  # Исключаем сравнение с самим собой
    
    keep = []
    suppressed = np.zeros(len(boxes), dtype=bool)
    
    for i in range(len(boxes)):
        if suppressed[i]:
            continue
            
        keep.append(i)
        
        # Подавляем все детекции с высоким IoU
        suppress_indices = np.where(ious[i] > iou_threshold)[0]
        suppressed[suppress_indices] = True
    
    # Возвращаем оригинальные детекции в правильном порядке
    result = [detections_sorted[i] for i in keep]
    return result

# =============================================================================
# УСКОРЕНИЕ С NUMBA
# =============================================================================

if NUMBA_AVAILABLE:
    @jit(nopython=True)
    def get_embeddings_for_batch_jit(arrays_data, embeddings_shape):
        """Ускоренная обработка эмбеддингов"""
        batch_size = embeddings_shape[0]
        emb_size = embeddings_shape[1]
        embeddings = np.zeros((batch_size, emb_size), dtype=np.float32)
        
        for i in range(batch_size):
            start_idx = i * emb_size
            end_idx = start_idx + emb_size
            embedding = arrays_data[start_idx:end_idx]
            
            # Нормализация
            norm = 0.0
            for j in range(emb_size):
                norm += embedding[j] * embedding[j]
            norm = np.sqrt(norm)
            
            if norm > 1e-6:
                for j in range(emb_size):
                    embeddings[i, j] = embedding[j] / norm
        
        return embeddings

class HeroRecognitionSystem:
    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, List[np.ndarray]] = {}
        self.hero_stats = {}
        logging.info("Инициализация системы распознавания героев...")
        
    def load_model(self) -> bool:
        try:
            # Для ускорения на GPU NVIDIA замените на ['CUDAExecutionProvider', 'CPUExecutionProvider']
            # Для этого нужно установить onnxruntime-gpu
            self.ort_session = onnxruntime.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
            self.input_name = self.ort_session.get_inputs()[0].name
            logging.info(f"Модель загружена. Вход: {self.input_name}")
            return True
        except Exception as e:
            logging.error(f"Ошибка загрузки модели: {e}")
            return False
            
    def load_embeddings(self) -> bool:
        try:
            hero_embedding_groups = defaultdict(list)
            for emb_file in os.listdir(EMBEDDINGS_DIR):
                if not emb_file.endswith('.npy'): continue
                base_name = os.path.splitext(emb_file)[0]
                parts = base_name.split('_')
                hero_name = '_'.join(parts[:-1]) if len(parts) > 1 and parts[-1].isdigit() else base_name
                embedding = np.load(os.path.join(EMBEDDINGS_DIR, emb_file))
                hero_embedding_groups[hero_name].append(embedding)
            
            self.hero_embeddings = dict(hero_embedding_groups)
            for hero_name in self.hero_embeddings:
                self.hero_stats[hero_name] = {'dino_confirmed': 0, 'avg_similarity': 0.0}
            
            logging.info(f"Загружено эмбеддингов для {len(self.hero_embeddings)} героев")
            return bool(self.hero_embeddings)
        except Exception as e:
            logging.error(f"Ошибка загрузки эмбеддингов: {e}")
            return False
            
    def is_ready(self) -> bool:
        return all((self.ort_session, self.input_name, self.hero_embeddings))
        
    def crop_image_to_recognition_area(self, image_pil: Image.Image) -> Image.Image:
        w, h = image_pil.size
        area = RECOGNITION_AREA
        l, t, r, b = int(w * area['left_pct']/100), int(h * area['top_pct']/100), int(w * (area['left_pct']+area['width_pct'])/100), int(h * (area['top_pct']+area['height_pct'])/100)
        return image_pil.crop((l, t, r, b))
        
    def pad_image_to_target_size(self, image_pil, target_height, target_width, padding_color=(0,0,0)):
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
        
    def preprocess_image_for_dino(self, image_pil: Image.Image) -> Optional[Image.Image]:
        if image_pil.mode != 'RGB': image_pil = image_pil.convert('RGB')
        return image_pil
        
    def get_cls_embeddings_for_batched_pil(self, pil_images_batch: List[Image.Image]) -> np.ndarray:
        if not self.is_ready() or not pil_images_batch: return np.array([])
        
        processed = [self.preprocess_image_for_dino(self.pad_image_to_target_size(img, TARGET_SIZE, TARGET_SIZE)) for img in pil_images_batch]
        
        valid_imgs = [img for img in processed if img is not None]
        if not valid_imgs: return np.array([])
        
        arrays = []
        for img in valid_imgs:
            arr = (np.array(img, dtype=np.float32)/255.0 - np.array(IMAGE_MEAN, dtype=np.float32)) / np.array(IMAGE_STD, dtype=np.float32)
            arrays.append(np.transpose(arr, (2, 0, 1)))
        
        outputs = self.ort_session.run(None, {self.input_name: np.stack(arrays, axis=0)})
        embeddings = outputs[0][:, 0, :]
        
        # Используем Numba для ускорения нормализации
        if NUMBA_AVAILABLE:
            batch_size = embeddings.shape[0]
            emb_size = embeddings.shape[1]
            arrays_data = embeddings.flatten()
            embeddings = get_embeddings_for_batch_jit(arrays_data, (batch_size, emb_size))
        else:
            # Стандартная нормализация
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = np.divide(embeddings, norms, out=np.zeros_like(embeddings), where=norms!=0)
        
        return embeddings
        
    def get_best_match(self, query_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        if query_embedding.size == 0: return None, 0.0
        all_sims = sorted([(h, np.dot(query_embedding, emb)) for h, el in self.hero_embeddings.items() for emb in el], key=lambda x: x[1], reverse=True)
        return all_sims[0] if all_sims else (None, 0.0)
        
    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        return hero_name.replace('_', ' ').title().replace('And', '&')
        
    def method_fast_projection(self, image_pil: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Улучшенный метод поиска кандидатов - как в Rust коде"""
        height = image_pil.height
        
        # Создаем кандидатов с фиксированным шагом, как в Rust
        candidate_squares = []
        for y in range(0, height - HERO_SQUARE_SIZE + 1, STEP_SIZE):
            candidate_squares.append((LEFT_OFFSET, y, HERO_SQUARE_SIZE, HERO_SQUARE_SIZE))
        
        return candidate_squares
        
    def recognize_heroes_optimized(self, test_file_index: int, save_debug: bool = False) -> List[str]:
        """Оптимизированное распознавание героев с использованием NMS"""
        scr_path = os.path.join(SCREENSHOTS_DIR, f"{test_file_index}.png")
        if not os.path.exists(scr_path): 
            return []
        
        scr_pil = self.crop_image_to_recognition_area(Image.open(scr_path))
        
        if save_debug:
            scr_pil.save(os.path.join(DEBUG_DIR, f"debug_crop_{test_file_index}.png"))
        
        logging.info(f"Размер скриншота: {scr_pil.width}x{scr_pil.height}")
        
        roi_dir = None
        if save_debug:
            roi_dir = os.path.join(DEBUG_DIR, f"roi_test_{test_file_index}")
            os.makedirs(roi_dir, exist_ok=True)
        
        # Этап 1: Находим всех кандидатов с улучшенным методом
        candidate_squares = self.method_fast_projection(scr_pil)
        logging.info(f"Найдено {len(candidate_squares)} уникальных кандидатов для распознавания")
        
        if not candidate_squares:
            return []
            
        # Этап 2: Пакетная обработка всех кандидатов
        rois_batch = [scr_pil.crop((x, y, x + w, y + h)) for (x, y, w, h) in candidate_squares]
        all_embeddings = self.get_cls_embeddings_for_batched_pil(rois_batch)
        
        if all_embeddings.size == 0:
            return []
            
        # Этап 3: Сопоставление результатов
        all_detections = []
        for i, embedding in enumerate(all_embeddings):
            best_hero, confidence = self.get_best_match(embedding)
            
            if best_hero and confidence >= CONFIDENCE_THRESHOLD:
                x, y, w, h = candidate_squares[i]
                all_detections.append({
                    'hero': best_hero,
                    'confidence': confidence,
                    'position': (x, y),
                    'size': (w, h)
                })
                
                if save_debug:
                    roi = rois_batch[i]
                    roi_filename = os.path.join(roi_dir, f"roi_{i:02d}_{best_hero}_conf{confidence:.3f}.png")
                    roi.save(roi_filename)
        
        logging.info(f"Всего найдено {len(all_detections)} детекций с уверенностью >= {CONFIDENCE_THRESHOLD}")
        
        # Этап 4: Применяем NMS для удаления пересекающихся детекций
        nms_detections = non_max_suppression(all_detections, iou_threshold=0.4)
        logging.info(f"Осталось {len(nms_detections)} детекций после NMS")
        
        # Этап 5: Выбираем лучшего кандидата для каждого уникального героя
        hero_dict = {}
        for det in nms_detections:
            hero_name = det['hero']
            if hero_name not in hero_dict or det['confidence'] > hero_dict[hero_name]['confidence']:
                hero_dict[hero_name] = det
        
        unique_detections = sorted(hero_dict.values(), key=lambda x: x['confidence'], reverse=True)
        final_detections = unique_detections[:MAX_HEROES]
        final_detections.sort(key=lambda x: x['position'][1])
        
        result = [det['hero'] for det in final_detections]
        
        logging.info(f"\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ (оптимизированный с NMS) ===")
        logging.info(f"Распознано героев: {len(result)}")
        for i, detection in enumerate(final_detections, 1):
            logging.info(f"  {i}. {self.normalize_hero_name_for_display(detection['hero'])} "
                       f"(уверенность: {detection['confidence']:.3f}, позиция: {detection['position']})")
        
        return result

def calculate_metrics(recognized, expected):
    rec_set, exp_set = set(recognized), set(expected)
    correct = len(rec_set & exp_set)
    fp, fn = len(rec_set - exp_set), len(exp_set - rec_set)
    precision = correct / len(rec_set) if rec_set else 0
    recall = correct / len(exp_set) if exp_set else 0
    f1 = 2*precision*recall / (precision+recall) if (precision+recall) > 0 else 0
    return {'correct': correct, 'false_positive': fp, 'false_negative': fn, 'precision': precision, 'recall': recall, 'f1': f1}

def print_test_summary(total_stats, recognition_times):
    logging.info(f"\n{'='*60}\nСВОДНЫЙ ОТЧЕТ ПО ТЕСТИРОВАНИЮ\n{'='*60}")
    logging.info(f"Всего тестов: {total_stats['total_tests']}")
    if total_stats['total_tests'] > 0:
        avg_p = total_stats['total_precision'] / total_stats['total_tests']
        avg_r = total_stats['total_recall'] / total_stats['total_tests']
        avg_f1 = total_stats['total_f1'] / total_stats['total_tests']
        logging.info(f"Средняя точность (Precision): {avg_p:.3f}")
        logging.info(f"Средняя полнота (Recall): {avg_r:.3f}")
        logging.info(f"Средний F1-score: {avg_f1:.3f}")
        logging.info(f"\nДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:\n{'-'*80}")
        logging.info(f"{'Тест':<10} {'Верных':<8} {'Ложных':<8} {'Пропущ':<8} {'Precision':<10} {'Recall':<10} {'F1':<10}")
        logging.info(f"{'-'*80}")
        for res in total_stats['results']:
            logging.info(f"{res['test_id']:<10} {res['correct']:<8} {res['false_positive']:<8} {res['false_negative']:<8} {res['precision']:<10.3f} {res['recall']:<10.3f} {res['f1']:<10.3f}")
        logging.info(f"{'-'*80}")
    
    # Логирование среднего времени
    if recognition_times:
        avg_time = sum(recognition_times) / len(recognition_times)
        logging.info(f"\nСреднее время распознавания одного скриншота: {avg_time:.3f} секунд")
        if NUMBA_AVAILABLE:
            logging.info(f"(Ускорено с помощью Numba JIT)")
        logging.info(f"{'='*60}")

def main():
    if NUMBA_AVAILABLE:
        logging.info("Numba доступна - будет использовано ускорение JIT")
    else:
        logging.warning("Numba не установлена - будет использован стандартный режим")
    
    system = HeroRecognitionSystem()
    if not all([system.load_model(), system.load_embeddings()]):
        return
    
    logging.info("Система готова! Начинаем тестирование...")
    
    try:
        with open(CORRECT_ANSWERS_FILE, 'r', encoding='utf-8') as f:
            correct_answers = json.load(f)
    except FileNotFoundError:
        logging.error(f"Файл ответов не найден: {CORRECT_ANSWERS_FILE}")
        return
    
    total_stats = {'total_tests': 0, 'total_precision': 0, 'total_recall': 0, 'total_f1': 0, 'results': []}
    recognition_times = []
    
    for i in range(1, 8):
        if os.path.exists(os.path.join(SCREENSHOTS_DIR, f"{i}.png")):
            logging.info(f"\n{'='*80}\nТЕСТИРОВАНИЕ СКРИНШОТА {i}\n{'='*80}")
            
            start_time = time.time()
            recognized_raw = system.recognize_heroes_optimized(test_file_index=i, save_debug=True)
            end_time = time.time()
            
            current_time = end_time - start_time
            recognition_times.append(current_time)
            logging.info(f"Время выполнения для теста {i}: {current_time:.3f} секунд")
            
            expected = correct_answers.get(str(i), [])
            recognized_norm = [system.normalize_hero_name_for_display(h) for h in recognized_raw]
            metrics = calculate_metrics(recognized_norm, expected)
            
            logging.info(f"\n=== СРАВНЕНИЕ С ОЖИДАЕМЫМ РЕЗУЛЬТАТОМ ===")
            logging.info(f"Ожидаемые герои: {expected}")
            logging.info(f"Распознанные герои: {recognized_norm}")
            logging.info(f"Правильных: {metrics['correct']}, Ложных срабатываний: {metrics['false_positive']}, Пропущенных: {metrics['false_negative']}")
            logging.info(f"Precision: {metrics['precision']:.3f}, Recall: {metrics['recall']:.3f}, F1-score: {metrics['f1']:.3f}")
            
            total_stats['total_tests'] += 1
            total_stats['total_precision'] += metrics['precision']
            total_stats['total_recall'] += metrics['recall']
            total_stats['total_f1'] += metrics['f1']
            total_stats['results'].append({'test_id': f"Тест {i}", **metrics})
        else:
            logging.warning(f"Скриншот {i}.png не найден, пропуск.")
            
    print_test_summary(total_stats, recognition_times)

if __name__ == "__main__":
    main()