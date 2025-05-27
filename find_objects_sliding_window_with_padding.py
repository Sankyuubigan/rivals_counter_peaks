# find_objects_dynamic_roi_v5_center_assumption.py
import os
import numpy as np
from PIL import Image, ImageOps
import onnxruntime
from transformers import AutoImageProcessor
import time
import cv2
import logging
from collections import Counter

# --- Конфигурация ---
MODELS_DIR = "models"
EMBEDDINGS_DIR = "embeddings_padded"
IMAGES_DIR = "resources\\templates"
ONNX_MODEL_FILENAME = "onnx/model.onnx"
IMAGE_PROCESSOR_ID = "facebook/dinov2-small"
ONNX_PROVIDERS = ['CPUExecutionProvider'] # Или 'OpenVINOExecutionProvider', 'CUDAExecutionProvider'

SCREENSHOT_PATH = "C:/Users/user/Desktop/test3.png" # УБЕДИТЕСЬ, ЧТО ПУТЬ ВЕРНЫЙ!

# Ожидаемый размер иконки героя на скриншоте (в пикселях)
WINDOW_SIZE_W = 93 
WINDOW_SIZE_H = 93
# Шаг по Y для генерации ROI в найденной колонке
ROI_GENERATION_STRIDE_Y = int(WINDOW_SIZE_H * 0.8) 

# Параметры для fallback DINO (полное сканирование, если AKAZE не найдет колонку)
FALLBACK_DINO_STRIDE_W = int(WINDOW_SIZE_W * 0.9) 
FALLBACK_DINO_STRIDE_H = int(WINDOW_SIZE_H * 0.9)

BATCH_SIZE_SLIDING_WINDOW = 32
# Порог для AKAZE, чтобы считать, что герой найден (для определения центра колонки)
AKAZE_MIN_MATCH_COUNT_CONFIG = 3 # Можно поднять до 5, если нужно больше уверенности от AKAZE
# Минимальное количество героев, которых AKAZE должен найти для определения центра колонки
MIN_HEROES_FOR_COLUMN_DETECTION = 2 
# Джиттер для X-координаты ROI (применяется к вычисленному левому краю)
ROI_X_JITTER_VALUES = [-3, 0, 3] # Используем небольшой джиттер для робастности
# ROI_X_JITTER_VALUES = [0] # Для теста без джиттера (быстрее, но может быть менее точно)


DINOV2_LOGGING_SIMILARITY_THRESHOLD = 0.10
DINOV2_FINAL_DECISION_THRESHOLD = 0.60
TOP_N_OVERALL = 10
PADDING_COLOR_WINDOW = (0,0,0)
AKAZE_DESCRIPTOR_TYPE = cv2.AKAZE_DESCRIPTOR_MLDB
AKAZE_LOWE_RATIO = 0.75
MAX_NOT_PASSED_AKAZE_TO_LOG = 15


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

def ensure_dir_exists(dir_path):
    if not os.path.exists(dir_path):
        logging.error(f"Директория не найдена: {dir_path}")
        return False
    return True

def cosine_similarity_single(vec_a, vec_b):
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0: return 0.0
    return dot_product / (norm_a * norm_b)

def pad_image_to_target_size(image_pil, target_height, target_width, padding_color=(0,0,0)):
    original_width, original_height = image_pil.size
    if original_width == target_width and original_height == target_height:
        return image_pil
    target_aspect = target_width / target_height
    original_aspect = original_width / original_height
    if original_aspect > target_aspect:
        new_width = target_width
        new_height = int(new_width / original_aspect) if original_aspect != 0 else 0
    else:
        new_height = target_height
        new_width = int(new_height * original_aspect) if target_aspect !=0 or original_aspect !=0 else 0
    if new_width <= 0 or new_height <= 0 :
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

def get_cls_embeddings_for_batched_pil(pil_images_batch, ort_session, input_name, image_processor, target_h_model, target_w_model):
    if not pil_images_batch:
        return np.array([])
    padded_batch_for_processor = [
        pad_image_to_target_size(img, target_h_model, target_w_model, PADDING_COLOR_WINDOW)
        for img in pil_images_batch
    ]
    inputs = image_processor(images=padded_batch_for_processor, return_tensors="np")
    onnx_outputs = ort_session.run(None, {input_name: inputs.pixel_values})
    batch_cls_embeddings = onnx_outputs[0][:, 0, :]
    return batch_cls_embeddings

# Функция AKAZE для определения предполагаемого ЦЕНТРА колонки героев
def get_hero_column_center_x_akaze(large_image_cv2, hero_template_images_cv2_dict, min_match_count):
    if large_image_cv2 is None:
        logging.error("[AKAZE CENTER] Входное изображение - None.")
        return None, []
    if not hero_template_images_cv2_dict:
        logging.error("[AKAZE CENTER] Словарь шаблонов пуст.")
        return None, []

    try:
        image_gray = cv2.cvtColor(large_image_cv2, cv2.COLOR_BGR2GRAY)
    except cv2.error as e:
        logging.error(f"[AKAZE CENTER] Ошибка конвертации в серое: {e}")
        return None, []

    akaze = cv2.AKAZE_create(descriptor_type=AKAZE_DESCRIPTOR_TYPE)
    try:
        kp_screenshot, des_screenshot = akaze.detectAndCompute(image_gray, None)
    except cv2.error as e:
        logging.error(f"[AKAZE CENTER] Ошибка detectAndCompute для скриншота: {e}")
        return None, []

    if des_screenshot is None or len(kp_screenshot) == 0:
        logging.warning("[AKAZE CENTER] Не найдено дескрипторов на скриншоте.")
        return None, []

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    all_matched_x_coords_on_screenshot = []
    akaze_candidates_found = [] # Герои, прошедшие порог AKAZE
    hero_match_details = [] # Детали для героев, прошедших порог

    logging.info(f"[AKAZE CENTER] Поиск центра колонки (порог совпадений: {min_match_count}):")

    for hero_name, templates_cv2_list in hero_template_images_cv2_dict.items():
        max_good_matches_for_hero = 0
        best_match_coords_for_hero = []
        if not templates_cv2_list: continue
        for i, template_cv2_single in enumerate(templates_cv2_list):
            if template_cv2_single is None: continue
            try:
                template_gray = cv2.cvtColor(template_cv2_single, cv2.COLOR_BGR2GRAY) if len(template_cv2_single.shape) == 3 else template_cv2_single
                kp_template, des_template = akaze.detectAndCompute(template_gray, None)
            except cv2.error as e:
                logging.warning(f"[AKAZE CENTER] Ошибка detectAndCompute для шаблона {hero_name}_{i}: {e}")
                continue
            if des_template is None or len(kp_template) == 0: continue
            try: matches = bf.knnMatch(des_template, des_screenshot, k=2)
            except cv2.error: continue
            good_matches = []
            current_match_coords = []
            valid_matches = [m_pair for m_pair in matches if m_pair is not None and len(m_pair) == 2]
            for m, n in valid_matches:
                if m.distance < AKAZE_LOWE_RATIO * n.distance:
                    good_matches.append(m)
                    screenshot_pt_idx = m.trainIdx
                    if screenshot_pt_idx < len(kp_screenshot):
                         current_match_coords.append(kp_screenshot[screenshot_pt_idx].pt[0]) # Собираем X-координаты совпавших точек
            if len(good_matches) > max_good_matches_for_hero:
                max_good_matches_for_hero = len(good_matches)
                best_match_coords_for_hero = current_match_coords
        
        if max_good_matches_for_hero >= min_match_count:
            hero_match_details.append({"name": hero_name, "matches": max_good_matches_for_hero, "x_coords": best_match_coords_for_hero})
            akaze_candidates_found.append(hero_name)

    # Логирование героев, прошедших фильтр
    sorted_hero_match_details = sorted(hero_match_details, key=lambda item: item["matches"], reverse=True)
    for detail in sorted_hero_match_details:
         logging.info(f"[AKAZE CENTER]   {detail['name']}: {detail['matches']} совпадений (ПРОШЕЛ ФИЛЬТР)")
         all_matched_x_coords_on_screenshot.extend(detail['x_coords']) # Добавляем X-координаты только от надежно найденных героев
    
    # Логирование героев, не прошедших фильтр
    all_template_heroes = set(hero_template_images_cv2_dict.keys())
    passed_heroes_set = set(d['name'] for d in hero_match_details)
    not_passed_heroes = sorted(list(all_template_heroes - passed_heroes_set))
    logged_not_passed_count = 0
    for hero_name in not_passed_heroes:
        if logged_not_passed_count < MAX_NOT_PASSED_AKAZE_TO_LOG:
            logging.info(f"[AKAZE CENTER]   {hero_name}: <{min_match_count} совпадений (НЕ ПРОШЕЛ)")
            logged_not_passed_count += 1
        elif logged_not_passed_count == MAX_NOT_PASSED_AKAZE_TO_LOG: # Вывести сообщение один раз
            logging.info(f"[AKAZE CENTER]   ... и еще {len(not_passed_heroes) - MAX_NOT_PASSED_AKAZE_TO_LOG} не прошли фильтр (логирование ограничено).")
            logged_not_passed_count += 1 # Чтобы больше не выводить это сообщение
            break 

    if len(akaze_candidates_found) < MIN_HEROES_FOR_COLUMN_DETECTION:
        logging.warning(f"[AKAZE CENTER] Найдено слишком мало героев ({len(akaze_candidates_found)}), чтобы надежно определить центр колонки. Требуется: {MIN_HEROES_FOR_COLUMN_DETECTION}.")
        return None, akaze_candidates_found # Возвращаем None для X-центра и список кандидатов (может быть пустым)

    if not all_matched_x_coords_on_screenshot:
        logging.warning("[AKAZE CENTER] Не найдено X-координат совпадений для определения центра колонки.")
        return None, akaze_candidates_found

    # Определяем наиболее вероятную X-координату центра колонки
    rounded_x_coords = [round(x / 10.0) * 10 for x in all_matched_x_coords_on_screenshot] # Округление для группировки
    if not rounded_x_coords:
        logging.warning("[AKAZE CENTER] Нет округленных X-координат.")
        return None, akaze_candidates_found

    most_common_x_center = Counter(rounded_x_coords).most_common(1)[0][0]
    
    return most_common_x_center, akaze_candidates_found

def main():
    print("--- Запуск скрипта поиска (v_dynamic_roi_v5_center_assumption) ---")
    script_start_time = time.time()

    if not os.path.exists(SCREENSHOT_PATH): logging.error(f"Файл скриншота не найден: {SCREENSHOT_PATH}"); return
    if not ensure_dir_exists(MODELS_DIR) or \
       not ensure_dir_exists(EMBEDDINGS_DIR) or \
       not ensure_dir_exists(IMAGES_DIR):
        return

    onnx_model_path = os.path.join(MODELS_DIR, ONNX_MODEL_FILENAME)
    if not os.path.exists(onnx_model_path): logging.error(f"Файл модели ONNX DINOv2 не найден: {onnx_model_path}"); return

    try:
        logging.info("Загрузка ONNX сессии DINOv2 и процессора...")
        session_options = onnxruntime.SessionOptions()
        ort_session_dino = onnxruntime.InferenceSession(onnx_model_path, sess_options=session_options, providers=ONNX_PROVIDERS)
        input_name_dino = ort_session_dino.get_inputs()[0].name
        image_processor_dino = AutoImageProcessor.from_pretrained(IMAGE_PROCESSOR_ID, use_fast=False)
        target_h_model, target_w_model = 224, 224
        if hasattr(image_processor_dino, 'size') and isinstance(image_processor_dino.size, dict) and \
           'height' in image_processor_dino.size and 'width' in image_processor_dino.size:
            target_h_model = image_processor_dino.size['height']
            target_w_model = image_processor_dino.size['width']
        logging.info(f"DINOv2 ONNX и процессор загружены. Целевой размер для паддинга DINOv2: {target_w_model}x{target_h_model}")
    except Exception as e: logging.error(f"Ошибка при загрузке DINOv2: {e}"); return

    dino_reference_embeddings = {}
    embedding_files = [f for f in os.listdir(EMBEDDINGS_DIR) if f.lower().endswith(".npy")]
    if not embedding_files: logging.error(f"В '{EMBEDDINGS_DIR}' не найдено DINOv2 эмбеддингов."); return
    logging.info(f"Загрузка {len(embedding_files)} DINOv2 эмбеддингов эталонов...")
    for emb_filename in embedding_files:
        name = os.path.splitext(emb_filename)[0]
        try: dino_reference_embeddings[name] = np.load(os.path.join(EMBEDDINGS_DIR, emb_filename))
        except Exception as e: logging.warning(f"  Ошибка при загрузке DINOv2 эмбеддинга '{emb_filename}': {e}")
    if not dino_reference_embeddings: logging.error("Не удалось загрузить ни одного DINOv2 эмбеддинга."); return
    logging.info(f"Загружено DINOv2 эмбеддингов: {len(dino_reference_embeddings)}")

    akaze_template_images_cv2 = {} # Словарь для хранения CV2 изображений шаблонов AKAZE
    logging.info(f"Загрузка шаблонов изображений для AKAZE из '{IMAGES_DIR}'...")
    loaded_akaze_templates_count = 0
    for ref_name in dino_reference_embeddings.keys(): # Загружаем шаблоны для всех героев с эмбеддингами
        found_img_path_for_akaze = None
        for ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'):
            temp_path = os.path.join(IMAGES_DIR, ref_name + ext)
            if os.path.exists(temp_path): found_img_path_for_akaze = temp_path; break
        if found_img_path_for_akaze:
            try:
                img_cv2 = cv2.imread(found_img_path_for_akaze)
                if img_cv2 is not None: 
                    akaze_template_images_cv2[ref_name] = [img_cv2] # Храним как список для единообразия, если будет несколько шаблонов на героя
                    loaded_akaze_templates_count += 1
                else: logging.warning(f"  Ошибка cv2.imread для AKAZE шаблона '{found_img_path_for_akaze}'")
            except Exception as e: logging.warning(f"  Исключение при загрузке AKAZE шаблона '{found_img_path_for_akaze}': {e}")
    if not akaze_template_images_cv2: logging.warning("Не удалось загрузить ни одного шаблона для AKAZE. Определение центра колонки будет невозможно.");
    logging.info(f"Загружено шаблонов для AKAZE: {loaded_akaze_templates_count} (для {len(akaze_template_images_cv2)} героев)")

    try:
        screenshot_pil_original = Image.open(SCREENSHOT_PATH).convert("RGB")
        screenshot_cv2_original = cv2.cvtColor(np.array(screenshot_pil_original), cv2.COLOR_RGB2BGR)
        s_width, s_height = screenshot_pil_original.size
        logging.info(f"Размер оригинального скриншота: {s_width}x{s_height}")
    except Exception as e: logging.error(f"Ошибка при открытии скриншота: {e}"); return

    akaze_loc_start_time = time.time()
    # Используем только те AKAZE шаблоны, для которых есть DINO эмбеддинги (обычно это все)
    akaze_templates_to_use = {name: templates for name, templates in akaze_template_images_cv2.items() if name in dino_reference_embeddings}
    
    column_x_center = None 
    akaze_initial_candidates = [] # Герои, найденные AKAZE на этапе локализации

    if akaze_templates_to_use:
        column_x_center, akaze_initial_candidates = get_hero_column_center_x_akaze(screenshot_cv2_original, akaze_templates_to_use, AKAZE_MIN_MATCH_COUNT_CONFIG)
    else:
        logging.warning("Нет шаблонов AKAZE для использования, локализация центра колонки невозможна.")
        
    akaze_loc_end_time = time.time()
    logging.info(f"Время выполнения AKAZE локализации центра колонки: {akaze_loc_end_time - akaze_loc_start_time:.2f} сек.")
    if column_x_center is not None:
        logging.info(f"AKAZE определил предполагаемый ЦЕНТР колонки X={column_x_center}")
    logging.info(f"AKAZE (для локализации) нашел кандидатов: {akaze_initial_candidates}")


    rois_for_dino = []
    use_fallback_dino = False
    base_roi_start_x_for_log = "N/A" # Для логирования

    if column_x_center is not None:
        base_roi_start_x = column_x_center - (WINDOW_SIZE_W // 2)
        base_roi_start_x_for_log = base_roi_start_x # Сохраняем для лога
        logging.info(f"Генерация ROI для DINOv2. Базовый левый край ROI X={base_roi_start_x} (на основе центра X={column_x_center}). Шаг Y={ROI_GENERATION_STRIDE_Y}")
        
        for y_base in range(0, s_height - WINDOW_SIZE_H + 1, ROI_GENERATION_STRIDE_Y):
            for x_offset in ROI_X_JITTER_VALUES: 
                current_roi_start_x = base_roi_start_x + x_offset
                if current_roi_start_x >= 0 and current_roi_start_x + WINDOW_SIZE_W <= s_width:
                     rois_for_dino.append({'x': current_roi_start_x, 'y': y_base})
        logging.info(f"Сгенерировано {len(rois_for_dino)} динамических ROI на основе центра колонки.")
    else:
        logging.warning("Не удалось определить X-координату центра колонки с помощью AKAZE. Включается fallback на полное сканирование DINOv2.")
        use_fallback_dino = True
        logging.info(f"Fallback DINO: генерация ROI для всего экрана с шагом W={FALLBACK_DINO_STRIDE_W}, H={FALLBACK_DINO_STRIDE_H}")
        for y in range(0, s_height - WINDOW_SIZE_H + 1, FALLBACK_DINO_STRIDE_H):
            for x_val in range(0, s_width - WINDOW_SIZE_W + 1, FALLBACK_DINO_STRIDE_W):
                rois_for_dino.append({'x': x_val, 'y': y})
        logging.info(f"Сгенерировано {len(rois_for_dino)} ROI для fallback DINO.")

    if not rois_for_dino:
        logging.warning("Не было сгенерировано ни одного ROI. Проверьте параметры или логику.")
        script_end_time_early = time.time(); print(f"\nОбщее время выполнения скрипта (нет ROI): {script_end_time_early - script_start_time:.2f} сек."); return

    dino_ref_embeddings_to_check = dino_reference_embeddings
    if use_fallback_dino:
        logging.info(f"\nЗапуск FALLBACK DINOv2 для {len(rois_for_dino)} ROI по всему экрану.")
    else: # Если не fallback, значит column_x_center был найден
        logging.info(f"\nЗапуск DINOv2 для {len(rois_for_dino)} динамических ROI (базовый левый край X={base_roi_start_x_for_log}).")
    
    logging.info(f"Для каждого ROI будут проверены {len(dino_ref_embeddings_to_check)} эталонов DINOv2.")

    all_detections_for_windows = {}
    pil_batch = []
    coordinates_batch = []
    processed_windows_count = 0
    dino_processing_start_time = time.time()

    for roi_coord in rois_for_dino:
        x, y = roi_coord['x'], roi_coord['y']
        # Проверка границ (хотя должна быть уже при генерации)
        if x < 0 or y < 0 or x + WINDOW_SIZE_W > s_width or y + WINDOW_SIZE_H > s_height:
            continue 
        window_pil = screenshot_pil_original.crop((x, y, x + WINDOW_SIZE_W, y + WINDOW_SIZE_H))
        pil_batch.append(window_pil)
        coordinates_batch.append({'x': x, 'y': y})

        if len(pil_batch) >= BATCH_SIZE_SLIDING_WINDOW:
            window_embeddings_batch = get_cls_embeddings_for_batched_pil(
                pil_batch, ort_session_dino, input_name_dino, image_processor_dino,
                target_h_model, target_w_model
            )
            for i in range(len(window_embeddings_batch)):
                window_embedding = window_embeddings_batch[i]
                coord = coordinates_batch[i]
                best_sim_for_window = -1.0
                best_ref_name_for_window = None
                for ref_name, ref_embedding in dino_ref_embeddings_to_check.items():
                    similarity = cosine_similarity_single(window_embedding, ref_embedding)
                    if similarity > best_sim_for_window:
                        best_sim_for_window = similarity
                        best_ref_name_for_window = ref_name
                if best_sim_for_window >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                    window_key = (coord['x'], coord['y'])
                    if window_key not in all_detections_for_windows or \
                       best_sim_for_window > all_detections_for_windows[window_key]['similarity']:
                        all_detections_for_windows[window_key] = {
                            "name": best_ref_name_for_window, "similarity": best_sim_for_window,
                            "x": coord['x'], "y": coord['y'], "w": WINDOW_SIZE_W, "h": WINDOW_SIZE_H
                        }
            processed_windows_count += len(pil_batch)
            pil_batch = []
            coordinates_batch = []

    if pil_batch: # Хвост батча
        window_embeddings_batch = get_cls_embeddings_for_batched_pil(
            pil_batch, ort_session_dino, input_name_dino, image_processor_dino,
            target_h_model, target_w_model
        )
        for i in range(len(window_embeddings_batch)):
            window_embedding = window_embeddings_batch[i]
            coord = coordinates_batch[i]
            best_sim_for_window = -1.0
            best_ref_name_for_window = None
            for ref_name, ref_embedding in dino_ref_embeddings_to_check.items():
                similarity = cosine_similarity_single(window_embedding, ref_embedding)
                if similarity > best_sim_for_window:
                    best_sim_for_window = similarity
                    best_ref_name_for_window = ref_name
            if best_sim_for_window >= DINOV2_LOGGING_SIMILARITY_THRESHOLD:
                window_key = (coord['x'], coord['y'])
                if window_key not in all_detections_for_windows or \
                   best_sim_for_window > all_detections_for_windows[window_key]['similarity']:
                    all_detections_for_windows[window_key] = {
                        "name": best_ref_name_for_window, "similarity": best_sim_for_window,
                        "x": coord['x'], "y": coord['y'], "w": WINDOW_SIZE_W, "h": WINDOW_SIZE_H
                    }
        processed_windows_count += len(pil_batch)

    dino_processing_end_time = time.time()
    logging.info(f"Обработано окон (DINOv2): {processed_windows_count}")
    logging.info(f"Время DINOv2 обработки ROI: {dino_processing_end_time - dino_processing_start_time:.2f} сек.")

    best_match_for_each_unique_ref_name_dino = {}
    for window_data in all_detections_for_windows.values():
        ref_name = window_data["name"]
        if ref_name not in best_match_for_each_unique_ref_name_dino or \
           window_data["similarity"] > best_match_for_each_unique_ref_name_dino[ref_name]["similarity"]:
            best_match_for_each_unique_ref_name_dino[ref_name] = window_data
    sorted_final_results_dino = sorted(best_match_for_each_unique_ref_name_dino.values(), key=lambda x: x["similarity"], reverse=True)

    print(f"\n--- Топ-{TOP_N_OVERALL} найденных уникальных объектов (DINOv2, порог лог.: {DINOV2_LOGGING_SIMILARITY_THRESHOLD*100:.0f}%) ---")
    print(f"--- (Для решения используйте порог DINOv2 около {DINOV2_FINAL_DECISION_THRESHOLD*100:.0f}%) ---")
    if not sorted_final_results_dino:
        print(f"DINOv2 не нашел объектов со сходством выше {DINOV2_LOGGING_SIMILARITY_THRESHOLD*100:.0f}% в ROI.")
    else:
        count_above_final_threshold = 0
        for i, res in enumerate(sorted_final_results_dino[:TOP_N_OVERALL]):
            percentage = res["similarity"] * 100; marker = ""
            if res["similarity"] >= DINOV2_FINAL_DECISION_THRESHOLD:
                marker = " ***"; count_above_final_threshold +=1
            print(f"{i+1}. Объект: '{res['name']}' - DINOv2 Сходство: {percentage:.2f}% (Окно ROI: x={res['x']}, y={res['y']}){marker}")
        print(f"\nНайдено (DINOv2) {count_above_final_threshold} объектов с уверенностью >= {DINOV2_FINAL_DECISION_THRESHOLD*100:.0f}%")
    
    script_end_time = time.time()
    print(f"\nОбщее время выполнения скрипта: {script_end_time - script_start_time:.2f} сек.")
    print("--- Завершение скрипта ---")

if __name__ == "__main__":
    main()