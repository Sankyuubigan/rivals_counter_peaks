# File: core/mode_manager.py
import logging

class ModeManager:
    """Управляет текущим режимом окна (упрощенная версия)."""
    def __init__(self, main_window):
        self.main_window = main_window
        # Единственный режим работы - 'middle'
        self.current_mode = "middle"
        logging.info(f"[ModeManager] Initialized. Default mode is '{self.current_mode}'.")

    def change_mode(self, new_mode_name: str):
        """Больше не меняет режим, так как он один."""
        if new_mode_name != self.current_mode:
            logging.warning(f"[ModeManager] Attempted to change mode to '{new_mode_name}', but only '{self.current_mode}' is supported. Ignoring.")
        else:
            logging.debug(f"[ModeManager] change_mode called for current mode '{self.current_mode}'. No action taken.")