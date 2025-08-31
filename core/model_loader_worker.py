# File: core/model_loader_worker.py
import logging
import os
from typing import Dict, Any, Optional, Tuple

from PySide6.QtCore import QObject, Signal, Slot
import onnxruntime
from transformers import AutoImageProcessor
import numpy as np

# Импортируем напрямую, чтобы избежать циклической зависимости, если бы AdvancedRecognitionLogic импортировал это
NN_MODELS_DIR_REL_TO_PROJECT_ROOT = "vision_models"
EMBEDDINGS_DIR_REL_TO_PROJECT_ROOT = "resources/embeddings_padded"
ONNX_SUBDIR_IN_NN_MODELS = "dinov3-vitb16-pretrain-lvd1689m"
ONNX_MODEL_FILENAME = "model_q4.onnx"
IMAGE_PROCESSOR_ID = "facebook/dinov2-small"
ONNX_PROVIDERS = ['CPUExecutionProvider']


class ModelLoaderWorker(QObject):
    # Сигнал: success, ort_session, image_processor, dino_embeddings, target_h, target_w
    models_loaded_signal = Signal(bool, object, object, dict, int, int)

    def __init__(self, project_root_path: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.project_root_path = project_root_path
        logging.info(f"[ModelLoaderWorker] Initialized with project_root: {self.project_root_path}")

    def _get_abs_path(self, relative_to_project_root: str) -> str:
        parts = relative_to_project_root.split('/')
        return os.path.join(self.project_root_path, *parts)

    def _ensure_dir_exists(self, dir_path_abs: str) -> bool:
        if not os.path.exists(dir_path_abs) or not os.path.isdir(dir_path_abs):
            logging.error(f"[ModelLoaderWorker] Директория не найдена или не является директорией: {dir_path_abs}")
            return False
        logging.debug(f"[ModelLoaderWorker] Директория подтверждена: {dir_path_abs}")
        return True

    @Slot()
    def run_load(self):
        logging.info("[ModelLoaderWorker] Starting model and embeddings load...")
        ort_session_dino: Optional[onnxruntime.InferenceSession] = None
        input_name_dino: Optional[str] = None
        image_processor_dino: Optional[AutoImageProcessor] = None
        dino_reference_embeddings: Dict[str, np.ndarray] = {}
        target_h_model_dino: int = 224 # Значения по умолчанию
        target_w_model_dino: int = 224

        nn_models_dir_abs = self._get_abs_path(NN_MODELS_DIR_REL_TO_PROJECT_ROOT)
        embeddings_dir_abs = self._get_abs_path(EMBEDDINGS_DIR_REL_TO_PROJECT_ROOT) 
        onnx_model_dir_abs = os.path.join(nn_models_dir_abs, ONNX_SUBDIR_IN_NN_MODELS)

        if not self._ensure_dir_exists(nn_models_dir_abs) or \
           not self._ensure_dir_exists(embeddings_dir_abs) or \
           not self._ensure_dir_exists(onnx_model_dir_abs):
            logging.error("[ModelLoaderWorker] Critical directory missing. Load aborted.")
            self.models_loaded_signal.emit(False, None, None, {}, target_h_model_dino, target_w_model_dino)
            return

        onnx_model_path = os.path.join(onnx_model_dir_abs, ONNX_MODEL_FILENAME)
        if not os.path.exists(onnx_model_path) or not os.path.isfile(onnx_model_path):
            logging.error(f"[ModelLoaderWorker] ONNX model file not found: {onnx_model_path}. Load aborted.")
            self.models_loaded_signal.emit(False, None, None, {}, target_h_model_dino, target_w_model_dino)
            return
        
        try:
            session_options = onnxruntime.SessionOptions()
            ort_session_dino = onnxruntime.InferenceSession(onnx_model_path, sess_options=session_options, providers=ONNX_PROVIDERS)
            input_name_dino = ort_session_dino.get_inputs()[0].name # Сохраняем, хотя в AdvRec он тоже получается
            image_processor_dino = AutoImageProcessor.from_pretrained(IMAGE_PROCESSOR_ID, use_fast=False)
            
            if hasattr(image_processor_dino, 'size') and \
               isinstance(image_processor_dino.size, dict) and \
               'height' in image_processor_dino.size and 'width' in image_processor_dino.size:
                target_h_model_dino = image_processor_dino.size['height']
                target_w_model_dino = image_processor_dino.size['width']
            logging.info(f"[ModelLoaderWorker] DINOv2 ONNX and processor loaded. Target size: {target_w_model_dino}x{target_h_model_dino}")
        except Exception as e:
            logging.error(f"[ModelLoaderWorker] Error loading DINOv2 (ONNX session or processor): {e}", exc_info=True)
            self.models_loaded_signal.emit(False, None, None, {}, target_h_model_dino, target_w_model_dino)
            return

        embedding_files = [f for f in os.listdir(embeddings_dir_abs) if f.lower().endswith(".npy")]
        if not embedding_files:
            logging.error(f"[ModelLoaderWorker] No DINOv2 embeddings (.npy files) found in '{embeddings_dir_abs}'.")
            # Продолжаем, если модели загрузились, но эмбеддинги можно будет загрузить позже или они не критичны для старта

        # Группировка эмбеддингов как в эталоне check_recognition.py
        from collections import defaultdict
        hero_embedding_groups = defaultdict(list)

        for emb_filename in embedding_files:
            base_name = os.path.splitext(emb_filename)[0]
            parts = base_name.split('_')
            hero_name = '_'.join(parts[:-1]) if len(parts) > 1 and parts[-1].isdigit() else base_name
            try:
                embedding = np.load(os.path.join(embeddings_dir_abs, emb_filename))
                hero_embedding_groups[hero_name].append(embedding)
            except Exception as e:
                logging.warning(f"[ModelLoaderWorker] Error loading DINOv2 embedding '{emb_filename}': {e}")

        # Преобразуем в dict с списками
        dino_reference_embeddings = dict(hero_embedding_groups)

        if not dino_reference_embeddings and embedding_files: # Если были файлы, но ничего не загрузилось
            logging.error("[ModelLoaderWorker] Failed to load any DINOv2 embeddings from found files.")
            # Решаем, является ли это критической ошибкой. Если да:
            # self.models_loaded_signal.emit(False, ort_session_dino, image_processor_dino, {}, target_h_model_dino, target_w_model_dino)
            # return

        logging.info(f"[ModelLoaderWorker] Loaded DINOv2 embeddings: {len(dino_reference_embeddings)}")
        
        # Передаем input_name_dino неявно, он будет получен в AdvancedRecognitionLogic из сессии
        self.models_loaded_signal.emit(True, ort_session_dino, image_processor_dino, dino_reference_embeddings, target_h_model_dino, target_w_model_dino)
        logging.info("[ModelLoaderWorker] Model and embeddings load process finished.")
