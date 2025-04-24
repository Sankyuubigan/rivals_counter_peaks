# File: core/recognition.py
import logging
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox
import cv2
import numpy as np

import utils
import translations
# Используем актуальные константы
from utils import RECOGNITION_AREA, AKAZE_MIN_MATCH_COUNT, capture_screen_area
from translations import get_text

class RecognitionWorker(QObject):
    """Воркер для распознавания героев в отдельном потоке."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, logic, recognition_area, templates, parent=None):
        super().__init__(parent)
        self.logic = logic; self.recognition_area = recognition_area
        self.templates = templates; self._is_running = True
        logging.debug(f"[RecognitionWorker] Initialized.")

    @Slot()
    def run(self):
        """Основная функция воркера."""
        logging.info("[THREAD][RecognitionWorker] Worker started execution.")
        recognized_heroes = []
        if not self._is_running:
            logging.warning("[THREAD][RecognitionWorker] Worker stopped before starting."); self.error.emit("Recognition cancelled before start.")
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished early (stopped)."); return

        screenshot_cv2 = capture_screen_area(self.recognition_area)
        if screenshot_cv2 is None:
            logging.error("[THREAD][RecognitionWorker] Failed to capture screenshot.")
            if self._is_running: self.error.emit(get_text('recognition_no_screenshot', language=self.logic.DEFAULT_LANGUAGE))
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (screenshot error)."); return

        if not self._is_running: logging.info("[THREAD][RecognitionWorker] Worker stopped after screenshot."); return
        if not self.templates:
            logging.error("[THREAD][RecognitionWorker] Hero templates not loaded.")
            if self._is_running: self.error.emit(get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))
            logging.info(f"[THREAD][RecognitionWorker] Worker run method finished (no templates)."); return

        # Вызов функции распознавания AKAZE
        recognized_heroes = self.logic.recognize_heroes_from_image( screenshot_cv2, self.templates)
        if not self._is_running: logging.info("[THREAD][RecognitionWorker] Worker stopped after recognition."); return

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
        self.main_window = main_window; self.logic = logic; self.win_api_manager = win_api_manager
        self._recognition_thread: QThread | None = None; self._recognition_worker: RecognitionWorker | None = None
        self.recognize_heroes_signal.connect(self._handle_recognize_heroes); logging.info("[RecognitionManager] Initialized.")

    @Slot()
    def _handle_recognize_heroes(self):
        """Запускает процесс распознавания героев в отдельном потоке."""
        logging.info("[ACTION][RecognitionManager] Recognition requested...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            logging.warning("[WARN][RecognitionManager] Recognition process already running.")
            QMessageBox.information(self.main_window, "Распознавание", "Процесс распознавания уже выполняется.")
            return
        if not self.main_window.hero_templates:
             logging.error("[ERROR][RecognitionManager] Hero templates not loaded.")
             QMessageBox.warning(self.main_window, get_text('error', language=self.logic.DEFAULT_LANGUAGE), get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE)); return

        self._recognition_worker = RecognitionWorker( self.logic, RECOGNITION_AREA, self.main_window.hero_templates)
        self._recognition_thread = QThread(self.main_window)
        self._recognition_worker.moveToThread(self._recognition_thread)
        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)
        self._recognition_worker.error.connect(self.error.emit)
        self._recognition_thread.finished.connect(self._reset_recognition_state)
        self._recognition_worker.finished.connect(self._recognition_thread.quit)
        self._recognition_worker.finished.connect(self._recognition_worker.deleteLater)
        self._recognition_thread.finished.connect(self._recognition_thread.deleteLater)

        self._recognition_thread.start()
        logging.info("[INFO][RecognitionManager] Recognition thread started.")

    @Slot()
    def _reset_recognition_state(self):
        logging.info("[INFO][RecognitionManager] Resetting recognition thread state.")
        self._recognition_thread = None; self._recognition_worker = None
        logging.info("[INFO][RecognitionManager] Recognition thread state reset complete.")

    def stop_recognition(self):
         logging.info("[INFO][RecognitionManager] Stop recognition requested.")
         if self._recognition_worker: self._recognition_worker.stop()
