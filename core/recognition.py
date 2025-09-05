# File: core/recognition.py
import logging
import os 
import sys 
import numpy as np 
from PySide6.QtCore import QObject, Signal, Slot, QThread
import cv2
import datetime
from core.utils import RECOGNITION_AREA, capture_screen_area, capture_full_screen
from info.translations import get_text
from core.advanced_recognition_logic import AdvancedRecognition 
from core.app_settings_manager import AppSettingsManager

class RecognitionWorker(QObject):
    finished = Signal(list, object) 
    error = Signal(str)
    def __init__(self, advanced_recognizer: AdvancedRecognition, recognition_area_dict: dict, parent=None):
        super().__init__(parent)
        self.advanced_recognizer = advanced_recognizer
        self.recognition_area_to_capture = recognition_area_dict
        self._is_running = True
        self.current_language = "ru_RU" 
        logging.debug(f"[RecognitionWorker] Initialized with recognition_area: {self.recognition_area_to_capture}")
    @Slot()
    def run(self):
        logging.info("[THREAD][RecognitionWorker] Worker started.")
        if not self._is_running:
            self.error.emit("Recognition cancelled before start.") 
            return
        screenshot = capture_screen_area(self.recognition_area_to_capture)
        if screenshot is None:
            logging.error(f"[THREAD] Failed to capture screen area: {self.recognition_area_to_capture}")
            if self._is_running: self.error.emit(get_text('recognition_no_screenshot', language=self.current_language))
            self.finished.emit([], None)
            return
        logging.info(f"[THREAD] Screenshot captured successfully, shape: {screenshot.shape if screenshot is not None else 'None'}")
        
        if not self._is_running: return
        
        if not self.advanced_recognizer.is_ready():
            error_msg = "Модели для распознавания не загружены."
            logging.error(f"[THREAD] {error_msg}")
            if self._is_running: self.error.emit(error_msg)
            self.finished.emit([], screenshot)
            return
        logging.info("[THREAD] Starting hero recognition...")
        recognized_heroes = self.advanced_recognizer.recognize_heroes_on_screenshot(screenshot)
        logging.info(f"[THREAD] Recognition completed. Found heroes: {recognized_heroes}")
        
        if self._is_running: 
            self.finished.emit(recognized_heroes, screenshot) 
        logging.info(f"[THREAD][RecognitionWorker] Worker finished.")
    def stop(self):
        self._is_running = False

class RecognitionManager(QObject):
    recognition_complete_signal = Signal(list)
    error = Signal(str)
    recognize_heroes_signal = Signal()
    models_ready_signal = Signal(bool)
    recognition_started = Signal() 
    recognition_stopped = Signal()
    def __init__(self, main_window, logic, win_api_manager, app_settings_manager: AppSettingsManager):
        super().__init__()
        self.main_window = main_window
        self.logic = logic
        self.app_settings_manager = app_settings_manager
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        self._models_ready = False
        self.is_recognizing = False
        
        project_root = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.advanced_recognizer = AdvancedRecognition(project_root_path=project_root, parent=self)
        
        self.advanced_recognizer.load_finished.connect(self._on_model_load_finished)
        self.advanced_recognizer.start_async_load_models()
        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        logging.info("[RecognitionManager] Initialized and started loading models")
    @Slot(bool)
    def _on_model_load_finished(self, success: bool):
        self._models_ready = success
        log_msg = "Model loading finished successfully." if success else "Model loading failed."
        logging.info(f"[RecognitionManager] {log_msg}")
        if not success:
            self.error.emit("Ошибка загрузки моделей распознавания.")
        self.models_ready_signal.emit(self._models_ready)
    @Slot(list, object)
    def _on_recognition_complete(self, heroes: list, screenshot_cv2: np.ndarray | None):
        logging.info(f"[RecognitionManager] Recognition completed. Heroes: {heroes}")
        if screenshot_cv2 is not None:
            save_flag = self.app_settings_manager.get_save_screenshot_flag()
            save_path = self.app_settings_manager.get_screenshot_path()
            # ИЗМЕНЕНО: Сохраняем скриншот, если распознано от 1 до 5 героев включительно
            if save_flag and 1 <= len(heroes) <= 5 and save_path and os.path.isdir(save_path):
                try:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"rcp_recognition_{timestamp}_{len(heroes)}_heroes.png"
                    full_path = os.path.join(save_path, filename)
                    
                    # ИЗМЕНЕНО: Сохраняем скриншот всего экрана, а не только области распознавания
                    full_screen_screenshot = capture_full_screen()
                    if full_screen_screenshot is not None:
                        is_success, buffer = cv2.imencode(".png", full_screen_screenshot)
                        if is_success:
                            with open(full_path, "wb") as f: 
                                f.write(buffer)
                            logging.info(f"Full screen screenshot saved to {full_path}")
                    else:
                        # Если не удалось сделать скриншот всего экрана, сохраняем хотя бы область распознавания
                        is_success, buffer = cv2.imencode(".png", screenshot_cv2)
                        if is_success:
                            with open(full_path, "wb") as f: 
                                f.write(buffer)
                            logging.info(f"Area screenshot saved to {full_path} (failed to capture full screen)")
                except Exception as e:
                    logging.error(f"Failed to save screenshot: {e}", exc_info=True)
        self.recognition_complete_signal.emit(heroes)
    @Slot()
    def _handle_recognize_heroes(self):
        logging.info("[RecognitionManager] Recognition requested")
        logging.info(f"[RecognitionManager] Models ready? {self._models_ready}")
        if self.is_recognizing:
            logging.warning("Recognition already in progress.")
            return
        if not self._models_ready:
            logging.error(f"[RecognitionManager] MODELS NOT READY! Advanced recognizer is_ready: {self.advanced_recognizer.is_ready()}")
            logging.error("[RecognitionManager] Models not ready for recognition")
            self.error.emit(get_text('recognition_models_not_ready', language=self.logic.DEFAULT_LANGUAGE))
            return
        self.is_recognizing = True
        logging.info("[RecognitionManager] Starting recognition process")
        self.recognition_started.emit()
        
        self._recognition_worker = RecognitionWorker(self.advanced_recognizer, RECOGNITION_AREA)
        self._recognition_worker.current_language = self.logic.DEFAULT_LANGUAGE
        
        self._recognition_thread = QThread(self.main_window)
        self._recognition_worker.moveToThread(self._recognition_thread)
        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self._on_recognition_complete)
        self._recognition_worker.error.connect(self.error.emit)
        
        self._recognition_thread.finished.connect(self._reset_recognition_state)
        self._recognition_worker.finished.connect(self._recognition_thread.quit)
        
        self._recognition_thread.start()
        logging.info("[RecognitionManager] Recognition thread started")
    @Slot()
    def _reset_recognition_state(self):
        logging.info("[RecognitionManager] Resetting recognition state")
        if self._recognition_worker: self._recognition_worker.deleteLater()
        if self._recognition_thread: self._recognition_thread.deleteLater()
        self._recognition_thread = None
        self._recognition_worker = None
        self.is_recognizing = False
        self.recognition_stopped.emit()
    def stop_recognition(self):
         logging.info("[RecognitionManager] Stopping recognition")
         if self._recognition_worker: self._recognition_worker.stop()
         if self._recognition_thread and self._recognition_thread.isRunning():
             self._recognition_thread.quit()