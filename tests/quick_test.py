#!/usr/bin/env python3
"""
Скрипт для быстрого запуска самых важных и быстрых unit-тестов.
Полезен для быстрой проверки работоспособности основной логики.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Запускает основные unit-тесты."""
    print("🚀 Быстрый запуск ключевых тестов...")
    
    project_root = Path(__file__).parent
    tests_path = project_root / 'tests' / 'test_logic.py'

    if not tests_path.exists():
        print(f"❌ Файл с тестами не найден: {tests_path}")
        return False

    try:
        # Запускаем только unit-тесты, они самые быстрые
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(tests_path), '-m', 'not (gui or integration or slow)'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)

        if result.returncode == 0:
            print("\n✅ Быстрые тесты прошли успешно!")
            return True
        else:
            print("\n❌ Обнаружены проблемы в быстрых тестах.")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Тесты не завершились за 60 секунд.")
        return False
    except Exception as e:
        print(f"💥 Произошла ошибка при запуске тестов: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
