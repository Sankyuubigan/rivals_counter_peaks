import os
import sys
import time
import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from PIL import Image
import onnxruntime
import shutil
from hero_recognition_system import HeroRecognitionSystem
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
            
            # Загружаем изображение
            scr_path = os.path.join(SCREENSHOTS_DIR, f"{i}.png")
            full_image = Image.open(scr_path)
            
            # Обрезаем до области распознавания
            roi_image = system.crop_image_to_recognition_area(full_image)
            
            # Распознаем героев
            recognized_raw = system.recognize_heroes_optimized(roi_image, debug_id=str(i))
            
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