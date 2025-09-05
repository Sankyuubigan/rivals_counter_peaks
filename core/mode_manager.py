# File: core/mode_manager.py
import logging

class ModeManager:
    """Управляет текущим режимом окна (упрощенная версия)."""
    def __init__(self, main_window):
        self.main_window = main_window
        # Единственный режим работы - 'middle'
        self.current_mode = "middle"
        logging.info(f"[ModeManager] Initialized. Default mode is '{self.current_mode}'.")