# File: core/advanced_recognition_logic.py
import os
import numpy as np
from PIL import Image
import onnxruntime
import time
import cv2
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple, Optional, Set
from PySide6.QtCore import QObject, Signal, QThread, Slot
from utils import normalize_hero_name as normalize_hero_name_util
from core.image_processing_utils import preprocess_image_for_dino
from core.model_loader_worker import ModelLoaderWorker

# Установка Numba (если еще не установлена)
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("Numba не установлена. Установите: pip install numba")


# Константы остаются те же, но некоторые значения по умолчанию могут быть изменены в _on_models_loaded_from_worker
WINDOW_SIZE_W_DINO = 95
WINDOW_SIZE_H_DINO = 95
ROI_GENERATION_STRIDE_Y_DINO = int(WINDOW_SIZE_H_DINO * 0.5)
FALLBACK_DINO_STRIDE_W = int(WINDOW_SIZE_W_DINO * 0.5)
FALLBACK_DINO_STRIDE_H = int(WINDOW_SIZE_H_DINO * 0.5)
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0,0,0)

AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
AKAZE_MIN_MATCH_COUNT_COLUMN_LOC = 3
MIN_HEROES_FOR_COLUMN_DETECTION = 2
ROI_X_JITTER_VALUES_DINO = [-3, 0, 3]
MAX_NOT_PASSED_AKAZE_TO_LOG = 15

DINOv3_LOGGING_SIMILARITY_THRESHOLD = 0.10
DINOv3_FINAL_DECISION_THRESHOLD = 0.70
DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE = 0.40
TEAM_SIZE = 6
Y_OVERLAP_THRESHOLD_RATIO = 0.5

# Консанты из эталонного check_recognition.py
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]
CONFIDENCE_THRESHOLD = 0.70
MAX_HEROES = 6

# =============================================================================
# ФУНКЦИИ NMS ИЗ ЭТАЛОННОГО check_recognition.py
# =============================================================================

def box_area(box):
    """Вычислить площадь bounding box"""
    return (box[2] - box[0]) * (box[3] - box[1])

def box_iou_batch(boxes_a_np: np.ndarray, boxes_b_np: np.ndarray) -> np.ndarray:
    """Векторизованный расчет IoU для двух наборов bounding boxes"""
    # Конвертируем в numpy если не являются
    if not isinstance(boxes_a_np, np.ndarray):
        boxes_a_np = np.array(boxes_a_np)
    if not isinstance(boxes_b_np, np.ndarray):
        boxes_b_np = np.array(boxes_b_np)

    area_a = box_area(boxes_a_np.T)
    area_b = box_area(boxes_b_np.T)

    top_left = np.maximum(boxes_a_np[:, None, :2], boxes_b_np[:, :2])
    bottom_right = np.minimum(boxes_a_np[:, None, 2:], boxes_b_np[:, 2:])

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


class AdvancedRecognition(QObject):
    load_started = Signal()
    load_finished = Signal(bool)

    def __init__(self, akaze_hero_template_images_cv2_dict: Dict[str, List[np.ndarray]], project_root_path: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.project_root_path = project_root_path
        self.ort_session_dino: Optional[onnxruntime.InferenceSession] = None
        self.input_name_dino: Optional[str] = None
        self.target_h_model_dino: int = 224
        self.target_w_model_dino: int = 224
        self.dino_reference_embeddings: Dict[str, np.ndarray] = {}

        self.akaze_template_images_cv2: Dict[str, List[np.ndarray]] = akaze_hero_template_images_cv2_dict

        self._models_ready = False
        self._is_loading = False
        self._loader_thread: Optional[QThread] = None
        self._loader_worker: Optional[ModelLoaderWorker] = None
        logging.info("[AdvRec] AdvancedRecognition initialized (models not loaded yet).")

    def start_async_load_models(self):
        if self._models_ready or self._is_loading:
            state = "ready" if self._models_ready else "loading"
            logging.info(f"[AdvRec] Model load requested, but already in state: {state}. Ignoring.")
            if self._models_ready:
                self.load_finished.emit(True)
            return

        logging.info("[AdvRec] Starting asynchronous model load...")
        self._is_loading = True
        self.load_started.emit()

        self._loader_worker = ModelLoaderWorker(self.project_root_path)
        self._loader_thread = QThread(self)

        if self._loader_worker is None or self._loader_thread is None :
            logging.error("[AdvRec] Не удалось создать воркер или поток для загрузки моделей.")
            self.load_finished.emit(False)
            self._is_loading = False
            return

        self._loader_worker.moveToThread(self._loader_thread)

        self._loader_worker.models_loaded_signal.connect(self._on_models_loaded_from_worker)
        self._loader_thread.started.connect(self._loader_worker.run_load)

        self._loader_thread.finished.connect(self._loader_thread.deleteLater)
        self._loader_worker.models_loaded_signal.connect(self._handle_worker_cleanup_after_signal)

        self._loader_thread.start()

    @Slot(bool, object, dict, int, int)
    def _on_models_loaded_from_worker(self, success: bool,
                                      ort_session: Optional[onnxruntime.InferenceSession],
                                      embeddings_dict: Dict[str, np.ndarray],
                                      target_h: int, target_w: int):
        logging.info(f"[AdvRec] Received models_loaded_signal from worker. Success: {success}")
        self._is_loading = False
        if success and ort_session:
            self.ort_session_dino = ort_session
            if self.ort_session_dino: # Добавил проверку для mypy
                 self.input_name_dino = self.ort_session_dino.get_inputs()[0].name
            self.dino_reference_embeddings = embeddings_dict
            self.target_h_model_dino = target_h
            self.target_w_model_dino = target_w
            # Теперь dino_reference_embeddings это Dict[str, List[np.ndarray]] как в эталоне
            self.dino_reference_embeddings = embeddings_dict  # key: hero_name, val: list[np.ndarray]
            self._models_ready = True
            logging.info("[AdvRec] Модели и эмбеддинги успешно установлены из воркера.")
        else:
            logging.error("[AdvRec] Ошибка асинхронной загрузки моделей или неполные данные от воркера.")
            self._models_ready = False

        self.load_finished.emit(self._models_ready)

    @Slot()
    def _handle_worker_cleanup_after_signal(self):
        """Слот для безопасного удаления воркера после обработки его сигнала."""
        if self._loader_worker:
            self._loader_worker.deleteLater()
            self._loader_worker = None
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()

    def is_ready(self) -> bool:
        """Проверка готовности системы (убрана зависимость от image_processor_dino)"""
        return self._models_ready and bool(self.ort_session_dino)

    def _cosine_similarity_single(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        if vec_a is None or vec_b is None: return 0.0
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0: return 0.0
        return float(dot_product / (norm_a * norm_b))

    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        """Нормализует имя героя для отображения (заменяет подчеркивания, заглавные буквы)"""
        return hero_name.replace('_', ' ').title().replace('And', '&')

    def _pad_image_to_target_size_pil(self, image_pil: Image.Image, target_height: int, target_width: int, padding_color: Tuple[int,int,int]) -> Image.Image:
        if image_pil is None:
             return Image.new("RGB", (target_width, target_height), padding_color)
        original_width, original_height = image_pil.size
        if original_width == target_width and original_height == target_height:
            return image_pil

        target_aspect = target_width / target_height if target_height != 0 else 1.0
        original_aspect = original_width / original_height if original_height != 0 else 0

        if original_aspect > target_aspect:
            new_width = target_width
            new_height = int(new_width / original_aspect) if original_aspect != 0 else 0
        else:
            new_height = target_height
            new_width = int(new_height * original_aspect)

        if new_width <= 0 or new_height <= 0:
            return Image.new(image_pil.mode if hasattr(image_pil, 'mode') else "RGB", (target_width, target_height), padding_color)

        try:
            resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except ValueError:
            return Image.new(image_pil.mode if hasattr(image_pil, 'mode') else "RGB", (target_width, target_height), padding_color)

        padded_image = Image.new(image_pil.mode if hasattr(image_pil, 'mode') else "RGB", (target_width, target_height), padding_color)
        paste_x = (target_width - new_width) // 2
        paste_y = (target_height - new_height) // 2
        padded_image.paste(resized_image, (paste_x, paste_y))
        return padded_image

    def _get_cls_embeddings_for_batched_pil(self, pil_images_batch: List[Image.Image]) -> np.ndarray:
        """Эталонная обработка изображений как в check_recognition.py с поддержкой Numba"""
        if not self.ort_session_dino or not self.input_name_dino:
            return np.array([])

        valid_imgs = [img for img in pil_images_batch if img is not None]
        if not valid_imgs:
            return np.array([])

        # Прямая обработка как в эталоне - без transformer image processor
        arrays = []
        for img in valid_imgs:
            # Паддинг до целевого размера как в эталоне
            padded_img = self._pad_image_to_target_size_pil(img, self.target_h_model_dino, self.target_w_model_dino, PADDING_COLOR_WINDOW_DINO)
            # Простая нормализация как в эталоне
            arr = (np.array(padded_img, dtype=np.float32)/255.0 - np.array(IMAGE_MEAN, dtype=np.float32)) / np.array(IMAGE_STD, dtype=np.float32)
            arrays.append(np.transpose(arr, (2, 0, 1)))

        if not arrays:
            return np.array([])

        outputs = self.ort_session_dino.run(None, {self.input_name_dino: np.stack(arrays, axis=0)})
        embeddings = outputs[0][:, 0, :]

        # Используем Numba для ускорения нормализации эмбеддингов как в эталоне
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

    # def _get_hero_column_center_x_akaze(self, large_image_cv2: np.ndarray) -> Tuple[Optional[int], List[str]]:
    #     if large_image_cv2 is None:
    #         logging.error("[AdvRec][AKAZE CENTER] Входное изображение - None.")
    #         return None, []
    #     if not self.akaze_template_images_cv2:
    #         logging.warning("[AdvRec][AKAZE CENTER] Словарь AKAZE шаблонов пуст. Локализация колонки невозможна.")
    #         return None, []

    #     try:
    #         image_gray = cv2.cvtColor(large_image_cv2, cv2.COLOR_BGR2GRAY)
    #     except cv2.error as e:
    #         logging.error(f"[AdvRec][AKAZE CENTER] Ошибка конвертации в серое: {e}")
    #         return None, []

    #     akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
    #     try:
    #         kp_screenshot, des_screenshot = akaze.detectAndCompute(image_gray, None)
    #     except cv2.error as e:
    #         logging.error(f"[AdvRec][AKAZE CENTER] Ошибка detectAndCompute для скриншота: {e}")
    #         return None, []

    #     if des_screenshot is None or len(kp_screenshot) == 0:
    #         logging.warning("[AdvRec][AKAZE CENTER] Не найдено дескрипторов на скриншоте.")
    #         return None, []

    #     bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    #     all_matched_x_coords_on_screenshot: List[float] = []
    #     akaze_candidates_found: List[str] = []
    #     hero_match_details: List[Dict[str, Any]] = []

    #     logging.info(f"[AdvRec][AKAZE CENTER] Поиск центра колонки (порог совпадений: {AKAZE_MIN_MATCH_COUNT_COLUMN_LOC}):")

    #     for hero_name, templates_cv2_list in self.akaze_template_images_cv2.items():
    #         max_good_matches_for_hero = 0
    #         best_match_coords_for_hero: List[float] = []
    #         if not templates_cv2_list: continue
    #         for i, template_cv2_single in enumerate(templates_cv2_list):
    #             if template_cv2_single is None: continue
    #             try:
    #                 template_gray = cv2.cvtColor(template_cv2_single, cv2.COLOR_BGR2GRAY) if len(template_cv2_single.shape) == 3 else template_cv2_single
    #                 kp_template, des_template = akaze.detectAndCompute(template_gray, None)
    #             except cv2.error as e:
    #                 logging.warning(f"[AdvRec][AKAZE CENTER] Ошибка detectAndCompute для шаблона {hero_name}_{i}: {e}")
    #                 continue
    #             if des_template is None or len(kp_template) == 0: continue
    #             try: matches = bf.knnMatch(des_template, des_screenshot, k=2)
    #             except cv2.error: continue

    #             good_matches = []
    #             current_match_coords_for_template: List[float] = []
    #             valid_matches = [m_pair for m_pair in matches if m_pair is not None and len(m_pair) == 2]
    #             for m, n in valid_matches:
    #                 if m.distance < AKAZE_LOWE_RATIO * n.distance:
    #                     good_matches.append(m)
    #                     screenshot_pt_idx = m.trainIdx
    #                     if screenshot_pt_idx < len(kp_screenshot):
    #                          current_match_coords_for_template.append(kp_screenshot[screenshot_pt_idx].pt[0])

    #             if len(good_matches) > max_good_matches_for_hero:
    #                 max_good_matches_for_hero = len(good_matches)
    #                 best_match_coords_for_hero = current_match_coords_for_template

    #         if max_good_matches_for_hero >= AKAZE_MIN_MATCH_COUNT_COLUMN_LOC:
    #             hero_match_details.append({"name": hero_name, "matches": max_good_matches_for_hero, "x_coords": best_match_coords_for_hero})
    #             akaze_candidates_found.append(hero_name)

    #     sorted_hero_match_details = sorted(hero_match_details, key=lambda item: item["matches"], reverse=True)
    #     for detail in sorted_hero_match_details:
    #          logging.info(f"[AdvRec][AKAZE CENTER]   {detail['name']}: {detail['matches']} совпадений (ПРОШЕЛ ФИЛЬТР)")
    #          all_matched_x_coords_on_screenshot.extend(detail['x_coords'])

    #     all_template_heroes_set = set(self.akaze_template_images_cv2.keys())
    #     passed_heroes_set = set(d['name'] for d in hero_match_details)
    #     not_passed_heroes = sorted(list(all_template_heroes_set - passed_heroes_set))
    #     logged_not_passed_count = 0
    #     for hero_name in not_passed_heroes:
    #         if logged_not_passed_count < MAX_NOT_PASSED_AKAZE_TO_LOG:
    #             logging.info(f"[AdvRec][AKAZE CENTER]   {hero_name}: <{AKAZE_MIN_MATCH_COUNT_COLUMN_LOC} совпадений (НЕ ПРОШЕЛ)")
    #             logged_not_passed_count += 1
    #         elif logged_not_passed_count == MAX_NOT_PASSED_AKAZE_TO_LOG:
    #             logging.info(f"[AdvRec][AKAZE CENTER]   ... и еще {len(not_passed_heroes) - MAX_NOT_PASSED_AKAZE_TO_LOG} не прошли фильтр (логирование ограничено).")
    #             break

    #     if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
    #         logging.warning(f"[AdvRec][AKAZE CENTER] Найдено слишком мало героев ({len(akaze_candidates_found)}), чтобы надежно определить центр колонки. Требуется: {MIN_HEROES_FOR_COLUMN_DETECTION}.")
    #         return None, akaze_candidates_found

    #     if not all_matched_x_coords_on_screenshot:
    #         logging.warning("[AdvRec][AKAZE CENTER] Не найдено X-координат совпадений для определения центра колонки.")
    #         return None, akaze_candidates_found

    #     rounded_x_coords = [round(x / 10.0) * 10 for x in all_matched_x_coords_on_screenshot]
    #     if not rounded_x_coords:
    #         logging.warning("[AdvRec][AKAZE CENTER] Нет округленных X-координат для определения центра.")
    #         return None, akaze_candidates_found

    #     most_common_x_center = Counter(rounded_x_coords).most_common(1)[0][0]
    #     return int(most_common_x_center), akaze_candidates_found


    def recognize_heroes_on_screenshot(self, screenshot_cv2: np.ndarray) -> List[str]:
        """Упрощенное распознавание только с DINO моделью, аналогично эталонному check_recognition.py"""
        logging.info(f"[AdvRec] --->>> recognize_heroes_on_screenshot ВЫЗВАН <<<---. is_ready: {self.is_ready()}") # ДОБАВЛЕНО ЛОГИРОВАНИЕ
        if not self.is_ready():
            logging.error("[AdvRec] Модели не загружены. Распознавание невозможно.")
            return []
        if screenshot_cv2 is None:
            logging.error("[AdvRec] Входной скриншот - None.")
            return []

        script_start_time = time.time()

        try:
            screenshot_pil_original = Image.fromarray(cv2.cvtColor(screenshot_cv2, cv2.COLOR_BGR2RGB))
            s_width, s_height = screenshot_pil_original.size
        except Exception as e:
            logging.error(f"[AdvRec] Ошибка при конвертации скриншота CV2 в PIL: {e}")
            return []

        # Убрана локализация AKAZE - используем только DINO как в эталоне
        logging.info("[AdvRec] Используется только DINO распознавание (без AKAZE)")

        # Генерация ROI по принципу эталона: простой вертикальный прокрут слева
        roi_generation_start_time = time.time()

        # Параметры как в эталоне
        LEFT_OFFSET = 45  # Левое смещение для ROI
        HERO_SQUARE_SIZE = 95  # Размер квадрата героя
        STEP_SIZE = HERO_SQUARE_SIZE // 4  # Шаг как в эталоне (95//4 = 23.75)

        rois_for_dino: List[Dict[str, int]] = []

        # Генерируем кандидатов по вертикали слева (как method_fast_projection в эталоне, но пропускаем верхнюю часть)
        y = 69
        while y <= s_height - HERO_SQUARE_SIZE:
            roi = {
                'x': LEFT_OFFSET,
                'y': y,
                'width': HERO_SQUARE_SIZE,
                'height': HERO_SQUARE_SIZE
            }
            if roi['x'] + roi['width'] <= s_width and roi['y'] + roi['height'] <= s_height:
                rois_for_dino.append(roi)
            y += STEP_SIZE

        roi_generation_end_time = time.time()
        logging.info(f"[AdvRec] Время генерации ROI (эталонный метод): {roi_generation_end_time - roi_generation_start_time:.2f} сек. Сгенерировано ROI: {len(rois_for_dino)}")

        logging.info(f"[AdvRec] Сгенерировано {len(rois_for_dino)} ROI для DINO.")
        if not rois_for_dino:
            logging.warning("[AdvRec] Не сгенерировано ни одного ROI для DINO.")
            return []

        roi_generation_end_time = time.time()
        logging.info(f"[AdvRec] Время генерации ROI: {roi_generation_end_time - roi_generation_start_time:.2f} сек. Всего ROI: {len(rois_for_dino)}")

        all_dino_detections_from_roi: List[Dict[str, Any]] = []
        pil_batch: List[Image.Image] = []
        coordinates_batch: List[Dict[str, int]] = []
        processed_windows_count = 0
        dino_processing_start_time = time.time()

        for roi_coord in rois_for_dino:
            x, y = roi_coord['x'], roi_coord['y']
            window_pil_original = screenshot_pil_original.crop((x, y, x + HERO_SQUARE_SIZE, y + HERO_SQUARE_SIZE))

            # Простая конвертация в RGB как в эталоне (без preprocess_image_for_dino)
            if window_pil_original.mode != 'RGB':
                window_pil_original = window_pil_original.convert('RGB')

            pil_batch.append(window_pil_original)
            coordinates_batch.append({'x': x, 'y': y})

            if len(pil_batch) >= BATCH_SIZE_SLIDING_WINDOW_DINO:
                window_embeddings_batch = self._get_cls_embeddings_for_batched_pil(pil_batch)
                if window_embeddings_batch.size == 0 and pil_batch:
                    logging.warning(f"[AdvRec] Получен пустой батч эмбеддингов, хотя в pil_batch было {len(pil_batch)} элементов.")
                else:
                    for i in range(len(window_embeddings_batch)):
                        window_embedding = window_embeddings_batch[i]
                        coord = coordinates_batch[i]
                        best_sim_for_window = -1.0
                        best_ref_name_for_window = None
                        # Искать лучший hero как в эталоне get_best_match: макс sim из всех emb для героя
                        all_sim_scores = []
                        for ref_name, ref_embedding_list in self.dino_reference_embeddings.items():
                            best_sim_for_hero = -1.0
                            for emb in ref_embedding_list:
                                similarity = self._cosine_similarity_single(window_embedding, emb)
                                if similarity > best_sim_for_hero:
                                    best_sim_for_hero = similarity
                            all_sim_scores.append((ref_name, best_sim_for_hero))
                            if best_sim_for_hero > best_sim_for_window:
                                best_sim_for_window = best_sim_for_hero
                                best_ref_name_for_window = ref_name

                        # Логировать топ-5 если confidence низкий (для отладки)
                        if best_sim_for_window < 0.8:
                            sorted_sims = sorted(all_sim_scores, key=lambda x: x[1], reverse=True)
                            top_5 = sorted_sims[:5]
                            logging.info(f"[DEBUG] Окно ({coord['x']}, {coord['y']}), лучшая conf: {best_sim_for_window:.3f} -> {best_ref_name_for_window}. Топ-5: " + ", ".join(f"{h}@{s:.3f}" for h, s in top_5))
                        if best_ref_name_for_window is not None and best_sim_for_window >= DINOv3_FINAL_DECISION_THRESHOLD:
                            all_dino_detections_from_roi.append({
                                "hero": best_ref_name_for_window,
                                "confidence": best_sim_for_window,
                                "position": (coord['x'], coord['y']),
                                "size": (HERO_SQUARE_SIZE, HERO_SQUARE_SIZE)
                            })
                processed_windows_count += len(pil_batch)
                pil_batch = []
                coordinates_batch = []

        if pil_batch:
            window_embeddings_batch = self._get_cls_embeddings_for_batched_pil(pil_batch)
            if window_embeddings_batch.size == 0 and pil_batch:
                 logging.warning(f"[AdvRec] Получен пустой батч эмбеддингов для остатка, pil_batch: {len(pil_batch)}.")
            else:
                for i in range(len(window_embeddings_batch)):
                    window_embedding = window_embeddings_batch[i]
                    coord = coordinates_batch[i]
                    best_sim_for_window = -1.0
                    best_ref_name_for_window = None
                    # Искать лучший hero как в эталоне get_best_match: макс sim из всех emb для героя
                    all_sim_scores = []
                    for ref_name, ref_embedding_list in self.dino_reference_embeddings.items():
                        best_sim_for_hero = -1.0
                        for emb in ref_embedding_list:
                            similarity = self._cosine_similarity_single(window_embedding, emb)
                            if similarity > best_sim_for_hero:
                                best_sim_for_hero = similarity
                        all_sim_scores.append((ref_name, best_sim_for_hero))
                        if best_sim_for_hero > best_sim_for_window:
                            best_sim_for_window = best_sim_for_hero
                            best_ref_name_for_window = ref_name

                    # Логировать топ-5 если confidence низкий (для отладки)
                    if best_sim_for_window < 0.8:
                        sorted_sims = sorted(all_sim_scores, key=lambda x: x[1], reverse=True)
                        top_5 = sorted_sims[:5]
                        logging.info(f"[DEBUG] Окно ({coord['x']}, {coord['y']}), лучшая conf: {best_sim_for_window:.3f} -> {best_ref_name_for_window}. Топ-5: " + ", ".join(f"{h}@{s:.3f}" for h, s in top_5))
                    if best_ref_name_for_window is not None and best_sim_for_window >= CONFIDENCE_THRESHOLD:
                        all_dino_detections_from_roi.append({
                            "hero": best_ref_name_for_window,
                            "confidence": best_sim_for_window,
                            "position": (coord['x'], coord['y']),
                            "size": (HERO_SQUARE_SIZE, HERO_SQUARE_SIZE)
                        })
            processed_windows_count += len(pil_batch)

        dino_processing_end_time = time.time()
        logging.info(f"[AdvRec] Обработано окон: {processed_windows_count}, Детекций выше порога: {len(all_dino_detections_from_roi)}")
        logging.info(f"[AdvRec] Время обработки: {dino_processing_end_time - dino_processing_start_time:.2f} сек")

        # ЭТАП: Применяем NMS для удаления пересекающихся детекций
        logging.info(f"[AdvRec] Применяем NMS (порог IoU={0.4}) для {len(all_dino_detections_from_roi)} детекций")
        nms_detections = non_max_suppression(all_dino_detections_from_roi, iou_threshold=0.4)
        logging.info(f"[AdvRec] После NMS осталось {len(nms_detections)} детекций")

        # Дедупликация по уникальным героям (как в эталоне, но после NMS)
        hero_dict = {}
        for det in nms_detections:
            hero_name = det['hero']
            if hero_name not in hero_dict or det['confidence'] > hero_dict[hero_name]['confidence']:
                hero_dict[hero_name] = det

        unique_detections = sorted(hero_dict.values(), key=lambda x: x['confidence'], reverse=True)
        final_detections = unique_detections[:MAX_HEROES]
        final_detections.sort(key=lambda x: x['position'][1])

        result = [det['hero'] for det in final_detections]

        logging.info(f"\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ (только DINO, как в эталоне) ===")
        logging.info(f"Распознано героев: {len(result)}")
        for i, detection in enumerate(final_detections, 1):
            logging.info(f"  {i}. {self.normalize_hero_name_for_display(detection['hero'])} "
                        f"(уверенность: {detection['confidence']:.3f}, позиция: {detection['position']})")

        script_end_time = time.time()
        logging.info(f"[AdvRec] Общее время выполнения распознавания: {script_end_time - script_start_time:.2f} сек.")
        logging.info(f"[AdvRec] <<<--- recognize_heroes_on_screenshot ЗАВЕРШЕН ---<<<")

        return result
