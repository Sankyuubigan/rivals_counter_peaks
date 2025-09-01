# File: core/recognition.py
import logging
import os 
import sys 
import numpy as np 
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox

from utils import RECOGNITION_AREA, capture_screen_area 
from info.translations import get_text
from core.advanced_recognition_logic import AdvancedRecognition 
from core.images_load import load_hero_templates_cv2 

class RecognitionWorker(QObject):
    finished = Signal(list) 
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
        logging.info("[THREAD][RecognitionWorker] Worker started execution.")
        recognized_heroes_original_names = []
        if not self._is_running:
            logging.warning("[THREAD][RecognitionWorker] Worker stopped before starting.")
            if hasattr(self, 'error') and self.error is not None : self.error.emit("Recognition cancelled before start.") 
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished early (stopped).")
            return

        screenshot_to_recognize_cv2 = capture_screen_area(self.recognition_area_to_capture)

        if screenshot_to_recognize_cv2 is None:
            logging.error(f"[THREAD][RecognitionWorker] Failed to capture RECOGNITION_AREA: {self.recognition_area_to_capture}")
            if self._is_running and hasattr(self, 'error') and self.error is not None : self.error.emit(get_text('recognition_no_screenshot', language=self.current_language))
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (RECOGNITION_AREA screenshot error).")
            return
        
        logging.info(f"[THREAD][RecognitionWorker] RECOGNITION_AREA captured, shape: {screenshot_to_recognize_cv2.shape}")

        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after screenshot processing.")
            return
        
        # Проверка готовности AdvancedRecognition ПЕРЕД вызовом
        if not self.advanced_recognizer.is_ready():
            error_msg = "Модели для расширенного распознавания не загружены или не готовы."
            logging.error(f"[THREAD][RecognitionWorker] {error_msg}")
            if self._is_running and hasattr(self, 'error') and self.error is not None : self.error.emit(error_msg)
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (models not ready).")
            return

        recognized_heroes_original_names = self.advanced_recognizer.recognize_heroes_on_screenshot(screenshot_to_recognize_cv2)
        
        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after recognition.")
            return
        
        if hasattr(self, 'finished') and self.finished is not None: 
            self.finished.emit(recognized_heroes_original_names) 
        logging.info(f"[THREAD][RecognitionWorker] Worker finished signal emitted with original names: {recognized_heroes_original_names}")
        logging.info(f"[THREAD][RecognitionWorker] Worker run method finished.")

    def stop(self):
        logging.info("[THREAD][RecognitionWorker] Stop requested.")
        self._is_running = False


class RecognitionManager(QObject):
    recognition_complete_signal = Signal(list) 
    error = Signal(str)
    recognize_heroes_signal = Signal()
    models_ready_signal = Signal(bool) # Новый сигнал о готовности моделей

    def __init__(self, main_window, logic, win_api_manager):
        super().__init__()
        logging.info("[RecognitionManager] Initializing...")
        self.main_window = main_window
        self.logic_for_lang = logic 
        self.win_api_manager = win_api_manager
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        self._models_are_actually_ready = False # Новый флаг состояния
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            project_root_for_adv_rec = sys._MEIPASS
            logging.info(f"[RecognitionManager] Приложение 'заморожено', project_root_for_adv_rec установлен в sys._MEIPASS: {project_root_for_adv_rec}")
        else:
            project_root_for_adv_rec = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
            logging.info(f"[RecognitionManager] Приложение не 'заморожено', project_root_for_adv_rec установлен в: {project_root_for_adv_rec}")

        akaze_cv2_templates = load_hero_templates_cv2() 
        if not akaze_cv2_templates:
            logging.warning("[RecognitionManager] Не удалось загрузить CV2 шаблоны для AKAZE.")

        self.advanced_recognizer = AdvancedRecognition(
            akaze_hero_template_images_cv2_dict=akaze_cv2_templates,
            project_root_path=project_root_for_adv_rec,
            parent=self # Устанавливаем родителя для AdvancedRecognition
        )
        
        # Подписываемся на сигналы загрузки моделей
        self.advanced_recognizer.load_started.connect(self._on_model_load_started)
        self.advanced_recognizer.load_finished.connect(self._on_model_load_finished)
        
        # Запускаем асинхронную загрузку моделей
        self.advanced_recognizer.start_async_load_models()

        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        logging.info("[RecognitionManager] Initialized and model loading started asynchronously.")

    @Slot()
    def _on_model_load_started(self):
        logging.info("[RecognitionManager] Model loading has started...")
        # Здесь можно, например, деактивировать кнопку распознавания в UI

    @Slot(bool)
    def _on_model_load_finished(self, success: bool):
        if success:
            self._models_are_actually_ready = True
            logging.info("[RecognitionManager] Model loading finished successfully.")
            # Активировать кнопку распознавания
        else:
            self._models_are_actually_ready = False
            logging.error("[RecognitionManager] Model loading failed.")
            # Показать ошибку пользователю, оставить кнопку неактивной
            self.error.emit("Ошибка загрузки моделей распознавания. Функция будет недоступна.")
        self.models_ready_signal.emit(self._models_are_actually_ready)


    @Slot()
    def _handle_recognize_heroes(self):
        logging.info("[ACTION][RecognitionManager] Recognition requested...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            logging.warning("[WARN][RecognitionManager] Recognition process already running.")
            return

        if not self._models_are_actually_ready: # Используем новый флаг
            error_msg_key = 'recognition_models_not_ready' # Нужен новый ключ для перевода
            error_msg = get_text(error_msg_key, default_text="Модели распознавания еще не загружены. Пожалуйста, подождите.", language=self.logic_for_lang.DEFAULT_LANGUAGE)
            logging.error(f"[ERROR][RecognitionManager] {error_msg}")
            if hasattr(self, 'error') and self.error is not None: self.error.emit(error_msg)
            return
        
        self._recognition_worker = RecognitionWorker(self.advanced_recognizer, RECOGNITION_AREA)
        if self._recognition_worker : 
             self._recognition_worker.current_language = self.logic_for_lang.DEFAULT_LANGUAGE 
        
        self._recognition_thread = QThread(self.main_window) # Родитель потока - MainWindow
        if self._recognition_worker and self._recognition_thread: 
            self._recognition_worker.moveToThread(self._recognition_thread)
            self._recognition_thread.started.connect(self._recognition_worker.run)
            if hasattr(self._recognition_worker, 'finished') and self._recognition_worker.finished is not None:
                 self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)
            if hasattr(self._recognition_worker, 'error') and self._recognition_worker.error is not None:
                 self._recognition_worker.error.connect(self.error.emit)
            
            # Связываем finished потока с его удалением и сбросом состояния
            self._recognition_thread.finished.connect(self._reset_recognition_state) # Сначала сброс
            self._recognition_thread.finished.connect(self._recognition_thread.deleteLater) # Затем удаление потока
            
            # Удаление воркера после того, как он завершит работу и его сигналы будут обработаны
            if hasattr(self._recognition_worker, 'finished') and self._recognition_worker.finished is not None:
                self._recognition_worker.finished.connect(self._recognition_thread.quit) # Сначала выходим из цикла событий потока
                self._recognition_worker.finished.connect(self._recognition_worker.deleteLater) # Затем удаляем воркер
            

            self._recognition_thread.start()
            logging.info("[INFO][RecognitionManager] Recognition thread started.")
        else:
            logging.error("[ERROR][RecognitionManager] Не удалось создать воркер или поток для распознавания.")


    @Slot()
    def _reset_recognition_state(self):
        # Этот слот теперь вызывается по self._recognition_thread.finished
        logging.info("[INFO][RecognitionManager] Resetting recognition thread state (called by thread.finished).")
        # Worker и Thread должны удаляться через deleteLater, так что здесь просто None
        self._recognition_thread = None
        self._recognition_worker = None
        logging.info("[INFO][RecognitionManager] Recognition thread state reset complete.")

    def stop_recognition(self):
         logging.info("[INFO][RecognitionManager] Stop recognition requested.")
         if self._recognition_worker:
             self._recognition_worker.stop() # Говорим воркеру остановиться
         if self._recognition_thread and self._recognition_thread.isRunning():
             logging.info("[INFO][RecognitionManager] Quitting recognition thread...")
             self._recognition_thread.quit()
             if not self._recognition_thread.wait(1000): # Ждем до 1 секунды
                 logging.warning("[WARN][RecognitionManager] Recognition thread did not finish in time.")
                 # Можно принудительно терминировать, но это менее безопасно
                 # self._recognition_thread.terminate()
         else:
             # Если поток не запущен, но воркер мог быть создан, сбрасываем
             self._reset_recognition_state()
