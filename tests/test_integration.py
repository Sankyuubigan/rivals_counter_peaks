import pytest
import subprocess
import time
import psutil
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.mark.slow
class TestFullApplicationFlow:
    """Полные интеграционные тесты, запускающие приложение как отдельный процесс."""

    app_process = None

    @classmethod
    def setup_class(cls):
        """Запускает приложение один раз перед всеми тестами в классе."""
        main_script = Path('core/main.py')
        if not main_script.exists():
            pytest.fail(f"Основной скрипт не найден: {main_script}")

        logger.info(f"Запуск процесса приложения: {main_script}")
        cls.app_process = subprocess.Popen(
            [sys.executable, str(main_script)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        time.sleep(5)  # Даем время на инициализацию приложения

        # Проверяем, что процесс не упал сразу после запуска
        if cls.app_process.poll() is not None:
            stdout, stderr = cls.app_process.communicate()
            pytest.fail(
                f"Приложение не запустилось. Код возврата: {cls.app_process.returncode}\n"
                f"Stderr: {stderr}"
            )
        logger.info(f"Приложение успешно запущено с PID: {cls.app_process.pid}")

    @classmethod
    def teardown_class(cls):
        """Корректно завершает процесс приложения после всех тестов."""
        if cls.app_process and cls.app_process.poll() is None:
            logger.info(f"Завершение процесса приложения с PID: {cls.app_process.pid}")
            try:
                proc = psutil.Process(cls.app_process.pid)
                for child in proc.children(recursive=True):
                    child.kill()
                proc.kill()
                cls.app_process.wait(timeout=5)
                logger.info("Процесс приложения успешно завершен.")
            except (psutil.NoSuchProcess, subprocess.TimeoutExpired) as e:
                logger.warning(f"Не удалось корректно завершить процесс: {e}")
                cls.app_process.kill()

    def test_application_is_running(self):
        """Тест: проверяет, что процесс приложения активен."""
        assert self.app_process.poll() is None, "Процесс приложения неожиданно завершился."

    def test_memory_usage_is_reasonable(self):
        """Тест: проверяет, что приложение не потребляет слишком много памяти."""
        try:
            process = psutil.Process(self.app_process.pid)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            assert memory_mb < 500, f"Потребление памяти слишком велико: {memory_mb:.1f} МБ"
            logger.info(f"Текущее потребление памяти: {memory_mb:.1f} МБ.")
        except psutil.NoSuchProcess:
            pytest.fail("Процесс приложения не найден для проверки памяти.")

    def test_ml_model_file_exists(self):
        """Тест: проверяет наличие файла ML-модели."""
        model_path = Path('nn_models/onnx/model.onnx')
        assert model_path.is_file(), f"Файл ML-модели не найден: {model_path}"
        assert model_path.stat().st_size > 1024, "Файл ML-модели пуст или слишком мал."
        logger.info("Файл ML-модели найден и имеет корректный размер.")
