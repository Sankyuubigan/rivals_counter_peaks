# File: core/advanced_recognition_logic.py
import os
import numpy as np
from PIL import Image
import onnxruntime
import time
import cv2
import logging
from typing import Dict, List, Any, Tuple, Optional
from PySide6.QtCore import QObject, Signal, QThread, Slot
from core.model_loader_worker import ModelLoaderWorker
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    logging.warning("Numba not installed. Calculations will be slower. Install with: pip install numba")
# Увеличиваем размер пакета как в эталонном файле
BATCH_SIZE_SLIDING_WINDOW_DINO = 32
PADDING_COLOR_WINDOW_DINO = (0,0,0)
TEAM_SIZE = 6
IMAGE_MEAN = [0.485, 0.456, 0.406]
IMAGE_STD = [0.229, 0.224, 0.225]
CONFIDENCE_THRESHOLD = 0.70
MAX_HEROES = 6
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
class AdvancedRecognition(QObject):
    load_started = Signal()
    load_finished = Signal(bool)
    
    def __init__(self, project_root_path: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.project_root_path = project_root_path
        self.ort_session_dino: Optional[onnxruntime.InferenceSession] = None
        self.input_name_dino: Optional[str] = None
        self.target_h_model_dino = 224
        self.target_w_model_dino = 224
        self.dino_reference_embeddings: Dict[str, List[np.ndarray]] = {}
        self._models_ready = False
        self._is_loading = False
        self._loader_thread: Optional[QThread] = None
        self._loader_worker: Optional[ModelLoaderWorker] = None
        logging.info("[AdvRec] Initialized.")
        
    def start_async_load_models(self):
        if self._models_ready or self._is_loading: return
        self._is_loading = True
        self.load_started.emit()
        self._loader_worker = ModelLoaderWorker(self.project_root_path)
        self._loader_thread = QThread(self)
        self._loader_worker.moveToThread(self._loader_thread)
        self._loader_worker.models_loaded_signal.connect(self._on_models_loaded_from_worker)
        self._loader_thread.started.connect(self._loader_worker.run_load)
        self._loader_thread.finished.connect(self._loader_thread.deleteLater)
        self._loader_worker.models_loaded_signal.connect(self._handle_worker_cleanup_after_signal)
        self._loader_thread.start()
        
    @Slot(bool, object, dict, int, int)
    def _on_models_loaded_from_worker(self, success: bool, ort_session: Optional[onnxruntime.InferenceSession], embeddings_dict: Dict[str, List[np.ndarray]], target_h: int, target_w: int):
        self._is_loading = False
        if success and ort_session:
            self.ort_session_dino = ort_session
            self.input_name_dino = self.ort_session_dino.get_inputs()[0].name
            self.dino_reference_embeddings = embeddings_dict
            self.target_h_model_dino = target_h
            self.target_w_model_dino = target_w
            self._models_ready = True
            logging.info("Models and embeddings loaded successfully.")
        else:
            self._models_ready = False
            logging.error("Failed to load models or embeddings from worker.")
        self.load_finished.emit(self._models_ready)
        
    @Slot()
    def _handle_worker_cleanup_after_signal(self):
        if self._loader_worker:
            self._loader_worker.deleteLater()
            self._loader_worker = None
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            
    def is_ready(self) -> bool:
        return self._models_ready and bool(self.ort_session_dino)
    
    def _cosine_similarity_single(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0: return 0.0
        return float(dot_product / (norm_a * norm_b))
    
    def normalize_hero_name_for_display(self, hero_name: str) -> str:
        return hero_name.replace('_', ' ').title().replace('And', '&')
    
    def _pad_image_to_target_size_pil(self, image_pil: Image.Image) -> Image.Image:
        w, h = image_pil.size
        target_w, target_h = self.target_w_model_dino, self.target_h_model_dino
        if w == target_w and h == target_h: return image_pil
        
        # Оптимизированная версия как в эталонном файле
        target_aspect = target_w / target_h if target_h != 0 else 1.0
        original_aspect = w / h if h != 0 else 1.0
        
        if original_aspect > target_aspect: 
            new_w = target_w
            new_h = int(new_w / original_aspect)
        else: 
            new_h = target_h
            new_w = int(new_h * original_aspect)
            
        if new_w <= 0 or new_h <= 0:
            return Image.new("RGB", (target_w, target_h), PADDING_COLOR_WINDOW_DINO)
            
        resized = image_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        padded = Image.new("RGB", (target_w, target_h), PADDING_COLOR_WINDOW_DINO)
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        padded.paste(resized, (paste_x, paste_y))
        return padded
    
    def _get_cls_embeddings_for_batched_pil(self, pil_images_batch: List[Image.Image]) -> np.ndarray:
        if not self.ort_session_dino or not self.input_name_dino or not pil_images_batch:
            return np.array([])
        
        # Оптимизированная предобработка как в эталонном файле
        processed_images = []
        for img in pil_images_batch:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            processed_images.append(img)
        
        # Пакетная обработка изображений
        arrays = []
        for img in processed_images:
            padded_img = self._pad_image_to_target_size_pil(img)
            arr = (np.array(padded_img, dtype=np.float32) / 255.0 - np.array(IMAGE_MEAN, dtype=np.float32)) / np.array(IMAGE_STD, dtype=np.float32)
            arrays.append(np.transpose(arr, (2, 0, 1)))
        
        # Оптимизированный запуск модели
        outputs = self.ort_session_dino.run(None, {self.input_name_dino: np.stack(arrays)})
        embeddings = outputs[0][:, 0, :]
        
        # Оптимизированная нормализация с использованием Numba
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
        """Оптимизированный метод поиска лучшего совпадения как в эталонном файле"""
        if query_embedding.size == 0: return None, 0.0
        
        # Векторизованное вычисление сходства как в эталонном файле
        all_sims = []
        for hero_name, ref_embeddings in self.dino_reference_embeddings.items():
            for ref_emb in ref_embeddings:
                sim = np.dot(query_embedding, ref_emb)
                all_sims.append((hero_name, sim))
        
        # Сортируем по убыванию сходства
        all_sims_sorted = sorted(all_sims, key=lambda x: x[1], reverse=True)
        
        # Возвращаем лучшее совпадение
        return all_sims_sorted[0] if all_sims_sorted else (None, 0.0)
    
    def recognize_heroes_on_screenshot(self, screenshot_cv2: np.ndarray) -> List[str]:
        if not self.is_ready() or screenshot_cv2 is None: return []
        
        start_time = time.time()
        screenshot_pil = Image.fromarray(cv2.cvtColor(screenshot_cv2, cv2.COLOR_BGR2RGB))
        s_width, s_height = screenshot_pil.size
        LEFT_OFFSET, HERO_SQUARE_SIZE, STEP_SIZE = 45, 95, 95 // 4
        
        # Оптимизированный метод поиска кандидатов как в эталонном файле
        rois = []
        for y in range(0, s_height - HERO_SQUARE_SIZE + 1, STEP_SIZE):
            rois.append({'x': LEFT_OFFSET, 'y': y, 'width': HERO_SQUARE_SIZE, 'height': HERO_SQUARE_SIZE})
        
        logging.info(f"Найдено {len(rois)} уникальных кандидатов для распознавания")
        
        all_detections = []
        
        # Пакетная обработка всех кандидатов
        for i in range(0, len(rois), BATCH_SIZE_SLIDING_WINDOW_DINO):
            batch_rois = rois[i:i + BATCH_SIZE_SLIDING_WINDOW_DINO]
            pil_batch = [screenshot_pil.crop((r['x'], r['y'], r['x'] + r['width'], r['y'] + r['height'])) for r in batch_rois]
            
            embeddings_batch = self._get_cls_embeddings_for_batched_pil(pil_batch)
            if embeddings_batch.size == 0: continue
            
            # Оптимизированное сопоставление результатов
            for j, window_embedding in enumerate(embeddings_batch):
                best_hero, confidence = self.get_best_match(window_embedding)
                
                if best_hero and confidence >= CONFIDENCE_THRESHOLD:
                    all_detections.append({
                        "hero": best_hero, "confidence": confidence,
                        "position": (batch_rois[j]['x'], batch_rois[j]['y']),
                        "size": (HERO_SQUARE_SIZE, HERO_SQUARE_SIZE)
                    })
        
        logging.info(f"Всего найдено {len(all_detections)} детекций с уверенностью >= {CONFIDENCE_THRESHOLD}")
        
        # Применяем NMS для удаления пересекающихся детекций
        nms_detections = non_max_suppression(all_detections, iou_threshold=0.4)
        logging.info(f"Осталось {len(nms_detections)} детекций после NMS")
        
        # Выбираем лучшего кандидата для каждого уникального героя
        hero_dict = {}
        for det in nms_detections:
            hero_name = det['hero']
            if hero_name not in hero_dict or det['confidence'] > hero_dict[hero_name]['confidence']:
                hero_dict[hero_name] = det
        
        unique_detections = sorted(hero_dict.values(), key=lambda x: x['confidence'], reverse=True)
        final_detections = unique_detections[:MAX_HEROES]
        final_detections.sort(key=lambda x: x['position'][1])
        
        result = [det['hero'] for det in final_detections]
        
        # Выводим в логи порог и топ15 героев
        logging.info(f"\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ (оптимизированный с NMS) ===")
        logging.info(f"ПОРОГ УВЕРЕННОСТИ: {CONFIDENCE_THRESHOLD}")
        logging.info(f"Топ15 героев по баллам обнаружения:")
        
        # Получаем все детекции, отсортированные по уверенности
        all_sorted_detections = sorted(hero_dict.values(), key=lambda x: x['confidence'], reverse=True)
        
        # Выводим топ15 героев
        for i, detection in enumerate(all_sorted_detections[:15], 1):
            status = "ПРОШЕЛ ПОРОГ" if detection['confidence'] >= CONFIDENCE_THRESHOLD else "НЕ ПРОШЕЛ ПОРОГ"
            logging.info(f"  {i}. {self.normalize_hero_name_for_display(detection['hero'])} "
                       f"(уверенность: {detection['confidence']:.3f}) - {status}")
        
        logging.info(f"Распознано героев: {len(result)}")
        for i, detection in enumerate(final_detections, 1):
            logging.info(f"  {i}. {self.normalize_hero_name_for_display(detection['hero'])} "
                       f"(уверенность: {detection['confidence']:.3f}, позиция: {detection['position']})")
        
        logging.info(f"Recognition finished in {time.time() - start_time:.2f}s. Found {len(result)} heroes: {result}")
        return result