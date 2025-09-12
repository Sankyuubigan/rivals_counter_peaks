import logging
import os
import sys
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PIL import Image, ImageDraw, ImageFont
import datetime
import time
from mss import mss
from core.utils import RECOGNITION_AREA, capture_screen_area
from info.translations import get_text
from core.app_settings_manager import AppSettingsManager
from core.hero_recognition_system import HeroRecognitionSystem

class ModelLoaderWorker(QObject):
    finished = Signal(bool)

    def __init__(self, system: HeroRecognitionSystem, parent=None):
        super().__init__(parent)
        self.system = system

    @Slot()
    def run(self):
        logging.info("[ModelLoaderWorker] Starting async model load...")
        success = self.system.load_model() and self.system.load_embeddings()
        logging.info(f"[ModelLoaderWorker] Async load finished. Success: {success}")
        self.finished.emit(success)

class RecognitionWorker(QObject):
    finished = Signal(list, object, float)
    error = Signal(str)

    def __init__(self, hero_recognition_system: HeroRecognitionSystem, recognition_area_dict: dict, start_time: float, parent=None):
        super().__init__(parent)
        self.hero_recognition_system = hero_recognition_system
        self.recognition_area_to_capture = recognition_area_dict
        self.start_time = start_time
        self._is_running = True
        self.current_language = "ru_RU"

    @Slot()
    def run(self):
        delta = time.time() - self.start_time
        logging.info(f"[TIME-LOG] {delta:.3f}s: RecognitionWorker thread started.")
        if not self._is_running:
            self.error.emit("Recognition cancelled before start.")
            return

        t1 = time.time()
        screenshot = capture_screen_area(self.recognition_area_to_capture)
        t2 = time.time()
        logging.info(f"[TIME-LOG] {t2 - self.start_time:.3f}s: Screenshot captured in {t2 - t1:.3f}s.")

        if screenshot is None:
            logging.error(f"[THREAD] Failed to capture screen area: {self.recognition_area_to_capture}")
            if self._is_running: self.error.emit(get_text('recognition_no_screenshot', language=self.current_language))
            self.finished.emit([], None, self.start_time)
            return

        if not self._is_running: return

        if not self.hero_recognition_system.is_ready():
            error_msg = "Модели для распознавания не загружены."
            logging.error(f"[THREAD] {error_msg}")
            if self._is_running: self.error.emit(error_msg)
            self.finished.emit([], screenshot, self.start_time)
            return

        try:
            screenshot_pil = Image.fromarray(screenshot)
        except Exception as e:
            logging.error(f"[THREAD] Error converting image format: {e}")
            if self._is_running: self.error.emit(f"Ошибка преобразования изображения: {e}")
            self.finished.emit([], screenshot, self.start_time)
            return

        t1_rec = time.time()
        recognized_heroes = self.hero_recognition_system.recognize_heroes_optimized(screenshot_pil)
        t2_rec = time.time()
        duration = t2_rec - t1_rec
        logging.info(f"[TIME-LOG] {t2_rec - self.start_time:.3f}s: Recognition inference took {duration:.3f}s.")

        if self._is_running:
            self.finished.emit(recognized_heroes, screenshot, self.start_time)

        delta_end = time.time() - self.start_time
        logging.info(f"[TIME-LOG] {delta_end:.3f}s: RecognitionWorker finished.")

    def stop(self):
        self._is_running = False

class RecognitionManager(QObject):
    recognition_complete_signal = Signal(list, float)
    error = Signal(str)
    recognize_heroes_signal = Signal(float)
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
        self._loader_thread: QThread | None = None
        self._loader_worker: ModelLoaderWorker | None = None
        self._models_ready = False
        self.is_recognizing = False

        self.hero_recognition_system = HeroRecognitionSystem()
        self.recognize_heroes_signal.connect(self._handle_recognize_heroes)
        logging.info("[RecognitionManager] Initialized.")

    def start_async_model_load(self):
        if self._models_ready or self._loader_thread is not None:
            logging.warning("[RecognitionManager] Model loading already started or completed.")
            return

        logging.info("[RecognitionManager] Starting asynchronous model loading...")
        self._loader_worker = ModelLoaderWorker(self.hero_recognition_system)
        self._loader_thread = QThread(self.main_window)
        self._loader_worker.moveToThread(self._loader_thread)

        self._loader_thread.started.connect(self._loader_worker.run)
        self._loader_worker.finished.connect(self._on_models_loaded)
        self._loader_thread.finished.connect(self._loader_thread.deleteLater)

        self._loader_thread.start()

    @Slot(bool)
    def _on_models_loaded(self, success: bool):
        self._models_ready = success
        self.models_ready_signal.emit(success)
        if success:
            logging.info("[RecognitionManager] Models and embeddings loaded successfully.")
        else:
            logging.error("[RecognitionManager] Failed to load models or embeddings.")
            self.error.emit("Ошибка загрузки моделей распознавания.")

        if self._loader_thread: self._loader_thread.quit()
        if self._loader_worker: self._loader_worker.deleteLater()
        self._loader_thread = None
        self._loader_worker = None

    @Slot(list, object, float)
    def _on_recognition_complete(self, heroes: list, screenshot_np: np.ndarray | None, start_time: float):
        delta = time.time() - start_time
        logging.info(f"[TIME-LOG] {delta:.3f}s: RecognitionManager received results from worker.")

        if screenshot_np is not None:
            save_flag = self.app_settings_manager.get_save_screenshot_flag()
            save_path = self.app_settings_manager.get_screenshot_path()
            min_heroes_to_save = self.app_settings_manager.get_min_recognized_heroes()
            num_heroes_found = len(heroes)

            should_save = (save_flag and
                           save_path and
                           os.path.isdir(save_path) and
                           min_heroes_to_save <= num_heroes_found <= 5)

            if should_save:
                try:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"recognition_{timestamp}_{num_heroes_found}_heroes.png"
                    filepath = os.path.join(save_path, filename)
                    logging.info(f"Trying to save screenshot to: {filepath}")

                    with mss() as sct:
                        monitors = sct.monitors
                        if not monitors:
                            logging.error("No monitors found for screenshot scaling.")
                            self.recognition_complete_signal.emit(heroes, start_time)
                            return

                        monitor_index = RECOGNITION_AREA.get('monitor', 1)
                        if not (0 <= monitor_index < len(monitors)):
                            monitor_index = 1 if len(monitors) > 1 else 0

                        monitor = monitors[monitor_index]
                        screen_width, screen_height = monitor["width"], monitor["height"]

                        full_screen_canvas = Image.new("RGB", (screen_width, screen_height), (128, 128, 128))

                        left = int(monitor["width"] * RECOGNITION_AREA['left_pct'] / 100)
                        top = int(monitor["height"] * RECOGNITION_AREA['top_pct'] / 100)
                        width = int(monitor["width"] * RECOGNITION_AREA['width_pct'] / 100)
                        height = int(monitor["height"] * RECOGNITION_AREA['height_pct'] / 100)

                        roi_pil = Image.fromarray(screenshot_np).resize((width, height), Image.LANCZOS)
                        full_screen_canvas.paste(roi_pil, (left, top))

                        heroes_text = ", ".join(heroes) if heroes else "None"
                        draw = ImageDraw.Draw(full_screen_canvas)
                        try:
                            font = ImageFont.truetype("arial.ttf", 24)
                        except:
                            font = ImageFont.load_default()

                        text_pos = (10, 30)
                        draw.text((text_pos[0] + 1, text_pos[1] + 1), f"Recognized: {heroes_text}", fill="black", font=font)
                        draw.text(text_pos, f"Recognized: {heroes_text}", fill="white", font=font)

                        full_screen_canvas.save(filepath)
                        logging.info(f"Screenshot saved to {filepath}")

                except Exception as e:
                    logging.error(f"Failed to save screenshot: {e}", exc_info=True)
                    self.error.emit(f"Ошибка сохранения скриншота: {e}")

        self.recognition_complete_signal.emit(heroes, start_time)

    @Slot(float)
    def _handle_recognize_heroes(self, start_time: float):
        delta = time.time() - start_time
        logging.info(f"[TIME-LOG] {delta:.3f}s: RecognitionManager handling request.")
        if self.is_recognizing:
            logging.warning("Recognition already in progress.")
            return
        if not self._models_ready:
            logging.error("[RecognitionManager] Models not ready for recognition.")
            self.error.emit(get_text('recognition_models_not_ready', language=self.logic.DEFAULT_LANGUAGE))
            return

        self.is_recognizing = True
        self.recognition_started.emit()

        self._recognition_worker = RecognitionWorker(self.hero_recognition_system, RECOGNITION_AREA, start_time)
        self._recognition_worker.current_language = self.logic.DEFAULT_LANGUAGE

        self._recognition_thread = QThread(self.main_window)
        self._recognition_worker.moveToThread(self._recognition_thread)
        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self._on_recognition_complete)
        self._recognition_worker.error.connect(self.error.emit)

        self._recognition_thread.finished.connect(self._reset_recognition_state)
        self._recognition_worker.finished.connect(self._recognition_thread.quit)

        self._recognition_thread.start()
        delta_end = time.time() - start_time
        logging.info(f"[TIME-LOG] {delta_end:.3f}s: Recognition thread started.")

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
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()