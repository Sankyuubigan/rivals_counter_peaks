# File: core/mode_manager.py
import logging

# --- Константы ---
PANEL_MIN_WIDTHS = {
    'max': {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300},
    'min': {'left': 0, 'right': 0}
}
MODE_DEFAULT_WINDOW_SIZES = {
    'max': {'width': 1100, 'height': 800},
    'middle': {'width': 950, 'height': 600},
    # Увеличена ширина для min режима, чтобы иконки влезали
    'min': {'width': 1400, 'height': 0} # Height будет рассчитана автоматически
}
# --- ---

class ModeManager:
    """Управляет текущим режимом окна."""
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_mode = "middle"
        # Позиции теперь хранятся и управляются в MainWindow
        # self.mode_positions = { ... } # Убрано

    def change_mode(self, new_mode_name: str):
        """Устанавливает новый режим."""
        # Проверка корректности режима
        if new_mode_name not in MODE_DEFAULT_WINDOW_SIZES: # Проверяем по ключам размеров
            logging.error(f"[ERROR][ModeManager] Попытка установить неизвестный режим: {new_mode_name}")
            return
        # Если режим не изменился, ничего не делаем
        if self.current_mode == new_mode_name:
            return

        logging.info(f"[MODE][ModeManager] Установка нового режима: {new_mode_name}")
        self.current_mode = new_mode_name
        # Обновляем атрибут mode в главном окне (если он есть)
        if hasattr(self.main_window, 'mode'):
             self.main_window.mode = new_mode_name
        else:
             logging.warning("[WARN][ModeManager] Атрибут 'mode' не найден в main_window при смене режима.")

        # Логика сохранения/восстановления позиции ПЕРЕНЕСЕНА в MainWindow.change_mode

    # Метод очистки layout больше не нужен здесь, если он не используется
    # def clear_layout_recursive(self, layout): ...
