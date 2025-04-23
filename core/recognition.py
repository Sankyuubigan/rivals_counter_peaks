# File: core/recognition.py
print("[LOG] recognition.py loaded")

from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox
import cv2
import numpy as np

# <<< ИСПРАВЛЕНО: Используем абсолютные импорты >>>
import utils
import translations
# <<< ---------------------------------------- >>>
from utils import RECOGNITION_AREA, RECOGNITION_THRESHOLD, capture_screen_area
from translations import get_text

class RecognitionWorker(QObject):
    """Воркер для распознавания героев в отдельном потоке."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, logic, recognition_area, recognition_threshold, templates, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.recognition_area = recognition_area
        self.recognition_threshold = recognition_threshold
        self.templates = templates
        self._is_running = True

    @Slot()
    def run(self):
        """Основная функция воркера."""
        print("[THREAD][RecognitionWorker] Worker started.")
        if not self._is_running:
            print("[THREAD][RecognitionWorker] Worker stopped before starting.")
            self.error.emit("Recognition cancelled before start.")
            return

        try:
            screenshot_cv2 = capture_screen_area(self.recognition_area)
            if screenshot_cv2 is None:
                raise ValueError(get_text('recognition_no_screenshot', language=self.logic.DEFAULT_LANGUAGE))
            if not self._is_running: return

            if not self.templates:
                 raise ValueError(get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))

            recognized_heroes = self.logic.recognize_heroes_from_image(
                screenshot_cv2,
                self.templates,
                self.recognition_threshold
            )
            if not self._is_running: return

            self.finished.emit(recognized_heroes)

        except Exception as e:
            print(f"[THREAD ERROR][RecognitionWorker] Ошибка в потоке: {e}")
            if self._is_running:
                self.error.emit(str(e))
        finally:
             print(f"[THREAD][RecognitionWorker] Worker finished.")

    def stop(self):
        """Устанавливает флаг остановки воркера."""
        print("[THREAD][RecognitionWorker] Stop requested.")
        self._is_running = False


class RecognitionManager(QObject):
    """Управляет процессом распознавания."""
    recognition_complete_signal = Signal(list)
    error = Signal(str)
    recognize_heroes_signal = Signal()

    def __init__(self, main_window, logic, win_api_manager):
        super().__init__()
        print("[LOG] RecognitionManager.__init__ started")
        self.main_window = main_window
        self.logic = logic
        self.win_api_manager = win_api_manager
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        print("[LOG] RecognitionManager.__init__ finished")

    @Slot()
    def _handle_recognize_heroes(self):
        """Запускает процесс распознавания героев в отдельном потоке."""
        print("[ACTION][RecognitionManager] Запрос на распознавание героев...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            print("[WARN][RecognitionManager] Процесс распознавания уже запущен.")
            QMessageBox.information(self.main_window, "Распознавание", "Процесс распознавания уже выполняется.")
            return

        if not self.main_window.hero_templates:
             print("[ERROR][RecognitionManager] Шаблоны героев не загружены.")
             QMessageBox.warning(self.main_window, get_text('error', language=self.logic.DEFAULT_LANGUAGE),
                                 get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))
             return

        self._recognition_worker = RecognitionWorker(
            self.logic,
            RECOGNITION_AREA,
            RECOGNITION_THRESHOLD,
            self.main_window.hero_templates
        )
        self._recognition_thread = QThread(self.main_window)
        self._recognition_worker.moveToThread(self._recognition_thread)

        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)
        self._recognition_worker.error.connect(self.error.emit)
        self._recognition_thread.finished.connect(self._recognition_thread.quit)
        self._recognition_thread.finished.connect(self._recognition_worker.deleteLater)
        self._recognition_thread.finished.connect(self._recognition_thread.deleteLater)
        self._recognition_thread.finished.connect(self._reset_recognition_state)

        self._recognition_thread.start()
        print("[INFO][RecognitionManager] Поток распознавания запущен.")

    @Slot()
    def _reset_recognition_state(self):
        """Сбрасывает ссылки на поток и воркер."""
        print("[INFO][RecognitionManager] Сброс ссылок на поток распознавания.")
        self._recognition_thread = None
        self._recognition_worker = None

    def stop_recognition(self):
         """Останавливает текущий процесс распознавания."""
         if self._recognition_worker:
             self._recognition_worker.stop()