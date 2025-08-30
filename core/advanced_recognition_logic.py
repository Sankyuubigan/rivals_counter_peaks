# File: core/advanced_recognition_logic.py
import os
import numpy as np
from PIL import Image
import onnxruntime
# AutoImageProcessor будет загружен в воркере
import time
import cv2
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple, Optional, Set
from PySide6.QtCore import QObject, Signal, QThread, Slot # <--- ДОБАВЛЕН Slot

from utils import normalize_hero_name as normalize_hero_name_util
from core.image_processing_utils import preprocess_image_for_dino
from core.model_loader_worker import ModelLoaderWorker # Импортируем новый воркер


# Константы остаются те же, но некоторые значения по умолчанию могут быть изменены в _on_models_loaded_from_worker
WINDOW_SIZE_W_DINO = 93
WINDOW_SIZE_H_DINO = 93
ROI_GENERATION_STRIDE_Y_DINO = int(WINDOW_SIZE_H_DINO * 0.8)
FALLBACK_DINO_STRIDE_W = int(WINDOW_SIZE_W_DINO * 0.9)
FALLBACK_DINO_STRIDE_H = int(WINDOW_SIZE_H_DINO * 0.9)
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0,0,0)

AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
AKAZE_MIN_MATCH_COUNT_COLUMN_LOC = 3
MIN_HEROES_FOR_COLUMN_DETECTION = 2
ROI_X_JITTER_VALUES_DINO = [-3, 0, 3]
MAX_NOT_PASSED_AKAZE_TO_LOG = 15

DINOV2_LOGGING_SIMILARITY_THRESHOLD = 0.10
DINOV2_FINAL_DECISION_THRESHOLD = 0.65
DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE = 0.40
TEAM_SIZE = 6
Y_OVERLAP_THRESHOLD_RATIO = 0.5


class AdvancedRecognition(QObject):
    load_started = Signal()
    load_finished = Signal(bool)

    def __init__(self, akaze_hero_template_images_cv2_dict: Dict[str, List[np.ndarray]], project_root_path: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.project_root_path = project_root_path
        self.ort_session_dino: Optional[onnxruntime.InferenceSession] = None
        self.input_name_dino: Optional[str] = None
        self.image_processor_dino: Optional[Any] = None
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

    @Slot(bool, object, object, dict, int, int)
    def _on_models_loaded_from_worker(self, success: bool,
                                     ort_session: Optional[onnxruntime.InferenceSession],
                                     image_processor: Optional[Any],
                                     embeddings_dict: Dict[str, np.ndarray],
                                     target_h: int, target_w: int):
        logging.info(f"[AdvRec] Received models_loaded_signal from worker. Success: {success}")
        self._is_loading = False
        if success and ort_session and image_processor:
            self.ort_session_dino = ort_session
            if self.ort_session_dino: # Добавил проверку для mypy
                 self.input_name_dino = self.ort_session_dino.get_inputs()[0].name
            self.image_processor_dino = image_processor
            self.dino_reference_embeddings = embeddings_dict
            self.target_h_model_dino = target_h
            self.target_w_model_dino = target_w
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
        return self._models_ready and bool(self.ort_session_dino) and \
               bool(self.image_processor_dino)

    def _cosine_similarity_single(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        if vec_a is None or vec_b is None: return 0.0
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0: return 0.0
        return float(dot_product / (norm_a * norm_b))

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
        if not self.is_ready(): return np.array([])
        if not pil_images_batch or not self.image_processor_dino or not self.ort_session_dino or not self.input_name_dino:
            return np.array([])

        padded_batch_for_processor = [
            self._pad_image_to_target_size_pil(img, self.target_h_model_dino, self.target_w_model_dino, PADDING_COLOR_WINDOW_DINO)
            for img in pil_images_batch if img is not None
        ]

        if not padded_batch_for_processor:
            return np.array([])

        inputs = self.image_processor_dino(images=padded_batch_for_processor, return_tensors="np")
        onnx_outputs = self.ort_session_dino.run(None, {self.input_name_dino: inputs.pixel_values})
        batch_cls_embeddings = onnx_outputs[0][:, 0, :]
        return batch_cls_embeddings

    def _get_hero_column_center_x_akaze(self, large_image_cv2: np.ndarray) -> Tuple[Optional[int], List[str]]:
        if large_image_cv2 is None:
            logging.error("[AdvRec][AKAZE CENTER] Входное изображение - None.")
            return None, []
        if not self.akaze_template_images_cv2:
            logging.warning("[AdvRec][AKAZE CENTER] Словарь AKAZE шаблонов пуст. Локализация колонки невозможна.")
            return None, []

        try:
            image_gray = cv2.cvtColor(large_image_cv2, cv2.COLOR_BGR2GRAY)
        except cv2.error as e:
            logging.error(f"[AdvRec][AKAZE CENTER] Ошибка конвертации в серое: {e}")
            return None, []

        akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
        try:
            kp_screenshot, des_screenshot = akaze.detectAndCompute(image_gray, None)
        except cv2.error as e:
            logging.error(f"[AdvRec][AKAZE CENTER] Ошибка detectAndCompute для скриншота: {e}")
            return None, []

        if des_screenshot is None or len(kp_screenshot) == 0:
            logging.warning("[AdvRec][AKAZE CENTER] Не найдено дескрипторов на скриншоте.")
            return None, []

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        all_matched_x_coords_on_screenshot: List[float] = []
        akaze_candidates_found: List[str] = []
        hero_match_details: List[Dict[str, Any]] = []

        logging.info(f"[AdvRec][AKAZE CENTER] Поиск центра колонки (порог совпадений: {AKAZE_MIN_MATCH_COUNT_COLUMN_LOC}):")

        for hero_name, templates_cv2_list in self.akaze_template_images_cv2.items():
            max_good_matches_for_hero = 0
            best_match_coords_for_hero: List[float] = []
            if not templates_cv2_list: continue
            for i, template_cv2_single in enumerate(templates_cv2_list):
                if template_cv2_single is None: continue
                try:
                    template_gray = cv2.cvtColor(template_cv2_single, cv2.COLOR_BGR2GRAY) if len(template_cv2_single.shape) == 3 else template_cv2_single
                    kp_template, des_template = akaze.detectAndCompute(template_gray, None)
                except cv2.error as e:
                    logging.warning(f"[AdvRec][AKAZE CENTER] Ошибка detectAndCompute для шаблона {hero_name}_{i}: {e}")
                    continue
                if des_template is None or len(kp_template) == 0: continue
                try: matches = bf.knnMatch(des_template, des_screenshot, k=2)
                except cv2.error: continue

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
                hero_match_details.append({"name": hero_name, "matches": max_good_matches_for_hero, "x_coords": best_match_coords_for_hero})
                akaze_candidates_found.append(hero_name)

        sorted_hero_match_details = sorted(hero_match_details, key=lambda item: item["matches"], reverse=True)
        for detail in sorted_hero_match_details:
             logging.info(f"[AdvRec][AKAZE CENTER]   {detail['name']}: {detail['matches']} совпадений (ПРОШЕЛ ФИЛЬТР)")
             all_matched_x_coords_on_screenshot.extend(detail['x_coords'])

        all_template_heroes_set = set(self.akaze_template_images_cv2.keys())
        passed_heroes_set = set(d['name'] for d in hero_match_details)
        not_passed_heroes = sorted(list(all_template_heroes_set - passed_heroes_set))
        logged_not_passed_count = 0
        for hero_name in not_passed_heroes:
            if logged_not_passed_count < MAX_NOT_PASSED_AKAZE_TO_LOG:
                logging.info(f"[AdvRec][AKAZE CENTER]   {hero_name}: <{AKAZE_MIN_MATCH_COUNT_COLUMN_LOC} совпадений (НЕ ПРОШЕЛ)")
                logged_not_passed_count += 1
            elif logged_not_passed_count == MAX_NOT_PASSED_AKAZE_TO_LOG:
                logging.info(f"[AdvRec][AKAZE CENTER]   ... и еще {len(not_passed_heroes) - MAX_NOT_PASSED_AKAZE_TO_LOG} не прошли фильтр (логирование ограничено).")
                break

        if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
            logging.warning(f"[AdvRec][AKAZE CENTER] Найдено слишком мало героев ({len(akaze_candidates_found)}), чтобы надежно определить центр колонки. Требуется: {MIN_HEROES_FOR_COLUMN_DETECTION}.")
            return None, akaze_candidates_found

        if not all_matched_x_coords_on_screenshot:
            logging.warning("[AdvRec][AKAZE CENTER] Не найдено X-координат совпадений для определения центра колонки.")
            return None, akaze_candidates_found

        rounded_x_coords = [round(x / 10.0) * 10 for x in all_matched_x_coords_on_screenshot]
        if not rounded_x_coords:
            logging.warning("[AdvRec][AKAZE CENTER] Нет округленных X-координат для определения центра.")
            return None, akaze_candidates_found

        most_common_x_center = Counter(rounded_x_coords).most_common(1)[0][0]
        return int(most_common_x_center), akaze_candidates_found


    def recognize_heroes_on_screenshot(self, screenshot_cv2: np.ndarray) -> List[str]:
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

        akaze_loc_start_time = time.time()
        column_x_center, akaze_identified_canonical_names = self._get_hero_column_center_x_akaze(screenshot_cv2)
        akaze_loc_end_time = time.time()
        logging.info(f"[AdvRec] Время AKAZE локализации: {akaze_loc_end_time - akaze_loc_start_time:.2f} сек. Найдено AKAZE: {akaze_identified_canonical_names}")

        rois_for_dino: List[Dict[str, int]] = []
        if column_x_center is not None:
            base_roi_start_x = column_x_center - (WINDOW_SIZE_W_DINO // 2)
            logging.info(f"[AdvRec] Генерация ROI для DINO. Базовый левый край ROI X={base_roi_start_x} (на основе центра X={column_x_center}). Шаг Y={ROI_GENERATION_STRIDE_Y_DINO}")
            for y_base in range(0, s_height - WINDOW_SIZE_H_DINO + 1, ROI_GENERATION_STRIDE_Y_DINO):
                for x_offset in ROI_X_JITTER_VALUES_DINO:
                    current_roi_start_x = base_roi_start_x + x_offset
                    if 0 <= current_roi_start_x and (current_roi_start_x + WINDOW_SIZE_W_DINO) <= s_width:
                         rois_for_dino.append({'x': current_roi_start_x, 'y': y_base})
        else:
            logging.warning("[AdvRec] Не удалось определить X-координату центра колонки. Включается fallback DINO (полное сканирование).")
            for y in range(0, s_height - WINDOW_SIZE_H_DINO + 1, FALLBACK_DINO_STRIDE_H):
                for x_val in range(0, s_width - WINDOW_SIZE_W_DINO + 1, FALLBACK_DINO_STRIDE_W):
                    rois_for_dino.append({'x': x_val, 'y': y})

        logging.info(f"[AdvRec] Сгенерировано {len(rois_for_dino)} ROI для DINO.")
        if not rois_for_dino:
            logging.warning("[AdvRec] Не сгенерировано ни одного ROI для DINO.")
            return []

        all_dino_detections_from_roi: List[Dict[str, Any]] = []
        pil_batch: List[Image.Image] = []
        coordinates_batch: List[Dict[str, int]] = []
        processed_windows_count = 0
        dino_processing_start_time = time.time()

        for roi_coord in rois_for_dino:
            x, y = roi_coord['x'], roi_coord['y']
            window_pil_original = screenshot_pil_original.crop((x, y, x + WINDOW_SIZE_W_DINO, y + WINDOW_SIZE_H_DINO))

            window_pil_preprocessed = preprocess_image_for_dino(window_pil_original)
            if window_pil_preprocessed is None:
                logging.warning(f"Предобработка для ROI ({x},{y}) вернула None. Пропуск этого ROI.")
                continue

            pil_batch.append(window_pil_preprocessed)
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
                        for ref_name, ref_embedding in self.dino_reference_embeddings.items():
                            similarity = self._cosine_similarity_single(window_embedding, ref_embedding)
                            if similarity > best_sim_for_window:
                                best_sim_for_window = similarity
                                best_ref_name_for_window = ref_name
                        if best_ref_name_for_window is not None and best_sim_for_window >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                            all_dino_detections_from_roi.append({
                                "name": best_ref_name_for_window,
                                "similarity": best_sim_for_window,
                                "x": coord['x'], "y": coord['y']
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
                    for ref_name, ref_embedding in self.dino_reference_embeddings.items():
                        similarity = self._cosine_similarity_single(window_embedding, ref_embedding)
                        if similarity > best_sim_for_window:
                            best_sim_for_window = similarity
                            best_ref_name_for_window = ref_name
                    if best_ref_name_for_window is not None and best_sim_for_window >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                        all_dino_detections_from_roi.append({
                            "name": best_ref_name_for_window,
                            "similarity": best_sim_for_window,
                            "x": coord['x'], "y": coord['y']
                        })
            processed_windows_count += len(pil_batch)

        dino_processing_end_time = time.time()
        logging.info(f"[AdvRec] Обработано окон (DINOv2): {processed_windows_count}, Всего DINO детекций (выше порога логирования {DINOV2_LOGGING_SIMILARITY_THRESHOLD*100:.0f}%): {len(all_dino_detections_from_roi)}")
        logging.info(f"[AdvRec] Время DINOv2 обработки ROI: {dino_processing_end_time - dino_processing_start_time:.2f} сек.")

        all_dino_detections_sorted = sorted(all_dino_detections_from_roi, key=lambda x: x["similarity"], reverse=True)

        logging.info(f"[AdvRec] --- Все кандидаты DINO (прошедшие порог логирования {DINOV2_LOGGING_SIMILARITY_THRESHOLD*100:.0f}%) ---")
        for i, res in enumerate(all_dino_detections_sorted):
            percentage = res["similarity"] * 100
            logging.info(f"[AdvRec]   Raw DINO {i+1}. '{res['name']}' ({normalize_hero_name_util(res['name'])}) - Сходство: {percentage:.2f}% (ROI: x={res['x']}, y={res['y']})")

        final_team_raw_names: List[str] = []
        final_team_normalized_names_set: Set[str] = set()
        occupied_y_slots_by_akaze: List[Tuple[int, int, str]] = []

        akaze_hero_norm_names_unique = sorted(list(set(akaze_identified_canonical_names)))

        for akaze_norm_name in akaze_hero_norm_names_unique:
            if len(final_team_raw_names) >= TEAM_SIZE: break
            if akaze_norm_name in final_team_normalized_names_set: continue

            best_dino_match_for_akaze_hero: Optional[Dict[str, Any]] = None
            highest_similarity = -1.0
            for dino_cand_data in all_dino_detections_sorted:
                if normalize_hero_name_util(dino_cand_data["name"]) == akaze_norm_name:
                    if dino_cand_data["similarity"] > highest_similarity and \
                       dino_cand_data["similarity"] >= DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE:
                        highest_similarity = dino_cand_data["similarity"]
                        best_dino_match_for_akaze_hero = dino_cand_data

            if best_dino_match_for_akaze_hero:
                raw_name_to_add = best_dino_match_for_akaze_hero["name"]
                final_team_raw_names.append(raw_name_to_add)
                final_team_normalized_names_set.add(akaze_norm_name)

                y_start = best_dino_match_for_akaze_hero["y"]
                y_end = y_start + WINDOW_SIZE_H_DINO
                occupied_y_slots_by_akaze.append((y_start, y_end, akaze_norm_name))
                logging.info(f"[AdvRec] Гибрид (AKAZE): Добавлен '{raw_name_to_add}' ({akaze_norm_name}) с DINO sim: {highest_similarity*100:.1f}%. Занятый Y-слот: ({y_start}-{y_end})")
            else:
                logging.warning(f"[AdvRec] Гибрид (AKAZE): AKAZE нашел '{akaze_norm_name}', но DINO не подтвердил его с достаточной уверенностью (>{DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE*100:.0f}%).")

        dino_candidates_for_final_decision = [
            cand for cand in all_dino_detections_sorted
            if cand["similarity"] >= DINOV2_FINAL_DECISION_THRESHOLD
        ]

        logging.info(f"[AdvRec] --- Кандидаты DINOv2 для финального решения (прошедшие порог {DINOV2_FINAL_DECISION_THRESHOLD*100:.0f}%, {len(dino_candidates_for_final_decision)} шт.) ---")

        for dino_cand_data in dino_candidates_for_final_decision:
            if len(final_team_raw_names) >= TEAM_SIZE: break

            dino_raw_name = dino_cand_data["name"]
            dino_norm_name = normalize_hero_name_util(dino_raw_name)

            if dino_norm_name in final_team_normalized_names_set: continue

            dino_roi_y_start = dino_cand_data["y"]
            dino_roi_y_end = dino_roi_y_start + WINDOW_SIZE_H_DINO
            is_overlapping = False

            for occ_y_start, occ_y_end, occ_hero_name in occupied_y_slots_by_akaze:
                overlap_start = max(dino_roi_y_start, occ_y_start)
                overlap_end = min(dino_roi_y_end, occ_y_end)
                overlap_height = overlap_end - overlap_start

                if overlap_height > (WINDOW_SIZE_H_DINO * Y_OVERLAP_THRESHOLD_RATIO):
                    if dino_norm_name == occ_hero_name:
                        logging.debug(f"[AdvRec] Гибрид (DINO): Кандидат '{dino_raw_name}' ({dino_norm_name}) совпадает с уже добавленным AKAZE-героем '{occ_hero_name}'. Пропуск добавления.")
                    else:
                        logging.info(f"[AdvRec] Гибрид (DINO): Кандидат '{dino_raw_name}' ({dino_norm_name}, ROI Y:{dino_roi_y_start}-{dino_roi_y_end}) пересекается с '{occ_hero_name}' от AKAZE (слот Y:{occ_y_start}-{occ_y_end}). Пропуск.")
                    is_overlapping = True
                    break

            if not is_overlapping:
                final_team_raw_names.append(dino_raw_name)
                final_team_normalized_names_set.add(dino_norm_name)
                logging.info(f"[AdvRec] Гибрид (DINO): Добавлен '{dino_raw_name}' ({dino_norm_name}) с DINO sim: {dino_cand_data['similarity']*100:.1f}%.")
                occupied_y_slots_by_akaze.append((dino_roi_y_start, dino_roi_y_end, dino_norm_name))


        logging.info(f"[AdvRec] --- Финальный гибридный результат (сырые имена, {len(final_team_raw_names)} героев) ---")
        for i, name in enumerate(final_team_raw_names):
            logging.info(f"[AdvRec]   {i+1}. {name} ({normalize_hero_name_util(name)})")

        script_end_time = time.time()
        logging.info(f"[AdvRec] Общее время выполнения распознавания: {script_end_time - script_start_time:.2f} сек.")
        logging.info(f"[AdvRec] <<<--- recognize_heroes_on_screenshot ЗАВЕРШЕН ---<<<") # ДОБАВЛЕНО ЛОГИРОВАНИЕ

        return final_team_raw_names
