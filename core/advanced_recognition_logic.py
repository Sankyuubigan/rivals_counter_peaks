# File: core/advanced_recognition_logic.py
import os
import numpy as np
from PIL import Image
import onnxruntime
from transformers import AutoImageProcessor 
import time
import cv2
import logging
from collections import Counter
from typing import Dict, List, Any, Tuple, Optional

# --- Конфигурация ---
# ИЗМЕНЕНО: Пути к моделям и эмбеддингам
NN_MODELS_DIR_REL_TO_PROJECT_ROOT = "nn_models" # Папка с моделями теперь nn_models
EMBEDDINGS_DIR_REL_TO_PROJECT_ROOT = "resources/embeddings_padded" # Эмбеддинги теперь в resources
ONNX_SUBDIR_IN_NN_MODELS = "onnx" # Подпапка onnx внутри nn_models
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
DINOV2_FINAL_DECISION_THRESHOLD = 0.60 
TEAM_SIZE = 6 


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
        # Убедимся, что используется правильный разделитель для текущей ОС
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
        
        # ИЗМЕНЕНО: Пути к папкам
        nn_models_dir_abs = self._get_abs_path(NN_MODELS_DIR_REL_TO_PROJECT_ROOT)
        embeddings_dir_abs = self._get_abs_path(EMBEDDINGS_DIR_REL_TO_PROJECT_ROOT) # Эмбеддинги теперь напрямую в resources
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
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0: return 0.0
        return float(dot_product / (norm_a * norm_b))

    def _pad_image_to_target_size_pil(self, image_pil: Image.Image, target_height: int, target_width: int, padding_color: Tuple[int,int,int]) -> Image.Image:
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
            return Image.new(image_pil.mode, (target_width, target_height), padding_color)
        
        try:
            resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except ValueError: 
            return Image.new(image_pil.mode, (target_width, target_height), padding_color)

        padded_image = Image.new(image_pil.mode, (target_width, target_height), padding_color)
        paste_x = (target_width - new_width) // 2
        paste_y = (target_height - new_height) // 2
        padded_image.paste(resized_image, (paste_x, paste_y))
        return padded_image

    def _get_cls_embeddings_for_batched_pil(self, pil_images_batch: List[Image.Image]) -> np.ndarray:
        if not pil_images_batch or not self.image_processor_dino or not self.ort_session_dino or not self.input_name_dino:
            return np.array([])
        
        padded_batch_for_processor = [
            self._pad_image_to_target_size_pil(img, self.target_h_model_dino, self.target_w_model_dino, PADDING_COLOR_WINDOW_DINO)
            for img in pil_images_batch
        ]
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
                logged_not_passed_count += 1
                break 

        if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
            logging.warning(f"[AdvRec][AKAZE CENTER] Найдено слишком мало героев ({len(akaze_candidates_found)}), чтобы надежно определить центр колонки. Требуется: {MIN_HEROES_FOR_COLUMN_DETECTION}.")
            return None, akaze_candidates_found

        if not all_matched_x_coords_on_screenshot:
            logging.warning("[AdvRec][AKAZE CENTER] Не найдено X-координат совпадений для определения центра колонки.")
            return None, akaze_candidates_found

        rounded_x_coords = [round(x / 10.0) * 10 for x in all_matched_x_coords_on_screenshot]
        if not rounded_x_coords:
            logging.warning("[AdvRec][AKAZE CENTER] Нет округленных X-координат.")
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
            screenshot_pil_original = Image.fromarray(cv2.cvtColor(screenshot_cv2, cv2.COLOR_BGR2RGB))
            s_width, s_height = screenshot_pil_original.size
        except Exception as e:
            logging.error(f"[AdvRec] Ошибка при конвертации скриншота CV2 в PIL: {e}")
            return []

        akaze_loc_start_time = time.time()
        column_x_center, _ = self._get_hero_column_center_x_akaze(screenshot_cv2)
        akaze_loc_end_time = time.time()
        logging.info(f"[AdvRec] Время выполнения AKAZE локализации: {akaze_loc_end_time - akaze_loc_start_time:.2f} сек.")

        rois_for_dino: List[Dict[str, int]] = []
        use_fallback_dino = False
        base_roi_start_x_for_log: Any = "N/A"

        if column_x_center is not None:
            base_roi_start_x = column_x_center - (WINDOW_SIZE_W_DINO // 2)
            base_roi_start_x_for_log = base_roi_start_x
            logging.info(f"[AdvRec] Генерация ROI для DINO. Базовый левый край ROI X={base_roi_start_x} (на основе центра X={column_x_center}). Шаг Y={ROI_GENERATION_STRIDE_Y_DINO}")
            for y_base in range(0, s_height - WINDOW_SIZE_H_DINO + 1, ROI_GENERATION_STRIDE_Y_DINO):
                for x_offset in ROI_X_JITTER_VALUES_DINO: 
                    current_roi_start_x = base_roi_start_x + x_offset
                    if 0 <= current_roi_start_x and (current_roi_start_x + WINDOW_SIZE_W_DINO) <= s_width:
                         rois_for_dino.append({'x': current_roi_start_x, 'y': y_base})
        else:
            logging.warning("[AdvRec] Не удалось определить X-координату центра колонки. Включается fallback DINO.")
            use_fallback_dino = True
            for y in range(0, s_height - WINDOW_SIZE_H_DINO + 1, FALLBACK_DINO_STRIDE_H):
                for x_val in range(0, s_width - WINDOW_SIZE_W_DINO + 1, FALLBACK_DINO_STRIDE_W):
                    rois_for_dino.append({'x': x_val, 'y': y})
        
        logging.info(f"[AdvRec] Сгенерировано {len(rois_for_dino)} ROI {'для fallback DINO' if use_fallback_dino else '(динамических)'}.")
        if not rois_for_dino:
            logging.warning("[AdvRec] Не было сгенерировано ни одного ROI.")
            return []

        all_detections_for_windows: Dict[Tuple[int, int], Dict[str, Any]] = {}
        pil_batch: List[Image.Image] = []
        coordinates_batch: List[Dict[str, int]] = []
        processed_windows_count = 0
        dino_processing_start_time = time.time()

        for roi_coord in rois_for_dino:
            x, y = roi_coord['x'], roi_coord['y']
            window_pil = screenshot_pil_original.crop((x, y, x + WINDOW_SIZE_W_DINO, y + WINDOW_SIZE_H_DINO))
            pil_batch.append(window_pil)
            coordinates_batch.append({'x': x, 'y': y})

            if len(pil_batch) >= BATCH_SIZE_SLIDING_WINDOW_DINO:
                window_embeddings_batch = self._get_cls_embeddings_for_batched_pil(pil_batch)
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
                    if best_sim_for_window >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                        window_key = (coord['x'], coord['y'])
                        if window_key not in all_detections_for_windows or \
                           best_sim_for_window > all_detections_for_windows[window_key]['similarity']:
                            all_detections_for_windows[window_key] = {
                                "name": best_ref_name_for_window, "similarity": best_sim_for_window,
                                "x": coord['x'], "y": coord['y']
                            }
                processed_windows_count += len(pil_batch)
                pil_batch = []
                coordinates_batch = []
        
        if pil_batch: # Хвост батча
            window_embeddings_batch = self._get_cls_embeddings_for_batched_pil(pil_batch)
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
                if best_sim_for_window >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                    window_key = (coord['x'], coord['y'])
                    if window_key not in all_detections_for_windows or \
                       best_sim_for_window > all_detections_for_windows[window_key]['similarity']:
                        all_detections_for_windows[window_key] = {
                            "name": best_ref_name_for_window, "similarity": best_sim_for_window,
                            "x": coord['x'], "y": coord['y']
                        }
            processed_windows_count += len(pil_batch)

        dino_processing_end_time = time.time()
        logging.info(f"[AdvRec] Обработано окон (DINOv2): {processed_windows_count}")
        logging.info(f"[AdvRec] Время DINOv2 обработки ROI: {dino_processing_end_time - dino_processing_start_time:.2f} сек.")

        best_match_for_each_unique_ref_name_dino: Dict[str, Dict[str, Any]] = {}
        for window_data in all_detections_for_windows.values():
            ref_name = window_data["name"]
            if ref_name is not None: 
                if ref_name not in best_match_for_each_unique_ref_name_dino or \
                   window_data["similarity"] > best_match_for_each_unique_ref_name_dino[ref_name]["similarity"]:
                    best_match_for_each_unique_ref_name_dino[ref_name] = window_data
        
        final_recognized_heroes_data = [
            data for data in best_match_for_each_unique_ref_name_dino.values() 
            if data["similarity"] >= DINOV2_FINAL_DECISION_THRESHOLD
        ]
        
        final_recognized_heroes_data_sorted = sorted(final_recognized_heroes_data, key=lambda x: x["similarity"], reverse=True)
        
        final_hero_names_list = [data["name"] for data in final_recognized_heroes_data_sorted if data.get("name")] 

        logging.info(f"[AdvRec] --- Итоги DINOv2 (порог решения: {DINOV2_FINAL_DECISION_THRESHOLD*100:.0f}%) ---")
        if not final_recognized_heroes_data_sorted:
            logging.info(f"[AdvRec] DINOv2 не нашел объектов с уверенностью выше {DINOV2_FINAL_DECISION_THRESHOLD*100:.0f}%.")
        else:
            for i, res in enumerate(final_recognized_heroes_data_sorted):
                percentage = res["similarity"] * 100
                logging.info(f"[AdvRec]   {i+1}. Объект: '{res['name']}' - Сходство: {percentage:.2f}% (Окно ROI: x={res['x']}, y={res['y']})")
        
        script_end_time = time.time()
        logging.info(f"[AdvRec] Общее время выполнения распознавания: {script_end_time - script_start_time:.2f} сек.")
        
        return final_hero_names_list[:TEAM_SIZE]
