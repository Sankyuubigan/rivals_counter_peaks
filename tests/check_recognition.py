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

# Имя файла лога
LOG_FILENAME = "recognition_test.log"
log_file_path = os.path.join(DEBUG_DIR, LOG_FILENAME)

# Очищаем файл лога перед началом работы (РЕШЕНИЕ ПРОБЛЕМЫ 1)
if os.path.exists(log_file_path):
    try:
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write("")  # Очищаем файл
        logging.info(f"Файл лога очищен: {log_file_path}")
    except Exception as e:
        logging.warning(f"Не удалось очистить файл лога: {e}")

# Сначала очищаем директорию DEBUG_DIR (кроме файла лога)
for item in os.listdir(DEBUG_DIR):
    item_path = os.path.join(DEBUG_DIR, item)
    if os.path.isfile(item_path) and item != LOG_FILENAME:
        try:
            os.unlink(item_path)
        except PermissionError:
            logging.warning(f"Не удалось удалить файл {item_path}, возможно он используется другим процессом")
    elif os.path.isdir(item_path):
        try:
            shutil.rmtree(item_path)
        except PermissionError:
            logging.warning(f"Не удалось удалить директорию {item_path}, возможно она используется другим процессом")

# Настройка логирования с правильной кодировкой UTF-8
# Создаем логгер
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Очищаем существующие обработчики
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Создаем форматтер
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Добавляем вывод в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Добавляем вывод в файл с кодировкой UTF-8
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# =============================================================================
# ОСНОВНЫЕ НАСТРОЙКИ - ИЗМЕНИТЕ ЭТУ ПЕРЕМЕННУЮ ДЛЯ ДРУГОГО РАЗМЕРА ИЗОБРАЖЕНИЯ
# =============================================================================
TARGET_SIZE = 95  # Размер изображения для распознавания (измени эту цифру для другого размера)
LEFT_OFFSET = 45   # Отступ от левого края в пикселях
# =============================================================================
# Константы модели
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]
# Размеры ROI (используют TARGET_SIZE)
WINDOW_SIZE_W_DINO = TARGET_SIZE
WINDOW_SIZE_H_DINO = TARGET_SIZE
ROI_GENERATION_STRIDE_Y_DINO = int(WINDOW_SIZE_H_DINO * 0.5)  # УМЕНЬШИЛИ ШАГ ДЛЯ БОЛЬШЕГО КОЛИЧЕСТВА ROI
FALLBACK_DINO_STRIDE_W = int(WINDOW_SIZE_W_DINO * 0.9)
FALLBACK_DINO_STRIDE_H = int(WINDOW_SIZE_H_DINO * 0.9)
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0, 0, 0)
# Параметры AKAZE
AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
AKAZE_MIN_MATCH_COUNT_COLUMN_LOC = 3  # ПОРОГ ДЛЯ ОПРЕДЕЛЕНИЯ ЦЕНТРА КОЛОНКИ
AKAZE_MIN_MATCH_COUNT_HERO_LOC = 5      # ПОРОГ ДЛЯ ОПРЕДЕЛЕНИЯ КОНКРЕТНОГО ГЕРОЯ
MIN_HEROES_FOR_COLUMN_DETECTION = 2
# ИЗМЕНЕННЫЕ ПАРАМЕТРЫ СМЕЩЕНИЯ ROI (РЕШЕНИЕ ПРОБЛЕМЫ 2)
ROI_X_JITTER_VALUES_DINO = [-5, 0, 5]  # Увеличили диапазон смещения
ROI_Y_JITTER_VALUES_DINO = [-3, 0, 3]  # Добавили смещение по Y
MAX_NOT_PASSED_AKAZE_TO_LOG = 15
# ВОССТАНОВЛЕНЫ ПОРОГИ ИЗ СТАРОГО КОДА
DINOV2_LOGGING_SIMILARITY_THRESHOLD = 0.10
DINOV2_FINAL_DECISION_THRESHOLD = 0.65
DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE = 0.40
TEAM_SIZE = 6
Y_OVERLAP_THRESHOLD_RATIO = 0.5
# ОБЛАСТЬ ЗАХВАТА ЭКРАНА
RECOGNITION_AREA = {
    'monitor': 1, 
    'left_pct': 50, 
    'top_pct': 20, 
    'width_pct': 20,
    'height_pct': 50
}

class HeroRecognitionSystem:
    """Система распознавания героев Marvel Rivals с AKAZE для X и Y координат"""
    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, List[np.ndarray]] = {}
        self.hero_icons: Dict[str, np.ndarray] = {}
        self.similarity_stats = []
        self.test_results = []
        self.hero_stats = {}  # Статистика по каждому герою
        self.last_column_x_center = None  # Сохраняем последний известный центр колонки
        logging.info("Инициализация системы распознавания героев...")
    
    def load_model(self) -> bool:
        """Загрузка ONNX модели DINOv3"""
        try:
            if not os.path.exists(MODEL_PATH):
                logging.error(f"Модель не найдена: {MODEL_PATH}")
                return False
            self.ort_session = onnxruntime.InferenceSession(
                MODEL_PATH,
                providers=['CPUExecutionProvider']
            )
            self.input_name = self.ort_session.get_inputs()[0].name
            logging.info(f"Модель загружена. Вход: {self.input_name}")
            return True
        except Exception as e:
            logging.error(f"Ошибка загрузки модели: {e}")
            return False
    
    def load_embeddings(self) -> bool:
        """Загрузка эмбеддингов героев"""
        try:
            if not os.path.exists(EMBEDDINGS_DIR):
                logging.error(f"Директория эмбеддингов не найдена: {EMBEDDINGS_DIR}")
                return False
            embedding_files = [f for f in os.listdir(EMBEDDINGS_DIR) if f.endswith('.npy')]
            if not embedding_files:
                logging.error("Не найдено файлов эмбеддингов (.npy)")
                return False
            
            hero_embedding_groups = defaultdict(list)
            for emb_file in embedding_files:
                base_name = os.path.splitext(emb_file)[0]
                parts = base_name.split('_')
                if len(parts) >= 2 and parts[-1].isdigit():
                    hero_name = '_'.join(parts[:-1])
                else:
                    hero_name = base_name
                emb_path = os.path.join(EMBEDDINGS_DIR, emb_file)
                try:
                    embedding = np.load(emb_path)
                    # Нормализуем эталонные эмбеддинги при загрузке
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm
                    hero_embedding_groups[hero_name].append(embedding)
                except Exception as e:
                    logging.warning(f"Ошибка загрузки эмбеддинга {emb_file}: {e}")
            
            for hero_name, embeddings in hero_embedding_groups.items():
                self.hero_embeddings[hero_name] = embeddings
                # Инициализируем статистику для героя
                self.hero_stats[hero_name] = {
                    'akaze_found': 0,
                    'dino_confirmed': 0,
                    'dino_rejected': 0,
                    'avg_similarity': 0.0,
                    'recognition_rate': 0.0
                }
            
            logging.info(f"Загружено эмбеддингов для {len(self.hero_embeddings)} героев")
            return len(self.hero_embeddings) > 0
        except Exception as e:
            logging.error(f"Ошибка загрузки эмбеддингов: {e}")
            return False
    
    def load_hero_icons(self) -> bool:
        """Загрузка иконок героев для AKAZE"""
        try:
            if not os.path.exists(HEROES_ICONS_DIR):
                logging.error(f"Директория иконок не найдена: {HEROES_ICONS_DIR}")
                return False
            icon_files = [f for f in os.listdir(HEROES_ICONS_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
            for icon_file in icon_files:
                base_name = os.path.splitext(icon_file)[0]
                parts = base_name.split('_')
                if len(parts) >= 2:
                    hero_name_parts = parts[:-1]
                    hero_name = '_'.join(hero_name_parts)
                else:
                    hero_name = base_name
                
                icon_path = os.path.join(HEROES_ICONS_DIR, icon_file)
                try:
                    img = cv2.imread(icon_path, cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        # ИСПРАВЛЕНО: Используем cv2.COLOR_BGRA2BGR вместо cv2.BGRA2BGR
                        if len(img.shape) == 3 and img.shape[2] == 4:
                            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                        if hero_name not in self.hero_icons:
                            self.hero_icons[hero_name] = []
                        self.hero_icons[hero_name].append(img)
                except Exception as e:
                    logging.warning(f"Ошибка загрузки иконки {icon_file}: {e}")
            logging.info(f"Загружено иконок для героев: {len(self.hero_icons)}")
            return len(self.hero_icons) > 0
        except Exception as e:
            logging.error(f"Ошибка загрузки иконок: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Проверка готовности системы"""
        return (self.ort_session is not None and
                self.input_name is not None and
                len(self.hero_embeddings) > 0 and
                len(self.hero_icons) > 0)
    
    def capture_screen_area(self, area: Dict[str, Any] = None) -> Optional[np.ndarray]:
        """Захват области экрана с использованием PIL"""
        if area is None:
            area = RECOGNITION_AREA
        
        try:
            # Получаем размер всего экрана
            screen_width, screen_height = ImageGrab.grab().size
            
            # Вычисляем координаты и размеры области
            left = int(screen_width * area['left_pct'] / 100)
            top = int(screen_height * area['top_pct'] / 100)
            width = int(screen_width * area['width_pct'] / 100)
            height = int(screen_height * area['height_pct'] / 100)
            
            # Захватываем область
            bbox = (left, top, left + width, top + height)
            screenshot_pil = ImageGrab.grab(bbox=bbox)
            
            # Конвертируем PIL Image в numpy array (BGR формат)
            screenshot_rgb = np.array(screenshot_pil)
            screenshot_bgr = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2BGR)
            
            return screenshot_bgr
        except Exception as e:
            logging.error(f"Ошибка захвата области экрана: {e}")
            return None
    
    def crop_image_to_recognition_area(self, image_pil: Image.Image) -> Image.Image:
        """Обрезает изображение по области RECOGNITION_AREA"""
        try:
            # Получаем размер изображения
            img_width, img_height = image_pil.size
            area = RECOGNITION_AREA
            
            # Вычисляем координаты и размеры области
            left = int(img_width * area['left_pct'] / 100)
            top = int(img_height * area['top_pct'] / 100)
            width = int(img_width * area['width_pct'] / 100)
            height = int(img_height * area['height_pct'] / 100)
            
            # Обрезаем изображение
            bbox = (left, top, left + width, top + height)
            cropped_image = image_pil.crop(bbox)
            
            return cropped_image
        except Exception as e:
            logging.error(f"Ошибка обрезки изображения: {e}")
            return image_pil
    
    def save_debug_image(self, image_pil: Image.Image, filename: str, subdir: str = ""):
        """Сохраняет отладочное изображение"""
        try:
            if subdir:
                save_dir = os.path.join(DEBUG_DIR, subdir)
                os.makedirs(save_dir, exist_ok=True)
            else:
                save_dir = DEBUG_DIR
            
            filepath = os.path.join(save_dir, filename)
            image_pil.save(filepath)
        except Exception as e:
            logging.error(f"Ошибка сохранения отладочного изображения: {e}")
    
    def pad_image_to_target_size(self, image_pil: Image.Image, target_height: int, target_width: int, padding_color: Tuple[int,int,int]) -> Image.Image:
        """Паддинг изображения до целевого размера (как в старом коде)"""
        if image_pil is None:
            return Image.new("RGB", (target_width, target_height), padding_color)
        
        original_width, original_height = image_pil.size
        if original_width == target_width and original_height == target_height:
            return image_pil
        
        target_aspect = target_width / target_height if target_height != 0 else 1.0
        original_aspect = original_width / original_height if original_height != 0 else 1.0
        
        if original_aspect > target_aspect:
            new_width = target_width
            new_height = int(new_width / original_aspect) if original_aspect != 0 else 0
        else:
            new_height = target_height
            new_width = int(new_height * original_aspect)
        
        if new_width <= 0 or new_height <= 0:
            return Image.new("RGB", (target_width, target_height), padding_color)
        
        try:
            resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except ValueError:
            return Image.new("RGB", (target_width, target_height), padding_color)
        
        padded_image = Image.new("RGB", (target_width, target_height), padding_color)
        paste_x = (target_width - new_width) // 2
        paste_y = (target_height - new_height) // 2
        padded_image.paste(resized_image, (paste_x, paste_y))
        
        return padded_image
    
    def preprocess_image_for_dino(self, image_pil: Image.Image) -> Image.Image:
        """Предобработка изображения для DINO (упрощенная как в старом коде)"""
        if image_pil is None:
            return None
        
        try:
            # Убедимся, что изображение в RGB
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')
            
            # Применяем простое нерезкое маскирование (как в старом коде)
            sharpened_image_pil = image_pil.filter(
                ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3)
            )
            
            return sharpened_image_pil
        except Exception as e:
            logging.error(f"Ошибка в preprocess_image_for_dino: {e}")
            return None
    
    def get_cls_embeddings_for_batched_pil(self, pil_images_batch: List[Image.Image]) -> np.ndarray:
        """Получение эмбеддингов для батча изображений (батчевая обработка)"""
        if not self.is_ready():
            return np.array([])
        
        if not pil_images_batch or not self.ort_session or not self.input_name:
            return np.array([])
        
        # Применяем паддинг к каждому изображению в батче
        padded_batch_for_processor = []
        for img in pil_images_batch:
            if img is not None:
                padded_img = self.pad_image_to_target_size(img, TARGET_SIZE, TARGET_SIZE, PADDING_COLOR_WINDOW_DINO)
                padded_batch_for_processor.append(padded_img)
        
        if not padded_batch_for_processor:
            return np.array([])
        
        # Предобрабатываем каждое изображение
        processed_batch = []
        for img in padded_batch_for_processor:
            preprocessed_img = self.preprocess_image_for_dino(img)
            if preprocessed_img is not None:
                processed_batch.append(preprocessed_img)
        
        if not processed_batch:
            return np.array([])
        
        # Конвертируем в numpy массив и нормализуем
        batch_arrays = []
        for img in processed_batch:
            img_array = np.array(img, dtype=np.float32) / 255.0
            
            # Нормализация ImageNet
            mean = np.array(IMAGE_MEAN, dtype=np.float32)
            std = np.array(IMAGE_STD, dtype=np.float32)
            img_array = (img_array - mean) / std
            
            # Транспонирование HWC -> CHW
            img_array = np.transpose(img_array, (2, 0, 1))
            batch_arrays.append(img_array)
        
        # Объединяем в батч
        batch_tensor = np.stack(batch_arrays, axis=0)
        
        # Получаем эмбеддинги через модель
        try:
            onnx_outputs = self.ort_session.run(None, {self.input_name: batch_tensor})
            last_hidden_state = onnx_outputs[0]
            
            # Извлекаем только CLS токены (как в старом коде)
            batch_cls_embeddings = last_hidden_state[:, 0, :]
            
            # Нормализуем эмбеддинги
            normalized_embeddings = []
            for embedding in batch_cls_embeddings:
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    normalized_embeddings.append(embedding / norm)
                else:
                    normalized_embeddings.append(embedding)
            
            return np.array(normalized_embeddings)
            
        except Exception as e:
            logging.error(f"Ошибка получения эмбеддингов: {e}")
            return np.array([])
    
    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Вычисление косинусного сходства"""
        if vec_a is None or vec_b is None or len(vec_a) == 0 or len(vec_b) == 0:
            return 0.0
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
    
    def get_best_match(self, query_embedding: np.ndarray, roi_info: str = "") -> Tuple[Optional[str], float, List[Tuple[str, float]]]:
        """
        Находит лучшее совпадение со всеми эмбеддингами героя
        Возвращает: (имя героя, схожесть, топ-5 совпадений)
        """
        if len(query_embedding) == 0:
            return None, 0.0, []
        
        best_sim = -1.0
        best_hero = None
        all_similarities = []
        
        # Сравниваем со всеми эмбеддингами всех героев
        for hero_name, hero_emb_list in self.hero_embeddings.items():
            for hero_emb in hero_emb_list:
                similarity = self.cosine_similarity(query_embedding, hero_emb)
                all_similarities.append((hero_name, similarity))
                
                if similarity > best_sim:
                    best_sim = similarity
                    best_hero = hero_name
        
        # Сортируем все сходства и берем топ-5
        all_similarities.sort(key=lambda x: x[1], reverse=True)
        top_matches = all_similarities[:5]
        
        # Логируем топ-5 совпадений для DINO
        if roi_info:
            logging.info(f"--- ТОП-5 СОВПАДЕНИЙ DINO ДЛЯ {roi_info} ---")
            for i, (hero, sim) in enumerate(top_matches, 1):
                logging.info(f"  {i}. {self.normalize_hero_name_for_display(hero)}: {sim:.4f}")
        
        return best_hero, best_sim, top_matches
    
    def get_hero_specific_threshold(self, hero_name: str, base_threshold: float) -> float:
        """
        Возвращает индивидуальный порог для каждого героя на основе статистики
        """
        # Если у нас еще нет статистики, используем базовый порог
        if hero_name not in self.hero_stats or self.hero_stats[hero_name]['akaze_found'] < 3:
            return base_threshold
        
        # Получаем статистику для героя
        stats = self.hero_stats[hero_name]
        
        # Если у героя низкий процент подтверждения DINO, снижаем порог
        if stats['akaze_found'] > 0:
            confirmation_rate = stats['dino_confirmed'] / stats['akaze_found']
            if confirmation_rate < 0.5:  # Если подтверждается менее 50%
                return base_threshold * 0.7  # Сильно снижаем порог
            elif confirmation_rate < 0.7:  # Если подтверждается 50-70%
                return base_threshold * 0.85  # Умеренно снижаем порог
        
        # Если среднее сходство низкое, снижаем порог
        if stats['avg_similarity'] > 0 and stats['avg_similarity'] < 0.3:
            return base_threshold * 0.8
        
        return base_threshold
    
    def get_adaptive_threshold(self, base_threshold: float, akaze_matches: int, hero_name: str = "") -> float:
        """
        Адаптивный порог на основе количества AKAZE совпадений и статистики героя
        """
        # Базовые корректировки на основе AKAZE совпадений
        if akaze_matches >= 20:
            threshold_multiplier = 0.6
        elif akaze_matches >= 15:
            threshold_multiplier = 0.7
        elif akaze_matches >= 10:
            threshold_multiplier = 0.8
        elif akaze_matches >= 6:
            threshold_multiplier = 0.9
        else:
            threshold_multiplier = 1.0
        
        # Получаем индивидуальный порог для героя
        hero_specific_threshold = self.get_hero_specific_threshold(hero_name, base_threshold)
        
        return hero_specific_threshold * threshold_multiplier
    
    def check_rectangle_overlap(self, rect1: Dict[str, int], rect2: Dict[str, int]) -> bool:
        """Проверяет пересечение двух прямоугольников"""
        x1 = max(rect1['x'], rect2['x'])
        y1 = max(rect1['y'], rect2['y'])
        x2 = min(rect1['x'] + rect1['width'], rect2['x'] + rect2['width'])
        y2 = min(rect1['y'] + rect1['height'], rect2['y'] + rect2['height'])
        
        return x1 < x2 and y1 < y2
    
    def get_hero_column_center_akaze(self, large_image_cv2: np.ndarray) -> Tuple[Optional[int], List[str]]:
        """Определение центра колонки героев с помощью AKAZE (порог 3) - УЛУЧШЕННАЯ ВЕРСИЯ"""
        if large_image_cv2 is None:
            return None, []
        if not self.hero_icons:
            return None, []
        
        try:
            image_gray = cv2.cvtColor(large_image_cv2, cv2.COLOR_BGR2GRAY)
        except cv2.error as e:
            logging.error(f"Ошибка конвертации в серое: {e}")
            return None, []
        
        akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
        try:
            kp_screenshot, des_screenshot = akaze.detectAndCompute(image_gray, None)
        except cv2.error as e:
            logging.error(f"Ошибка detectAndCompute для скриншота: {e}")
            return None, []
        
        if des_screenshot is None or len(kp_screenshot) == 0:
            return None, []
        
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        all_matched_x_coords_on_screenshot: List[float] = []
        akaze_candidates_found: List[str] = []
        hero_match_details: List[Dict[str, Any]] = []
        
        for hero_name, templates_cv2_list in self.hero_icons.items():
            if not templates_cv2_list:
                continue
            max_good_matches_for_hero = 0
            best_match_coords_for_hero: List[float] = []
            
            for i, template_cv2_single in enumerate(templates_cv2_list):
                if template_cv2_single is None:
                    continue
                try:
                    template_gray = cv2.cvtColor(template_cv2_single, cv2.COLOR_BGR2GRAY) if len(template_cv2_single.shape) == 3 else template_cv2_single
                    kp_template, des_template = akaze.detectAndCompute(template_gray, None)
                except cv2.error as e:
                    continue
                
                if des_template is None or len(kp_template) == 0:
                    continue
                
                try:
                    matches = bf.knnMatch(des_template, des_screenshot, k=2)
                except cv2.error:
                    continue
                
                good_matches = []
                current_match_coords_for_template: List[float] = []
                valid_matches = [m_pair for m_pair in matches if m_pair is not None and len(m_pair) == 2]
                for m, n in valid_matches:
                    if m.distance < AKAZE_LOWE_RATIO * n.distance:
                        good_matches.append(m)
                        screenshot_pt_idx = m.trainIdx
                        if screenshot_pt_idx < len(kp_screenshot):
                            current_match_coords_for_template.append(kp_screenshot[screenshot_pt_idx].pt[0])
                
                if len(good_matches) > max_good_matches_for_hero:
                    max_good_matches_for_hero = len(good_matches)
                    best_match_coords_for_hero = current_match_coords_for_template
            
            if max_good_matches_for_hero >= AKAZE_MIN_MATCH_COUNT_COLUMN_LOC:  # ПОРОГ 3 ДЛЯ ЦЕНТРА КОЛОНКИ
                hero_match_details.append({
                    "name": hero_name,
                    "matches": max_good_matches_for_hero,
                    "x_coords": best_match_coords_for_hero
                })
                akaze_candidates_found.append(hero_name)
                
                # Обновляем статистику героя
                if hero_name in self.hero_stats:
                    self.hero_stats[hero_name]['akaze_found'] += 1
        
        # Сортируем по количеству совпадений
        sorted_hero_match_details = sorted(hero_match_details, key=lambda item: item["matches"], reverse=True)
        
        for detail in sorted_hero_match_details:
            logging.info(f"  {detail['name']}: {detail['matches']} совпадений (кандидат для центра колонки)")
            all_matched_x_coords_on_screenshot.extend(detail['x_coords'])
        
        if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
            return None, akaze_candidates_found
        
        if not all_matched_x_coords_on_screenshot:
            return None, akaze_candidates_found
        
        # УЛУЧШЕНИЕ: Используем медиану вместо среднего для более устойчивой оценки центра
        rounded_x_coords = [round(x / 5.0) * 5 for x in all_matched_x_coords_on_screenshot]  # Уменьшили шаг округления
        most_common_x_center = np.median(rounded_x_coords)  # Используем медиану
        
        # Сохраняем центр колонки для использования в find_hero_positions_akaze
        self.last_column_x_center = int(most_common_x_center)
        
        return int(most_common_x_center), akaze_candidates_found
    
    def find_hero_positions_akaze(self, large_image_cv2: np.ndarray, target_heroes: List[str]) -> List[Dict[str, Any]]:
        """Находит точные позиции героев с помощью AKAZE (порог 5)"""
        if large_image_cv2 is None or not target_heroes:
            return []
        
        try:
            image_gray = cv2.cvtColor(large_image_cv2, cv2.COLOR_BGR2GRAY)
        except cv2.error as e:
            logging.error(f"Ошибка конвертации в серое: {e}")
            return []
        
        akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
        try:
            kp_screenshot, des_screenshot = akaze.detectAndCompute(image_gray, None)
        except cv2.error as e:
            logging.error(f"Ошибка detectAndCompute для скриншота: {e}")
            return []
        
        if des_screenshot is None or len(kp_screenshot) == 0:
            return []
        
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        hero_positions = []
        img_height, img_width = large_image_cv2.shape[:2]
        
        for hero_name in target_heroes:
            if hero_name not in self.hero_icons:
                continue
            
            templates_cv2_list = self.hero_icons[hero_name]
            if not templates_cv2_list:
                continue
            
            best_match_for_hero = None
            max_good_matches = 0
            best_location = None
            
            for i, template_cv2_single in enumerate(templates_cv2_list):
                if template_cv2_single is None:
                    continue
                
                try:
                    template_gray = cv2.cvtColor(template_cv2_single, cv2.COLOR_BGR2GRAY) if len(template_cv2_single.shape) == 3 else template_cv2_single
                    kp_template, des_template = akaze.detectAndCompute(template_gray, None)
                except cv2.error as e:
                    continue
                
                if des_template is None or len(kp_template) == 0:
                    continue
                
                try:
                    matches = bf.knnMatch(des_template, des_screenshot, k=2)
                except cv2.error:
                    continue
                
                good_matches = []
                valid_matches = [m_pair for m_pair in matches if m_pair is not None and len(m_pair) == 2]
                for m, n in valid_matches:
                    if m.distance < AKAZE_LOWE_RATIO * n.distance:
                        good_matches.append(m)
                
                if len(good_matches) > max_good_matches and len(good_matches) >= AKAZE_MIN_MATCH_COUNT_HERO_LOC:  # ПОРОГ 5 ДЛЯ ГЕРОЕВ
                    max_good_matches = len(good_matches)
                    
                    # Находим локацию героя по совпадающим точкам
                    if len(good_matches) >= 4:
                        src_pts = np.float32([kp_template[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp_screenshot[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        
                        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                        if M is not None:
                            h, w = template_gray.shape
                            pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
                            dst = cv2.perspectiveTransform(pts, M)
                            
                            # Вычисляем центр bounding box
                            center_x = int(np.mean(dst[:, 0, 0]))
                            center_y = int(np.mean(dst[:, 0, 1]))
                            
                            # ПРОВЕРКА И КОРРЕКЦИЯ КООРДИНАТ
                            # Убедимся, что координаты в пределах изображения
                            center_x = max(WINDOW_SIZE_W_DINO // 2, min(center_x, img_width - WINDOW_SIZE_W_DINO // 2))
                            center_y = max(WINDOW_SIZE_H_DINO // 2, min(center_y, img_height - WINDOW_SIZE_H_DINO // 2))
                            
                            # Дополнительная проверка - координата X должна быть близка к центру колонки
                            if self.last_column_x_center and abs(center_x - self.last_column_x_center) > WINDOW_SIZE_W_DINO * 1.5:
                                logging.warning(f"Координата X для {hero_name} слишком далеко от центра колонки: {center_x} vs {self.last_column_x_center}")
                                continue
                            
                            best_location = (center_x, center_y)
                            best_match_for_hero = {
                                "name": hero_name,
                                "matches": len(good_matches),
                                "x": center_x - WINDOW_SIZE_W_DINO // 2,
                                "y": center_y - WINDOW_SIZE_H_DINO // 2,
                                "confidence": len(good_matches) / AKAZE_MIN_MATCH_COUNT_HERO_LOC
                            }
            
            if best_match_for_hero and best_location:
                hero_positions.append(best_match_for_hero)
                logging.info(f"AKAZE нашел героя {hero_name} в позиции ({best_match_for_hero['x']}, {best_match_for_hero['y']}) с {best_match_for_hero['matches']} совпадениями")
        
        return hero_positions
    
    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        """Конвертирует имя героя из формата эмбеддингов в формат отображения"""
        normalized = hero_name.replace('_', ' ').title()
        if normalized == 'Cloak And Dagger':
            return 'Cloak & Dagger'
        elif normalized == 'Jeff The Land Shark':
            return 'Jeff The Land Shark'
        elif normalized == 'The Punisher':
            return 'The Punisher'
        elif normalized == 'The Thing':
            return 'The Thing'
        elif normalized == 'Mister Fantastic':
            return 'Mister Fantastic'
        elif normalized == 'Doctor Strange':
            return 'Doctor Strange'
        elif normalized == 'Captain America':
            return 'Captain America'
        elif normalized == 'Human Torch':
            return 'Human Torch'
        elif normalized == 'Iron Man':
            return 'Iron Man'
        elif normalized == 'Black Panther':
            return 'Black Panther'
        elif normalized == 'Black Widow':
            return 'Black Widow'
        elif normalized == 'Winter Soldier':
            return 'Winter Soldier'
        elif normalized == 'Scarlet Witch':
            return 'Scarlet Witch'
        elif normalized == 'Moon Knight':
            return 'Moon Knight'
        elif normalized == 'Rocket Raccoon':
            return 'Rocket Raccoon'
        elif normalized == 'Star Lord':
            return 'Star Lord'
        elif normalized == 'Peni Parker':
            return 'Peni Parker'
        elif normalized == 'Squirrel Girl':
            return 'Squirrel Girl'
        elif normalized == 'Invisible Woman':
            return 'Invisible Woman'
        elif normalized == 'Adam Warlock':
            return 'Adam Warlock'
        else:
            return normalized
    
    def generate_rois(self, screenshot_pil: Image.Image, column_x_center: Optional[int], akaze_hero_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Генерация ROI для анализа с учетом AKAZE позиций героев (УЛУЧШЕННАЯ ВЕРСИЯ)"""
        s_width, s_height = screenshot_pil.size
        rois_for_dino = []
        
        # Если AKAZE нашел героев и есть центр колонки
        if column_x_center is not None and akaze_hero_positions:
            logging.info(f"Генерация интеллектуальных ROI на основе {len(akaze_hero_positions)} AKAZE позиций")
            
            # Сортируем позиции героев по Y-координате
            akaze_hero_positions_sorted = sorted(akaze_hero_positions, key=lambda pos: pos['y'])
            
            # УЛУЧШЕНИЕ: Создаем ROI для подтверждения AKAZE находок (ПЕРВЫЕ)
            logging.info("Генерация ROI для подтверждения AKAZE находок...")
            for hero_pos in akaze_hero_positions_sorted:
                # Создаем несколько ROI с разными смещениями для подтверждения героя
                for x_offset in ROI_X_JITTER_VALUES_DINO:
                    for y_offset in ROI_Y_JITTER_VALUES_DINO:
                        roi_x = hero_pos['x'] + x_offset
                        roi_y = hero_pos['y'] + y_offset
                        
                        # Проверяем, что ROI не выходит за границы
                        if (0 <= roi_x and roi_x + WINDOW_SIZE_W_DINO <= s_width and
                            0 <= roi_y and roi_y + WINDOW_SIZE_H_DINO <= s_height):
                            
                            rois_for_dino.append({
                                'x': roi_x,
                                'y': roi_y,
                                'width': WINDOW_SIZE_W_DINO,
                                'height': WINDOW_SIZE_H_DINO,
                                'hero_name': hero_pos['name'],
                                'akaze_confidence': hero_pos['confidence']
                            })
            
            # УЛУЧШЕНИЕ: Создаем ROI для пустых слотов (ВТОРЫЕ)
            if len(akaze_hero_positions_sorted) < TEAM_SIZE:
                logging.info("Генерация ROI для пустых слотов...")
                
                # Проверяем область перед первым героем
                first_hero = akaze_hero_positions_sorted[0]
                if first_hero['y'] > WINDOW_SIZE_H_DINO * 1.5:  # Увеличили порог
                    # УЛУЧШЕНИЕ: Более точный расчет позиции для пустого слота
                    empty_y = max(WINDOW_SIZE_H_DINO // 2, first_hero['y'] // 3)  # Изменили расчет
                    rois_for_dino.append({
                        'x': column_x_center - WINDOW_SIZE_W_DINO // 2,
                        'y': empty_y - WINDOW_SIZE_H_DINO // 2,
                        'width': WINDOW_SIZE_W_DINO,
                        'height': WINDOW_SIZE_H_DINO,
                        'hero_name': 'unknown',
                        'akaze_confidence': 0.0
                    })
                
                # Проверяем области между героями
                for i in range(len(akaze_hero_positions_sorted) - 1):
                    current_hero = akaze_hero_positions_sorted[i]
                    next_hero = akaze_hero_positions_sorted[i + 1]
                    
                    # Вычисляем расстояние между героями
                    gap = next_hero['y'] - (current_hero['y'] + WINDOW_SIZE_H_DINO)
                    
                    # Если есть достаточно места для еще одного героя
                    if gap > WINDOW_SIZE_H_DINO * 1.5:  # Увеличили порог
                        # УЛУЧШЕНИЕ: Более точный расчет позиции для пустого слота
                        empty_y = current_hero['y'] + WINDOW_SIZE_H_DINO + gap // 2
                        rois_for_dino.append({
                            'x': column_x_center - WINDOW_SIZE_W_DINO // 2,
                            'y': empty_y - WINDOW_SIZE_H_DINO // 2,
                            'width': WINDOW_SIZE_W_DINO,
                            'height': WINDOW_SIZE_H_DINO,
                            'hero_name': 'unknown',
                            'akaze_confidence': 0.0
                        })
                
                # Проверяем область после последнего героя
                last_hero = akaze_hero_positions_sorted[-1]
                if s_height - (last_hero['y'] + WINDOW_SIZE_H_DINO) > WINDOW_SIZE_H_DINO * 1.5:  # Увеличили порог
                    # УЛУЧШЕНИЕ: Более точный расчет позиции для пустого слота
                    empty_y = last_hero['y'] + WINDOW_SIZE_H_DINO + (s_height - (last_hero['y'] + WINDOW_SIZE_H_DINO)) // 2
                    if empty_y + WINDOW_SIZE_H_DINO // 2 <= s_height:
                        rois_for_dino.append({
                            'x': column_x_center - WINDOW_SIZE_W_DINO // 2,
                            'y': empty_y - WINDOW_SIZE_H_DINO // 2,
                            'width': WINDOW_SIZE_W_DINO,
                            'height': WINDOW_SIZE_H_DINO,
                            'hero_name': 'unknown',
                            'akaze_confidence': 0.0
                        })
            
            logging.info(f"Сгенерировано {len(rois_for_dino)} ROI (подтверждение AKAZE: {len(akaze_hero_positions_sorted) * len(ROI_X_JITTER_VALUES_DINO) * len(ROI_Y_JITTER_VALUES_DINO)}, пустые слоты: {len(rois_for_dino) - len(akaze_hero_positions_sorted) * len(ROI_X_JITTER_VALUES_DINO) * len(ROI_Y_JITTER_VALUES_DINO)})")
        
        # Если AKAZE не нашел героев или нет центра колонки
        elif column_x_center is not None:
            logging.info("AKAZE не нашел героев, используем стандартную генерацию ROI по центру колонки")
            base_roi_start_x = column_x_center - (WINDOW_SIZE_W_DINO // 2)
            
            for y in range(0, s_height - WINDOW_SIZE_H_DINO + 1, ROI_GENERATION_STRIDE_Y_DINO):
                for x_offset in ROI_X_JITTER_VALUES_DINO:
                    current_roi_start_x = base_roi_start_x + x_offset
                    if 0 <= current_roi_start_x and (current_roi_start_x + WINDOW_SIZE_W_DINO) <= s_width:
                        rois_for_dino.append({
                            'x': current_roi_start_x, 
                            'y': y,
                            'width': WINDOW_SIZE_W_DINO,
                            'height': WINDOW_SIZE_H_DINO
                        })
        
        # Полный fallback, если не удалось определить центр колонки
        else:
            logging.warning("Не удалось определить центр колонки. Включается fallback DINO (полное сканирование с отступом).")
            for y in range(0, s_height - WINDOW_SIZE_H_DINO + 1, FALLBACK_DINO_STRIDE_H):
                for x_val in range(LEFT_OFFSET, s_width - WINDOW_SIZE_W_DINO + 1, FALLBACK_DINO_STRIDE_W):
                    rois_for_dino.append({
                        'x': x_val, 
                        'y': y,
                        'width': WINDOW_SIZE_W_DINO,
                        'height': WINDOW_SIZE_H_DINO
                    })
        
        return rois_for_dino
    
    def filter_overlapping_detections(self, detections: List[Dict[str, Any]], akaze_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Фильтрует детекции с сильным пересечением, отдавая приоритет AKAZE"""
        if not detections:
            return []
        
        # Сначала создаем список областей, занятых AKAZE
        akaze_areas = []
        for akaze_pos in akaze_positions:
            akaze_areas.append({
                'x': akaze_pos['x'],
                'y': akaze_pos['y'],
                'width': WINDOW_SIZE_W_DINO,
                'height': WINDOW_SIZE_H_DINO,
                'hero_name': akaze_pos['name']
            })
        
        # Сортируем детекции по схожести (от высокой к низкой)
        sorted_detections = sorted(detections, key=lambda x: x["similarity"], reverse=True)
        filtered_detections = []
        
        for detection in sorted_detections:
            is_overlapping = False
            detection_rect = {
                'x': detection["x"],
                'y': detection["y"],
                'width': detection["width"],
                'height': detection["height"]
            }
            
            # Проверяем пересечение с AKAZE областями
            for akaze_area in akaze_areas:
                if self.check_rectangle_overlap(detection_rect, akaze_area):
                    # Если детекция пересекается с AKAZE областью
                    if detection.get('hero_name') == akaze_area['hero_name']:
                        # Если это тот же герой, оставляем с более высоким порогом
                        if detection["similarity"] >= DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE:
                            logging.info(f"DINO подтверждает героя {akaze_area['hero_name']} со схожестью {detection['similarity']:.3f}")
                            filtered_detections.append(detection)
                    else:
                        # Если это разные герои, пропускаем DINO детекцию
                        logging.info(f"DINO детекция {detection.get('hero_name', 'unknown')} пересекается с AKAZE {akaze_area['hero_name']}, пропускаем")
                    is_overlapping = True
                    break
            
            # Если нет пересечения с AKAZE, проверяем пересечение с другими DINO детекциями
            if not is_overlapping:
                for existing in filtered_detections:
                    existing_rect = {
                        'x': existing["x"],
                        'y': existing["y"],
                        'width': existing["width"],
                        'height': existing["height"]
                    }
                    
                    if self.check_rectangle_overlap(detection_rect, existing_rect):
                        iou = self.calculate_iou(detection_rect, existing_rect)
                        y_overlap_ratio = self.calculate_y_overlap_ratio(detection_rect, existing_rect)
                        
                        if iou > 0.5 or y_overlap_ratio > Y_OVERLAP_THRESHOLD_RATIO:
                            is_overlapping = True
                            break
                
                if not is_overlapping:
                    filtered_detections.append(detection)
        
        return filtered_detections
    
    def calculate_iou(self, rect1: Dict[str, int], rect2: Dict[str, int]) -> float:
        """Вычисляет IoU (Intersection over Union) двух прямоугольников"""
        x1 = max(rect1['x'], rect2['x'])
        y1 = max(rect1['y'], rect2['y'])
        x2 = min(rect1['x'] + rect1['width'], rect2['x'] + rect2['width'])
        y2 = min(rect1['y'] + rect1['height'], rect2['y'] + rect2['height'])
        
        intersection_area = max(0, x2 - x1) * max(0, y2 - y1)
        
        area1 = rect1['width'] * rect1['height']
        area2 = rect2['width'] * rect2['height']
        union_area = area1 + area2 - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def calculate_y_overlap_ratio(self, rect1: Dict[str, int], rect2: Dict[str, int]) -> float:
        """Вычисляет отношение пересечения по оси Y"""
        y_overlap_start = max(rect1['y'], rect2['y'])
        y_overlap_end = min(rect1['y'] + rect1['height'], rect2['y'] + rect2['height'])
        y_overlap_height = y_overlap_end - y_overlap_start
        
        return y_overlap_height / rect1['height'] if rect1['height'] > 0 else 0.0
    
    def analyze_similarity_distribution(self):
        """Анализирует распределение similarity scores"""
        if not self.similarity_stats:
            return
        
        correct_sims = []
        incorrect_sims = []
        
        for stat in self.similarity_stats:
            if stat['best_similarity'] > 0:
                if stat['best_similarity'] > DINOV2_FINAL_DECISION_THRESHOLD:
                    correct_sims.append(stat['best_similarity'])
                else:
                    incorrect_sims.append(stat['best_similarity'])
        
        logging.info(f"\n=== Анализ распределения similarity scores ===")
        logging.info(f"Всего измерений: {len(self.similarity_stats)}")
        logging.info(f"Высокие similarity (> {DINOV2_FINAL_DECISION_THRESHOLD}): {len(correct_sims)}")
        logging.info(f"Низкие similarity (<= {DINOV2_FINAL_DECISION_THRESHOLD}): {len(incorrect_sims)}")
        
        if correct_sims:
            logging.info(f"Средний high similarity: {np.mean(correct_sims):.4f} (min: {np.min(correct_sims):.4f}, max: {np.max(correct_sims):.4f})")
        
        if incorrect_sims:
            logging.info(f"Средний low similarity: {np.mean(incorrect_sims):.4f} (min: {np.min(incorrect_sims):.4f}, max: {np.max(incorrect_sims):.4f})")
    
    def recognize_heroes(self, use_screen_capture=True, test_file_index=None, save_debug=False, experiment_roi_size=None) -> List[str]:
        """Основная функция распознавания героев с AKAZE для X и Y координат (УЛУЧШЕННАЯ ВЕРСИЯ)"""
        start_time = time.time()
        self.similarity_stats = []
        
        try:
            # 1. Загружаем скриншот
            if use_screen_capture:
                screenshot_cv2 = self.capture_screen_area()
                if screenshot_cv2 is None:
                    logging.error("Не удалось захватить область экрана")
                    return []
                screenshot_pil = Image.fromarray(cv2.cvtColor(screenshot_cv2, cv2.COLOR_BGR2RGB))
            else:
                if test_file_index is None:
                    test_file_index = 1
                
                screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{test_file_index}.png")
                if not os.path.exists(screenshot_path):
                    logging.error(f"Скриншот не найден: {screenshot_path}")
                    return []
                
                full_screenshot_pil = Image.open(screenshot_path)
                screenshot_pil = self.crop_image_to_recognition_area(full_screenshot_pil)
                
                if save_debug:
                    debug_path = os.path.join(SCREENSHOTS_DIR, "debug.png")
                    screenshot_pil.save(debug_path)
                    logging.info(f"Сохранен отладочный скриншот: {debug_path}")
                
                screenshot_cv2 = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
            
            s_width, s_height = screenshot_pil.size
            logging.info(f"Размер скриншота: {s_width}x{s_height}")
            
            # 2. Определяем центр колонки героев с помощью AKAZE (порог 3)
            akaze_start_time = time.time()
            column_x_center, akaze_identified_names = self.get_hero_column_center_akaze(screenshot_cv2)
            
            # 3. Находим точные позиции героев с помощью AKAZE (порог 5)
            akaze_hero_positions = self.find_hero_positions_akaze(screenshot_cv2, akaze_identified_names)
            akaze_end_time = time.time()
            logging.info(f"AKAZE локализация: {akaze_end_time - akaze_start_time:.2f} сек. Найдено героев: {len(akaze_hero_positions)}")
            
            # 4. Генерируем ROI для анализа (ИНТЕЛЛЕКТУАЛЬНАЯ ГЕНЕРАЦИЯ)
            dino_start_time = time.time()
            rois_for_dino = self.generate_rois(screenshot_pil, column_x_center, akaze_hero_positions)
            logging.info(f"Сгенерировано ROI для анализа: {len(rois_for_dino)}")
            if not rois_for_dino:
                logging.warning("Не сгенерировано ни одного ROI для анализа.")
                return []
            
            # Создаем директорию для сохранения ROI, если включен режим отладки
            roi_debug_dir = None
            if save_debug:
                roi_debug_dir = os.path.join(DEBUG_DIR, f"roi_test_{test_file_index}")
                os.makedirs(roi_debug_dir, exist_ok=True)
                logging.info(f"Сохранение ROI в директорию: {roi_debug_dir}")
            
            # 5. Обрабатываем ROI с БАТЧЕВОЙ обработкой
            all_dino_detections: List[Dict[str, Any]] = []
            pil_batch: List[Image.Image] = []
            coordinates_batch: List[Dict[str, int]] = []
            processed_windows_count = 0
            
            for i, roi_coord in enumerate(rois_for_dino):
                if i % 10 == 0:
                    logging.info(f"Обработка ROI {i}/{len(rois_for_dino)}")
                
                x, y, width, height = roi_coord['x'], roi_coord['y'], roi_coord['width'], roi_coord['height']
                window_pil = screenshot_pil.crop((x, y, x + width, y + height))
                
                # Сохраняем вырезанное окно для дебага
                if save_debug and roi_debug_dir:
                    roi_filename = f"roi_{i:03d}_x{x}_y{y}_w{width}_h{height}.png"
                    roi_filepath = os.path.join(roi_debug_dir, roi_filename)
                    window_pil.save(roi_filepath)
                
                # Предобрабатываем изображение
                preprocessed_window = self.preprocess_image_for_dino(window_pil)
                if preprocessed_window is None:
                    continue
                
                pil_batch.append(preprocessed_window)
                coordinates_batch.append({'x': x, 'y': y})
                
                # Обрабатываем батч, когда он наполнился
                if len(pil_batch) >= BATCH_SIZE_SLIDING_WINDOW_DINO:
                    window_embeddings_batch = self.get_cls_embeddings_for_batched_pil(pil_batch)
                    
                    if window_embeddings_batch.size == 0 and pil_batch:
                        logging.warning(f"Получен пустой батч эмбеддингов, хотя в pil_batch было {len(pil_batch)} элементов.")
                    else:
                        for j in range(len(window_embeddings_batch)):
                            window_embedding = window_embeddings_batch[j]
                            coord = coordinates_batch[j]
                            
                            # Используем get_best_match с логированием топ-5
                            roi_info = f"ROI_{i}_{j}"
                            best_hero_name, best_sim, top_matches = self.get_best_match(window_embedding, roi_info)
                            
                            if best_hero_name is not None and best_sim >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                                detection = {
                                    "name": best_hero_name,
                                    "similarity": best_sim,
                                    "x": coord['x'], 
                                    "y": coord['y'],
                                    "width": width,
                                    "height": height
                                }
                                
                                # Добавляем информацию из AKAZE если есть
                                if 'hero_name' in roi_coord:
                                    detection['hero_name'] = roi_coord['hero_name']
                                    detection['akaze_confidence'] = roi_coord.get('akaze_confidence', 0.0)
                                
                                all_dino_detections.append(detection)
                    
                    processed_windows_count += len(pil_batch)
                    pil_batch = []
                    coordinates_batch = []
            
            # Обрабатываем оставшиеся изображения в батче
            if pil_batch:
                window_embeddings_batch = self.get_cls_embeddings_for_batched_pil(pil_batch)
                
                if window_embeddings_batch.size == 0 and pil_batch:
                    logging.warning(f"Получен пустой батч эмбеддингов для остатка, pil_batch: {len(pil_batch)}.")
                else:
                    for j in range(len(window_embeddings_batch)):
                        window_embedding = window_embeddings_batch[j]
                        coord = coordinates_batch[j]
                        
                        # Используем get_best_match с логированием топ-5
                        roi_info = f"ROI_final_{j}"
                        best_hero_name, best_sim, top_matches = self.get_best_match(window_embedding, roi_info)
                        
                        if best_hero_name is not None and best_sim >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                            detection = {
                                "name": best_hero_name,
                                "similarity": best_sim,
                                "x": coord['x'], 
                                "y": coord['y'],
                                "width": width,
                                "height": height
                            }
                            
                            # Добавляем информацию из AKAZE если есть
                            if 'hero_name' in roi_coord:
                                detection['hero_name'] = roi_coord['hero_name']
                                detection['akaze_confidence'] = roi_coord.get('akaze_confidence', 0.0)
                            
                            all_dino_detections.append(detection)
                
                processed_windows_count += len(pil_batch)
            
            dino_end_time = time.time()
            logging.info(f"Обработано окон (DINOv2): {processed_windows_count}, Всего DINO детекций (выше порога логирования {DINOV2_LOGGING_SIMILARITY_THRESHOLD*100:.0f}%): {len(all_dino_detections)}")
            logging.info(f"DINO обработка: {dino_end_time - dino_start_time:.2f} сек.")
            
            # 6. Фильтруем детекции с учетом AKAZE (ПРИОРИТЕТ AKAZE)
            all_dino_detections = self.filter_overlapping_detections(all_dino_detections, akaze_hero_positions)
            
            # Анализируем распределение similarity scores
            self.analyze_similarity_distribution()
            
            # 7. УЛУЧШЕННАЯ логика финального решения с приоритетом AKAZE
            final_team_raw_names: List[str] = []
            final_team_normalized_names_set: Set[str] = set()
            occupied_y_slots: List[Tuple[int, int, str]] = []
            
            # Сначала добавляем героев, найденных AKAZE (приоритет)
            akaze_normalized_names = [self.normalize_hero_name_for_display(name) for name in akaze_identified_names]
            akaze_unique_normalized = sorted(list(set(akaze_normalized_names)))
            
            for akaze_norm_name in akaze_unique_normalized:
                if len(final_team_raw_names) >= TEAM_SIZE:
                    break
                if akaze_norm_name in final_team_normalized_names_set:
                    continue
                
                # Ищем подтверждение от DINO для этого героя
                best_dino_match_for_akaze_hero: Optional[Dict[str, Any]] = None
                highest_similarity = -1.0
                akaze_matches_count = 0
                
                # Находим количество совпадений AKAZE для этого героя
                for hero_pos in akaze_hero_positions:
                    if self.normalize_hero_name_for_display(hero_pos["name"]) == akaze_norm_name:
                        akaze_matches_count = hero_pos["matches"]
                        break
                
                # Ищем лучшее совпадение DINO
                for dino_cand_data in all_dino_detections:
                    dino_norm_name = self.normalize_hero_name_for_display(dino_cand_data["name"])
                    if dino_norm_name == akaze_norm_name:
                        if dino_cand_data["similarity"] > highest_similarity:
                            highest_similarity = dino_cand_data["similarity"]
                            best_dino_match_for_akaze_hero = dino_cand_data
                
                # Используем адаптивный порог
                adaptive_threshold = self.get_adaptive_threshold(DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE, akaze_matches_count, akaze_norm_name)
                
                # Обновляем статистику героя
                akaze_raw_name = None
                for hero_pos in akaze_hero_positions:
                    if self.normalize_hero_name_for_display(hero_pos["name"]) == akaze_norm_name:
                        akaze_raw_name = hero_pos["name"]
                        break
                
                if akaze_raw_name and akaze_raw_name in self.hero_stats:
                    stats = self.hero_stats[akaze_raw_name]
                    if highest_similarity > 0:
                        current_count = stats['avg_similarity'] * stats['dino_confirmed'] if stats['dino_confirmed'] > 0 else 0
                        stats['avg_similarity'] = (current_count + highest_similarity) / (stats['dino_confirmed'] + 1)
                    
                    if highest_similarity >= adaptive_threshold:
                        stats['dino_confirmed'] += 1
                    else:
                        stats['dino_rejected'] += 1
                
                # Добавляем героя (AKAZE + возможное подтверждение DINO)
                if akaze_raw_name:
                    final_team_raw_names.append(akaze_raw_name)
                    final_team_normalized_names_set.add(akaze_norm_name)
                    
                    # Находим Y-координату для занятого слота
                    y_start = None
                    for hero_pos in akaze_hero_positions:
                        if self.normalize_hero_name_for_display(hero_pos["name"]) == akaze_norm_name:
                            y_start = hero_pos["y"]
                            y_end = y_start + WINDOW_SIZE_H_DINO
                            occupied_y_slots.append((y_start, y_end, akaze_norm_name))
                            break
                    
                    if best_dino_match_for_akaze_hero and highest_similarity >= adaptive_threshold:
                        logging.info(f"Добавлен герой (AKAZE+DINO): {akaze_norm_name} (sim: {highest_similarity:.3f}, адаптивный порог: {adaptive_threshold:.3f})")
                    else:
                        logging.info(f"Добавлен герой (AKAZE только): {akaze_norm_name} (совпадений: {akaze_matches_count})")
            
            # Затем добавляем героев, найденных только DINO
            dino_candidates_for_final_decision = [
                cand for cand in all_dino_detections
                if cand["similarity"] >= DINOV2_FINAL_DECISION_THRESHOLD
            ]
            
            logging.info(f"--- Кандидаты DINOv2 для финального решения (прошедшие порог {DINOV2_FINAL_DECISION_THRESHOLD*100:.0f}%, {len(dino_candidates_for_final_decision)} шт.) ---")
            
            for dino_cand_data in dino_candidates_for_final_decision:
                if len(final_team_raw_names) >= TEAM_SIZE:
                    break
                dino_raw_name = dino_cand_data["name"]
                dino_norm_name = self.normalize_hero_name_for_display(dino_raw_name)
                
                if dino_norm_name in final_team_normalized_names_set:
                    continue
                
                dino_roi_y_start = dino_cand_data["y"]
                dino_roi_y_end = dino_roi_y_start + dino_cand_data["height"]
                
                # Проверяем пересечение по Y-координате с уже добавленными героями
                is_overlapping = False
                for occ_y_start, occ_y_end, occ_hero_name in occupied_y_slots:
                    overlap_start = max(dino_roi_y_start, occ_y_start)
                    overlap_end = min(dino_roi_y_end, occ_y_end)
                    overlap_height = overlap_end - overlap_start
                    overlap_ratio = overlap_height / dino_cand_data["height"]
                    
                    if overlap_ratio > Y_OVERLAP_THRESHOLD_RATIO:
                        if dino_norm_name == occ_hero_name:
                            logging.debug(f"Кандидат '{dino_raw_name}' ({dino_norm_name}) совпадает с уже добавленным героем '{occ_hero_name}'. Пропуск добавления.")
                        else:
                            logging.info(f"Кандидат '{dino_raw_name}' ({dino_norm_name}, ROI Y:{dino_roi_y_start}-{dino_roi_y_end}) пересекается с '{occ_hero_name}' (слот Y:{occ_y_start}-{occ_y_end}). Пропуск.")
                        is_overlapping = True
                        break
                
                if not is_overlapping:
                    final_team_raw_names.append(dino_raw_name)
                    final_team_normalized_names_set.add(dino_norm_name)
                    occupied_y_slots.append((dino_roi_y_start, dino_roi_y_end, dino_norm_name))
                    logging.info(f"Добавлен герой (DINO): {dino_norm_name} (sim: {dino_cand_data['similarity']:.3f})")
            
            # 8. Финальные результаты
            end_time = time.time()
            total_time = end_time - start_time
            
            logging.info(f"=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ (ПЛАН Б - УЛУЧШЕННЫЙ) ===")
            logging.info(f"Время выполнения: {total_time:.2f} секунд")
            logging.info(f"Распознано героев: {len(final_team_raw_names)}")
            for i, hero_name in enumerate(final_team_raw_names, 1):
                display_name = self.normalize_hero_name_for_display(hero_name)
                logging.info(f"  {i}. {display_name}")
            
            # Выводим статистику по героям
            logging.info(f"\n=== СТАТИСТИКА ПО ГЕРОЯМ ===")
            for hero_name, stats in self.hero_stats.items():
                if stats['akaze_found'] > 0:
                    recognition_rate = stats['dino_confirmed'] / stats['akaze_found']
                    logging.info(f"{self.normalize_hero_name_for_display(hero_name)}: AKAZE найден {stats['akaze_found']} раз, "
                               f"DINO подтвердил {stats['dino_confirmed']} раз ({recognition_rate:.2%}), "
                               f"среднее сходство: {stats['avg_similarity']:.3f}")
            
            return final_team_raw_names
        except Exception as e:
            logging.error(f"Ошибка распознавания: {e}")
            return []

def calculate_metrics(recognized_heroes, expected_heroes):
    """Вычисляет метрики precision, recall и F1-score"""
    recognized_set = set(recognized_heroes)
    expected_set = set(expected_heroes)
    
    correct = len(recognized_set & expected_set)
    false_positive = len(recognized_set - expected_set)
    false_negative = len(expected_set - recognized_set)
    
    precision = correct / len(recognized_set) if recognized_set else 0
    recall = correct / len(expected_set) if expected_set else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'correct': correct,
        'false_positive': false_positive,
        'false_negative': false_negative,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

def print_test_summary(total_stats):
    """Выводит сводку результатов тестирования"""
    logging.info(f"\n{'='*60}")
    logging.info(f"СВОДНЫЙ ОТЧЕТ ПО ТЕСТИРОВАНИЮ СИСТЕМЫ РАСПОЗНАВАНИЯ")
    logging.info(f"{'='*60}")
    logging.info(f"Всего тестов: {total_stats['total_tests']}")
    
    if total_stats['total_tests'] > 0:
        avg_precision = total_stats['total_precision'] / total_stats['total_tests']
        avg_recall = total_stats['total_recall'] / total_stats['total_tests']
        avg_f1 = total_stats['total_f1'] / total_stats['total_tests']
        
        logging.info(f"Средняя точность (Precision): {avg_precision:.3f}")
        logging.info(f"Средняя полнота (Recall): {avg_recall:.3f}")
        logging.info(f"Средний F1-score: {avg_f1:.3f}")
        
        # Оценка качества
        if avg_f1 >= 0.9:
            quality = "ОТЛИЧНО"
        elif avg_f1 >= 0.8:
            quality = "ОЧЕНЬ ХОРОШО"
        elif avg_f1 >= 0.7:
            quality = "ХОРОШО"
        elif avg_f1 >= 0.6:
            quality = "УДОВЛЕТВОРИТЕЛЬНО"
        else:
            quality = "ТРЕБУЕТ УЛУЧШЕНИЯ"
        
        logging.info(f"\nОБЩАЯ ОЦЕНКА КАЧЕСТВА: {quality}")
        
        # Детальная таблица результатов
        logging.info(f"\nДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        logging.info(f"{'-'*100}")
        logging.info(f"{'Тест':<8} {'ROI':<8} {'Верных':<8} {'Ложных':<8} {'Пропущ':<8} {'Precision':<10} {'Recall':<10} {'F1':<10}")
        logging.info(f"{'-'*100}")
        
        for result in total_stats['results']:
            logging.info(f"{result['test_id']:<8} {result['roi_size']:<8} {result['correct']:<8} "
                       f"{result['false_positive']:<8} {result['false_negative']:<8} "
                       f"{result['precision']:<10.3f} {result['recall']:<10.3f} {result['f1']:<10.3f}")
        
        logging.info(f"{'-'*100}")

def main():
    """Основная функция для тестирования с AKAZE для X и Y координат"""
    system = HeroRecognitionSystem()
    
    # Загружаем компоненты
    if not system.load_model():
        logging.error("Не удалось загрузить модель")
        return
    if not system.load_embeddings():
        logging.error("Не удалось загрузить эмбеддинги")
        return
    if not system.load_hero_icons():
        logging.error("Не удалось загрузить иконки героев")
        return
    if not system.is_ready():
        logging.error("Система не готова к работе")
        return
    
    logging.info("Система готова! Начинаем тестирование...")
    
    # Загружаем правильные ответы
    if os.path.exists(CORRECT_ANSWERS_FILE):
        with open(CORRECT_ANSWERS_FILE, 'r', encoding='utf-8') as f:
            correct_answers = json.load(f)
        
        # Статистика по всем тестам
        total_stats = {
            'total_tests': 0,
            'total_precision': 0,
            'total_recall': 0,
            'total_f1': 0,
            'results': []
        }
        
        # Тестируем на всех скриншотах
        for i in range(1, 8):
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{i}.png")
            if os.path.exists(screenshot_path):
                logging.info(f"\n=== ТЕСТИРОВАНИЕ СКРИНШОТА {i} ===")
                
                # ИЗМЕНЕНО: Сохраняем отладочную информацию для ВСЕХ скриншотов
                save_debug = True
                
                roi_sizes = [95, 224]
                
                for roi_size in roi_sizes:
                    logging.info(f"\n--- Тестирование с размером ROI: {roi_size}x{roi_size} ---")
                    
                    recognized_heroes = system.recognize_heroes(
                        use_screen_capture=False, 
                        test_file_index=i, 
                        save_debug=save_debug,
                        experiment_roi_size=roi_size
                    )
                    
                    expected_heroes = correct_answers.get(str(i), [])
                    
                    # Конвертируем распознанные имена в правильный формат для сравнения
                    normalized_recognized = [system.normalize_hero_name_for_display(hero) for hero in recognized_heroes]
                    
                    # Вычисляем метрики
                    metrics = calculate_metrics(normalized_recognized, expected_heroes)
                    
                    # Выводим результаты
                    logging.info(f"Ожидаемые герои: {expected_heroes}")
                    logging.info(f"Распознанные герои: {normalized_recognized}")
                    logging.info(f"Правильных: {metrics['correct']}")
                    logging.info(f"Ложных срабатываний: {metrics['false_positive']}")
                    logging.info(f"Пропущенных: {metrics['false_negative']}")
                    logging.info(f"Precision: {metrics['precision']:.3f}")
                    logging.info(f"Recall: {metrics['recall']:.3f}")
                    logging.info(f"F1-score: {metrics['f1']:.3f}")
                    
                    # Сохраняем результаты для общего отчета
                    test_result = {
                        'test_id': f"{i}_{roi_size}",
                        'roi_size': roi_size,
                        'correct': metrics['correct'],
                        'false_positive': metrics['false_positive'],
                        'false_negative': metrics['false_negative'],
                        'precision': metrics['precision'],
                        'recall': metrics['recall'],
                        'f1': metrics['f1']
                    }
                    total_stats['results'].append(test_result)
                    
                    # Накопительная статистика
                    total_stats['total_tests'] += 1
                    total_stats['total_precision'] += metrics['precision']
                    total_stats['total_recall'] += metrics['recall']
                    total_stats['total_f1'] += metrics['f1']
            else:
                logging.warning(f"Скриншот {i}.png не найден")
        
        # Выводим сводный отчет
        print_test_summary(total_stats)
    else:
        logging.error(f"Файл с правильными ответами не найден: {CORRECT_ANSWERS_FILE}")

if __name__ == "__main__":
    main()