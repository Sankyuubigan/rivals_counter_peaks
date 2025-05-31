# File: core/advanced_recognition_logic.py
import os
import numpy as np
from PIL import Image
import onnxruntime
from transformers import AutoImageProcessor 
import time
import cv2
import logging
from collections import Counter, defaultdict # Добавил defaultdict
from typing import Dict, List, Any, Tuple, Optional, Set # Добавил Set
from utils import normalize_hero_name as normalize_hero_name_util

# --- Добавляем импорт функции предобработки ---
from core.image_processing_utils import preprocess_image_for_dino
# ---------------------------------------------


# --- Конфигурация ---
NN_MODELS_DIR_REL_TO_PROJECT_ROOT = "nn_models" 
EMBEDDINGS_DIR_REL_TO_PROJECT_ROOT = "resources/embeddings_padded" 
ONNX_SUBDIR_IN_NN_MODELS = "onnx" 
ONNX_MODEL_FILENAME = "model.onnx" 

IMAGE_PROCESSOR_ID = "facebook/dinov2-small"
ONNX_PROVIDERS = ['CPUExecutionProvider']

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


class AdvancedRecognition:
    def __init__(self, akaze_hero_template_images_cv2_dict: Dict[str, List[np.ndarray]], project_root_path: str):
        self.project_root_path = project_root_path 
        self.ort_session_dino: Optional[onnxruntime.InferenceSession] = None
        self.input_name_dino: Optional[str] = None
        self.image_processor_dino: Optional[AutoImageProcessor] = None
        self.target_h_model_dino: int = 224
        self.target_w_model_dino: int = 224
        self.dino_reference_embeddings: Dict[str, np.ndarray] = {}
        
        self.akaze_template_images_cv2: Dict[str, List[np.ndarray]] = akaze_hero_template_images_cv2_dict
        
        self._models_loaded = False
        self._load_models_and_embeddings()

    def _get_abs_path(self, relative_to_project_root: str) -> str:
        parts = relative_to_project_root.split('/')
        return os.path.join(self.project_root_path, *parts)


    def _ensure_dir_exists(self, dir_path_abs: str) -> bool:
        if not os.path.exists(dir_path_abs) or not os.path.isdir(dir_path_abs):
            logging.error(f"[AdvRec] Директория не найдена или не является директорией: {dir_path_abs}")
            return False
        logging.debug(f"[AdvRec] Директория подтверждена: {dir_path_abs}")
        return True

    def _load_models_and_embeddings(self):
        logging.info("[AdvRec] Загрузка моделей и эмбеддингов для расширенного распознавания...")
        
        nn_models_dir_abs = self._get_abs_path(NN_MODELS_DIR_REL_TO_PROJECT_ROOT)
        embeddings_dir_abs = self._get_abs_path(EMBEDDINGS_DIR_REL_TO_PROJECT_ROOT) 
        onnx_model_dir_abs = os.path.join(nn_models_dir_abs, ONNX_SUBDIR_IN_NN_MODELS)

        logging.info(f"[AdvRec] Путь к папке nn_models: {nn_models_dir_abs}")
        logging.info(f"[AdvRec] Путь к папке ONNX (внутри nn_models): {onnx_model_dir_abs}")
        logging.info(f"[AdvRec] Путь к папке эмбеддингов: {embeddings_dir_abs}")

        if not self._ensure_dir_exists(nn_models_dir_abs) or \
           not self._ensure_dir_exists(embeddings_dir_abs) or \
           not self._ensure_dir_exists(onnx_model_dir_abs):
            logging.error("[AdvRec] Не удалось найти одну из ключевых директорий (nn_models, embeddings_padded в resources, или onnx в nn_models).")
            return

        onnx_model_path = os.path.join(onnx_model_dir_abs, ONNX_MODEL_FILENAME)
        if not os.path.exists(onnx_model_path) or not os.path.isfile(onnx_model_path):
            logging.error(f"[AdvRec] Файл модели ONNX DINOv2 не найден: {onnx_model_path}")
            return
        logging.info(f"[AdvRec] Файл модели ONNX найден: {onnx_model_path}")
        
        try:
            session_options = onnxruntime.SessionOptions()
            # session_options.log_severity_level = 3 # 0:Verbose, 1:Info, 2:Warning, 3:Error, 4:Fatal
            self.ort_session_dino = onnxruntime.InferenceSession(onnx_model_path, sess_options=session_options, providers=ONNX_PROVIDERS)
            self.input_name_dino = self.ort_session_dino.get_inputs()[0].name
            self.image_processor_dino = AutoImageProcessor.from_pretrained(IMAGE_PROCESSOR_ID, use_fast=False)
            
            if hasattr(self.image_processor_dino, 'size') and \
               isinstance(self.image_processor_dino.size, dict) and \
               'height' in self.image_processor_dino.size and 'width' in self.image_processor_dino.size:
                self.target_h_model_dino = self.image_processor_dino.size['height']
                self.target_w_model_dino = self.image_processor_dino.size['width']
            logging.info(f"[AdvRec] DINOv2 ONNX и процессор загружены. Целевой размер для паддинга: {self.target_w_model_dino}x{self.target_h_model_dino}")
        except Exception as e:
            logging.error(f"[AdvRec] Ошибка при загрузке DINOv2 (ONNX сессия или процессор): {e}", exc_info=True)
            return

        embedding_files = [f for f in os.listdir(embeddings_dir_abs) if f.lower().endswith(".npy")]
        if not embedding_files:
            logging.error(f"[AdvRec] В '{embeddings_dir_abs}' не найдено DINOv2 эмбеддингов (.npy файлов).")
            return
        
        for emb_filename in embedding_files:
            name = os.path.splitext(emb_filename)[0] 
            try:
                self.dino_reference_embeddings[name] = np.load(os.path.join(embeddings_dir_abs, emb_filename))
            except Exception as e:
                logging.warning(f"[AdvRec] Ошибка при загрузке DINOv2 эмбеддинга '{emb_filename}': {e}")
        
        if not self.dino_reference_embeddings:
            logging.error("[AdvRec] Не удалось загрузить ни одного DINOv2 эмбеддинга из найденных файлов.")
            return

        logging.info(f"[AdvRec] Загружено DINOv2 эмбеддингов: {len(self.dino_reference_embeddings)}")
        self._models_loaded = True
        logging.info("[AdvRec] Модели и эмбеддинги успешно загружены.")

    def is_ready(self) -> bool:
        return self._models_loaded and bool(self.ort_session_dino) and \
               bool(self.image_processor_dino) and bool(self.dino_reference_embeddings)

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
        if not pil_images_batch or not self.image_processor_dino or not self.ort_session_dino or not self.input_name_dino:
            return np.array([])
        
        # Паддинг происходит ПОСЛЕ предобработки (если она есть)
        padded_batch_for_processor = [
            self._pad_image_to_target_size_pil(img, self.target_h_model_dino, self.target_w_model_dino, PADDING_COLOR_WINDOW_DINO)
            for img in pil_images_batch if img is not None # Пропускаем None изображения
        ]

        if not padded_batch_for_processor: # Если все изображения в батче были None
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
                # logged_not_passed_count += 1 # Убрал, чтобы не было бесконечного цикла, если MAX_NOT_PASSED_AKAZE_TO_LOG = 0
                break 

        if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
            logging.warning(f"[AdvRec][AKAZE CENTER] Найдено слишком мало героев ({len(akaze_candidates_found)}), чтобы надежно определить центр колонки. Требуется: {MIN_HEROES_FOR_COLUMN_DETECTION}.")
            return None, akaze_candidates_found

        if not all_matched_x_coords_on_screenshot:
            logging.warning("[AdvRec][AKAZE CENTER] Не найдено X-координат совпадений для определения центра колонки.")
            return None, akaze_candidates_found

        rounded_x_coords = [round(x / 10.0) * 10 for x in all_matched_x_coords_on_screenshot]
        if not rounded_x_coords: # Добавил проверку на пустой список
            logging.warning("[AdvRec][AKAZE CENTER] Нет округленных X-координат для определения центра.")
            return None, akaze_candidates_found

        most_common_x_center = Counter(rounded_x_coords).most_common(1)[0][0]
        return int(most_common_x_center), akaze_candidates_found


    def recognize_heroes_on_screenshot(self, screenshot_cv2: np.ndarray) -> List[str]:
        if not self.is_ready(): 
            logging.error("[AdvRec] Модели не загружены. Распознавание невозможно.")
            return []
        if screenshot_cv2 is None:
            logging.error("[AdvRec] Входной скриншот - None.")
            return []

        script_start_time = time.time()
        
        try: 
            # Убедимся, что скриншот конвертируется в RGB для PIL
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
                    # Проверка выхода за пределы изображения
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
            
            # --- Применяем предобработку к ROI ---
            window_pil_preprocessed = preprocess_image_for_dino(window_pil_original)
            if window_pil_preprocessed is None:
                logging.warning(f"Предобработка для ROI ({x},{y}) вернула None. Пропуск этого ROI.")
                continue # Пропускаем этот ROI, если предобработка не удалась
            # ------------------------------------
            
            pil_batch.append(window_pil_preprocessed) # Добавляем обработанное изображение в батч
            coordinates_batch.append({'x': x, 'y': y})

            if len(pil_batch) >= BATCH_SIZE_SLIDING_WINDOW_DINO:
                window_embeddings_batch = self._get_cls_embeddings_for_batched_pil(pil_batch)
                if window_embeddings_batch.size == 0 and pil_batch: # Проверка, если батч не пуст, а эмбеддинги пусты
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
        
        if pil_batch: # Обработка оставшегося батча
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
        
        # Шаг 1: Добавляем героев, найденных AKAZE и подтвержденных DINO
        for akaze_norm_name in akaze_hero_norm_names_unique:
            if len(final_team_raw_names) >= TEAM_SIZE: break
            if akaze_norm_name in final_team_normalized_names_set: continue

            best_dino_match_for_akaze_hero: Optional[Dict[str, Any]] = None
            highest_similarity = -1.0
            # Ищем в полном списке DINO-кандидатов (all_dino_detections_sorted)
            for dino_cand_data in all_dino_detections_sorted: 
                if normalize_hero_name_util(dino_cand_data["name"]) == akaze_norm_name:
                    # DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE - порог для подтверждения
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

        # Шаг 2: Добавляем оставшихся героев только по DINO
        # Фильтруем кандидатов для Шага 2 по DINOV2_FINAL_DECISION_THRESHOLD
        dino_candidates_for_final_decision = [
            cand for cand in all_dino_detections_sorted 
            if cand["similarity"] >= DINOV2_FINAL_DECISION_THRESHOLD
        ]
        
        logging.info(f"[AdvRec] --- Кандидаты DINOv2 для финального решения (прошедшие порог {DINOV2_FINAL_DECISION_THRESHOLD*100:.0f}%, {len(dino_candidates_for_final_decision)} шт.) ---")

        for dino_cand_data in dino_candidates_for_final_decision: 
            if len(final_team_raw_names) >= TEAM_SIZE: break

            dino_raw_name = dino_cand_data["name"]
            dino_norm_name = normalize_hero_name_util(dino_raw_name)

            if dino_norm_name in final_team_normalized_names_set: continue # Уже добавлен

            dino_roi_y_start = dino_cand_data["y"]
            dino_roi_y_end = dino_roi_y_start + WINDOW_SIZE_H_DINO
            is_overlapping = False

            for occ_y_start, occ_y_end, occ_hero_name in occupied_y_slots_by_akaze:
                overlap_start = max(dino_roi_y_start, occ_y_start)
                overlap_end = min(dino_roi_y_end, occ_y_end)
                overlap_height = overlap_end - overlap_start
                
                if overlap_height > (WINDOW_SIZE_H_DINO * Y_OVERLAP_THRESHOLD_RATIO):
                    if dino_norm_name == occ_hero_name:
                        # Кандидат от DINO совпадает с уже добавленным AKAZE-героем.
                        # Это нормально, просто не добавляем его снова.
                        logging.debug(f"[AdvRec] Гибрид (DINO): Кандидат '{dino_raw_name}' ({dino_norm_name}) совпадает с уже добавленным AKAZE-героем '{occ_hero_name}'. Пропуск добавления.")
                    else:
                        # Пересечение с другим героем, уже добавленным AKAZE
                        logging.info(f"[AdvRec] Гибрид (DINO): Кандидат '{dino_raw_name}' ({dino_norm_name}, ROI Y:{dino_roi_y_start}-{dino_roi_y_end}) пересекается с '{occ_hero_name}' от AKAZE (слот Y:{occ_y_start}-{occ_y_end}). Пропуск.")
                    is_overlapping = True
                    break 
            
            if not is_overlapping:
                final_team_raw_names.append(dino_raw_name)
                final_team_normalized_names_set.add(dino_norm_name)
                logging.info(f"[AdvRec] Гибрид (DINO): Добавлен '{dino_raw_name}' ({dino_norm_name}) с DINO sim: {dino_cand_data['similarity']*100:.1f}%.")
                # Добавляем Y-слот этого DINO-героя, чтобы избежать наложений с другими DINO-героями
                occupied_y_slots_by_akaze.append((dino_roi_y_start, dino_roi_y_end, dino_norm_name))


        logging.info(f"[AdvRec] --- Финальный гибридный результат (сырые имена, {len(final_team_raw_names)} героев) ---")
        for i, name in enumerate(final_team_raw_names):
            logging.info(f"[AdvRec]   {i+1}. {name} ({normalize_hero_name_util(name)})")

        script_end_time = time.time()
        logging.info(f"[AdvRec] Общее время выполнения распознавания: {script_end_time - script_start_time:.2f} сек.")
        
        return final_team_raw_names