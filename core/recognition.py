# File: core/recognition.py
import logging
import os 
import sys 
import numpy as np 
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox
import cv2
import datetime

from utils import RECOGNITION_AREA, capture_screen_area 
from info.translations import get_text
from core.advanced_recognition_logic import AdvancedRecognition 
from core.images_load import load_hero_templates_cv2 
from core.app_settings_manager import AppSettingsManager

class RecognitionWorker(QObject):
    # Сигнал теперь передает и сам скриншот (или None)
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
        logging.info("[THREAD][RecognitionWorker] Worker started execution.")
        recognized_heroes_original_names = []
        screenshot_to_recognize_cv2 = None # Инициализируем
        if not self._is_running:
            logging.warning("[THREAD][RecognitionWorker] Worker stopped before starting.")
            if hasattr(self, 'error') and self.error is not None : self.error.emit("Recognition cancelled before start.") 
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished early (stopped).")
            return

        screenshot_to_recognize_cv2 = capture_screen_area(self.recognition_area_to_capture)

        if screenshot_to_recognize_cv2 is None:
            logging.error(f"[THREAD][RecognitionWorker] Failed to capture RECOGNITION_AREA: {self.recognition_area_to_capture}")
            if self._is_running and hasattr(self, 'error') and self.error is not None : self.error.emit(get_text('recognition_no_screenshot', language=self.current_language))
            # Отправляем сигнал finished с пустыми данными
            if hasattr(self, 'finished') and self.finished is not None:
                self.finished.emit([], None)
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (RECOGNITION_AREA screenshot error).")
            return
        
        logging.info(f"[THREAD][RecognitionWorker] RECOGNITION_AREA captured, shape: {screenshot_to_recognize_cv2.shape}")

        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after screenshot processing.")
            return
        
        if not self.advanced_recognizer.is_ready():
            error_msg = "Модели для расширенного распознавания не загружены или не готовы."
            logging.error(f"[THREAD][RecognitionWorker] {error_msg}")
            if self._is_running and hasattr(self, 'error') and self.error is not None : self.error.emit(error_msg)
            # Отправляем сигнал finished с пустыми данными, но с изображением
            if hasattr(self, 'finished') and self.finished is not None:
                self.finished.emit([], screenshot_to_recognize_cv2)
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (models not ready).")
            return

        recognized_heroes_original_names = self.advanced_recognizer.recognize_heroes_on_screenshot(screenshot_to_recognize_cv2)
        
        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after recognition.")
            return
        
        if hasattr(self, 'finished') and self.finished is not None: 
            # Передаем и героев, и скриншот
            self.finished.emit(recognized_heroes_original_names, screenshot_to_recognize_cv2) 
        logging.info(f"[THREAD][RecognitionWorker] Worker finished signal emitted with {len(recognized_heroes_original_names)} heroes and screenshot.")
        logging.info(f"[THREAD][RecognitionWorker] Worker run method finished.")

    def stop(self):
        logging.info("[THREAD][RecognitionWorker] Stop requested.")
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
        logging.info("[RecognitionManager] Initializing...")
        self.main_window = main_window
        self.logic_for_lang = logic
        self.win_api_manager = win_api_manager
        self.app_settings_manager = app_settings_manager
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        self._models_are_actually_ready = False
        self.is_recognizing = False
        
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
            parent=self
        )
        
        self.advanced_recognizer.load_started.connect(self._on_model_load_started)
        self.advanced_recognizer.load_finished.connect(self._on_model_load_finished)
        self.advanced_recognizer.start_async_load_models()

        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        logging.info("[RecognitionManager] Initialized and model loading started asynchronously.")

    @Slot()
    def _on_model_load_started(self):
        logging.info("[RecognitionManager] Model loading has started...")

    @Slot(bool)
    def _on_model_load_finished(self, success: bool):
        if success:
            self._models_are_actually_ready = True
            logging.info("[RecognitionManager] Model loading finished successfully.")
        else:
            self._models_are_actually_ready = False
            logging.error("[RecognitionManager] Model loading failed.")
            self.error.emit("Ошибка загрузки моделей распознавания. Функция будет недоступна.")
        self.models_ready_signal.emit(self._models_are_actually_ready)

    @Slot(list, object)
    def _on_recognition_complete_with_screenshot(self, heroes: list, screenshot_cv2: np.ndarray | None):
        """Слот, который обрабатывает результат от воркера, включая скриншот, с расширенным логированием."""
        logging.info(f"Received recognition result: {len(heroes)} heroes.")
        
        # --- БЛОК СОХРАНЕНИЯ СКРИНШОТА С РАСШИРЕННЫМ ЛОГИРОВАНИЕМ ---
        if screenshot_cv2 is None:
            logging.warning("[SS_SAVE] Скриншот для сохранения не получен (None). Пропускаем логику сохранения.")
        else:
            logging.info("[SS_SAVE] --- Начало проверки сохранения скриншота ---")
            save_flag = self.app_settings_manager.get_save_screenshot_flag()
            save_path = self.app_settings_manager.get_screenshot_path()
            num_heroes = len(heroes)
            
            logging.info(f"[SS_SAVE] Чтение настроек: save_flag = {save_flag}, save_path = '{save_path}'")
            logging.info(f"[SS_SAVE] Данные распознавания: num_heroes = {num_heroes}")

            # 1. Проверка флага и количества героев
            if save_flag and num_heroes < 6:
                logging.info(f"[SS_SAVE] УСЛОВИЕ 1 ПРОЙДЕНО: Флаг включен ({save_flag}) и героев ({num_heroes}) < 6.")
                
                # 2. Проверка пути
                if save_path and os.path.isdir(save_path):
                    logging.info(f"[SS_SAVE] УСЛОВИЕ 2 ПРОЙДЕНО: Путь '{save_path}' существует и является директорией.")
                    try:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"rcp_recognition_{timestamp}_{num_heroes}_heroes.png"
                        full_path = os.path.join(save_path, filename)
                        logging.info(f"[SS_SAVE] Попытка сохранения файла: {full_path}")
                        
                        # ИСПРАВЛЕНИЕ: Используем imencode для корректной работы с non-ASCII путями
                        is_success, buffer = cv2.imencode(".png", screenshot_cv2)
                        if is_success:
                            with open(full_path, "wb") as f:
                                f.write(buffer)
                            success = True
                        else:
                            success = False
                        
                        if success:
                            logging.info(f"[SS_SAVE] УСПЕХ: Скриншот успешно сохранен в {full_path}")
                        else:
                            logging.error(f"[SS_SAVE] ОШИБКА: cv2.imencode или запись в файл вернули ошибку для пути {full_path}. Проверьте права доступа и целостность данных.")
                    except Exception as e:
                        logging.error(f"[SS_SAVE] ИСКЛЮЧЕНИЕ: Произошла ошибка при попытке сохранить скриншот: {e}", exc_info=True)
                else:
                    logging.warning(f"[SS_SAVE] УСЛОВИЕ 2 НЕ ПРОЙДЕНО: Путь для сохранения ('{save_path}') не указан или не является директорией. Сохранение отменено.")
            else:
                logging.info(f"[SS_SAVE] УСЛОВИЕ 1 НЕ ПРОЙДЕНО: Флаг выключен ({save_flag}) или количество героев ({num_heroes}) не меньше 6. Сохранение отменено.")
            
            logging.info("[SS_SAVE] --- Конец проверки сохранения скриншота ---")

        # Передаем только список героев дальше в UI
        self.recognition_complete_signal.emit(heroes)

    @Slot()
    def _handle_recognize_heroes(self):
        logging.info("[ACTION][RecognitionManager] Recognition requested...")

        if self.is_recognizing:
            logging.warning("[WARN][RecognitionManager] Recognition already in progress, ignoring duplicate request.")
            return

        if not self._models_are_actually_ready:
            error_msg = get_text('recognition_models_not_ready', default_text="Модели распознавания еще не загружены. Пожалуйста, подождите.", language=self.logic_for_lang.DEFAULT_LANGUAGE)
            logging.error(f"[ERROR][RecognitionManager] {error_msg}")
            if hasattr(self, 'error') and self.error is not None: self.error.emit(error_msg)
            return

        self.is_recognizing = True
        if hasattr(self, 'recognition_started'):
            self.recognition_started.emit()
        logging.info("[ACTION][RecognitionManager] Recognition started, is_recognizing=True")
        
        self._recognition_worker = RecognitionWorker(self.advanced_recognizer, RECOGNITION_AREA)
        if self._recognition_worker : 
             self._recognition_worker.current_language = self.logic_for_lang.DEFAULT_LANGUAGE 
        
        self._recognition_thread = QThread(self.main_window)
        if self._recognition_worker and self._recognition_thread: 
            self._recognition_worker.moveToThread(self._recognition_thread)
            self._recognition_thread.started.connect(self._recognition_worker.run)
            if hasattr(self._recognition_worker, 'finished') and self._recognition_worker.finished is not None:
                 self._recognition_worker.finished.connect(self._on_recognition_complete_with_screenshot)
            if hasattr(self._recognition_worker, 'error') and self._recognition_worker.error is not None:
                 self._recognition_worker.error.connect(self.error.emit)
            
            self._recognition_thread.finished.connect(self._reset_recognition_state)
            self._recognition_thread.finished.connect(self._recognition_thread.deleteLater)
            
            if hasattr(self._recognition_worker, 'finished') and self._recognition_worker.finished is not None:
                self._recognition_worker.finished.connect(self._recognition_thread.quit)
                self._recognition_worker.finished.connect(self._recognition_worker.deleteLater)
            
            self._recognition_thread.start()
            logging.info("[INFO][RecognitionManager] Recognition thread started.")
        else:
            logging.error("[ERROR][RecognitionManager] Не удалось создать воркер или поток для распознавания.")
            self.is_recognizing = False
            if hasattr(self, 'recognition_stopped'):
                self.recognition_stopped.emit()

    @Slot()
    def _reset_recognition_state(self):
        logging.info("[INFO][RecognitionManager] Resetting recognition thread state.")
        self._recognition_thread = None
        self._recognition_worker = None
        self.is_recognizing = False
        if hasattr(self, 'recognition_stopped'):
            self.recognition_stopped.emit()
        logging.info("[INFO][RecognitionManager] Recognition thread state reset complete.")

    def stop_recognition(self):
         logging.info("[INFO][RecognitionManager] Stop recognition requested.")
         if self._recognition_worker:
             self._recognition_worker.stop()
         if self._recognition_thread and self._recognition_thread.isRunning():
             logging.info("[INFO][RecognitionManager] Quitting recognition thread...")
             self._recognition_thread.quit()
             if not self._recognition_thread.wait(1000):
                 logging.warning("[WARN][RecognitionManager] Recognition thread did not finish in time.")
         else:
             self._reset_recognition_state