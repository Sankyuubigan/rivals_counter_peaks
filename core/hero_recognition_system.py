import os
import sys
import logging
import numpy as np
from PIL import Image
import onnxruntime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from core.utils import RECOGNITION_AREA

# Константы для распознавания
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "vision_models", "dinov3-vitb16-pretrain-lvd1689m", "model_q4.onnx")
EMBEDDINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "embeddings_padded")
TARGET_SIZE = 224
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]
CONFIDENCE_THRESHOLD = 0.70
MAX_HEROES = 6
LEFT_OFFSET = 45
HERO_SQUARE_SIZE = 95
STEP_SIZE = HERO_SQUARE_SIZE // 4

# Проверка доступности Numba
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    logging.warning("Numba not installed. Calculations will be slower. Install with: pip install numba")

def box_area(box):
    return (box[2] - box[0]) * (box[3] - box[1])

def box_iou_batch(boxes_a_np: np.ndarray, boxes_b_np: np.ndarray) -> np.ndarray:
    area_a = box_area(boxes_a_np.T)
    area_b = box_area(boxes_b_np.T)
    top_left = np.maximum(boxes_a_np[:, None, :2], boxes_b_np[:, :2])
    bottom_right = np.minimum(boxes_a_np[:, None, 2:], boxes_b_np[:, 2:])
    area_inter = np.prod(np.clip(bottom_right - top_left, a_min=0, a_max=None), axis=2)
    return area_inter / (area_a[:, None] + area_b - area_inter)

def non_max_suppression(detections: List[Dict], iou_threshold: float = 0.4) -> List[Dict]:
    if not detections: return []
    detections_sorted = sorted(detections, key=lambda x: x['confidence'], reverse=True)
    
    boxes = []
    for d in detections_sorted:
        x, y = d['position']
        w, h = d['size']
        boxes.append([x, y, x + w, y + h])
    
    boxes_np = np.array(boxes, dtype=np.float32)
    
    if boxes_np.ndim != 2 or boxes_np.shape[1] != 4:
        logging.error(f"Invalid boxes shape: {boxes_np.shape}")
        return detections_sorted
    
    ious = box_iou_batch(boxes_np, boxes_np)
    np.fill_diagonal(ious, 0)
    keep = []
    suppressed = np.zeros(len(boxes), dtype=bool)
    for i in range(len(boxes)):
        if suppressed[i]: continue
        keep.append(i)
        suppress_indices = np.where(ious[i] > iou_threshold)
        suppressed[suppress_indices] = True
    return [detections_sorted[i] for i in keep]

if NUMBA_AVAILABLE:
    @jit(nopython=True)
    def get_embeddings_for_batch_jit(arrays_data, embeddings_shape):
        batch_size, emb_size = embeddings_shape
        embeddings = np.zeros((batch_size, emb_size), dtype=np.float32)
        for i in range(batch_size):
            start_idx = i * emb_size
            end_idx = start_idx + emb_size
            embedding = arrays_data[start_idx:end_idx]
            norm = np.sqrt(np.sum(embedding * embedding))
            if norm > 1e-6:
                embeddings[i, :] = embedding / norm
        return embeddings

class HeroRecognitionSystem:
    def __init__(self):
        self.ort_session: Optional[onnxruntime.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.hero_embeddings: Dict[str, List[np.ndarray]] = {}
        self.hero_stats = {}
        logging.info("Инициализация системы распознавания героев...")
        
    def load_model(self) -> bool:
        try:
            # Для ускорения на GPU NVIDIA замените на ['CUDAExecutionProvider', 'CPUExecutionProvider']
            # Для этого нужно установить onnxruntime-gpu
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
                self.hero_stats[hero_name] = {'dino_confirmed': 0, 'avg_similarity': 0.0}
            
            logging.info(f"Загружено эмбеддингов для {len(self.hero_embeddings)} героев")
            return bool(self.hero_embeddings)
        except Exception as e:
            logging.error(f"Ошибка загрузки эмбеддингов: {e}")
            return False
            
    def is_ready(self) -> bool:
        return all((self.ort_session, self.input_name, self.hero_embeddings))
        
    def crop_image_to_recognition_area(self, image_pil: Image.Image) -> Image.Image:
        w, h = image_pil.size
        area = RECOGNITION_AREA
        l, t, r, b = int(w * area['left_pct']/100), int(h * area['top_pct']/100), int(w * (area['left_pct']+area['width_pct'])/100), int(h * (area['top_pct']+area['height_pct'])/100)
        return image_pil.crop((l, t, r, b))
        
    def pad_image_to_target_size(self, image_pil, target_height, target_width, padding_color=(0,0,0)):
        if image_pil is None: 
            return Image.new("RGB", (target_width, target_height), padding_color) 
        
        original_width, original_height = image_pil.size
        if original_width == target_width and original_height == target_height:
            return image_pil
        
        target_aspect = target_width / target_height if target_height != 0 else 1.0
        original_aspect = original_width / original_height if original_height != 0 else 1.0
        
        if original_aspect > target_aspect: 
            new_width = target_width
            new_height = int(new_width / original_aspect)
        else: 
            new_height = target_height
            new_width = int(new_height * original_aspect)
            
        if new_width <= 0 or new_height <= 0:
            return Image.new("RGB", (target_width, target_height), padding_color)
            
        resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        padded_image = Image.new("RGB", (target_width, target_height), padding_color)
        paste_x = (target_width - new_width) // 2
        paste_y = (target_height - new_height) // 2
        padded_image.paste(resized_image, (paste_x, paste_y))
        
        return padded_image
        
    def preprocess_image_for_dino(self, image_pil: Image.Image) -> Optional[Image.Image]:
        if image_pil.mode != 'RGB': image_pil = image_pil.convert('RGB')
        return image_pil
        
    def get_cls_embeddings_for_batched_pil(self, pil_images_batch: List[Image.Image]) -> np.ndarray:
        if not self.is_ready() or not pil_images_batch: return np.array([])
        
        processed = [self.preprocess_image_for_dino(self.pad_image_to_target_size(img, TARGET_SIZE, TARGET_SIZE)) for img in pil_images_batch]
        
        valid_imgs = [img for img in processed if img is not None]
        if not valid_imgs: return np.array([])
        
        arrays = []
        for img in valid_imgs:
            arr = (np.array(img, dtype=np.float32)/255.0 - np.array(IMAGE_MEAN, dtype=np.float32)) / np.array(IMAGE_STD, dtype=np.float32)
            arrays.append(np.transpose(arr, (2, 0, 1)))
        
        outputs = self.ort_session.run(None, {self.input_name: np.stack(arrays, axis=0)})
        embeddings = outputs[0][:, 0, :]
        
        # Используем Numba для ускорения нормализации
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
        
    def get_best_match(self, query_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        if query_embedding.size == 0: return None, 0.0
        all_sims = sorted([(h, np.dot(query_embedding, emb)) for h, el in self.hero_embeddings.items() for emb in el], key=lambda x: x[1], reverse=True)
        return all_sims[0] if all_sims else (None, 0.0)
        
    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        return hero_name.replace('_', ' ').title().replace('And', '&')
        
    def method_fast_projection(self, image_pil: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Улучшенный метод поиска кандидатов - как в Rust коде"""
        height = image_pil.height
        
        # Создаем кандидатов с фиксированным шагом, как в Rust
        candidate_squares = []
        for y in range(0, height - HERO_SQUARE_SIZE + 1, STEP_SIZE):
            candidate_squares.append((LEFT_OFFSET, y, HERO_SQUARE_SIZE, HERO_SQUARE_SIZE))
        
        return candidate_squares
        
    def recognize_heroes_optimized(self, roi_image: Image.Image, debug_id: Optional[str] = None) -> List[str]:
        """Оптимизированное распознавание героев с использованием NMS
        
        Args:
            roi_image: PIL.Image изображение области распознавания (уже обрезанное)
            debug_id: Опциональный идентификатор для отладочных сообщений
            
        Returns:
            Список распознанных героев
        """
        logging.info(f"Размер области распознавания: {roi_image.width}x{roi_image.height}")
        
        # Этап 1: Находим всех кандидатов с улучшенным методом
        candidate_squares = self.method_fast_projection(roi_image)
        logging.info(f"Найдено {len(candidate_squares)} уникальных кандидатов для распознавания")
        
        if not candidate_squares:
            return []
            
        # Этап 2: Пакетная обработка всех кандидатов
        rois_batch = [roi_image.crop((x, y, x + w, y + h)) for (x, y, w, h) in candidate_squares]
        all_embeddings = self.get_cls_embeddings_for_batched_pil(rois_batch)
        
        if all_embeddings.size == 0:
            return []
            
        # Этап 3: Сопоставление результатов
        all_detections = []
        for i, embedding in enumerate(all_embeddings):
            best_hero, confidence = self.get_best_match(embedding)
            
            if best_hero and confidence >= CONFIDENCE_THRESHOLD:
                x, y, w, h = candidate_squares[i]
                all_detections.append({
                    'hero': best_hero,
                    'confidence': confidence,
                    'position': (x, y),
                    'size': (w, h)
                })
        
        logging.info(f"Всего найдено {len(all_detections)} детекций с уверенностью >= {CONFIDENCE_THRESHOLD}")
        
        # Этап 4: Применяем NMS для удаления пересекающихся детекций
        nms_detections = non_max_suppression(all_detections, iou_threshold=0.4)
        logging.info(f"Осталось {len(nms_detections)} детекций после NMS")
        
        # Этап 5: Выбираем лучшего кандидата для каждого уникального героя
        hero_dict = {}
        for det in nms_detections:
            hero_name = det['hero']
            if hero_name not in hero_dict or det['confidence'] > hero_dict[hero_name]['confidence']:
                hero_dict[hero_name] = det
        
        unique_detections = sorted(hero_dict.values(), key=lambda x: x['confidence'], reverse=True)
        final_detections = unique_detections[:MAX_HEROES]
        final_detections.sort(key=lambda x: x['position'][1])
        
        result = [det['hero'] for det in final_detections]
        
        logging.info(f"\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ (оптимизированный с NMS) ===")
        if debug_id:
            logging.info(f"ID изображения: {debug_id}")
        logging.info(f"Распознано героев: {len(result)}")
        for i, detection in enumerate(final_detections, 1):
            logging.info(f"  {i}. {self.normalize_hero_name_for_display(detection['hero'])} "
                       f"(уверенность: {detection['confidence']:.3f}, позиция: {detection['position']})")
        
        return result