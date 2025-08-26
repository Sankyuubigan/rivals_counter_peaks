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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("recognition_test.log")
    ]
)

# =============================================================================
# ОСНОВНЫЕ НАСТРОЙКИ - ИЗМЕНИТЕ ЭТУ ПЕРЕМЕННУЮ ДЛЯ ДРУГОГО РАЗМЕРА ИЗОБРАЖЕНИЯ
# =============================================================================
TARGET_SIZE = 150  # Размер изображения для распознавания (измени эту цифру для другого размера)
# =============================================================================

# Пути к ресурсам
VISION_MODELS_DIR = "vision_models"
MODEL_PATH = "vision_models/dinov3-vitb16-pretrain-lvd1689m/model_q4.onnx"
EMBEDDINGS_DIR = "resources/embeddings_padded"
HEROES_ICONS_DIR = "resources/heroes_icons"
SCREENSHOTS_DIR = "tests/for_recogn/screenshots"
CORRECT_ANSWERS_FILE = "tests/for_recogn/correct_answers.json"
DEBUG_DIR = "tests/debug"

# Константы модели
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]

# Размеры ROI (используют TARGET_SIZE)
WINDOW_SIZE_W_DINO = TARGET_SIZE
WINDOW_SIZE_H_DINO = TARGET_SIZE
ROI_GENERATION_STRIDE_Y_DINO = int(WINDOW_SIZE_H_DINO * 0.7)
FALLBACK_DINO_STRIDE_W = int(WINDOW_SIZE_W_DINO * 0.8)
FALLBACK_DINO_STRIDE_H = int(WINDOW_SIZE_H_DINO * 0.8)
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0, 0, 0)

# Параметры AKAZE
AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
AKAZE_MIN_MATCH_COUNT_COLUMN_LOC = 5
MIN_HEROES_FOR_COLUMN_DETECTION = 2
ROI_X_JITTER_VALUES_DINO = [-3, 0, 3]
MAX_NOT_PASSED_AKAZE_TO_LOG = 15

# УЛУЧШЕННЫЕ ПОРОГИ ДЛЯ DINO - еще более низкие
DINOV2_LOGGING_SIMILARITY_THRESHOLD = 0.05
DINOV2_FINAL_DECISION_THRESHOLD = 0.30  # СНИЖЕНО до 0.30
DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE = 0.20  # СНИЖЕНО до 0.20

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

# Создаем директорию для отладки
os.makedirs(DEBUG_DIR, exist_ok=True)

class HeroRecognitionSystem:
    """Система распознавания героев Marvel Rivals с кардинально улучшенным DINO"""
    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, List[np.ndarray]] = {}
        self.hero_icons: Dict[str, np.ndarray] = {}
        self.similarity_stats = []
        self.test_results = []
        self.hero_stats = {}  # Статистика по каждому герою
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
    
    def enhance_image_for_dino(self, image_pil: Image.Image) -> Image.Image:
        """
        Улучшенное предварительное улучшение изображения для DINO
        """
        try:
            # Убедимся, что изображение в RGB
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')
            
            # Применяем нерезкое маскирование для улучшения детализации
            enhancer = ImageEnhance.Sharpness(image_pil)
            image_pil = enhancer.enhance(2.0)  # Увеличиваем резкость
            
            # Улучшаем контрастность
            enhancer = ImageEnhance.Contrast(image_pil)
            image_pil = enhancer.enhance(1.5)
            
            # Улучшаем цветность
            enhancer = ImageEnhance.Color(image_pil)
            image_pil = enhancer.enhance(1.2)
            
            # Небольшая коррекция яркости
            enhancer = ImageEnhance.Brightness(image_pil)
            image_pil = enhancer.enhance(1.1)
            
            return image_pil
        except Exception as e:
            logging.error(f"Ошибка в enhance_image_for_dino: {e}")
            return image_pil
    
    def dynamic_resize_preprocess(self, image_pil: Image.Image, target_size=224, image_mean=None, image_std=None):
        """
        Кардинально улучшенная предобработка изображений для DINOv3
        """
        try:
            # 1. Улучшаем качество изображения перед обработкой
            image_pil = self.enhance_image_for_dino(image_pil)
            
            # 2. Получаем оригинальные размеры
            original_width, original_height = image_pil.size
            
            # 3. Стратегия обработки в зависимости от размера изображения
            max_dimension = max(original_width, original_height)
            
            if max_dimension <= target_size:
                # Для маленьких изображений: многоэтапное увеличение
                # Сначала увеличиваем в 2 раза с высоким качеством
                img_2x = image_pil.resize(
                    (original_width * 2, original_height * 2), 
                    Image.Resampling.LANCZOS
                )
                # Затем применяем нерезкое маскирование
                img_2x = img_2x.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
                # Финальное изменение размера
                img_resized = img_2x.resize((target_size, target_size), Image.Resampling.LANCZOS)
                
            elif max_dimension <= target_size * 2:
                # Для средних изображений: улучшение + изменение размера
                image_pil = image_pil.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
                img_resized = image_pil.resize((target_size, target_size), Image.Resampling.LANCZOS)
                
            else:
                # Для больших изображений: уменьшение с сохранением деталей
                image_pil = image_pil.filter(ImageFilter.UnsharpMask(radius=1, percent=100, threshold=3))
                img_resized = image_pil.resize((target_size, target_size), Image.Resampling.LANCZOS)
            
            # 4. Конвертируем в numpy array
            img_array = np.array(img_resized, dtype=np.float32) / 255.0
            
            # 5. Нормализация
            if image_mean is None:
                image_mean = [0.485, 0.456, 0.406]
            if image_std is None:
                image_std = [0.229, 0.224, 0.225]
                
            mean = np.array(image_mean, dtype=np.float32)
            std = np.array(image_std, dtype=np.float32)
            img_array = (img_array - mean) / std
            
            # 6. Транспонирование HWC -> CHW и добавление batch dimension
            img_array = np.transpose(img_array, (2, 0, 1))
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array.astype(np.float32)
            
        except Exception as e:
            logging.error(f"Ошибка в dynamic_resize_preprocess: {e}")
            return np.zeros((1, 3, target_size, target_size), dtype=np.float32)
    
    def preprocess_image_for_dino(self, image_pil: Image.Image, roi_info: str = "") -> np.ndarray:
        """Предобработка изображения для DINOv3 с улучшенным качеством"""
        processed_tensor = self.dynamic_resize_preprocess(image_pil, TARGET_SIZE, IMAGE_MEAN, IMAGE_STD)
        return processed_tensor
    
    def get_cls_embedding(self, image_pil: Image.Image, roi_info: str = "") -> np.ndarray:
        """Получение CLS эмбеддинга для изображения"""
        if not self.is_ready():
            return np.array([])
        try:
            inputs = self.preprocess_image_for_dino(image_pil, roi_info)
            onnx_outputs = self.ort_session.run(None, {self.input_name: inputs})
            last_hidden_state = onnx_outputs[0]
            
            # Используем не только CLS токен, но и взвешенное среднее всех токенов
            cls_embedding = last_hidden_state[0, 0, :]
            
            # Добавляем информацию из других токенов с весами
            all_tokens = last_hidden_state[0, 1:, :]  # Все токены кроме CLS
            if all_tokens.shape[0] > 0:
                # Вычисляем веса для токенов (линейно уменьшающиеся)
                weights = np.linspace(0.8, 0.2, all_tokens.shape[0])
                weights = weights / weights.sum()  # Нормализуем веса
                
                # Вычисляем взвешенное среднее
                weighted_mean = np.sum(all_tokens * weights[:, np.newaxis], axis=0)
                
                # Комбинируем CLS с взвешенным средним
                combined_embedding = 0.7 * cls_embedding + 0.3 * weighted_mean
                
                # Нормализуем результат
                norm = np.linalg.norm(combined_embedding)
                if norm > 0:
                    combined_embedding = combined_embedding / norm
                
                return combined_embedding
            
            return cls_embedding
        except Exception as e:
            logging.error(f"Ошибка получения эмбеддинга: {e}")
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
    
    def get_hero_column_center_akaze(self, large_image_cv2: np.ndarray) -> Tuple[Optional[int], List[str]]:
        """Определение центра колонки героев с помощью AKAZE"""
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
            
            if max_good_matches_for_hero >= AKAZE_MIN_MATCH_COUNT_COLUMN_LOC:
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
            logging.info(f"  {detail['name']}: {detail['matches']} совпадений (ПРОШЕЛ ФИЛЬТР)")
            all_matched_x_coords_on_screenshot.extend(detail['x_coords'])
        
        if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
            return None, akaze_candidates_found
        
        if not all_matched_x_coords_on_screenshot:
            return None, akaze_candidates_found
        
        rounded_x_coords = [round(x / 10.0) * 10 for x in all_matched_x_coords_on_screenshot]
        most_common_x_center = Counter(rounded_x_coords).most_common(1)[0][0]
        return int(most_common_x_center), akaze_candidates_found
    
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
    
    def generate_rois(self, screenshot_pil: Image.Image, column_x_center: Optional[int]) -> List[Dict[str, Any]]:
        """Генерация ROI для анализа"""
        s_width, s_height = screenshot_pil.size
        rois_for_dino = []
        
        logging.warning("Используем полное сканирование для тестирования")
        
        for y in range(0, s_height - WINDOW_SIZE_H_DINO + 1, FALLBACK_DINO_STRIDE_H):
            for x_val in range(0, s_width - WINDOW_SIZE_W_DINO + 1, FALLBACK_DINO_STRIDE_W):
                rois_for_dino.append({
                    'x': x_val, 
                    'y': y,
                    'width': WINDOW_SIZE_W_DINO,
                    'height': WINDOW_SIZE_H_DINO
                })
        
        return rois_for_dino
    
    def filter_overlapping_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Фильтрует детекции с сильным пересечением"""
        if not detections:
            return []
        
        sorted_detections = sorted(detections, key=lambda x: x["similarity"], reverse=True)
        filtered_detections = []
        
        for detection in sorted_detections:
            is_overlapping = False
            
            for existing in filtered_detections:
                x1 = max(detection["x"], existing["x"])
                y1 = max(detection["y"], existing["y"])
                x2 = min(detection["x"] + detection["width"], existing["x"] + existing["width"])
                y2 = min(detection["y"] + detection["height"], existing["y"] + existing["height"])
                
                intersection_area = max(0, x2 - x1) * max(0, y2 - y1)
                det_area = detection["width"] * detection["height"]
                existing_area = existing["width"] * existing["height"]
                
                iou = intersection_area / min(det_area, existing_area)
                
                if iou > 0.5:
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered_detections.append(detection)
        
        return filtered_detections
    
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
        """Основная функция распознавания героев с кардинально улучшенным DINO"""
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
            
            # 2. Определяем центр колонки героев с помощью AKAZE
            akaze_start_time = time.time()
            column_x_center, akaze_identified_names = self.get_hero_column_center_akaze(screenshot_cv2)
            akaze_end_time = time.time()
            logging.info(f"AKAZE локализация: {akaze_end_time - akaze_start_time:.2f} сек. Найдено: {akaze_identified_names}")
            
            # 3. Генерируем ROI для анализа
            dino_start_time = time.time()
            rois_for_dino = self.generate_rois(screenshot_pil, column_x_center)
            logging.info(f"Сгенерировано ROI для анализа: {len(rois_for_dino)}")
            if not rois_for_dino:
                logging.warning("Не сгенерировано ни одного ROI для анализа.")
                return []
            
            # 4. Обрабатываем ROI и получаем эмбеддинги
            all_dino_detections: List[Dict[str, Any]] = []
            
            for i, roi_coord in enumerate(rois_for_dino):
                if i % 10 == 0:
                    logging.info(f"Обработка ROI {i}/{len(rois_for_dino)}")
                
                x, y, width, height = roi_coord['x'], roi_coord['y'], roi_coord['width'], roi_coord['height']
                window_pil = screenshot_pil.crop((x, y, x + width, y + height))
                
                if experiment_roi_size:
                    window_pil = window_pil.resize((experiment_roi_size, experiment_roi_size), Image.Resampling.LANCZOS)
                
                roi_info = f"{i}_x{x}_y{y}"
                
                window_embedding = self.get_cls_embedding(window_pil, roi_info)
                if len(window_embedding) == 0:
                    continue
                
                best_hero, best_sim, top_matches = self.get_best_match(window_embedding, roi_info)
                
                if best_hero is not None and best_sim >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                    all_dino_detections.append({
                        "name": best_hero,
                        "similarity": best_sim,
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height,
                        "top_matches": top_matches
                    })
            
            # Фильтруем пересекающиеся детекции
            all_dino_detections = self.filter_overlapping_detections(all_dino_detections)
            
            dino_end_time = time.time()
            logging.info(f"DINO обработка: {dino_end_time - dino_start_time:.2f} сек. Найдено детекций: {len(all_dino_detections)}")
            
            # Анализируем распределение similarity scores
            self.analyze_similarity_distribution()
            
            # 5. Комбинированная логика DINO + AKAZE с адаптивными порогами
            final_team_raw_names: List[str] = []
            final_team_normalized_names_set: Set[str] = set()
            occupied_y_slots_by_akaze: List[Tuple[int, int, str]] = []
            
            akaze_normalized_names = akaze_identified_names
            akaze_unique_normalized = sorted(list(set(akaze_normalized_names)))
            
            # Сначала обрабатываем AKAZE-кандидатов
            for akaze_norm_name in akaze_unique_normalized:
                if len(final_team_raw_names) >= TEAM_SIZE:
                    break
                if akaze_norm_name in final_team_normalized_names_set:
                    continue
                
                best_dino_match = None
                highest_similarity = -1.0
                
                # Ищем соответствие в DINO детекциях
                for dino_cand in all_dino_detections:
                    dino_norm_name = dino_cand["name"]
                    if dino_norm_name == akaze_norm_name:
                        if dino_cand["similarity"] > highest_similarity:
                            highest_similarity = dino_cand["similarity"]
                            best_dino_match = dino_cand
                
                # Используем адаптивный порог
                akaze_matches = sum(1 for d in all_dino_detections if d["name"] == akaze_norm_name)
                adaptive_threshold = self.get_adaptive_threshold(DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE, akaze_matches, akaze_norm_name)
                
                # Обновляем статистику героя
                if akaze_norm_name in self.hero_stats:
                    stats = self.hero_stats[akaze_norm_name]
                    if highest_similarity > 0:
                        # Обновляем среднее сходство
                        current_count = stats['avg_similarity'] * stats['dino_confirmed'] if stats['dino_confirmed'] > 0 else 0
                        stats['avg_similarity'] = (current_count + highest_similarity) / (stats['dino_confirmed'] + 1)
                    
                    if highest_similarity >= adaptive_threshold:
                        stats['dino_confirmed'] += 1
                    else:
                        stats['dino_rejected'] += 1
                
                if best_dino_match and highest_similarity >= adaptive_threshold:
                    raw_name_to_add = best_dino_match["name"]
                    final_team_raw_names.append(raw_name_to_add)
                    final_team_normalized_names_set.add(akaze_norm_name)
                    y_start = best_dino_match["y"]
                    y_end = y_start + best_dino_match["height"]
                    occupied_y_slots_by_akaze.append((y_start, y_end, akaze_norm_name))
                    logging.info(f"Добавлен герой (AKAZE+DINO): {self.normalize_hero_name_for_display(raw_name_to_add)} (sim: {highest_similarity:.3f}, адаптивный порог: {adaptive_threshold:.3f})")
                else:
                    # Добавляем AKAZE героя без DINO подтверждения, если у него есть эмбеддинг
                    if akaze_norm_name in self.hero_embeddings:
                        final_team_raw_names.append(akaze_norm_name)
                        final_team_normalized_names_set.add(akaze_norm_name)
                        logging.info(f"Добавлен герой (AKAZE только): {self.normalize_hero_name_for_display(akaze_norm_name)}")
            
            # Затем добавляем оставшиеся DINO-детекции
            dino_candidates_sorted = sorted(
                [cand for cand in all_dino_detections if cand["similarity"] >= DINOV2_FINAL_DECISION_THRESHOLD],
                key=lambda x: x["similarity"],
                reverse=True
            )
            
            for dino_cand in dino_candidates_sorted:
                if len(final_team_raw_names) >= TEAM_SIZE:
                    break
                dino_raw_name = dino_cand["name"]
                dino_norm_name = dino_raw_name
                
                if dino_norm_name in final_team_normalized_names_set:
                    continue
                
                dino_roi_y_start = dino_cand["y"]
                dino_roi_y_end = dino_roi_y_start + dino_cand["height"]
                
                is_overlapping = False
                for occ_y_start, occ_y_end, occ_hero_name in occupied_y_slots_by_akaze:
                    overlap_start = max(dino_roi_y_start, occ_y_start)
                    overlap_end = min(dino_roi_y_end, occ_y_end)
                    overlap_height = overlap_end - overlap_start
                    if overlap_height > (dino_cand["height"] * Y_OVERLAP_THRESHOLD_RATIO):
                        is_overlapping = True
                        break
                
                if not is_overlapping:
                    final_team_raw_names.append(dino_raw_name)
                    final_team_normalized_names_set.add(dino_norm_name)
                    occupied_y_slots_by_akaze.append((dino_roi_y_start, dino_roi_y_end, dino_norm_name))
                    logging.info(f"Добавлен герой (DINO): {self.normalize_hero_name_for_display(dino_raw_name)} (sim: {dino_cand['similarity']:.3f})")
            
            # 6. Финальные результаты
            end_time = time.time()
            total_time = end_time - start_time
            
            logging.info(f"=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ ===")
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
    """Основная функция для тестирования с кардинально улучшенным DINO"""
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
                
                save_debug = (i == 1)
                roi_sizes = [150, 224]
                
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