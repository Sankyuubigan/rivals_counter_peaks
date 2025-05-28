# File: core/recognition.py
import logging
import os 
import sys # <--- Добавим sys
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
            lang_code = 'ru_RU' # Default
            # Пытаемся получить язык из advanced_recognizer, если он там есть и доступен (маловероятно)
            # или лучше из logic_for_lang, который есть в RecognitionManager
            if hasattr(self.advanced_recognizer, 'main_window_logic_lang_ref'): # Предположим, что мы передали ссылку
                 lang_code = self.advanced_recognizer.main_window_logic_lang_ref
            
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
        self.logic_for_lang = logic 
        self.win_api_manager = win_api_manager
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        
        # Определяем project_root_path для AdvancedRecognition
        # Если приложение "заморожено" PyInstaller, используем sys._MEIPASS
        # Иначе, используем путь относительно текущего файла (для разработки)
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Приложение запущено из EXE PyInstaller
            project_root_for_adv_rec = sys._MEIPASS
            logging.info(f"[RecognitionManager] Приложение 'заморожено', project_root_for_adv_rec установлен в sys._MEIPASS: {project_root_for_adv_rec}")
        else:
            # Приложение запущено как обычный Python скрипт (разработка)
            # __file__ указывает на текущий файл (recognition.py)
            # os.path.dirname(__file__) -> .../core/
            # os.path.join(..., '..') -> .../ (корень проекта, где лежат nn_models, resources)
            project_root_for_adv_rec = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            logging.info(f"[RecognitionManager] Приложение не 'заморожено', project_root_for_adv_rec установлен в: {project_root_for_adv_rec}")

        akaze_cv2_templates = load_hero_templates_cv2() # Эта функция должна использовать resource_path
        if not akaze_cv2_templates:
            logging.warning("[RecognitionManager] Не удалось загрузить CV2 шаблоны для AKAZE. Локализация колонки может не работать.")

        self.advanced_recognizer = AdvancedRecognition(
            akaze_hero_template_images_cv2_dict=akaze_cv2_templates,
            project_root_path=project_root_for_adv_rec # <--- Используем определенный выше путь
        )
        # Передаем ссылку на язык в воркер через advanced_recognizer (если это нужно там)
        # или лучше передавать язык напрямую в воркер при его создании.
        # Пока оставим так, как есть в воркере, он возьмет язык из logic.
        
        if not self.advanced_recognizer.is_ready():
            logging.warning("[RecognitionManager] Advanced recognizer models not immediately ready. Check logs from AdvancedRecognition for details.")

        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        logging.info("[RecognitionManager] Initialized.")

    @Slot()
    def _handle_recognize_heroes(self):
        logging.info("[ACTION][RecognitionManager] Recognition requested...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            logging.warning("[WARN][RecognitionManager] Recognition process already running.")
            # QMessageBox.information(self.main_window, "Распознавание", "Процесс распознавания уже выполняется.")
            # Вместо QMessageBox, которое может блокировать, просто логируем и выходим
            return

        if not self.advanced_recognizer.is_ready():
            error_msg = get_text('recognition_error_prefix', language=self.logic_for_lang.DEFAULT_LANGUAGE) + " " + \
                        "Модели для расширенного распознавания не загружены." # TODO: Перевести "Модели..."
            logging.error(f"[ERROR][RecognitionManager] {error_msg}")
            self.error.emit(error_msg) # Отправляем сигнал об ошибке в главный поток
            return

        # Передаем язык в воркер через advanced_recognizer или напрямую
        # Сейчас воркер пытается получить его сам, что не очень хорошо.
        # Лучше так:
        # self._recognition_worker = RecognitionWorker(self.advanced_recognizer, RECOGNITION_AREA, current_language=self.logic_for_lang.DEFAULT_LANGUAGE)
        # Но для этого нужно изменить конструктор RecognitionWorker
        self._recognition_worker = RecognitionWorker(self.advanced_recognizer, RECOGNITION_AREA)
        # Для доступа к языку в RecognitionWorker можно сделать так:
        if hasattr(self._recognition_worker.advanced_recognizer, 'main_window_logic_lang_ref'):
            self._recognition_worker.advanced_recognizer.main_window_logic_lang_ref = self.logic_for_lang.DEFAULT_LANGUAGE
        
        self._recognition_thread = QThread(self.main_window)
        self._recognition_worker.moveToThread(self._recognition_thread)
        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)
        self._recognition_worker.error.connect(self.error.emit) # Уже было
        self._recognition_thread.finished.connect(self._reset_recognition_state)
        self._recognition_worker.finished.connect(self._recognition_thread.quit) 
        self._recognition_worker.finished.connect(self._recognition_worker.deleteLater) 
        self._recognition_thread.finished.connect(self._recognition_thread.deleteLater) 

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