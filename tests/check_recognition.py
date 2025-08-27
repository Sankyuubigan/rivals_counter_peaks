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

# Параметры для распознавания
CONFIDENCE_THRESHOLD = 0.65
MAX_HEROES = 6
BATCH_SIZE_SLIDING_WINDOW_DINO = 32

# Параметры для поиска квадратов
HERO_SQUARE_SIZE = 95
MIN_SQUARE_SIZE = 85
MAX_SQUARE_SIZE = 105
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
        
    def get_best_match(self, query_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        if query_embedding.size == 0: return None, 0.0
        all_sims = sorted([(h, np.dot(query_embedding, emb)) for h, el in self.hero_embeddings.items() for emb in el], key=lambda x: x[1], reverse=True)
        return all_sims[0] if all_sims else (None, 0.0)
        
    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        return hero_name.replace('_', ' ').title().replace('And', '&')
        
    def calculate_vertical_projection(self, gray_image):
        """Вычисление вертикальной проекции"""
        width, height = gray_image.size
        projection = [0] * height
        
        for y in range(height):
            row_sum = 0
            for x in range(LEFT_OFFSET, LEFT_OFFSET + HERO_SQUARE_SIZE):
                if x < width:
                    row_sum += gray_image.getpixel((x, y))
            projection[y] = row_sum
        
        return projection
        
    def find_peaks_in_projection(self, projection):
        """Поиск пиков в проекции"""
        # Сглаживание проекции
        window_size = 3
        smoothed = []
        for i in range(len(projection)):
            start = max(0, i - window_size//2)
            end = min(len(projection), i + window_size//2 + 1)
            smoothed.append(sum(projection[start:end]) / (end - start))
        
        # Поиск пиков
        peaks = []
        min_peak_height = sum(smoothed) / len(smoothed) * 0.6
        
        for i in range(1, len(smoothed)-1):
            if smoothed[i] > smoothed[i-1] and smoothed[i] > smoothed[i+1] and smoothed[i] > min_peak_height:
                peaks.append(i)
        
        return peaks
        
    def method_fast_projection(self, image_pil):
        """Быстрый метод: анализ проекций"""
        gray = image_pil.convert('L')
        width, height = gray.size
        
        # Вычисляем проекцию и находим пики
        projection = self.calculate_vertical_projection(gray)
        peaks = self.find_peaks_in_projection(projection)
        
        # Создаем квадраты вокруг пиков
        squares = []
        for peak_y in peaks:
            y = peak_y - HERO_SQUARE_SIZE // 2
            if y >= 0 and y + HERO_SQUARE_SIZE <= height:
                squares.append((LEFT_OFFSET, y, HERO_SQUARE_SIZE, HERO_SQUARE_SIZE))
        
        return squares
        
    def method_detailed_analysis(self, image_pil, check_positions=None):
        """Детальный метод: комбинированный анализ"""
        gray = image_pil.convert('L')
        width, height = gray.size
        
        squares = []
        
        # Если указаны позиции для проверки, проверяем только их
        if check_positions:
            for y in check_positions:
                if y >= 0 and y + HERO_SQUARE_SIZE <= height:
                    region = gray.crop((LEFT_OFFSET, y, LEFT_OFFSET + HERO_SQUARE_SIZE, y + HERO_SQUARE_SIZE))
                    if self.is_hero_region(region):
                        squares.append((LEFT_OFFSET, y, HERO_SQUARE_SIZE, HERO_SQUARE_SIZE))
        else:
            # Иначе проверяем с шагом HERO_SQUARE_SIZE // 2
            for y in range(0, height - HERO_SQUARE_SIZE, HERO_SQUARE_SIZE // 2):
                region = gray.crop((LEFT_OFFSET, y, LEFT_OFFSET + HERO_SQUARE_SIZE, y + HERO_SQUARE_SIZE))
                if self.is_hero_region(region):
                    squares.append((LEFT_OFFSET, y, HERO_SQUARE_SIZE, HERO_SQUARE_SIZE))
        
        return squares
        
    def is_hero_region(self, region):
        """Проверка, является ли регион квадратом с героем"""
        histogram = region.histogram()
        total_pixels = sum(histogram)
        if total_pixels == 0:
            return False
        
        brightness = sum(i * count for i, count in enumerate(histogram)) / total_pixels
        
        if 5 < brightness < 250:
            pixels = list(region.getdata())
            std_dev = (sum((p - brightness)**2 for p in pixels) / len(pixels))**0.5
            
            threshold = 5 if brightness < 50 or brightness > 200 else 8
            
            if std_dev > threshold:
                return True
        
        return False
        
    def recognize_heroes_optimized(self, test_file_index: int, save_debug: bool = True) -> List[str]:
        """Оптимизированное распознавание героев"""
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
        
        # Этап 1: Быстрый анализ проекций
        fast_squares = self.method_fast_projection(scr_pil)
        logging.info(f"Быстрый метод нашел {len(fast_squares)} квадратов")
        
        # Проверяем найденные квадраты
        all_detections = []
        checked_positions = set()
        
        for i, (x, y, w, h) in enumerate(fast_squares):
            roi = scr_pil.crop((x, y, x + w, y + h))
            
            if save_debug:
                roi_filename = os.path.join(roi_dir, f"roi_fast_{i:03d}_x{x}_y{y}.png")
                roi.save(roi_filename)
            
            embedding = self.get_cls_embeddings_for_batched_pil([roi])
            if embedding.size == 0:
                continue
            
            best_hero, confidence = self.get_best_match(embedding[0])
            
            if save_debug and best_hero:
                roi_filename = os.path.join(roi_dir, f"roi_detected_{i:03d}_x{x}_y{y}_{best_hero.replace(' ', '_')}_conf{confidence:.3f}.png")
                roi.save(roi_filename)
                logging.info(f"Распознан герой: {best_hero} с уверенностью {confidence:.3f}")
            
            if best_hero and confidence >= CONFIDENCE_THRESHOLD:
                all_detections.append({
                    'hero': best_hero,
                    'confidence': confidence,
                    'position': (x, y),
                    'size': (w, h)
                })
                checked_positions.add(y)
        
        # Этап 2: Если нашли меньше 6 героев, используем детальный анализ
        if len(all_detections) < MAX_HEROES:
            logging.info(f"Найдено только {len(all_detections)} героев, применяем детальный анализ")
            
            # Определяем позиции для детальной проверки
            detail_positions = []
            height = scr_pil.height
            
            # Добавляем позиции вокруг найденных героев
            for y in checked_positions:
                for dy in range(-HERO_SQUARE_SIZE, HERO_SQUARE_SIZE + 1, HERO_SQUARE_SIZE // 2):
                    check_y = y + dy
                    if 0 <= check_y <= height - HERO_SQUARE_SIZE:
                        detail_positions.append(check_y)
            
            # Добавляем равномерно распределенные позиции
            step = max(HERO_SQUARE_SIZE // 2, height // (MAX_HEROES * 2))
            for y in range(0, height - HERO_SQUARE_SIZE, step):
                if y not in checked_positions and y not in detail_positions:
                    detail_positions.append(y)
            
            # Удаляем дубликаты и сортируем
            detail_positions = sorted(list(set(detail_positions)))
            
            # Применяем детальный анализ
            detail_squares = self.method_detailed_analysis(scr_pil, detail_positions)
            logging.info(f"Детальный анализ нашел {len(detail_squares)} дополнительных квадратов")
            
            for i, (x, y, w, h) in enumerate(detail_squares):
                if y in checked_positions:
                    continue
                
                roi = scr_pil.crop((x, y, x + w, y + h))
                
                if save_debug:
                    roi_filename = os.path.join(roi_dir, f"roi_detail_{i:03d}_x{x}_y{y}.png")
                    roi.save(roi_filename)
                
                embedding = self.get_cls_embeddings_for_batched_pil([roi])
                if embedding.size == 0:
                    continue
                
                best_hero, confidence = self.get_best_match(embedding[0])
                
                if save_debug and best_hero:
                    roi_filename = os.path.join(roi_dir, f"roi_detected_detail_{i:03d}_x{x}_y{y}_{best_hero.replace(' ', '_')}_conf{confidence:.3f}.png")
                    roi.save(roi_filename)
                    logging.info(f"Распознан герой: {best_hero} с уверенностью {confidence:.3f}")
                
                if best_hero and confidence >= CONFIDENCE_THRESHOLD:
                    all_detections.append({
                        'hero': best_hero,
                        'confidence': confidence,
                        'position': (x, y),
                        'size': (w, h)
                    })
                    checked_positions.add(y)
        
        # Постобработка: группировка по герою
        hero_dict = {}
        for det in all_detections:
            hero_name = det['hero']
            if hero_name not in hero_dict or det['confidence'] > hero_dict[hero_name]['confidence']:
                hero_dict[hero_name] = det
        
        # Сортируем по уверенности и берем топ-6
        unique_detections = sorted(hero_dict.values(), key=lambda x: x['confidence'], reverse=True)
        final_detections = unique_detections[:MAX_HEROES]
        
        # Сортируем по вертикальной позиции
        final_detections.sort(key=lambda x: x['position'][1])
        
        result = [det['hero'] for det in final_detections]
        
        # Логирование результатов
        total_time = time.time() - start_time
        logging.info(f"\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ (оптимизированный) ===")
        logging.info(f"Время выполнения: {total_time:.2f} секунд")
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
            logging.info(f"\n{'='*80}\nТЕСТИРОВАНИЕ СКРИНШОТА {i}\n{'='*80}")
            recognized_raw = system.recognize_heroes_optimized(test_file_index=i)
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
    print_test_summary(total_stats)

if __name__ == "__main__":
    main()