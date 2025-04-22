print("[LOG] recognition.py started")
from utils import capture_screen_area, RECOGNITION_AREA, RECOGNITION_THRESHOLD
from images_load import load_hero_templates
from heroes_bd import heroes
from typing import List
from PySide6.QtCore import QThread, QTimer, Signal

class RecognitionManager:
    recognition_result_signal = Signal(list)
    def __init__(self, logic):
        print("[LOG] RecognitionManager.__init__ called")
        self.logic = logic
        print(f"[LOG] RecognitionManager.__init__ got logic: {logic}")
        self.templates = {}
        self.templates_initialized = False
        self.templates_directory = None
        self.last_recognition_result = []
        self.capture_area = RECOGNITION_AREA
        self.threshold = RECOGNITION_THRESHOLD
        self.recognize_on_start = True # Выполнять распознавание сразу при запуске (иначе - по сигналу)
        self.min_recognition_interval = 1 # сек (мин интервал для распознавания, чтобы не перегружать)
        self.recognize_timer = QTimer()
        self.recognize_timer.setSingleShot(True)
        self.recognize_timer.timeout.connect(self.recognize_heroes)
        self.recognition_thread = QThread()
        self.recognition_thread.start()
        if self.recognize_on_start:
            self.start_recognition() # Запускаем распознавание

    def load_templates(self, directory = None):
        self.templates_initialized = False
        self.templates_directory = directory
        self.templates = load_hero_templates(directory)
        self.templates_initialized = True

    def start_recognition(self):
        if not self.templates_initialized:
            self.load_templates(self.templates_directory)
        self.recognize_timer.start(self.min_recognition_interval * 1000)

    def recognize_heroes(self):
        print("[LOG] recognize_heroes")
        capture = capture_screen_area(self.capture_area)
        result = []
        self.last_recognition_result = result
        self.recognition_result_signal.emit(result)
        self.recognize_timer.start(self.min_recognition_interval * 1000)