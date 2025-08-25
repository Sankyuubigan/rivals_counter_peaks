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
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict

import cv2
from PIL import Image, ImageOps, ImageEnhance
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

# Константы модели
TARGET_SIZE = 224
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]

# Константы AKAZE
WINDOW_SIZE_W_DINO = 93
WINDOW_SIZE_H_DINO = 93
ROI_GENERATION_STRIDE_Y_DINO = int(WINDOW_SIZE_H_DINO * 0.8)
FALLBACK_DINO_STRIDE_W = int(WINDOW_SIZE_W_DINO * 0.9)
FALLBACK_DINO_STRIDE_H = int(WINDOW_SIZE_H_DINO * 0.9)
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0, 0, 0)
AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
AKAZE_MIN_MATCH_COUNT_COLUMN_LOC = 3
MIN_HEROES_FOR_COLUMN_DETECTION = 2
ROI_X_JITTER_VALUES_DINO = [-3, 0, 3]
MAX_NOT_PASSED_AKAZE_TO_LOG = 15

# Константы распознавания
DINOV2_LOGGING_SIMILARITY_THRESHOLD = 0.10
DINOV2_FINAL_DECISION_THRESHOLD = 0.50  # Снижаем порог для финального решения
DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE = 0.30  # Снижаем порог для AKAZE подтверждения
TEAM_SIZE = 6
Y_OVERLAP_THRESHOLD_RATIO = 0.5


class HeroRecognitionSystem:
    """Система распознавания героев Marvel Rivals"""

    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, np.ndarray] = {}
        self.hero_icons: Dict[str, np.ndarray] = {}  # Для AKAZE

        logging.info("Инициализация системы распознавания героев...")

    def load_model(self) -> bool:
        """Загрузка ONNX модели DINOv3"""
        try:
            if not os.path.exists(MODEL_PATH):
                logging.error(f"Модель не найдена: {MODEL_PATH}")
                return False

            self.ort_session = onnxruntime.InferenceSession(
                MODEL_PATH,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
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

            # Группируем эмбеддинги по героям (hero_name -> [emb1, emb2, ...])
            hero_embedding_groups = defaultdict(list)

            for emb_file in embedding_files:
                # Извлекаем имя героя без номера (hero_name_1.npy -> hero_name)
                base_name = os.path.splitext(emb_file)[0]
                parts = base_name.split('_')

                if len(parts) >= 2 and parts[-1].isdigit():
                    # Убираем номер в конце
                    hero_name = '_'.join(parts[:-1])
                else:
                    hero_name = base_name

                emb_path = os.path.join(EMBEDDINGS_DIR, emb_file)

                try:
                    embedding = np.load(emb_path)
                    hero_embedding_groups[hero_name].append(embedding)
                except Exception as e:
                    logging.warning(f"Ошибка загрузки эмбеддинга {emb_file}: {e}")

            # Для каждого героя усредняем все его эмбеддинги
            for hero_name, embeddings in hero_embedding_groups.items():
                if len(embeddings) == 1:
                    self.hero_embeddings[hero_name] = embeddings[0]
                else:
                    # Усредняем все эмбеддинги героя
                    self.hero_embeddings[hero_name] = np.mean(embeddings, axis=0)
                    logging.debug(f"Усреднен эмбеддинг для {hero_name}: {len(embeddings)} файлов")

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
                # Извлекаем имя героя из названия файла
                # Формат: hero_name_1.png, hero_name_2.png, etc.
                base_name = os.path.splitext(icon_file)[0]
                parts = base_name.split('_')

                if len(parts) >= 2:
                    # Убираем цифру в конце и соединяем части
                    hero_name_parts = parts[:-1]  # Все кроме последней части (цифры)
                    hero_name = ' '.join(hero_name_parts)

                    # Нормализуем имя героя
                    hero_name = hero_name.replace('_', ' ').title()

                    icon_path = os.path.join(HEROES_ICONS_DIR, icon_file)

                    try:
                        # Загружаем изображение
                        img = cv2.imread(icon_path, cv2.IMREAD_UNCHANGED)
                        if img is not None:
                            # Конвертируем в BGR если нужно
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

    def preprocess_image_dynamic_resize(self, image_pil: Image.Image) -> np.ndarray:
        """Динамическая предобработка изображений для DINOv3"""
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

            # 2. Получаем оригинальные размеры
            original_width, original_height = image_pil.size
            max_dimension = max(original_width, original_height)

            # 3. Динамический выбор стратегии обработки
            if max_dimension <= TARGET_SIZE:
                # Для маленьких изображений: upscale + resize
                intermediate_size = int(TARGET_SIZE * 1.5)

                scale = intermediate_size / max_dimension
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)

                img_intermediate = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img_resized = img_intermediate.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

            elif max_dimension <= TARGET_SIZE * 2:
                # Для средних изображений: прямой resize
                img_resized = image_pil.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

            else:
                # Для больших изображений: сначала уменьшаем, затем resize
                scale = (TARGET_SIZE * 1.5) / max_dimension
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)

                img_intermediate = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img_resized = img_intermediate.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

            # 4. Конвертируем в numpy array и нормализуем
            img_array = np.array(img_resized, dtype=np.float32) / 255.0

            # 5. ImageNet нормализация
            mean = np.array(IMAGE_MEAN, dtype=np.float32)
            std = np.array(IMAGE_STD, dtype=np.float32)
            img_array = (img_array - mean) / std

            # 6. Транспонирование HWC -> CHW и добавление batch dimension
            img_array = np.transpose(img_array, (2, 0, 1))
            img_array = np.expand_dims(img_array, axis=0)

            return img_array.astype(np.float32)

        except Exception as e:
            logging.error(f"Ошибка предобработки изображения: {e}")
            return np.zeros((1, 3, TARGET_SIZE, TARGET_SIZE), dtype=np.float32)

    def get_cls_embedding(self, image_pil: Image.Image) -> np.ndarray:
        """Получение CLS эмбеддинга для изображения"""
        if not self.is_ready():
            return np.array([])

        try:
            # Предобработка
            inputs = self.preprocess_image_dynamic_resize(image_pil)

            # Получаем выход модели
            onnx_outputs = self.ort_session.run(None, {self.input_name: inputs})

            # Извлекаем CLS токен (первый токен)
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

        # Инициализация AKAZE
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

    def recognize_heroes(self, screenshot_path: str) -> List[str]:
        """Основная функция распознавания героев"""
        start_time = time.time()

        try:
            # 1. Загружаем скриншот
            if not os.path.exists(screenshot_path):
                logging.error(f"Скриншот не найден: {screenshot_path}")
                return []

            logging.info(f"Загрузка скриншота: {screenshot_path}")
            screenshot_pil = Image.open(screenshot_path)
            screenshot_cv2 = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)

            s_width, s_height = screenshot_pil.size
            logging.info(f"Размер скриншота: {s_width}x{s_height}")

            # 2. Определяем центр колонки героев с помощью AKAZE
            akaze_start_time = time.time()
            column_x_center, akaze_identified_names = self.get_hero_column_center_akaze(screenshot_cv2)
            akaze_end_time = time.time()
            logging.info(f"AKAZE локализация: {akaze_end_time - akaze_start_time:.2f} сек. Найдено: {akaze_identified_names}")

            # 3. Генерируем ROI для анализа
            rois_for_dino: List[Dict[str, int]] = []

            if column_x_center is not None:
                base_roi_start_x = column_x_center - (WINDOW_SIZE_W_DINO // 2)
                logging.info(f"Генерация ROI. Базовый левый край X={base_roi_start_x}")

                for y_base in range(0, s_height - WINDOW_SIZE_H_DINO + 1, ROI_GENERATION_STRIDE_Y_DINO):
                    for x_offset in ROI_X_JITTER_VALUES_DINO:
                        current_roi_start_x = base_roi_start_x + x_offset
                        if 0 <= current_roi_start_x and (current_roi_start_x + WINDOW_SIZE_W_DINO) <= s_width:
                            rois_for_dino.append({'x': current_roi_start_x, 'y': y_base})
            else:
                logging.warning("Не удалось определить центр колонки. Используем fallback сканирование.")
                for y in range(0, s_height - WINDOW_SIZE_H_DINO + 1, FALLBACK_DINO_STRIDE_H):
                    for x_val in range(0, s_width - WINDOW_SIZE_W_DINO + 1, FALLBACK_DINO_STRIDE_W):
                        rois_for_dino.append({'x': x_val, 'y': y})

            logging.info(f"Сгенерировано ROI для анализа: {len(rois_for_dino)}")

            if not rois_for_dino:
                logging.warning("Не сгенерировано ни одного ROI для анализа.")
                return []

            # 4. Обрабатываем ROI и получаем эмбеддинги
            dino_start_time = time.time()
            all_dino_detections: List[Dict[str, Any]] = []

            for i, roi_coord in enumerate(rois_for_dino):
                if i % 100 == 0:
                    logging.info(f"Обработка ROI {i}/{len(rois_for_dino)}")

                x, y = roi_coord['x'], roi_coord['y']
                window_pil = screenshot_pil.crop((x, y, x + WINDOW_SIZE_W_DINO, y + WINDOW_SIZE_H_DINO))

                # Получаем эмбеддинг
                window_embedding = self.get_cls_embedding(window_pil)
                if len(window_embedding) == 0:
                    continue

                # Находим наиболее похожего героя
                best_sim = -1.0
                best_hero = None

                for hero_name, hero_embedding in self.hero_embeddings.items():
                    similarity = self.cosine_similarity(window_embedding, hero_embedding)
                    if similarity > best_sim:
                        best_sim = similarity
                        best_hero = hero_name

                if best_hero is not None and best_sim >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                    all_dino_detections.append({
                        "name": best_hero,
                        "similarity": best_sim,
                        "x": x,
                        "y": y
                    })

            dino_end_time = time.time()
            logging.info(f"DINO обработка: {dino_end_time - dino_start_time:.2f} сек. Найдено детекций: {len(all_dino_detections)}")

            # 5. Комбинированная логика DINO + AKAZE
            final_team_raw_names: List[str] = []
            final_team_normalized_names_set: Set[str] = set()
            occupied_y_slots_by_akaze: List[Tuple[int, int, str]] = []

            # Преобразуем имена AKAZE в правильный формат для сравнения
            akaze_normalized_names = []
            for name in akaze_identified_names:
                # Приводим к формату, соответствующему эмбеддингам (заменяем пробелы на подчеркивания)
                normalized = name.lower().replace(' ', '_')
                akaze_normalized_names.append(normalized)

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
                    # Сравниваем нормализованные имена
                    if dino_norm_name == akaze_norm_name:
                        if dino_cand["similarity"] > highest_similarity and \
                           dino_cand["similarity"] >= DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE:
                            highest_similarity = dino_cand["similarity"]
                            best_dino_match = dino_cand

                if best_dino_match:
                    raw_name_to_add = best_dino_match["name"]
                    final_team_raw_names.append(raw_name_to_add)
                    final_team_normalized_names_set.add(akaze_norm_name)

                    y_start = best_dino_match["y"]
                    y_end = y_start + WINDOW_SIZE_H_DINO
                    occupied_y_slots_by_akaze.append((y_start, y_end, akaze_norm_name))

                    logging.info(f"Добавлен герой (AKAZE+DINO): {raw_name_to_add} (sim: {highest_similarity:.3f})")
                else:
                    logging.warning(f"AKAZE нашел '{akaze_norm_name}', но DINO не подтвердил с достаточной уверенностью")
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
                dino_roi_y_end = dino_roi_y_start + WINDOW_SIZE_H_DINO
                is_overlapping = False

                for occ_y_start, occ_y_end, occ_hero_name in occupied_y_slots_by_akaze:
                    overlap_start = max(dino_roi_y_start, occ_y_start)
                    overlap_end = min(dino_roi_y_end, occ_y_end)
                    overlap_height = overlap_end - overlap_start

                    if overlap_height > (WINDOW_SIZE_H_DINO * Y_OVERLAP_THRESHOLD_RATIO):
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
                logging.info(f"  {i}. {hero_name}")

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

                recognized_heroes = system.recognize_heroes(screenshot_path)
                expected_heroes = correct_answers.get(str(i), [])

                logging.info(f"Ожидаемые герои: {expected_heroes}")
                logging.info(f"Распознанные герои: {recognized_heroes}")

                # Конвертируем распознанные имена в правильный формат для сравнения
                def normalize_for_comparison(name):
                    # Конвертируем из формата с подчеркиваниями в формат с пробелами и заглавными буквами
                    if isinstance(name, str):
                        # Заменяем подчеркивания на пробелы и делаем заглавными
                        normalized = name.replace('_', ' ').title()
                        # Обрабатываем специальные случаи
                        if 'Jeff The Land Shark' in normalized:
                            return 'Jeff The Land Shark'
                        elif 'Cloak And Dagger' in normalized:
                            return 'Cloak & Dagger'
                        elif 'The Punisher' in normalized:
                            return 'The Punisher'
                        elif 'The Thing' in normalized:
                            return 'The Thing'
                        elif 'Mister Fantastic' in normalized:
                            return 'Mister Fantastic'
                        elif 'Doctor Strange' in normalized:
                            return 'Doctor Strange'
                        elif 'Captain America' in normalized:
                            return 'Captain America'
                        elif 'Human Torch' in normalized:
                            return 'Human Torch'
                        elif 'Iron Man' in normalized:
                            return 'Iron Man'
                        elif 'Black Panther' in normalized:
                            return 'Black Panther'
                        elif 'Black Widow' in normalized:
                            return 'Black Widow'
                        elif 'Winter Soldier' in normalized:
                            return 'Winter Soldier'
                        elif 'Scarlet Witch' in normalized:
                            return 'Scarlet Witch'
                        elif 'Moon Knight' in normalized:
                            return 'Moon Knight'
                        elif 'Rocket Raccoon' in normalized:
                            return 'Rocket Raccoon'
                        elif 'Star Lord' in normalized:
                            return 'Star Lord'
                        elif 'Peni Parker' in normalized:
                            return 'Peni Parker'
                        elif 'Squirrel Girl' in normalized:
                            return 'Squirrel Girl'
                        elif 'Invisible Woman' in normalized:
                            return 'Invisible Woman'
                        elif 'Adam Warlock' in normalized:
                            return 'Adam Warlock'
                        elif 'Doctor Strange' in normalized:
                            return 'Doctor Strange'
                        else:
                            return normalized
                    return name

                # Конвертируем распознанные имена
                normalized_recognized = [normalize_for_comparison(hero) for hero in recognized_heroes]
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
            logging.info(f"{'-'*80}")
            logging.info(f"{'Скриншот':<10} {'Верных':<8} {'Ложных':<8} {'Пропущ':<8} {'Precision':<10} {'Recall':<10} {'F1':<10}")
            logging.info(f"{'-'*80}")

            for result in total_stats['screenshot_results']:
                logging.info(f"{result['screenshot']:<10} {result['correct']:<8} {result['false_positive']:<8} {result['false_negative']:<8} "
                           f"{result['precision']:<10.3f} {result['recall']:<10.3f} {result['f1']:<10.3f}")

            logging.info(f"{'-'*80}")

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