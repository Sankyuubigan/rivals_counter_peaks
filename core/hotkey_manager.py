# File: core/hotkey_manager.py
import logging
from typing import Dict
from PySide6.QtCore import QObject, Signal

try:
    from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys
    GLOBAL_HOTKEYS_AVAILABLE = True
except ImportError:
    GLOBAL_HOTKEYS_AVAILABLE = False
    logging.error("HotkeyManager: 'global_hotkeys' library not found.")

from core.app_settings_manager import AppSettingsManager
import threading

class HotkeyManager(QObject):
    """
    Унифицированный менеджер горячих клавиш на базе 'global_hotkeys'.
    Использует сигнал Qt для безопасной передачи событий в основной поток.
    """
    hotkey_triggered = Signal(str)

    def __init__(self, app_settings_manager: AppSettingsManager):
        super().__init__()
        self.app_settings_manager = app_settings_manager
        self._is_running = False
        self._lock = threading.Lock()
        self.tab_pressed = False
        self.bindings = []

        if GLOBAL_HOTKEYS_AVAILABLE:
            self._setup_and_register_hotkeys()
        else:
            logging.error("Global hotkeys are not available. The application will not respond to hotkeys.")

    def _setup_and_register_hotkeys(self):
        """Настраивает и регистрирует глобальные хоткеи."""
        logging.info("Setting up and registering global hotkeys...")
        
        self.bindings = [
            {
                "hotkey": "tab",
                "on_press_callback": self._on_tab_press,
                "on_release_callback": self._on_tab_release
            },
            {
                "hotkey": "0",
                "on_press_callback": lambda: self._emit_if_tab_pressed("recognize_heroes"),
                "on_release_callback": None
            },
            {
                "hotkey": "right",
                "on_press_callback": lambda: self._emit_if_tab_pressed("move_cursor_right"),
                "on_release_callback": None
            },
            {
                "hotkey": "left",
                "on_press_callback": lambda: self._emit_if_tab_pressed("move_cursor_left"),
                "on_release_callback": None
            },
            {
                "hotkey": "up",
                "on_press_callback": lambda: self._emit_if_tab_pressed("move_cursor_up"),
                "on_release_callback": None
            },
            {
                "hotkey": "down",
                "on_press_callback": lambda: self._emit_if_tab_pressed("move_cursor_down"),
                "on_release_callback": None
            }
        ]
        
        try:
            register_hotkeys(self.bindings)
            start_checking_hotkeys()
            self._is_running = True
            logging.info("Global hotkeys registered and listener started successfully.")
        except Exception as e:
            logging.error(f"Failed to register global hotkeys: {e}", exc_info=True)

    def _on_tab_press(self):
        with self._lock:
            if not self.tab_pressed:
                self.tab_pressed = True
                logging.debug("Tab pressed, entering tab mode. Emitting signal...")
                self.hotkey_triggered.emit("enter_tab_mode")

    def _on_tab_release(self):
        with self._lock:
            if self.tab_pressed:
                self.tab_pressed = False
                logging.debug("Tab released, exiting tab mode. Emitting signal...")
                self.hotkey_triggered.emit("exit_tab_mode")

    def _emit_if_tab_pressed(self, action_id: str):
        with self._lock:
            if self.tab_pressed:
                logging.debug(f"Hotkey '{action_id}' triggered while tab is pressed. Emitting signal...")
                self.hotkey_triggered.emit(action_id)

    def stop(self):
        if not self._is_running:
            return
            
        self._is_running = False
        if GLOBAL_HOTKEYS_AVAILABLE:
            try:
                stop_checking_hotkeys()
                logging.info("Hotkey listener stopped successfully.")
            except Exception as e:
                logging.error(f"Error stopping global hotkeys listener: {e}")