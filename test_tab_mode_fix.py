#!/usr/bin/env python3
"""
Тест исправления геометрии для таб-режима
Этот скрипт тестирует логику исправления порядка операций установки флагов и геометрии окна.
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QRect
    from PySide6.QtCore import Qt, QTimer
    import logging
    import time

    # Настройки логирования
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    class TestMainWindow(QMainWindow):
        """Тестовый класс для проверки логики исправления таб-режима"""

        def __init__(self):
            super().__init__()
            self.setWindowTitle("Тест исправления таб-режима")
            self.setGeometry(100, 100, 1024, 287)  # Начальная геометрия как в логах
            self._intentional_geometry_change = False
            logging.info(f"[TEST] Начальная геометрия: {self.geometry()}")

        def test_simulated_enable_tab_mode(self):
            """Симуляция исправленной логики enable_tab_mode"""

            logging.info("[TEST] === НАЧАЛО ИСПРАВЛЕННОЙ ЛОГИКИ TAB MODE ===")

            # Сохраняем исходную геометрию
            original_geometry = self.geometry()
            logging.debug(f"[TEST] saved original geometry: {original_geometry}")

            # Вычисляем размеры таб-режима
            tab_window_width = 1024
            tab_window_height = 45  # Как в логе: _calculate_tab_mode_height возвращает 45

            logging.info(f"[TEST] [TAB_MODE_HEIGHT] Tab height calculated: {tab_window_height}px")

            # --- НОВЫЙ ПОРЯДОК: сначала устанавливаем intentional_geometry_change ---
            logging.debug("[TEST] setting _intentional_geometry_change = True")
            self._intentional_geometry_change = True

            # --- Симуляция изменения флагов (apply_mouse_invisible_mode) ---
            logging.debug("[TEST] Симуляция apply_mouse_invisible_mode вызова")

            # В оригинальном коде здесь бы менялись флаги через apply_window_flags_and_show
            # После возврата установлен флаг topmost (_is_win_topmost = True)

            logging.debug("[TEST] flags после apply_mouse_invisible_mode - симуляция завершена")

            # --- ТЕПЕРЬ устанавливаем геометрию ПОСЛЕ изменения флагов ---
            new_geometry = QRect(0, 0, tab_window_width, tab_window_height)
            logging.debug(f"[TEST] setting new geometry: {new_geometry}")

            geom_before_set = self.geometry()
            logging.debug(f"[TEST] geometry before setGeometry(): {geom_before_set}")

            # Применяем геометрию
            self.setGeometry(new_geometry)

            geom_after_set = self.geometry()
            logging.debug(f"[TEST] geometry after setGeometry(): {geom_after_set}")

            logging.info(f"[TEST] Tab mode geometry set: {tab_window_width}x{tab_window_height}")

            # Проверяем результат
            if geom_after_set.height() != tab_window_height:
                logging.warning(f"[TEST] PROBLEM - Expected height {tab_window_height}, got {geom_after_set.height()}")
            else:
                logging.info(f"[TEST] SUCCESS - Correct height {tab_window_height}")

            # Симуляция show()
            self.show()
            geom_after_show = self.geometry()
            logging.debug(f"[TEST] geometry after show(): {geom_after_show}")

            final_geometry = self.geometry()
            logging.debug(f"[TEST] final geometry: {final_geometry}")

            if final_geometry.height() != tab_window_height:
                logging.warning(f"[TEST] WARNING - Height still wrong. Expected: {tab_window_height}, Got: {final_geometry.height()}")
                logging.info("[TEST] Симуляция _force_tab_geometry через QTimer")
                QTimer.singleShot(10, lambda: self.force_tab_geometry_simulated(tab_window_width, tab_window_height))
            else:
                logging.info("[TEST] SUCCESS - Tab mode geometry applied correctly")

            # Сбрасываем флаг
            logging.debug("[TEST] setting _intentional_geometry_change = False")
            self._intentional_geometry_change = False

            logging.info("[TEST] === КОНЕЦ ИСПРАВЛЕННОЙ ЛОГИКИ TAB MODE ===")

        def force_tab_geometry_simulated(self, width: int, height: int):
            """Симуляция _force_tab_geometry"""
            logging.debug("[TEST] force_tab_geometry called")
            current_geom = self.geometry()
            logging.debug(f"[TEST] geometry before force: {current_geom}")

            if current_geom.width() != width or current_geom.height() != height:
                new_geom = QRect(current_geom.x(), current_geom.y(), width, height)
                self.setGeometry(new_geom)
                self.repaint()

                forced_geom = self.geometry()
                logging.debug(f"[TEST] geometry after force: {forced_geom}")

                if forced_geom.height() == height:
                    logging.info(f"[TEST] force_tab_geometry SUCCESS: {forced_geom}")
                else:
                    logging.error(f"[TEST] force_tab_geometry FAILED: still {forced_geom.height()}px")

    def main():
        app = QApplication(sys.argv)

        window = TestMainWindow()
        window.show()

        # Запускаем тест через таймер для гарантии инициализации
        QTimer.singleShot(1000, window.test_simulated_enable_tab_mode)

        # Завершаем тест через 3 секунды
        QTimer.singleShot(3000, app.quit)

        sys.exit(app.exec())

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"Не удалось импортировать PySide6: {e}")
    print("Тест не будет выполнен, но можно просмотреть логику исправлений в коде выше")
    sys.exit(1)