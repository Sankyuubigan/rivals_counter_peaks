# File: core/recognition.py
import logging
import os # Добавлен os для определения project_root
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox

from utils import RECOGNITION_AREA, capture_screen_area
from core.lang.translations import get_text
from core.advanced_recognition_logic import AdvancedRecognition 
from core.images_load import load_hero_templates_cv2 # Импортируем функцию загрузки CV2 шаблонов

class RecognitionWorker(QObject):
    """Воркер для распознавания героев в отдельном потоке."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, advanced_recognizer: AdvancedRecognition, recognition_area, parent=None):
        super().__init__(parent)
        self.advanced_recognizer = advanced_recognizer
        self.recognition_area = recognition_area
        self._is_running = True
        logging.debug(f"[RecognitionWorker] Initialized.")

    @Slot()
    def run(self):
        """Основная функция воркера."""
        logging.info("[THREAD][RecognitionWorker] Worker started execution.")
        recognized_heroes = []
        if not self._is_running:
            logging.warning("[THREAD][RecognitionWorker] Worker stopped before starting.")
            self.error.emit("Recognition cancelled before start.")
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished early (stopped).")
            return

        screenshot_cv2 = capture_screen_area(self.recognition_area)
        if screenshot_cv2 is None:
            logging.error("[THREAD][RecognitionWorker] Failed to capture screenshot.")
            # Используем main_window.logic.DEFAULT_LANGUAGE, если доступно, иначе просто 'ru_RU'
            lang_code = 'ru_RU'
            if hasattr(self.advanced_recognizer, 'main_window') and \
               hasattr(self.advanced_recognizer.main_window, 'logic'):
                lang_code = self.advanced_recognizer.main_window.logic.DEFAULT_LANGUAGE

            if self._is_running: self.error.emit(get_text('recognition_no_screenshot', language=lang_code))
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (screenshot error).")
            return

        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after screenshot.")
            return
        
        if not self.advanced_recognizer.is_ready():
            error_msg = "Модели для расширенного распознавания не загружены."
            logging.error(f"[THREAD][RecognitionWorker] {error_msg}")
            if self._is_running: self.error.emit(error_msg)
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (models not ready).")
            return

        recognized_heroes = self.advanced_recognizer.recognize_heroes_on_screenshot(screenshot_cv2)

        if not self._is_running:
            logging.info("[THREAD][RecognitionWorker] Worker stopped after recognition.")
            return

        self.finished.emit(recognized_heroes)
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
        self.logic_for_lang = logic # Сохраняем logic для доступа к языку
        self.win_api_manager = win_api_manager
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        
        # Определяем project_root_path
        project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # Загружаем CV2 шаблоны (AKAZE)
        # main_window.hero_templates больше не используется напрямую, если это были не CV2 шаблоны
        # AdvancedRecognition ожидает CV2 шаблоны
        akaze_cv2_templates = load_hero_templates_cv2()
        if not akaze_cv2_templates:
            logging.warning("[RecognitionManager] Не удалось загрузить CV2 шаблоны для AKAZE. Локализация колонки может не работать.")
            # Можно решить, показывать ли QMessageBox здесь или положиться на логи AdvancedRecognition
            # QMessageBox.warning(self.main_window, "Внимание", "Не удалось загрузить шаблоны для локализации героев (AKAZE).")


        self.advanced_recognizer = AdvancedRecognition(
            akaze_hero_template_images_cv2_dict=akaze_cv2_templates,
            project_root_path=project_root_path # Передаем путь к корню проекта
        )
        
        if not self.advanced_recognizer.is_ready():
            logging.warning("[RecognitionManager] Advanced recognizer models not immediately ready. Check logs from AdvancedRecognition for details.")
            # Можно показать QMessageBox, если критично
            # QMessageBox.warning(self.main_window, "Ошибка загрузки", "Не удалось загрузить модели для распознавания. Функция будет недоступна.")

        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        logging.info("[RecognitionManager] Initialized.")

    @Slot()
    def _handle_recognize_heroes(self):
        """Запускает процесс распознавания героев в отдельном потоке."""
        logging.info("[ACTION][RecognitionManager] Recognition requested...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            logging.warning("[WARN][RecognitionManager] Recognition process already running.")
            QMessageBox.information(self.main_window, "Распознавание", "Процесс распознавания уже выполняется.")
            return

        if not self.advanced_recognizer.is_ready():
            error_msg = "Модели для расширенного распознавания не загружены. Пожалуйста, проверьте логи."
            logging.error(f"[ERROR][RecognitionManager] {error_msg}")
            lang_code = self.logic_for_lang.DEFAULT_LANGUAGE if self.logic_for_lang else 'ru_RU'
            QMessageBox.warning(self.main_window, get_text('error', language=lang_code), error_msg)
            return

        self._recognition_worker = RecognitionWorker(self.advanced_recognizer, RECOGNITION_AREA, parent=None)
        self._recognition_thread = QThread(self.main_window)
        self._recognition_worker.moveToThread(self._recognition_thread)
        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)
        self._recognition_worker.error.connect(self.error.emit)
        self._recognition_thread.finished.connect(self._reset_recognition_state)
        self._recognition_worker.finished.connect(self._recognition_thread.quit) # Было self._recognition_worker.deleteLater, это неверно
        self._recognition_worker.finished.connect(self._recognition_worker.deleteLater) # worker удаляется сам
        self._recognition_thread.finished.connect(self._recognition_thread.deleteLater) # thread удаляется сам

        self._recognition_thread.start()
        logging.info("[INFO][RecognitionManager] Recognition thread started.")

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