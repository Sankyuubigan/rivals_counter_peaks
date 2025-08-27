import os
import sys
import time
import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import Counter, defaultdict
import cv2
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageGrab
import onnxruntime
import shutil
from sklearn.cluster import DBSCAN
from sklearn.metrics import pairwise_distances
from scipy.signal import find_peaks

# =============================================================================
# ПУТИ К РЕСУРСАМ
# =============================================================================
VISION_MODELS_DIR = "vision_models"
MODEL_PATH = "vision_models/dinov3-vitb16-pretrain-lvd1689m/model_q4.onnx"
EMBEDDINGS_DIR = "resources/embeddings_padded"
SCREENSHOTS_DIR = "tests/for_recogn/screenshots"
CORRECT_ANSWERS_FILE = "tests/for_recogn/correct_answers.json"
DEBUG_DIR = "tests/debug"

# Создаем директорию для отладки перед настройкой логирования
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

# Параметры для скользящего окна
WINDOW_SIZE = 95
STRIDE = 80
CONFIDENCE_THRESHOLD = 0.65
MAX_HEROES = 6

# Параметры распознавания
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
TEAM_SIZE = 6
Y_OVERLAP_THRESHOLD_RATIO = 0.3

# Параметры для колонок
COLUMN_WIDTH = 100  # Ширина колонки для ROI

RECOGNITION_AREA = {
    'monitor': 1, 'left_pct': 50, 'top_pct': 20, 'width_pct': 20, 'height_pct': 50
}

class HeroRecognitionSystem:
    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, List[np.ndarray]] = {}
        self.hero_stats = {}
        logging.info("Инициализация системы распознавания героев...")

    def load_model(self) -> bool:
        try:
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
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return np.divide(embeddings, norms, out=np.zeros_like(embeddings), where=norms!=0)

    def get_best_match(self, query_embedding: np.ndarray, roi_info: str = "") -> Tuple[Tuple[Optional[str], float], List[Tuple[str, float]]]:
        if query_embedding.size == 0: return (None, 0.0), []
        all_sims = sorted([(h, np.dot(query_embedding, emb)) for h, el in self.hero_embeddings.items() for emb in el], key=lambda x: x[1], reverse=True)
        top = all_sims[:5]
        if roi_info:
            logging.info(f"--- ТОП-5 СОВПАДЕНИЙ DINO ДЛЯ {roi_info} ---")
            for i, (hero, sim) in enumerate(top, 1):
                logging.info(f"  {i}. {self.normalize_hero_name_for_display(hero)}: {sim:.4f}")
        return top[0] if top else (None, 0.0), top

    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        return hero_name.replace('_', ' ').title().replace('And', '&')

    def remove_duplicate_detections(self, detections: List[Dict]) -> List[Dict]:
        """Удаляем дубликаты, учитывая вертикальное расстояние"""
        if not detections:
            return []
        
        # Сортируем по уверенности
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        keep = []
        for detection in detections:
            # Проверяем, есть ли уже герой с похожей вертикальной позицией
            is_duplicate = False
            for kept in keep:
                y_distance = abs(detection['position'][1] - kept['position'][1])
                if y_distance < WINDOW_SIZE and detection['hero'] == kept['hero']:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                keep.append(detection)
        
        return keep

    def recognize_heroes_fixed_column(self, test_file_index: int, save_debug: bool = True) -> List[str]:
        start_time = time.time()
        
        scr_path = os.path.join(SCREENSHOTS_DIR, f"{test_file_index}.png")
        if not os.path.exists(scr_path): 
            return []
        
        scr_pil = self.crop_image_to_recognition_area(Image.open(scr_path))
        if save_debug:
            scr_pil.save(os.path.join(DEBUG_DIR, "debug_crop.png"))
            logging.info(f"Сохранен отладочный скриншот: {os.path.join(DEBUG_DIR, 'debug_crop.png')}")
        
        logging.info(f"Размер скриншота: {scr_pil.width}x{scr_pil.height}")
        
        # Создаем директорию для сохранения ROI
        if save_debug:
            roi_dir = os.path.join(DEBUG_DIR, f"roi_test_{test_file_index}")
            os.makedirs(roi_dir, exist_ok=True)
            logging.info(f"Сохранение ROI в директорию: {roi_dir}")
        
        all_detections = []
        
        # Используем фиксированный отступ 45 пикселей от левого края recognition area
        column_left = LEFT_OFFSET
        column_right = min(scr_pil.width, column_left + COLUMN_WIDTH)
        
        logging.info(f"Используем колонку с фиксированным отступом: левая={column_left}, правая={column_right}")
        
        # Генерируем ROI в колонке
        rois = []
        roi_positions = []
        
        for y in range(0, scr_pil.height - WINDOW_SIZE + 1, STRIDE):
            roi = scr_pil.crop((column_left, y, column_left + WINDOW_SIZE, y + WINDOW_SIZE))
            rois.append(roi)
            roi_positions.append((column_left, y))
        
        logging.info(f"Сгенерировано {len(rois)} ROI для колонки")
        
        # Получение эмбеддингов для всех ROI
        batch_size = BATCH_SIZE_SLIDING_WINDOW_DINO
        
        for i in range(0, len(rois), batch_size):
            batch_rois = rois[i:i+batch_size]
            batch_positions = roi_positions[i:i+batch_size]
            
            embeddings = self.get_cls_embeddings_for_batched_pil(batch_rois)
            
            for j, (embedding, position) in enumerate(zip(embeddings, batch_positions)):
                if embedding.size == 0:
                    continue
                
                (best_hero, confidence), _ = self.get_best_match(embedding)
                
                if best_hero and confidence >= CONFIDENCE_THRESHOLD:
                    detection = {
                        'hero': best_hero,
                        'confidence': confidence,
                        'position': position,
                        'column_center': (column_left + column_right) // 2,
                        'column_idx': 0
                    }
                    all_detections.append(detection)
                    
                    # Сохраняем ROI с высокой уверенностью
                    if save_debug and confidence >= 0.75:
                        roi_img = batch_rois[j]
                        roi_img.save(os.path.join(roi_dir, f"roi_col1_{i+j:03d}_x{position[0]}_y{position[1]}_{best_hero.replace(' ', '_')}_conf{confidence:.3f}.png"))
        
        logging.info(f"Всего найдено {len(all_detections)} детекций с уверенностью >= {CONFIDENCE_THRESHOLD}")
        
        # Удаляем дубликаты
        final_detections = self.remove_duplicate_detections(all_detections)
        
        # Сортируем по вертикальной позиции
        final_detections.sort(key=lambda x: x['position'][1])
        
        # Ограничиваем количество героев
        final_detections = final_detections[:MAX_HEROES]
        result = [d['hero'] for d in final_detections]
        
        # Логирование результатов
        logging.info(f"\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ (DINO+фиксированная колонка) ===")
        logging.info(f"Время выполнения: {time.time() - start_time:.2f} секунд")
        logging.info(f"Распознано героев: {len(result)}")
        for i, detection in enumerate(final_detections, 1):
            logging.info(f"  {i}. {self.normalize_hero_name_for_display(detection['hero'])} "
                       f"(уверенность: {detection['confidence']:.3f}, позиция: {detection['position']}, колонка: {detection['column_idx']+1})")
        
        return result

def calculate_metrics(recognized, expected):
    rec_set, exp_set = set(recognized), set(expected)
    correct = len(rec_set & exp_set)
    fp, fn = len(rec_set - exp_set), len(exp_set - rec_set)
    precision = correct / len(rec_set) if rec_set else 0
    recall = correct / len(exp_set) if exp_set else 0
    f1 = 2*precision*recall / (precision+recall) if (precision+recall) > 0 else 0
    return {'correct': correct, 'false_positive': fp, 'false_negative': fn, 'precision': precision, 'recall': recall, 'f1': f1}

def print_test_summary(total_stats):
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

def main():
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
    for i in range(1, 8):
        if os.path.exists(os.path.join(SCREENSHOTS_DIR, f"{i}.png")):
            logging.info(f"\n=== ТЕСТИРОВАНИЕ СКРИНШОТА {i} ===")
            # Используем метод с фиксированной колонкой
            recognized_raw = system.recognize_heroes_fixed_column(test_file_index=i)
            expected = correct_answers.get(str(i), [])
            recognized_norm = [system.normalize_hero_name_for_display(h) for h in recognized_raw]
            metrics = calculate_metrics(recognized_norm, expected)
            
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
    print_test_summary(total_stats)

if __name__ == "__main__":
    main()