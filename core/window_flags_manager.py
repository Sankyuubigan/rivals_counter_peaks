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
        self._is_applying_flags_operation = False
        self._last_applied_target_flags = self.mw.windowFlags()
        logging.debug(f"[WFM Init] _last_applied_target_flags инициализированы как: {self._last_applied_target_flags:#x}")

    def _calculate_target_flags(self) -> Qt.WindowFlags:
        is_min_mode = (self.mw.mode == "min")

        if is_min_mode:
            base_flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        else:
            base_flags = Qt.WindowType.Window | Qt.WindowType.WindowSystemMenuHint | \
                         Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint
            if self.mw.mode == 'max' or self.mw.mode == 'middle':
                 base_flags |= Qt.WindowType.WindowMaximizeButtonHint

        topmost_flag_to_add = Qt.WindowType.WindowStaysOnTopHint if self.mw._is_win_topmost else Qt.WindowType(0)
        transparent_flag_to_add = Qt.WindowType.WindowTransparentForInput if getattr(self.mw, 'mouse_invisible_mode_enabled', False) else Qt.WindowType(0)

        return base_flags | topmost_flag_to_add | transparent_flag_to_add

    def apply_window_flags_and_show(self, new_target_flags: Qt.WindowFlags, reason: str):
        current_actual_flags = self.mw.windowFlags()
        # ИЗМЕНЕНИЕ: Если флаги уже такие, как надо, И окно видимо (если не свернуто), И НЕ в процессе другой операции - выходим.
        # Это должно предотвратить ненужные операции, если состояние уже корректно.
        if not self._is_applying_flags_operation and \
           current_actual_flags == new_target_flags and \
           (self.mw.isVisible() or self.mw.isMinimized()): # Если свернуто, isVisible()=False, но это ОК
            logging.debug(f"    [ApplyFlags] Пропущено: флаги уже соответствуют и окно в ожидаемом состоянии видимости/свернутости. Причина: {reason}")
            self._last_applied_target_flags = new_target_flags
            return

        if self._is_applying_flags_operation:
            logging.debug(f"    [ApplyFlags] Пропущено из-за флага _is_applying_flags_operation. Причина: {reason}, Целевые: {new_target_flags:#x}")
            return

        self._is_applying_flags_operation = True
        self.mw.setUpdatesEnabled(False) # Отключаем обновления UI
        logging.debug(f"    [ApplyFlags] Вход. Причина: {reason}. Целевые: {new_target_flags:#x}. setUpdatesEnabled(False).")
        t_start_apply = time.perf_counter()

        try:
            flags_need_change = (current_actual_flags != new_target_flags)
            logging.debug(f"    [ApplyFlags] Текущие фактические: {current_actual_flags:#x}, Новые целевые: {new_target_flags:#x}, Требуется изменение: {flags_need_change}. Причина: {reason}")

            geom_before_operation = self.mw.geometry()
            visible_before_operation = self.mw.isVisible()
            minimized_before_operation = self.mw.isMinimized()
            logging.debug(f"        Состояние до: Видимо={visible_before_operation}, Свернуто={minimized_before_operation}, Геометрия={geom_before_operation}, Флаги={current_actual_flags:#x}")

            if flags_need_change:
                # Если окно видимо и не свернуто, и меняются структурные флаги, его нужно скрыть
                # (Qt может сам скрыть, но лучше явно)
                significant_flags_mask = (
                    Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint |
                    Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint |
                    Qt.WindowType.WindowCloseButtonHint
                )
                structural_change = (current_actual_flags & significant_flags_mask) != (new_target_flags & significant_flags_mask)

                if structural_change and visible_before_operation and not minimized_before_operation:
                    logging.debug(f"    [ApplyFlags] Скрытие окна перед setWindowFlags (структурные изменения). Причина: {reason}")
                    self.mw.hide()

                self.mw.setWindowFlags(new_target_flags)
                self._last_applied_target_flags = new_target_flags # Важно обновить это ЗДЕСЬ

                current_actual_flags_after_set = self.mw.windowFlags()
                logging.debug(f"    [ApplyFlags] После setWindowFlags. Целевые были: {new_target_flags:#x}, Фактические стали: {current_actual_flags_after_set:#x}. Видимо: {self.mw.isVisible()}, Геометрия: {self.mw.geometry()}")
                if current_actual_flags_after_set != new_target_flags:
                    logging.warning(f"    [ApplyFlags] ВНИМАНИЕ: Фактические флаги ({current_actual_flags_after_set:#x}) отличаются от целевых ({new_target_flags:#x}) после setWindowFlags!")

            # Показываем окно, если оно должно быть видимым и не является таковым
            should_be_visible_after_ops = not minimized_before_operation
            if should_be_visible_after_ops and not self.mw.isVisible():
                logging.debug(f"    [ApplyFlags] Показ окна после операций. Причина: {reason}")
                self.mw.show() # Qt сама должна решить, нужно ли showNormal, showMaximized и т.д.
                # Важно: после show() геометрия может снова измениться
                logging.debug(f"        После show(): Видимо={self.mw.isVisible()}, Геометрия={self.mw.geometry()}")


            # Восстанавливаем геометрию, если она изменилась и окно видимо
            # ИСКЛЮЧЕНИЕ: не восстанавливаем, если была намеренное изменение геометрии (например, в таб-режиме)
            current_geom_after_ops = self.mw.geometry()
            intentional_change = getattr(self.mw, '_intentional_geometry_change', False)
            if (not intentional_change and
                self.mw.isVisible() and geom_before_operation.isValid() and current_geom_after_ops != geom_before_operation):
                logging.debug(f"    [ApplyFlags] Восстановление геометрии с {current_geom_after_ops} на {geom_before_operation}. Причина: {reason}")
                self.mw.setGeometry(geom_before_operation)
                logging.debug(f"        Геометрия после восстановления: {self.mw.geometry()}")
            elif intentional_change:
                logging.debug(f"    [ApplyFlags] Пропущено восстановление геометрии - было намеренное изменение. Причина: {reason}")

        finally:
            self.mw.setUpdatesEnabled(True) # Включаем обновления UI
            self._is_applying_flags_operation = False
            logging.debug(f"    [ApplyFlags] Выход. Причина: {reason}. setUpdatesEnabled(True). Общее время: {(time.perf_counter() - t_start_apply)*1000:.2f} ms. Конечное состояние: Видимо={self.mw.isVisible()}, Свернуто={self.mw.isMinimized()}, Флаги={self.mw.windowFlags():#x}, Геометрия={self.mw.geometry()}")


    def apply_mouse_invisible_mode(self, reason: str):
        logging.debug(f"--> apply_mouse_invisible_mode вызвана. Причина: '{reason}'")
        t_start_apply_mouse = time.perf_counter()
        target_flags = self._calculate_target_flags()
        self.apply_window_flags_and_show(target_flags, reason)
        logging.debug(f"<-- apply_mouse_invisible_mode завершена. Причина: '{reason}'. Время: {(time.perf_counter() - t_start_apply_mouse)*1000:.2f} ms")


    def force_taskbar_update_internal(self, reason_suffix="unknown"):
        caller_reason = f"force_taskbar_update_{reason_suffix}"
        logging.debug(f"    [TaskbarUpdate] START force_taskbar_update_internal. Причина вызова: {caller_reason}")
        t_start_force = time.perf_counter()

        if sys.platform == 'win32':
            target_flags_for_taskbar_update = self._calculate_target_flags()
            current_actual_flags_on_window = self.mw.windowFlags()
            # Сравниваем с _last_applied_target_flags, чтобы избежать ненужных вызовов, если мы только что их установили.
            # Но также проверяем current_actual_flags_on_window, если они были изменены извне.
            if self._last_applied_target_flags != target_flags_for_taskbar_update or \
               current_actual_flags_on_window != target_flags_for_taskbar_update:
                logging.debug(f"    [TaskbarUpdate] Флаги требуют обновления для панели задач. Целевые: {target_flags_for_taskbar_update:#x}, Текущие: {current_actual_flags_on_window:#x}, Последние примененные: {self._last_applied_target_flags:#x}")
                self.apply_window_flags_and_show(target_flags_for_taskbar_update, f"taskbar_update_for_{reason_suffix}")
            else:
                logging.debug("    [TaskbarUpdate] Флаги для панели задач уже корректны. Пропуск.")
                # Дополнительно, если окно видимо, но не активно, попробуем активировать
                if self.mw.isVisible() and not self.mw.isActiveWindow() and not self.mw.isMinimized():
                    logging.debug("    [TaskbarUpdate] Окно видимо, но неактивно. Попытка активации.")
                    QTimer.singleShot(0, self.mw.activateWindow)
                    QTimer.singleShot(10, self.mw.raise_)
        else:
            logging.debug(f"    [TaskbarUpdate] Пропущено на платформе не Windows. Причина вызова: {caller_reason}")

        logging.debug(f"    [TaskbarUpdate] END force_taskbar_update_internal. Время: {(time.perf_counter() - t_start_force)*1000:.2f} ms")
