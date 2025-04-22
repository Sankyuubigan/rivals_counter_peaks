# File: core/recognition.py
print("[LOG] recognition.py loaded")

from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox
import cv2
import numpy as np

# Используем относительные импорты
from utils import RECOGNITION_AREA, RECOGNITION_THRESHOLD, capture_screen_area
from translations import get_text

class RecognitionWorker(QObject):
    """Воркер для распознавания героев в отдельном потоке."""
    # Сигналы должны быть определены на уровне класса
    finished = Signal(list) # Передает список распознанных имен
    error = Signal(str)     # Передает сообщение об ошибке

    def __init__(self, logic, recognition_area, recognition_threshold, templates, parent=None):
        super().__init__(parent) # Передаем parent, если нужно
        self.logic = logic
        self.recognition_area = recognition_area
        self.recognition_threshold = recognition_threshold
        self.templates = templates
        self._is_running = True # Флаг для возможности остановки

    @Slot() # Декоратор для слота, который будет выполняться в потоке
    def run(self):
        """Основная функция воркера."""
        print("[THREAD][RecognitionWorker] Worker started.")
        if not self._is_running:
            print("[THREAD][RecognitionWorker] Worker stopped before starting.")
            self.error.emit("Recognition cancelled.")
            return

        try:
            # 1. Захват скриншота
            screenshot_cv2 = capture_screen_area(self.recognition_area)
            if screenshot_cv2 is None:
                raise ValueError(get_text('recognition_no_screenshot', language=self.logic.DEFAULT_LANGUAGE))
            if not self._is_running: return # Проверка после захвата

            # 2. Проверка шаблонов
            if not self.templates:
                 raise ValueError(get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))

            # 3. Распознавание
            recognized_heroes = self.logic.recognize_heroes_from_image(
                screenshot_cv2,
                self.templates,
                self.recognition_threshold
            )
            if not self._is_running: return # Проверка после распознавания

            # 4. Отправка результата
            self.finished.emit(recognized_heroes)

        except Exception as e:
            print(f"[THREAD ERROR][RecognitionWorker] Ошибка в потоке: {e}")
            if self._is_running: # Отправляем ошибку, только если нас не остановили
                self.error.emit(str(e))
        finally:
             print(f"[THREAD][RecognitionWorker] Worker finished.")

    def stop(self):
        """Устанавливает флаг остановки воркера."""
        print("[THREAD][RecognitionWorker] Stop requested.")
        self._is_running = False


class RecognitionManager(QObject):
    """Управляет процессом распознавания."""
    # Сигналы, которые будет эмитить менеджер в основной поток
    recognition_complete_signal = Signal(list)
    error = Signal(str)
    # Сигнал для запуска хоткеем
    recognize_heroes_signal = Signal()

    def __init__(self, main_window, logic, win_api_manager):
        super().__init__()
        print("[LOG] RecognitionManager.__init__ started")
        self.main_window = main_window # Ссылка на главное окно
        self.logic = logic
        self.win_api_manager = win_api_manager # Менеджер WinAPI (если нужен)
        self._recognition_thread: QThread | None = None
        self._recognition_worker: RecognitionWorker | None = None
        print("[LOG] RecognitionManager.__init__ finished")

    @Slot() # Слот для запуска по сигналу recognize_heroes_signal
    def _handle_recognize_heroes(self):
        """Запускает процесс распознавания героев в отдельном потоке."""
        print("[ACTION][RecognitionManager] Запрос на распознавание героев...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            print("[WARN][RecognitionManager] Процесс распознавания уже запущен.")
            QMessageBox.information(self.main_window, "Распознавание", "Процесс распознавания уже выполняется.")
            return

        # Проверяем наличие шаблонов перед запуском
        if not self.main_window.hero_templates:
             print("[ERROR][RecognitionManager] Шаблоны героев не загружены.")
             QMessageBox.warning(self.main_window, get_text('error', language=self.logic.DEFAULT_LANGUAGE),
                                 get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))
             return

        # Создаем воркер и поток
        self._recognition_worker = RecognitionWorker(
            self.logic,
            RECOGNITION_AREA, # Используем константу из utils
            RECOGNITION_THRESHOLD, # Используем константу из utils
            self.main_window.hero_templates # Передаем шаблоны из MainWindow
        )
        self._recognition_thread = QThread(self.main_window) # Родитель - главное окно
        self._recognition_worker.moveToThread(self._recognition_thread)

        # --- Подключаем сигналы ---
        # Запуск воркера при старте потока
        self._recognition_thread.started.connect(self._recognition_worker.run)
        # Перенаправляем сигналы воркера в сигналы менеджера (и далее в MainWindow)
        self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)
        self._recognition_worker.error.connect(self.error.emit)
        # Очистка после завершения потока
        # Важно сначала завершить поток, потом удалять объекты
        self._recognition_thread.finished.connect(self._recognition_thread.quit) # Запрашиваем выход из цикла событий потока
        self._recognition_thread.finished.connect(self._recognition_worker.deleteLater) # Ставим воркер на удаление
        self._recognition_thread.finished.connect(self._recognition_thread.deleteLater) # Ставим поток на удаление
        self._recognition_thread.finished.connect(self._reset_recognition_state) # Сбрасываем ссылки

        # Запускаем поток
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
         # Поток остановится сам после завершения run или по сигналу quit
