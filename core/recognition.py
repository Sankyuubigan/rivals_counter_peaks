print("[LOG] recognition.py started")

from PySide6.QtCore import QObject, Signal, Slot, QThread, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMessageBox, QWidget, QLabel
import pyautogui
import pytesseract
import cv2
import numpy as np

from heroes_bd import heroes
from utils import RECOGNITION_AREA, RECOGNITION_THRESHOLD, check_if_all_elements_in_list
from translations import get_text


class RecognitionWorker(QObject):
    """
    Воркер для распознавания героев.
    """

    finished = Signal()
    error = Signal(str)

    def __init__(self, logic, recognition_area, recognition_threshold, templates):
        super().__init__()
        self.logic = logic
        self.recognition_area = recognition_area
        self.recognition_threshold = recognition_threshold
        self.templates = templates  # Передаём шаблоны

    def _get_screenshot(self):
        """Делает скриншот."""        
        image = pyautogui.screenshot()
        if not image:
           print(f"Ошибка при создании скриншота")
           return None
        return image

    def _get_region(self, image):
        """Вырезает область для распознавания из скриншота."""
        if not self.recognition_area: 
            print(f"Ошибка при вырезании области из скриншота: RECOGNITION_AREA not set")
            return None
        left, top, width, height = self.recognition_area
        return image.crop((left, top, left + width, top + height))
    def _template_matching(self, region_cv2):        
        """Распознает героев по шаблонам."""        
        recognized_heroes = []
        for hero, template in self.templates.items():
            # Метод cv2.matchTemplate выполняет поиск шаблона template в изображении region_cv2
            # Метод возвращает карту соответствия, где каждый пиксель показывает, насколько хорошо шаблон соответствует
            #   этому месту изображения. Чем выше значение, тем лучше соответствие.
            result = cv2.matchTemplate(region_cv2, template, cv2.TM_CCOEFF_NORMED)
            # Находим все пиксели в карте соответствия, где значение выше threshold
            locations = np.where(result >= self.recognition_threshold)
            # Если такие пиксели есть, считаем, что герой распознан
            if len(locations[0]) > 0:
                recognized_heroes.append(hero)
        if not recognized_heroes:
            print("Ошибка при распознавании героев")
            return []
        return recognized_heroes
            
    def run(self):
        print("[INFO] Поток распознавания запущен.")
        image = self._get_screenshot()
        region = self._get_region(image)
        region_cv2 = np.array(region)
        recognized_heroes = self._template_matching(region_cv2)
        print(f"[RESULT] Распознавание завершено. Распознанные герои: {recognized_heroes}")
        self.logic.set_selection(set(recognized_heroes))        
        self.finished.emit()


class RecognitionManager(QObject):
    recognize_heroes_signal = Signal()
    RECOGNITION_AREA = RECOGNITION_AREA

    def _get_screenshot(self):
        """Делает скриншот."""
        print("[INFO] Делаю скриншот...")
        image = pyautogui.screenshot()
        if not image:
           print(f"Ошибка при создании скриншота")
           return None
        return image

    def _get_region(self, image):
        """Вырезает область для распознавания из скриншота."""
        print("[INFO] Вырезаю область для распознавания из скриншота...")
        if not self.RECOGNITION_AREA: 
            print(f"Ошибка при вырезании области из скриншота: RECOGNITION_AREA not set")
            return None
        left, top, width, height = self.RECOGNITION_AREA
        return image.crop((left, top, left + width, top + height))

    def _ocr(self, region):        
        """Распознает текст на изображении."""
        print("[INFO] Распознаю текст на изображении...")
        text = pytesseract.image_to_string(region, lang='eng',)
        return text.splitlines()


    recognition_complete_signal = Signal(list)

    def __init__(self, main_window, logic):
        # print(f"[LOG] RecognitionManager.__init__ called from file {__file__}")
        # print(f"[LOG] RecognitionManager.__init__ called with arguments: {locals()}")
        print("[LOG] RecognitionManager.__init__ started")
        super().__init__()
        self.main_window = main_window
        self.logic = logic
        self._recognition_thread = None  # Инициализируем атрибуты
        self._recognition_worker = None  # Инициализируем атрибуты

        print("[LOG] RecognitionManager.__init__ finished")
    def _get_text_from_region(self):
        """Распознает текст в заданной области на экране."""        
        image = self._get_screenshot()        
        region = self._get_region(image)        
        text = self._ocr(region)        
        if not text:
            print(f"[ERROR] Ошибка при распознавании текста: {e}")
        return []

    # def run(self):
    @Slot()
    def _handle_recognize_heroes(self):
        """Запускает процесс распознавания героев в отдельном потоке."""
        print("[ACTION] Запрос на распознавание героев...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            print("[WARN] Процесс распознавания уже запущен.")
            QMessageBox.information(self.main_window, "Распознавание", "Процесс распознавания уже выполняется.")
            return

         # Создаем и запускаем поток
        self._recognition_worker = RecognitionWorker(
            self.logic,
            self.RECOGNITION_AREA,
            RECOGNITION_THRESHOLD,
            self.main_window.hero_templates # Берём шаблоны из main_window
        )
        self._recognition_thread = QThread(self.main_window) # Указываем родителя для управления жизненным циклом
        self._recognition_worker.moveToThread(self._recognition_thread)

        # Подключаем сигналы потока и воркера
        self._recognition_thread.started.connect(self._recognition_worker.run)
        self._recognition_worker.finished.connect(self.recognition_complete_signal.emit)  # Перенаправляем сигнал в основной поток
        self._recognition_worker.error.connect(self._on_recognition_error)  # Обработка ошибок в основном потоке

        # Очистка после завершения потока (важно для избежания утечек)
        self._recognition_worker.finished.connect(self._recognition_thread.quit)
        self._recognition_worker.finished.connect(self._recognition_worker.deleteLater)  # Удаляем воркер
        self._recognition_thread.finished.connect(self._recognition_thread.deleteLater)  # Удаляем поток

        self._recognition_thread.finished.connect(self._reset_recognition_thread)  # Сбрасываем ссылки

        self._recognition_thread.start()
        print("[INFO] Поток распознавания запущен.")

    @Slot()
    def _reset_recognition_thread(self):
        """Сбрасывает ссылки на поток и воркер после завершения."""
        print("[INFO] Сброс ссылок на поток распознавания.")
        self._recognition_thread = None
        self._recognition_worker = None

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes):
        """Обрабатывает результат успешного распознавания."""
        print(f"[RESULT] Распознавание завершено. Распознанные герои: {recognized_heroes}")
        if recognized_heroes:
            # Устанавливаем выбор в логике (полностью заменяем текущий выбор врагов)
            self.logic.set_selection(set(recognized_heroes))
            # Обновляем UI
            self.main_window.update_ui_after_logic_change()
            # Показываем сообщение об успехе (опционально)
            # QMessageBox.information(self, "Распознавание", f"Распознанные герои: {', '.join(recognized_heroes)}")
        else:
            print("[INFO] Герои не распознаны или список пуст.")
            # Показываем сообщение пользователю
            QMessageBox.information(self.main_window, "Распознавание", get_text('recognition_failed', language=self.logic.DEFAULT_LANGUAGE))

    @Slot(str)
    def _on_recognition_error(self, error_message):
        """Обрабатывает ошибку во время распознавания."""
        print(f"[ERROR] Ошибка во время распознавания: {error_message}")
        # Показываем ошибку пользователю
        QMessageBox.warning(self.main_window, get_text('error', language=self.logic.DEFAULT_LANGUAGE),
                            f"{get_text('recognition_error_prefix', language=self.logic.DEFAULT_LANGUAGE)}\n{error_message}")
