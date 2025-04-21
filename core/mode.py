from PySide6.QtCore import QTimer

MIN_MODE = "min"
MIDDLE_MODE = "middle"
MAX_MODE = "max"


class ModeManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_mode = MIDDLE_MODE

    def change_mode(self, mode):
        """Инициирует смену режима отображения."""
        print(f"[MODE] Attempting to change mode to: {mode}")
        if self.current_mode == mode:
            print("[MODE] Mode is already set.")
            return

        # Сбрасываем индекс фокуса хоткея ДО перестройки UI
        old_cursor_index = self.main_window.hotkey_cursor_index
        self.main_window.hotkey_cursor_index = -1
        # Запрашиваем перерисовку для старого индекса, чтобы убрать рамку
        if (
            self.main_window.right_list_widget
            and self.main_window.right_list_widget.isVisible()
            and old_cursor_index >= 0
        ):
            # Вызываем обновление через QTimer, чтобы оно произошло после текущего события
            QTimer.singleShot(
                0,
                lambda idx=old_cursor_index: self.main_window._update_hotkey_highlight(
                    idx
                ),
            )

        # Вызываем функцию смены режима, которая перестраивает UI
        self.main_window.mode = mode
        self.current_mode = mode
        from mode_manager import change_mode as change_ui_mode

        change_ui_mode(self.main_window, mode)

        # Восстанавливаем фокус хоткея после небольшой задержки
        QTimer.singleShot(150, self._reset_hotkey_cursor_after_mode_change)

    def _reset_hotkey_cursor_after_mode_change(self):
        """Восстанавливает фокус хоткея после смены режима."""
        print("[MODE] Resetting hotkey cursor after mode change.")
        # Проверяем, что правая панель существует, видима и режим не минимальный
        if (
            self.main_window.right_list_widget
            and self.main_window.right_list_widget.isVisible()
            and self.current_mode != MIN_MODE
        ):
            count = self.main_window.right_list_widget.count()
            if count > 0:
                self.main_window.hotkey_cursor_index = 0  # Устанавливаем на первый элемент
                self.main_window._calculate_columns()  # Пересчитываем колонки
                self.main_window._update_hotkey_highlight(
                    None
                )  # Запрашиваем отрисовку рамки для нового индекса
            else:
                self.main_window.hotkey_cursor_index = -1  # Список пуст
        else:
            self.main_window.hotkey_cursor_index = -1  # В min режиме или если списка нет
            # Убедимся, что рамка точно убрана (если она была)
            self.main_window._update_hotkey_highlight(None)

    def get_next_mode(self):
        if self.current_mode == MIN_MODE:
            return MIDDLE_MODE
        elif self.current_mode == MIDDLE_MODE:
            return MAX_MODE
        elif self.current_mode == MAX_MODE:
            return MIN_MODE
        return MIDDLE_MODE