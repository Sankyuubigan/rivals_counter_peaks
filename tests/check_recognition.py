"""
Функция распознавания героев Marvel Rivals
Использует модель DINOv3 и AKAZE для определения героев на скриншоте
"""
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Пути к ресурсам
VISION_MODELS_DIR = "vision_models"
MODEL_PATH = "vision_models/dinov3-vitb16-pretrain-lvd1689m/model_q4.onnx"
EMBEDDINGS_DIR = "resources/embeddings_padded"
HEROES_ICONS_DIR = "resources/heroes_icons"
SCREENSHOTS_DIR = "tests/for_recogn/screenshots"
CORRECT_ANSWERS_FILE = "tests/for_recogn/correct_answers.json"
DEBUG_DIR = "tests/debug"  # Директория для отладочных изображений

# Константы модели
TARGET_SIZE = 224
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]

# КРИТИЧЕСКИ ВАЖНО: Размер ROI должен соответствовать размеру иконок (150x150)
WINDOW_SIZE_W_DINO = 224  # Соответствует размеру иконок
WINDOW_SIZE_H_DINO = 224  # Соответствует размеру иконок
ROI_GENERATION_STRIDE_Y_DINO = int(WINDOW_SIZE_H_DINO * 0.7)
FALLBACK_DINO_STRIDE_W = int(WINDOW_SIZE_W_DINO * 0.8)
FALLBACK_DINO_STRIDE_H = int(WINDOW_SIZE_H_DINO * 0.8)
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0, 0, 0)
AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
AKAZE_MIN_MATCH_COUNT_COLUMN_LOC = 5  # Порог AKAZE
MIN_HEROES_FOR_COLUMN_DETECTION = 2
ROI_X_JITTER_VALUES_DINO = [-3, 0, 3]
MAX_NOT_PASSED_AKAZE_TO_LOG = 15

# СНИЖАЕМ ПОРОГИ для DINOv3
DINOV2_LOGGING_SIMILARITY_THRESHOLD = 0.10
DINOV2_FINAL_DECISION_THRESHOLD = 0.50  # Снижаем с 0.65 до 0.50
DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE = 0.30  # Снижаем с 0.40 до 0.30
TEAM_SIZE = 6
Y_OVERLAP_THRESHOLD_RATIO = 0.5

# ОБЛАСТЬ ЗАХВАТА ЭКРАНА (как в старом коде, но с измененными параметрами)
RECOGNITION_AREA = {
    'monitor': 1, 
    'left_pct': 50, 
    'top_pct': 20, 
    'width_pct': 20,  # Изменено с 40% на 20%
    'height_pct': 50
}

# Создаем директорию для отладки
os.makedirs(DEBUG_DIR, exist_ok=True)

class HeroRecognitionSystem:
    """Система распознавания героев Marvel Rivals"""
    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, List[np.ndarray]] = {}
        self.hero_icons: Dict[str, np.ndarray] = {}
        self.similarity_stats = []  # Статистика similarity scores
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
                logging.debug(f"Загружено {len(embeddings)} эмбеддингов для {hero_name}")
            
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
            
            logging.info(f"Захвачена область экрана: {width}x{height} в позиции ({left}, {top})")
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
            
            logging.info(f"Изображение обрезано: {width}x{height} в позиции ({left}, {top})")
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
            logging.debug(f"Сохранено отладочное изображение: {filepath}")
        except Exception as e:
            logging.error(f"Ошибка сохранения отладочного изображения: {e}")
    
    # ТОЧНОЕ соответствие функции из файла создания эмбеддингов
    def dynamic_resize_preprocess(self, image_pil: Image.Image, target_size=224, image_mean=None, image_std=None):
        """
        Динамическая предобработка изображений любого размера для DINOv3
        Точная копия функции из файла создания эмбеддингов
        """
        try:
            # 1. Улучшаем качество изображения
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')
            
            # Улучшаем контрастность
            enhancer = ImageEnhance.Contrast(image_pil)
            image_pil = enhancer.enhance(1.5)
            
            # Улучшаем резкость
            enhancer = ImageEnhance.Sharpness(image_pil)
            image_pil = enhancer.enhance(1.2)
            
            # Небольшая коррекция яркости
            enhancer = ImageEnhance.Brightness(image_pil)
            image_pil = enhancer.enhance(1.1)
            
            # 2. Получаем оригинальные размеры для логирования
            original_width, original_height = image_pil.size
            logging.debug(f"Обработка изображения: {original_width}x{original_height} -> {target_size}x{target_size}")
            
            # 3. Динамический выбор стратегии обработки в зависимости от размера изображения
            max_dimension = max(original_width, original_height)
            
            if max_dimension <= target_size:
                # Для маленьких изображений (как ваши 150x150): upscale + resize
                intermediate_size = int(target_size * 1.5)  # Увеличиваем до 336px для 224 target
                
                # Сначала upscale с сохранением пропорций
                scale = intermediate_size / max_dimension
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                
                img_intermediate = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Затем финальный resize до целевого размера
                img_resized = img_intermediate.resize((target_size, target_size), Image.Resampling.LANCZOS)
                
            elif max_dimension <= target_size * 2:
                # Для средних изображений: прямой resize с высококачественной интерполяцией
                img_resized = image_pil.resize((target_size, target_size), Image.Resampling.LANCZOS)
                
            else:
                # Для больших изображений: сначала уменьшаем с сохранением пропорций, затем resize
                scale = (target_size * 1.5) / max_dimension
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                
                img_intermediate = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img_resized = img_intermediate.resize((target_size, target_size), Image.Resampling.LANCZOS)
            
            # 4. Конвертируем в numpy array
            img_array = np.array(img_resized, dtype=np.float32) / 255.0
            
            # 5. Нормализация (используем переданные параметры или значения по умолчанию)
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
            # Возвращаем нулевой тензор в случае ошибки
            return np.zeros((1, 3, target_size, target_size), dtype=np.float32)
    
    def preprocess_image_for_dino(self, image_pil: Image.Image, roi_info: str = "") -> np.ndarray:
        """Предобработка изображения для DINOv3 - точное соответствие созданию эмбеддингов"""
        logging.debug(f"Предобработка ROI {roi_info}: оригинальный размер {image_pil.size}")
        
        # Сохраняем оригинальное ROI для отладки
        if roi_info:
            self.save_debug_image(image_pil, f"roi_{roi_info}_original.png")
        
        # Применяем предобработку
        processed_tensor = self.dynamic_resize_preprocess(image_pil, TARGET_SIZE, IMAGE_MEAN, IMAGE_STD)
        
        # Сохраняем предобработанное изображение (конвертируем обратно в PIL)
        try:
            # Обратное преобразование для сохранения
            img_array = processed_tensor[0]  # Убираем batch dimension
            img_array = np.transpose(img_array, (1, 2, 0))  # CHW -> HWC
            img_array = img_array * np.array(IMAGE_STD) + np.array(IMAGE_MEAN)
            img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)
            processed_pil = Image.fromarray(img_array)
            
            if roi_info:
                self.save_debug_image(processed_pil, f"roi_{roi_info}_processed.png")
        except Exception as e:
            logging.error(f"Ошибка сохранения предобработанного изображения: {e}")
        
        return processed_tensor
    
    def get_cls_embedding(self, image_pil: Image.Image, roi_info: str = "") -> np.ndarray:
        """Получение CLS эмбеддинга для изображения"""
        if not self.is_ready():
            return np.array([])
        try:
            # Используем функцию, которая точно соответствует созданию эмбеддингов
            inputs = self.preprocess_image_for_dino(image_pil, roi_info)
            onnx_outputs = self.ort_session.run(None, {self.input_name: inputs})
            last_hidden_state = onnx_outputs[0]
            cls_embedding = last_hidden_state[0, 0, :]
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
    
    def get_best_match(self, query_embedding: np.ndarray, roi_info: str = "") -> Tuple[Optional[str], float]:
        """Находит лучшее совпадение со всеми эмбеддингами героя"""
        if len(query_embedding) == 0:
            return None, 0.0
        
        best_sim = -1.0
        best_hero = None
        all_similarities = []
        
        # Сравниваем со всеми эмбеддингами всех героев
        for hero_name, hero_emb_list in self.hero_embeddings.items():
            for i, hero_emb in enumerate(hero_emb_list):
                similarity = self.cosine_similarity(query_embedding, hero_emb)
                all_similarities.append((hero_name, similarity, i))
                
                if similarity > best_sim:
                    best_sim = similarity
                    best_hero = hero_name
        
        # Логируем топ-5 совпадений для анализа
        all_similarities.sort(key=lambda x: x[1], reverse=True)
        top_matches = all_similarities[:5]
        
        logging.debug(f"ROI {roi_info}: Топ-5 совпадений:")
        for hero, sim, emb_idx in top_matches:
            logging.debug(f"  {hero} (emb_{emb_idx}): {sim:.4f}")
        
        # Сохраняем статистику
        self.similarity_stats.append({
            'roi_info': roi_info,
            'best_hero': best_hero,
            'best_similarity': best_sim,
            'top_matches': top_matches
        })
        
        return best_hero, best_sim
    
    def get_adaptive_threshold(self, base_threshold: float, akaze_matches: int) -> float:
        """Адаптивный порог на основе количества AKAZE совпадений"""
        if akaze_matches >= 20:
            return base_threshold * 0.75  # Сильнее снижаем для хороших совпадений
        elif akaze_matches >= 15:
            return base_threshold * 0.85
        elif akaze_matches >= 10:
            return base_threshold * 0.90
        elif akaze_matches >= 6:
            return base_threshold * 0.95
        else:
            return base_threshold
    
    def get_hero_column_center_akaze(self, large_image_cv2: np.ndarray) -> Tuple[Optional[int], List[str]]:
        """Определение центра колонки героев с помощью AKAZE"""
        if large_image_cv2 is None:
            logging.error("Входное изображение - None")
            return None, []
        if not self.hero_icons:
            logging.warning("Словарь иконок героев пуст. Локализация колонки невозможна.")
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
            logging.warning("Не найдено дескрипторов на скриншоте.")
            return None, []
        
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        all_matched_x_coords_on_screenshot: List[float] = []
        akaze_candidates_found: List[str] = []
        hero_match_details: List[Dict[str, Any]] = []
        
        logging.info(f"Поиск центра колонки (порог совпадений: {AKAZE_MIN_MATCH_COUNT_COLUMN_LOC}):")
        
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
                    logging.warning(f"Ошибка detectAndCompute для шаблона {hero_name}_{i}: {e}")
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
        
        sorted_hero_match_details = sorted(hero_match_details, key=lambda item: item["matches"], reverse=True)
        for detail in sorted_hero_match_details:
            logging.info(f"  {detail['name']}: {detail['matches']} совпадений (ПРОШЕЛ ФИЛЬТР)")
            all_matched_x_coords_on_screenshot.extend(detail['x_coords'])
        
        all_template_heroes_set = set(self.hero_icons.keys())
        passed_heroes_set = set(d['name'] for d in hero_match_details)
        not_passed_heroes = sorted(list(all_template_heroes_set - passed_heroes_set))
        logged_not_passed_count = 0
        for hero_name in not_passed_heroes:
            if logged_not_passed_count < MAX_NOT_PASSED_AKAZE_TO_LOG:
                logging.info(f"  {hero_name}: <{AKAZE_MIN_MATCH_COUNT_COLUMN_LOC} совпадений (НЕ ПРОШЕЛ)")
                logged_not_passed_count += 1
            elif logged_not_passed_count == MAX_NOT_PASSED_AKAZE_TO_LOG:
                logging.info(f"  ... и еще {len(not_passed_heroes) - MAX_NOT_PASSED_AKAZE_TO_LOG} не прошли фильтр (логирование ограничено)")
                break
        
        if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
            logging.warning(f"Найдено слишком мало героев ({len(akaze_candidates_found)}), чтобы надежно определить центр колонки. Требуется: {MIN_HEROES_FOR_COLUMN_DETECTION}.")
            return None, akaze_candidates_found
        
        if not all_matched_x_coords_on_screenshot:
            logging.warning("Не найдено X-координат совпадений для определения центра колонки.")
            return None, akaze_candidates_found
        
        rounded_x_coords = [round(x / 10.0) * 10 for x in all_matched_x_coords_on_screenshot]
        if not rounded_x_coords:
            logging.warning("Нет округленных X-координат для определения центра.")
            return None, akaze_candidates_found
        
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
        """Временная версия для тестирования - всегда используем полное сканирование"""
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
            logging.warning("Нет данных для анализа similarity scores")
            return
        
        # Разделяем на правильные и неправильные детекции
        correct_sims = []
        incorrect_sims = []
        
        for stat in self.similarity_stats:
            if stat['best_similarity'] > 0:
                # Здесь можно добавить логику для определения правильности детекции
                # Пока просто разделяем по порогу
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
        """Основная функция распознавания героев"""
        start_time = time.time()
        self.similarity_stats = []  # Очищаем статистику для каждого распознавания
        
        try:
            # 1. Загружаем скриншот
            if use_screen_capture:
                # Захватываем область экрана
                logging.info("Захват области экрана...")
                screenshot_cv2 = self.capture_screen_area()
                if screenshot_cv2 is None:
                    logging.error("Не удалось захватить область экрана")
                    return []
                screenshot_pil = Image.fromarray(cv2.cvtColor(screenshot_cv2, cv2.COLOR_BGR2RGB))
            else:
                # Для тестирования - загружаем из файла
                if test_file_index is None:
                    test_file_index = 1  # По умолчанию первый файл
                
                screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{test_file_index}.png")
                if not os.path.exists(screenshot_path):
                    logging.error(f"Скриншот не найден: {screenshot_path}")
                    return []
                logging.info(f"Загрузка скриншота: {screenshot_path}")
                full_screenshot_pil = Image.open(screenshot_path)
                
                # Обрезаем по RECOGNITION_AREA (как в режиме захвата экрана)
                screenshot_pil = self.crop_image_to_recognition_area(full_screenshot_pil)
                
                # Сохраняем обрезанную область для теста (только если save_debug=True)
                if save_debug:
                    debug_path = os.path.join(SCREENSHOTS_DIR, "debug.png")
                    screenshot_pil.save(debug_path)
                    logging.info(f"Сохранен отладочный скриншот: {debug_path}")
                
                # Конвертируем в cv2 для дальнейшей обработки
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
                
                # Экспериментируем с размером ROI
                if experiment_roi_size:
                    # Изменяем размер ROI для эксперимента
                    window_pil = window_pil.resize((experiment_roi_size, experiment_roi_size), Image.Resampling.LANCZOS)
                
                roi_info = f"{i}_x{x}_y{y}"
                
                # Получаем эмбеддинг
                window_embedding = self.get_cls_embedding(window_pil, roi_info)
                if len(window_embedding) == 0:
                    continue
                
                # Находим наиболее похожего героя
                best_hero, best_sim = self.get_best_match(window_embedding, roi_info)
                
                if best_hero is not None and best_sim >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                    all_dino_detections.append({
                        "name": best_hero,
                        "similarity": best_sim,
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height
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
            logging.info(f"Нормализованные AKAZE имена: {akaze_unique_normalized}")
            
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
                adaptive_threshold = self.get_adaptive_threshold(DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE, akaze_matches)
                
                if best_dino_match and highest_similarity >= adaptive_threshold:
                    raw_name_to_add = best_dino_match["name"]
                    final_team_raw_names.append(raw_name_to_add)
                    final_team_normalized_names_set.add(akaze_norm_name)
                    y_start = best_dino_match["y"]
                    y_end = y_start + best_dino_match["height"]
                    occupied_y_slots_by_akaze.append((y_start, y_end, akaze_norm_name))
                    logging.info(f"Добавлен герой (AKAZE+DINO): {raw_name_to_add} (sim: {highest_similarity:.3f}, адаптивный порог: {adaptive_threshold:.3f})")
                else:
                    logging.warning(f"AKAZE нашел '{akaze_norm_name}', но DINO не подтвердил с достаточной уверенностью (порог: {adaptive_threshold:.3f})")
                    # Добавляем AKAZE героя без DINO подтверждения, если у него есть эмбеддинг
                    if akaze_norm_name in self.hero_embeddings:
                        final_team_raw_names.append(akaze_norm_name)
                        final_team_normalized_names_set.add(akaze_norm_name)
                        logging.info(f"Добавлен герой (AKAZE только): {akaze_norm_name}")
            
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
                        if dino_norm_name == occ_hero_name:
                            logging.debug(f"Пропускаем дубликат: {dino_raw_name}")
                        else:
                            logging.info(f"Пропускаем из-за пересечения с {occ_hero_name}: {dino_raw_name}")
                        is_overlapping = True
                        break
                
                if not is_overlapping:
                    final_team_raw_names.append(dino_raw_name)
                    final_team_normalized_names_set.add(dino_norm_name)
                    occupied_y_slots_by_akaze.append((dino_roi_y_start, dino_roi_y_end, dino_norm_name))
                    logging.info(f"Добавлен герой (DINO): {dino_raw_name} (sim: {dino_cand['similarity']:.3f})")
            
            # 6. Финальные результаты
            end_time = time.time()
            total_time = end_time - start_time
            logging.info(f"=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ ===")
            logging.info(f"Время выполнения: {total_time:.2f} секунд")
            logging.info(f"Распознано героев: {len(final_team_raw_names)}")
            for i, hero_name in enumerate(final_team_raw_names, 1):
                display_name = self.normalize_hero_name_for_display(hero_name)
                logging.info(f"  {i}. {display_name}")
            
            return final_team_raw_names
        except Exception as e:
            logging.error(f"Ошибка распознавания: {e}")
            return []

def main():
    """Основная функция для тестирования"""
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
        
        # Статистика по всем скриншотам
        total_stats = {
            'total_screenshots': 0,
            'total_correct': 0,
            'total_false_positive': 0,
            'total_false_negative': 0,
            'total_precision': 0,
            'total_recall': 0,
            'total_f1': 0,
            'screenshot_results': []
        }
        
        # Тестируем на всех скриншотах
        for i in range(1, 8):
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{i}.png")
            if os.path.exists(screenshot_path):
                logging.info(f"\n=== ТЕСТИРОВАНИЕ СКРИНШОТА {i} ===")
                
                # Для первого скриншота сохраняем debug, для остальных - нет
                save_debug = (i == 1)
                
                # Тестируем с разными размерами ROI
                roi_sizes = [150, 224]  # Текущий размер и размер модели
                
                for roi_size in roi_sizes:
                    logging.info(f"\n--- Тестирование с размером ROI: {roi_size}x{roi_size} ---")
                    
                    recognized_heroes = system.recognize_heroes(
                        use_screen_capture=False, 
                        test_file_index=i, 
                        save_debug=save_debug,
                        experiment_roi_size=roi_size
                    )
                    
                    expected_heroes = correct_answers.get(str(i), [])
                    logging.info(f"Ожидаемые герои: {expected_heroes}")
                    logging.info(f"Распознанные герои: {recognized_heroes}")
                    
                    # Конвертируем распознанные имена в правильный формат для сравнения
                    normalized_recognized = [system.normalize_hero_name_for_display(hero) for hero in recognized_heroes]
                    recognized_set = set(normalized_recognized)
                    expected_set = set(expected_heroes)
                    logging.info(f"Нормализованные распознанные герои: {normalized_recognized}")
                    
                    correct = len(recognized_set & expected_set)
                    false_positive = len(recognized_set - expected_set)
                    false_negative = len(expected_set - recognized_set)
                    
                    logging.info(f"Правильных: {correct}")
                    logging.info(f"Ложных срабатываний: {false_positive}")
                    logging.info(f"Пропущенных: {false_negative}")
                    
                    precision = correct / len(recognized_set) if recognized_set else 0
                    recall = correct / len(expected_set) if expected_set else 0
                    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                    
                    logging.info(f"Precision: {precision:.3f}")
                    logging.info(f"Recall: {recall:.3f}")
                    logging.info(f"F1-score: {f1:.3f}")
                    
                    # Сохраняем результаты для общего отчета
                    screenshot_result = {
                        'screenshot': i,
                        'roi_size': roi_size,
                        'correct': correct,
                        'false_positive': false_positive,
                        'false_negative': false_negative,
                        'precision': precision,
                        'recall': recall,
                        'f1': f1,
                        'expected_count': len(expected_heroes),
                        'recognized_count': len(recognized_heroes)
                    }
                    total_stats['screenshot_results'].append(screenshot_result)
                    
                    # Накопительная статистика
                    total_stats['total_screenshots'] += 1
                    total_stats['total_correct'] += correct
                    total_stats['total_false_positive'] += false_positive
                    total_stats['total_false_negative'] += false_negative
                    total_stats['total_precision'] += precision
                    total_stats['total_recall'] += recall
                    total_stats['total_f1'] += f1
            else:
                logging.warning(f"Скриншот {i}.png не найден")
        
        # Общий отчет
        if total_stats['total_screenshots'] > 0:
            logging.info(f"\n{'='*60}")
            logging.info(f"ОБЩИЙ ОТЧЕТ ПО ВСЕМ СКРИНШОТАМ")
            logging.info(f"{'='*60}")
            logging.info(f"Всего протестировано скриншотов: {total_stats['total_screenshots']}")
            
            # Средние метрики
            avg_precision = total_stats['total_precision'] / total_stats['total_screenshots']
            avg_recall = total_stats['total_recall'] / total_stats['total_screenshots']
            avg_f1 = total_stats['total_f1'] / total_stats['total_screenshots']
            
            logging.info(f"Средняя точность (Precision): {avg_precision:.3f}")
            logging.info(f"Средняя полнота (Recall): {avg_recall:.3f}")
            logging.info(f"Средний F1-score: {avg_f1:.3f}")
            
            # Детальная статистика по каждому скриншоту
            logging.info(f"\nПОДРОБНЫЕ РЕЗУЛЬТАТЫ:")
            logging.info(f"{'-'*100}")
            logging.info(f"{'Скриншот':<10} {'ROI':<8} {'Верных':<8} {'Ложных':<8} {'Пропущ':<8} {'Precision':<10} {'Recall':<10} {'F1':<10}")
            logging.info(f"{'-'*100}")
            for result in total_stats['screenshot_results']:
                logging.info(f"{result['screenshot']:<10} {result['roi_size']:<8} {result['correct']:<8} {result['false_positive']:<8} {result['false_negative']:<8} "
                           f"{result['precision']:<10.3f} {result['recall']:<10.3f} {result['f1']:<10.3f}")
            logging.info(f"{'-'*100}")
            
            # Общая оценка качества
            if avg_f1 >= 0.8:
                quality = "ОТЛИЧНО"
            elif avg_f1 >= 0.6:
                quality = "ХОРОШО"
            elif avg_f1 >= 0.4:
                quality = "УДОВЛЕТВОРИТЕЛЬНО"
            else:
                quality = "ТРЕБУЕТ УЛУЧШЕНИЯ"
            
            logging.info(f"\nОБЩАЯ ОЦЕНКА КАЧЕСТВА: {quality}")
            logging.info(f"{'='*60}")
    else:
        logging.error(f"Файл с правильными ответами не найден: {CORRECT_ANSWERS_FILE}")

if __name__ == "__main__":
    main()