# File: core/recognition.py
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QMessageBox
from images_load import load_hero_templates
from utils import RECOGNITION_AREA, RECOGNITION_THRESHOLD
from gui import RecognitionWorker
from translations import get_text
class RecognitionManager(QObject):
    recognize_heroes_signal = Signal()

    def _get_screenshot(self):
        """Делает скриншот."""
        print("[INFO] Делаю скриншот...")
        try:
            return pyautogui.screenshot()
        except Exception as e:
            raise Exception(f"Ошибка при создании скриншота: {e}")

    def _get_region(self, image):
        """Вырезает область для распознавания из скриншота."""
        print("[INFO] Вырезаю область для распознавания из скриншота...")
        try:
            left, top, width, height = RECOGNITION_AREA
            return image.crop((left, top, left + width, top + height))
        except Exception as e:
            raise Exception(f"Ошибка при вырезании области из скриншота: {e}")

    def _ocr(self, region):
        """Распознает текст на изображении."""
        print("[INFO] Распознаю текст на изображении...")
        try:
            text = pytesseract.image_to_string(region, lang='eng',)
            return text.splitlines()
        except Exception as e:
            raise Exception(f"Ошибка распознавания текста: {e}")


    recognition_complete_signal = Signal(list)

    def __init__(self, main_window, logic):
        super().__init__()
        self.main_window = main_window
        self.logic = logic
        self._recognition_thread = None
        self._recognition_worker = None
        self.hero_templates = {}
        self.load_templates()

    def load_templates(self):
        print("Загрузка шаблонов героев для распознавания...")
        try:
            # Функция из images_load.py использует кэш
            self.hero_templates = load_hero_templates()
            if not self.hero_templates:
                print("[WARN] Шаблоны героев не найдены или не удалось загрузить.")
            else:
                print(f"Загружено шаблонов для {len(self.hero_templates)} героев.")
        except Exception as e:
            print(f"[ERROR] Критическая ошибка при загрузке шаблонов: {e}")
            self.hero_templates = {}  # Очищаем на случай ошибки

    def _get_text_from_region(self):
        """Распознает текст в заданной области на экране."""
        try:
            image = self._get_screenshot()
            region = self._get_region(image)
            text = self._ocr(region)
            return text
        except Exception as e:
            print(f"[ERROR] Ошибка при распознавании текста: {e}")
            return []


    @Slot()
    def _handle_recognize_heroes(self):
        """Запускает процесс распознавания героев в отдельном потоке."""
        print("[ACTION] Запрос на распознавание героев...")
        if self._recognition_thread and self._recognition_thread.isRunning():
            print("[WARN] Процесс распознавания уже запущен.")
            QMessageBox.information(self.main_window, "Распознавание", "Процесс распознавания уже выполняется.")
            return

        if not self.hero_templates:
            print("[ERROR] Шаблоны героев не загружены. Распознавание невозможно.")
            QMessageBox.warning(self.main_window, get_text('error'), get_text('recognition_no_templates', language=self.logic.DEFAULT_LANGUAGE))
            return

        # Создаем и запускаем поток
        self._recognition_worker = RecognitionWorker(
            self.logic,
            RECOGNITION_AREA,
            RECOGNITION_THRESHOLD,
            self.hero_templates
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