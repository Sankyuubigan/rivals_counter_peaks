import subprocess
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

class TestRunner:
    """Класс для автоматизированного запуска всех наборов тестов и генерации отчета."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.log_file = f'tests/test_run_{self.start_time.strftime("%Y%m%d_%H%M%S")}.log'
        self.results = {}
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def run_test_suite(self, test_file: str, description: str, marker: str = None):
        """Запускает конкретный набор тестов с помощью pytest."""
        self.logger.info(f"\n{'='*60}\nЗАПУСК: {description} (Файл: {test_file})\n{'='*60}")
        
        command = [sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short']
        if marker:
            command.extend(['-m', marker])

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=300
            )
            success = result.returncode == 0 or result.returncode == 5 # 5 = no tests collected
            
            self.results[description] = {
                'success': success,
                'stdout': result.stdout,
                'stderr': result.stderr,
            }
            
            status = "✅ УСПЕШНО" if success else "❌ ПРОВАЛЕНО"
            self.logger.info(f"РЕЗУЛЬТАТ: {description} -> {status}")
            
            if not success:
                self.logger.error(f"STDOUT:\n{result.stdout}")
                self.logger.error(f"STDERR:\n{result.stderr}")
            
            return success
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ ТАЙМАУТ: {description} не завершился за 5 минут.")
            self.results[description] = {'success': False, 'error': 'Timeout'}
            return False
        except Exception as e:
            self.logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА при запуске {description}: {e}")
            self.results[description] = {'success': False, 'error': str(e)}
            return False

    def generate_report(self):
        """Генерирует и сохраняет итоговый отчет о тестировании."""
        self.logger.info(f"\n{'='*60}\nИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ\n{'='*60}")
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r['success'])
        failed = total - passed
        
        self.logger.info(f"Всего запущено сьютов: {total}")
        self.logger.info(f"✅ Успешно: {passed}")
        self.logger.info(f"❌ Провалено: {failed}")
        
        report_file = f'tests/report_{self.start_time.strftime("%Y%m%d_%H%M%S")}.json'
        report_data = {
            'run_timestamp': self.start_time.isoformat(),
            'summary': {'total': total, 'passed': passed, 'failed': failed},
            'details': self.results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Подробный JSON-отчет сохранен в: {report_file}")
        return failed == 0

    def run_all(self):
        """Последовательно запускает все определенные наборы тестов."""
        test_suites = [
            {'file': 'tests/test_logic.py', 'desc': 'Unit-тесты логики', 'marker': 'not (gui or integration)'},
            {'file': 'tests/test_gui.py', 'desc': 'GUI-тесты', 'marker': 'gui'},
            {'file': 'tests/test_integration.py', 'desc': 'Интеграционные тесты', 'marker': 'integration'},
        ]
        
        self.logger.info("🚀 Начало полного цикла тестирования Marvel Rivals Counter Picker")
        
        for suite in test_suites:
            if Path(suite['file']).exists():
                self.run_test_suite(suite['file'], suite['desc'], suite['marker'])
            else:
                self.logger.warning(f"⚠️ Файл теста не найден, пропуск: {suite['file']}")
                self.results[suite['desc']] = {'success': False, 'error': 'File not found'}
        
        overall_success = self.generate_report()
        
        if overall_success:
            self.logger.info("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        else:
            self.logger.error("\n💥 ОБНАРУЖЕНЫ ОШИБКИ В ТЕСТАХ!")
        
        return overall_success

if __name__ == "__main__":
    runner = TestRunner()
    is_successful = runner.run_all()
    sys.exit(0 if is_successful else 1)
