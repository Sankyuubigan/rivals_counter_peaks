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

# =============================================================================
# ПУТИ К РЕСУРСАМ
# =============================================================================
VISION_MODELS_DIR = "vision_models"
MODEL_PATH = "vision_models/dinov3-vitb16-pretrain-lvd1689m/model_q4.onnx"
EMBEDDINGS_DIR = "resources/embeddings_padded"
HEROES_ICONS_DIR = "resources/heroes_icons"
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
    if os.path.isfile(item_path) and item != LOG_FILENAME: os.unlink(item_path)
    elif os.path.isdir(item_path): shutil.rmtree(item_path)

# Настройка логирования
logger = logging.getLogger()
logger.setLevel(logging.INFO)
for handler in logger.handlers[:]: logger.removeHandler(handler)
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
TARGET_SIZE = 95
LEFT_OFFSET = 45

# =============================================================================
# КОНСТАНТЫ
# =============================================================================
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]
WINDOW_SIZE_W_DINO = TARGET_SIZE
WINDOW_SIZE_H_DINO = TARGET_SIZE
ROI_GENERATION_STRIDE_Y_DINO = int(WINDOW_SIZE_H_DINO * 0.25)
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0, 0, 0)

AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
AKAZE_MIN_MATCH_COUNT_COLUMN_LOC = 3
AKAZE_MIN_MATCH_COUNT_HERO_LOC = 5
MIN_HEROES_FOR_COLUMN_DETECTION = 2

ROI_X_JITTER_VALUES_DINO = [-5, 0, 5]
ROI_Y_JITTER_VALUES_DINO = [-3, 0, 3]

DINOV2_LOGGING_SIMILARITY_THRESHOLD = 0.10
DINOV2_FINAL_DECISION_THRESHOLD = 0.6
DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE = 0.40

TEAM_SIZE = 6
Y_OVERLAP_THRESHOLD_RATIO = 0.3

RECOGNITION_AREA = {
    'monitor': 1, 'left_pct': 50, 'top_pct': 20, 'width_pct': 20, 'height_pct': 50
}

class HeroRecognitionSystem:
    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, List[np.ndarray]] = {}
        self.hero_icons: Dict[str, List[np.ndarray]] = {}
        self.hero_stats = {}
        self.last_column_x_center = None
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
                self.hero_stats[hero_name] = {'akaze_found': 0, 'dino_confirmed': 0, 'avg_similarity': 0.0}
            logging.info(f"Загружено эмбеддингов для {len(self.hero_embeddings)} героев")
            return bool(self.hero_embeddings)
        except Exception as e:
            logging.error(f"Ошибка загрузки эмбеддингов: {e}")
            return False

    def load_hero_icons(self) -> bool:
        try:
            for icon_file in os.listdir(HEROES_ICONS_DIR):
                if not icon_file.lower().endswith(('.png', '.jpg', '.jpeg')): continue
                base_name = os.path.splitext(icon_file)[0]
                parts = base_name.split('_')
                hero_name = '_'.join(parts[:-1]) if len(parts) > 1 and parts[-1].isdigit() else base_name
                img = cv2.imread(os.path.join(HEROES_ICONS_DIR, icon_file), cv2.IMREAD_UNCHANGED)
                if img is None: continue
                if len(img.shape) == 3 and img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                if hero_name not in self.hero_icons: self.hero_icons[hero_name] = []
                self.hero_icons[hero_name].append(img)
            logging.info(f"Загружено иконок для {len(self.hero_icons)} героев")
            return bool(self.hero_icons)
        except Exception as e:
            logging.error(f"Ошибка загрузки иконок: {e}")
            return False

    def is_ready(self) -> bool:
        return all((self.ort_session, self.input_name, self.hero_embeddings, self.hero_icons))

    def crop_image_to_recognition_area(self, image_pil: Image.Image) -> Image.Image:
        w, h = image_pil.size
        area = RECOGNITION_AREA
        l, t, r, b = int(w * area['left_pct']/100), int(h * area['top_pct']/100), int(w * (area['left_pct']+area['width_pct'])/100), int(h * (area['top_pct']+area['height_pct'])/100)
        return image_pil.crop((l, t, r, b))

    def pad_image_to_target_size(self, image_pil: Image.Image) -> Image.Image:
        padded = Image.new("RGB", (TARGET_SIZE, TARGET_SIZE), PADDING_COLOR_WINDOW_DINO)
        padded.paste(image_pil, ((TARGET_SIZE - image_pil.width) // 2, (TARGET_SIZE - image_pil.height) // 2))
        return padded

    def preprocess_image_for_dino(self, image_pil: Image.Image) -> Optional[Image.Image]:
        if image_pil.mode != 'RGB': image_pil = image_pil.convert('RGB')
        # Убираем фильтры, чтобы соответствовать созданию эмбеддингов
        return image_pil

    def get_cls_embeddings_for_batched_pil(self, pil_images_batch: List[Image.Image]) -> np.ndarray:
        if not self.is_ready() or not pil_images_batch: return np.array([])
        processed = [self.preprocess_image_for_dino(self.pad_image_to_target_size(img)) for img in pil_images_batch]
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

    def get_hero_column_center_akaze(self, large_image_cv2: np.ndarray) -> Tuple[Optional[int], List[str]]:
        image_gray = cv2.cvtColor(large_image_cv2, cv2.COLOR_BGR2GRAY)
        akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
        kp_scr, des_scr = akaze.detectAndCompute(image_gray, None)
        if des_scr is None: return None, []
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        details = []
        for name, templates in self.hero_icons.items():
            max_good = 0
            best_coords = []
            for tpl in templates:
                tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY) if len(tpl.shape)==3 else tpl
                kp_tpl, des_tpl = akaze.detectAndCompute(tpl_gray, None)
                if des_tpl is None: continue
                matches = bf.knnMatch(des_tpl, des_scr, k=2)
                good = [m for m, n in matches if len(matches) > 1 and m.distance < AKAZE_LOWE_RATIO * n.distance]
                if len(good) > max_good:
                    max_good = len(good)
                    best_coords = [kp_scr[m.trainIdx].pt[0] for m in good]
            if max_good >= AKAZE_MIN_MATCH_COUNT_COLUMN_LOC:
                details.append({"name": name, "matches": max_good, "x_coords": best_coords})
        
        if len(details) < MIN_HEROES_FOR_COLUMN_DETECTION: return None, []
        
        sorted_heroes = sorted(details, key=lambda x: x["matches"], reverse=True)
        all_coords = [c for d in sorted_heroes for c in d['x_coords']]
        candidates = [d['name'] for d in sorted_heroes]
        for d in sorted_heroes: logging.info(f"  {d['name']}: {d['matches']} совпадений (кандидат для центра колонки)")
        if not all_coords: return None, []
        
        self.last_column_x_center = int(np.median(all_coords))
        return self.last_column_x_center, candidates

    def find_hero_positions_akaze(self, large_image_cv2: np.ndarray, target_heroes: List[str]) -> List[Dict[str, Any]]:
        if self.last_column_x_center is None: return []
        image_gray = cv2.cvtColor(large_image_cv2, cv2.COLOR_BGR2GRAY)
        akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
        kp_scr, des_scr = akaze.detectAndCompute(image_gray, None)
        if des_scr is None: return []
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        positions = []
        for name in target_heroes:
            if name not in self.hero_icons: continue
            max_good = 0
            best_data = None
            for tpl in self.hero_icons[name]:
                tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY) if len(tpl.shape)==3 else tpl
                kp_tpl, des_tpl = akaze.detectAndCompute(tpl_gray, None)
                if des_tpl is None: continue
                matches = bf.knnMatch(des_tpl, des_scr, k=2)
                good = [m for m, n in matches if len(matches) > 1 and m.distance < AKAZE_LOWE_RATIO * n.distance]
                if len(good) >= AKAZE_MIN_MATCH_COUNT_HERO_LOC and len(good) > max_good:
                    max_good = len(good)
                    y_coords = [kp_scr[m.trainIdx].pt[1] for m in good]
                    best_data = {"name": name, "matches": len(good), "x": self.last_column_x_center - WINDOW_SIZE_W_DINO // 2, "y": int(np.median(y_coords)) - WINDOW_SIZE_H_DINO // 2, "height": WINDOW_SIZE_H_DINO, "width": WINDOW_SIZE_W_DINO}
            if best_data:
                positions.append(best_data)
                logging.info(f"AKAZE нашел героя {name} в позиции ({best_data['x']}, {best_data['y']}) с {best_data['matches']} совпадениями")
        return positions

    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        return hero_name.replace('_', ' ').title().replace('And', '&')

    def generate_rois(self, s_width: int, s_height: int, column_x_center: Optional[int], akaze_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rois = []
        if column_x_center is None: return rois
        
        covered_y = []
        logging.info(f"Генерация ROI для подтверждения {len(akaze_positions)} AKAZE находок...")
        for pos in akaze_positions:
            covered_y.append((pos['y'], pos['y'] + WINDOW_SIZE_H_DINO))
            for x_off in ROI_X_JITTER_VALUES_DINO:
                for y_off in ROI_Y_JITTER_VALUES_DINO:
                    rx, ry = max(0, min(pos['x'] + x_off, s_width - WINDOW_SIZE_W_DINO)), max(0, min(pos['y'] + y_off, s_height - WINDOW_SIZE_H_DINO))
                    rois.append({'x': rx, 'y': ry, 'width': WINDOW_SIZE_W_DINO, 'height': WINDOW_SIZE_H_DINO, 'source': 'akaze', 'hero_name': pos['name']})
        
        logging.info("Генерация ROI для систематического сканирования колонки...")
        base_x = max(0, min(column_x_center - WINDOW_SIZE_W_DINO // 2, s_width - WINDOW_SIZE_W_DINO))
        for y in range(0, s_height - WINDOW_SIZE_H_DINO + 1, ROI_GENERATION_STRIDE_Y_DINO):
            if not any(max(y, s) < min(y + WINDOW_SIZE_H_DINO, e) for s, e in covered_y):
                rois.append({'x': base_x, 'y': y, 'width': WINDOW_SIZE_W_DINO, 'height': WINDOW_SIZE_H_DINO, 'source': 'scan'})
        
        logging.info(f"Сгенерировано всего {len(rois)} ROI для анализа.")
        return rois

    def recognize_heroes(self, test_file_index: int, save_debug: bool = True) -> List[str]:
        start_time = time.time()
        
        scr_path = os.path.join(SCREENSHOTS_DIR, f"{test_file_index}.png")
        if not os.path.exists(scr_path): return []

        scr_pil = self.crop_image_to_recognition_area(Image.open(scr_path))
        if save_debug:
            scr_pil.save(os.path.join(DEBUG_DIR, "debug_crop.png"))
            logging.info(f"Сохранен отладочный скриншот: {os.path.join(DEBUG_DIR, 'debug_crop.png')}")
        
        scr_cv2 = cv2.cvtColor(np.array(scr_pil), cv2.COLOR_RGB2BGR)
        logging.info(f"Размер скриншота: {scr_pil.width}x{scr_pil.height}")

        col_center, akaze_cand = self.get_hero_column_center_akaze(scr_cv2)
        akaze_pos = self.find_hero_positions_akaze(scr_cv2, akaze_cand)
        
        rois = self.generate_rois(scr_pil.width, scr_pil.height, col_center, akaze_pos)
        if not rois: return []

        if save_debug:
            roi_dir = os.path.join(DEBUG_DIR, f"roi_test_{test_file_index}")
            os.makedirs(roi_dir, exist_ok=True)
            logging.info(f"Сохранение ROI в директорию: {roi_dir}")

        all_detections = []
        for i in range(0, len(rois), BATCH_SIZE_SLIDING_WINDOW_DINO):
            if i % 10 == 0: logging.info(f"Обработка ROI {i}/{len(rois)}")
            
            batch_rois = rois[i:i+BATCH_SIZE_SLIDING_WINDOW_DINO]
            batch_pil = [scr_pil.crop((c['x'], c['y'], c['x']+c['width'], c['y']+c['height'])) for c in batch_rois]
            
            if save_debug:
                for j, roi_img in enumerate(batch_pil):
                    c = batch_rois[j]
                    roi_img.save(os.path.join(roi_dir, f"roi_{i+j:03d}_x{c['x']}_y{c['y']}.png"))

            embeddings = self.get_cls_embeddings_for_batched_pil(batch_pil)
            for j, emb in enumerate(embeddings):
                (best, sim), _ = self.get_best_match(emb, f"ROI_{i+j}")
                if best and sim >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                    det = batch_rois[j].copy()
                    det.update({"name": best, "similarity": sim})
                    all_detections.append(det)

        final_team, occupied_slots = [], []
        
        # Этап 1: AKAZE + DINO
        for pos in akaze_pos:
            name_raw, name_norm = pos['name'], self.normalize_hero_name_for_display(pos['name'])
            if name_norm in {self.normalize_hero_name_for_display(h['name']) for h in final_team}: continue
            
            best_confirm = {"similarity": -1.0}
            for det in all_detections:
                if det.get('source') == 'akaze' and det.get('hero_name') == name_raw and det['name'] == name_raw:
                    if det['similarity'] > best_confirm['similarity']:
                        best_confirm = det
            
            if best_confirm['similarity'] >= DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE:
                logging.info(f"Добавлен герой (AKAZE+DINO): {name_norm} (sim: {best_confirm['similarity']:.3f})")
            else:
                logging.info(f"Добавлен герой (AKAZE только): {name_norm} (совпадений: {pos['matches']})")
            
            final_team.append(pos)
            occupied_slots.append(pos)
        
        # Этап 2: DINO only
        dino_cands = sorted([d for d in all_detections if d['similarity'] >= DINOV2_FINAL_DECISION_THRESHOLD], key=lambda x: x['similarity'], reverse=True)
        for cand in dino_cands:
            if len(final_team) >= TEAM_SIZE: break
            cand_norm = self.normalize_hero_name_for_display(cand['name'])
            if cand_norm in {self.normalize_hero_name_for_display(h['name']) for h in final_team}: continue
            
            is_overlapping = False
            for slot in occupied_slots:
                overlap_start = max(cand['y'], slot['y'])
                overlap_end = min(cand['y'] + cand['height'], slot['y'] + slot['height'])
                overlap_height = overlap_end - overlap_start
                
                if overlap_height > (WINDOW_SIZE_H_DINO * Y_OVERLAP_THRESHOLD_RATIO):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                logging.info(f"Добавлен герой (DINO только): {cand_norm} (sim: {cand['similarity']:.3f})")
                final_team.append(cand)
                occupied_slots.append({'y': cand['y'], 'height': cand['height'], 'width': cand['width']})

        final_team.sort(key=lambda x: x['y'])
        raw_names = [h['name'] for h in final_team]
        
        logging.info(f"\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ ===")
        logging.info(f"Время выполнения: {time.time() - start_time:.2f} секунд")
        logging.info(f"Распознано героев: {len(raw_names)}")
        for i, name in enumerate(raw_names, 1):
            logging.info(f"  {i}. {self.normalize_hero_name_for_display(name)}")
            
        return raw_names

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
    if not all([system.load_model(), system.load_embeddings(), system.load_hero_icons()]):
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
            recognized_raw = system.recognize_heroes(test_file_index=i)
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