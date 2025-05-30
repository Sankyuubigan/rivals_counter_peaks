# File: core/window_flags_manager.py
import sys
import time
import logging
from typing import TYPE_CHECKING 
from PySide6.QtCore import Qt, QTimer, QPoint, QRect
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from main_window import MainWindow

class WindowFlagsManager:
    def __init__(self, main_window: 'MainWindow'):
        self.mw = main_window
        self._is_applying_flags_operation = False # Флаг, показывающий, что идет операция смены флагов
        self._last_applied_flags = self.mw.windowFlags() # Последние флаги, которые мы пытались установить

    def _calculate_target_flags(self) -> Qt.WindowFlags:
        """Рассчитывает целевые флаги окна на основе текущего режима и состояния."""
        is_min_mode = (self.mw.mode == "min")
        
        # Базовые флаги в зависимости от режима
        if is_min_mode:
            # Для компактного режима: окно без рамки
            base_flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        else:
            # Для обычных режимов: стандартное окно с системным меню и кнопками
            base_flags = Qt.WindowType.Window | Qt.WindowType.WindowSystemMenuHint | \
                         Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint
            # Кнопку Maximize можно добавить, если она нужна для средних/больших режимов
            if self.mw.mode == 'max' or self.mw.mode == 'middle':
                 base_flags |= Qt.WindowType.WindowMaximizeButtonHint


        # Флаг "Поверх всех окон"
        topmost_flag_to_add = Qt.WindowType.WindowStaysOnTopHint if self.mw._is_win_topmost else Qt.WindowType(0)
        
        # Флаг "Прозрачность для мыши"
        transparent_flag_to_add = Qt.WindowType.WindowTransparentForInput if getattr(self.mw, 'mouse_invisible_mode_enabled', False) else Qt.WindowType(0)
            
        return base_flags | topmost_flag_to_add | transparent_flag_to_add

    def apply_window_flags_and_show(self, new_flags: Qt.WindowFlags, reason: str):
        """
        Применяет новые флаги к окну и убеждается, что оно отображается корректно.
        Эта функция должна быть единственной точкой изменения флагов окна.
        """
        if self._is_applying_flags_operation:
            logging.debug(f"    [ApplyFlags] Пропущено из-за флага _is_applying_flags_operation. Причина: {reason}")
            return
        
        self._is_applying_flags_operation = True
        logging.debug(f"    [ApplyFlags] Вход. Причина: {reason}. _is_applying_flags_operation = True.")
        t_start_apply = time.perf_counter()

        try:
            current_actual_flags = self.mw.windowFlags()
            flags_need_change = (current_actual_flags != new_flags)
            logging.debug(f"    [ApplyFlags] Текущие флаги: {current_actual_flags:#x}, Новые целевые: {new_flags:#x}, Требуется изменение: {flags_need_change}. Причина: {reason}")

            # Запоминаем состояние окна ДО изменения флагов
            was_visible_before_operation = self.mw.isVisible()
            was_minimized_before_operation = self.mw.isMinimized()
            geom_before_operation = self.mw.geometry() # Сохраняем полную геометрию
            
            logging.debug(f"        Состояние до изменения флагов: Видимо={was_visible_before_operation}, Свернуто={was_minimized_before_operation}, Геометрия={geom_before_operation}")

            if flags_need_change:
                logging.debug(f"    [ApplyFlags] Применение новых флагов. Текущая геометрия: {self.mw.geometry()}")
                self.mw.setWindowFlags(new_flags)
                self._last_applied_flags = new_flags 
                logging.debug(f"    [ApplyFlags] После setWindowFlags. Новые фактические флаги: {self.mw.windowFlags():#x}. Видимо: {self.mw.isVisible()}, Геометрия: {self.mw.geometry()}")

            # Логика показа окна и восстановления геометрии
            if not self.mw.isMinimized(): # Если окно не свернуто
                if not self.mw.isVisible(): # И при этом невидимо (setWindowFlags могло скрыть)
                    logging.debug(f"    [ApplyFlags] Окно невидимо (и не свернуто). Вызов show(). Причина: {reason}")
                    t_show_start = time.perf_counter()
                    self.mw.show()
                    # После show() окно может появиться в непредсказуемом месте/размере
                    logging.debug(f"        После show(): Видимо={self.mw.isVisible()}, Активно={self.mw.isActiveWindow()}. Время: {(time.perf_counter() - t_show_start)*1000:.2f} ms. Геометрия: {self.mw.geometry()}")
                else: # Окно уже было видимо или стало видимым после setWindowFlags
                    logging.debug(f"    [ApplyFlags] Окно уже видимо или стало видимым. Явный show() не требуется. Причина: {reason}. Геометрия: {self.mw.geometry()}")

                # Восстанавливаем геометрию, если окно видимо и геометрия изменилась ИЛИ была валидна до
                # Это особенно важно, если setWindowFlags или show() сбросили позицию/размер
                # Проверяем, что окно сейчас видимо, чтобы не пытаться менять геометрию невидимого окна
                current_geom_after_ops = self.mw.geometry()
                if self.mw.isVisible() and geom_before_operation.isValid() and \
                   (current_geom_after_ops != geom_before_operation or not current_geom_after_ops.isValid()):
                    logging.debug(f"    [ApplyFlags] Восстановление геометрии с {current_geom_after_ops} на {geom_before_operation}. Причина: {reason}")
                    self.mw.setGeometry(geom_before_operation)
                    logging.debug(f"        Геометрия после восстановления: {self.mw.geometry()}")

                # Установка иконки, если окно видимо (может слететь после setWindowFlags/show)
                if self.mw.isVisible():
                    current_win_icon = self.mw.windowIcon()
                    if current_win_icon.isNull():
                        self.mw._set_application_icon() # Используем внутренний метод MainWindow

            elif self.mw.isMinimized(): # Если окно было свернуто или свернулось
                 logging.debug(f"    [ApplyFlags] Окно свернуто. Явный show() или восстановление геометрии не производятся. Причина: {reason}")
            
            # Финальная проверка видимости, если не свернуто
            if not self.mw.isMinimized() and not self.mw.isVisible():
                logging.warning(f"    [ApplyFlags] ФИНАЛЬНАЯ ПРОВЕРКА: Окно не свернуто, но все еще невидимо! Принудительный show. Флаги: {self.mw.windowFlags():#x}. Причина: {reason}")
                self.mw.show()
                if self.mw.isVisible() and geom_before_operation.isValid() and self.mw.geometry() != geom_before_operation:
                     logging.warning(f"    [ApplyFlags] ФИНАЛЬНАЯ ПРОВЕРКА: Восстановление геометрии снова на {geom_before_operation}")
                     self.mw.setGeometry(geom_before_operation)
                if not self.mw.isVisible():
                     logging.error(f"    [ApplyFlags] ФИНАЛЬНАЯ ПРОВЕРКА НЕУДАЧА: Окно ВСЕ ЕЩЕ НЕ ВИДИМО после принудительного show! Флаги: {self.mw.windowFlags():#x} Причина: {reason}")
        
        finally:
            self._is_applying_flags_operation = False
            logging.debug(f"    [ApplyFlags] Выход. Причина: {reason}. _is_applying_flags_operation = False. Общее время: {(time.perf_counter() - t_start_apply)*1000:.2f} ms. Конечное состояние: Видимо={self.mw.isVisible()}, Свернуто={self.mw.isMinimized()}, Флаги={self.mw.windowFlags():#x}, Геометрия={self.mw.geometry()}")


    def apply_mouse_invisible_mode(self, reason: str):
        """Применяет флаги, связанные с режимом "прозрачности для мыши" и другими состояниями."""
        logging.debug(f"--> apply_mouse_invisible_mode вызвана. Причина: '{reason}'")
        t_start_apply_mouse = time.perf_counter()
        target_flags = self._calculate_target_flags()
        self.apply_window_flags_and_show(target_flags, reason)
        logging.debug(f"<-- apply_mouse_invisible_mode завершена. Причина: '{reason}'. Время: {(time.perf_counter() - t_start_apply_mouse)*1000:.2f} ms")


    def force_taskbar_update_internal(self, reason_suffix="unknown"):
        """
        "Освежает" состояние окна для панели задач Windows, если флаги могли вызвать проблемы с отображением.
        Теперь просто вызывает apply_window_flags_and_show с текущими целевыми флагами.
        """
        caller_reason = f"force_taskbar_update_{reason_suffix}"
        logging.debug(f"    [TaskbarUpdate] START force_taskbar_update_internal. Причина вызова: {caller_reason}")
        t_start_force = time.perf_counter()

        if sys.platform == 'win32':
            target_flags = self._calculate_target_flags() # Пересчитываем актуальные целевые флаги
            logging.debug(f"        Обновление панели задач: Вызов apply_window_flags_and_show с целевыми флагами {target_flags:#x}")
            self.apply_window_flags_and_show(target_flags, f"taskbar_update_for_{reason_suffix}")
        else:
            logging.debug(f"    [TaskbarUpdate] Пропущено на платформе не Windows. Причина вызова: {caller_reason}")
        
        logging.debug(f"    [TaskbarUpdate] END force_taskbar_update_internal. Время: {(time.perf_counter() - t_start_force)*1000:.2f} ms")