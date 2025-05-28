# File: core/recognition.py
import logging
import os 
import sys 
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox

from utils import RECOGNITION_AREA, capture_screen_area
from core.lang.translations import get_text
from core.advanced_recognition_logic import AdvancedRecognition 
from core.images_load import load_hero_templates_cv2 

class RecognitionWorker(QObject):
    """Воркер для распознавания героев в отдельном потоке."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, advanced_recognizer: AdvancedRecognition, recognition_area, parent=None):
        super().__init__(parent)
        self.advanced_recognizer = advanced_recognizer
        self.recognition_area = recognition_area
        self._is_running = True
        self.current_language = "ru_RU" # Язык по умолчанию для воркера
        logging.debug(f"[RecognitionWorker] Initialized.")

    @Slot()
    def run(self):
        """Основная функция воркера."""
        logging.info("[THREAD][RecognitionWorker] Worker started execution.")
        recognized_heroes = []
        if not self._is_running:
            logging.warning("[THREAD][RecognitionWorker] Worker stopped before starting.")
            if hasattr(self, 'error') and self.error is not None : self.error.emit("Recognition cancelled before start.") # Проверка на None
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished early (stopped).")
            return

        screenshot_cv2 = capture_screen_area(self.recognition_area)
        if screenshot_cv2 is None:
            logging.error("[THREAD][RecognitionWorker] Failed to capture screenshot.")
            if self._is_running and hasattr(self, 'error') and self.error is not None : self.error.emit(get_text('recognition_no_screenshot', language=self.current_language))
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (screenshot error).")
            return

        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after screenshot.")
            return
        
        if not self.advanced_recognizer.is_ready():
            error_msg = "Модели для расширенного распознавания не загружены."
            logging.error(f"[THREAD][RecognitionWorker] {error_msg}")
            if self._is_running and hasattr(self, 'error') and self.error is not None : self.error.emit(error_msg)
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (models not ready).")
            return

        recognized_heroes = self.advanced_recognizer.recognize_heroes_on_screenshot(screenshot_cv2)

        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after recognition.")
            return
        if hasattr(self, 'finished') and self.finished is not None: self.finished.emit(recognized_heroes)
        logging.info(f"[THREAD][RecognitionWorker] Worker finished signal emitted with: {recognized_heroes}")
        logging.info(f"[THREAD][RecognitionWorker] Worker run method finished.")

    def stop(self):
        logging.info("[THREAD][RecognitionWorker] Stop requested.")
        self._is_running = False


class RecognitionManager(QObject):
    """Управляет процессом распознавания."""
    recognition_complete_signal = Signal(list)
    error = Signal(str)
    recognize_heroes_signal = Signal()

    def __init__(self, main_window, logic, win_api_manager):
        super().__init__()
        logging.info("[RecognitionManager] Initializing...")
        self.main_window = main_window
        self.logic_for_lang = logic 
        self.win_api_manager = win_api_manager
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            project_root_for_adv_rec = sys._MEIPASS
            logging.info(f"[RecognitionManager] Приложение 'заморожено', project_root_for_adv_rec установлен в sys._MEIPASS: {project_root_for_adv_rec}")
        else:
            # __file__ это core/recognition.py -> dirname это core/
            # '..' -> корень проекта, где лежат core, database, nn_models, resources
            project_root_for_adv_rec = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # <--- ИЗМЕНЕНО: один '..'
            logging.info(f"[RecognitionManager] Приложение не 'заморожено', project_root_for_adv_rec установлен в: {project_root_for_adv_rec}")

        akaze_cv2_templates = load_hero_templates_cv2() 
        if not akaze_cv2_templates:
            logging.warning("[RecognitionManager] Не удалось загрузить CV2 шаблоны для AKAZE.")

        self.advanced_recognizer = AdvancedRecognition(
            akaze_hero_template_images_cv2_dict=akaze_cv2_templates,
            project_root_path=project_root_for_adv_rec
        )
        
        if not self.advanced_recognizer.is_ready():
            logging.warning("[RecognitionManager] Advanced recognizer models not immediately ready.")

        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        logging.info("[RecognitionManager] Initialized.")

    @Slot()
    def _handle_recognize_heroes(self):
        logging.info("[ACTION][RecognitionManager] Recognition requested...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            logging.warning("[WARN][RecognitionManager] Recognition process already running.")
            return

        if not self.advanced_recognizer.is_ready():
            error_msg = get_text('recognition_error_prefix', language=self.logic_for_lang.DEFAULT_LANGUAGE) + " " + \
                        get_text('recognition_no_templates', language=self.logic_for_lang.DEFAULT_LANGUAGE) # Более общая ошибка
            logging.error(f"[ERROR][RecognitionManager] {error_msg}")
            if hasattr(self, 'error') and self.error is not None: self.error.emit(error_msg)
            return

        self._recognition_worker = RecognitionWorker(self.advanced_recognizer, RECOGNITION_AREA)
        if self._recognition_worker : # Проверка что worker создан
             self._recognition_worker.current_language = self.logic_for_lang.DEFAULT_LANGUAGE # Передаем язык
        
        self._recognition_thread = QThread(self.main_window)
        if self._recognition_worker and self._recognition_thread: # Доп. проверки
            self._recognition_worker.moveToThread(self._recognition_thread)
            self._recognition_thread.started.connect(self._recognition_worker.run)
            if hasattr(self._recognition_worker, 'finished') and self._recognition_worker.finished is not None:
                 self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)
            if hasattr(self._recognition_worker, 'error') and self._recognition_worker.error is not None:
                 self._recognition_worker.error.connect(self.error.emit)
            
            self._recognition_thread.finished.connect(self._reset_recognition_state)
            if hasattr(self._recognition_worker, 'finished') and self._recognition_worker.finished is not None:
                self._recognition_worker.finished.connect(self._recognition_thread.quit) 
                self._recognition_worker.finished.connect(self._recognition_worker.deleteLater) 
            self._recognition_thread.finished.connect(self._recognition_thread.deleteLater) 

            self._recognition_thread.start()
            logging.info("[INFO][RecognitionManager] Recognition thread started.")
        else:
            logging.error("[ERROR][RecognitionManager] Не удалось создать воркер или поток для распознавания.")


    @Slot()
    def _reset_recognition_state(self):
        logging.info("[INFO][RecognitionManager] Resetting recognition thread state.")
        self._recognition_thread = None
        self._recognition_worker = None
        logging.info("[INFO][RecognitionManager] Recognition thread state reset complete.")

    def stop_recognition(self):
         logging.info("[INFO][RecognitionManager] Stop recognition requested.")
         if self._recognition_worker:
             self._recognition_worker.stop()