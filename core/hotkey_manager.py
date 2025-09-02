import logging
import threading
from typing import Dict, Callable, Any, Optional
from PySide6.QtCore import QObject, Signal, Slot, QMetaObject, Q_ARG
from core.app_settings_manager import AppSettingsManager
from core.hotkey_config import HOTKEY_ACTIONS_CONFIG, DEFAULT_HOTKEYS
from info.translations import get_text

try:
    from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys
    GLOBAL_HOTKEYS_AVAILABLE = True
except ImportError:
    GLOBAL_HOTKEYS_AVAILABLE = False
    logging.error("Global hotkeys library not found")

class HotkeyManager(QObject):
    """Унифицированный менеджер горячих клавиш"""
    
    hotkey_pressed = Signal(str)  # Сигнал о нажатии хоткея (action_id)
    
    def __init__(self, main_window: QObject, app_settings_manager: AppSettingsManager):
        super().__init__()
        self.main_window = main_window
        self.app_settings_manager = app_settings_manager
        self.bindings = []
        self._is_running = False
        self._lock = threading.Lock()
        self.current_hotkeys = self.app_settings_manager.get_hotkeys()
        
        if GLOBAL_HOTKEYS_AVAILABLE:
            self._setup_hotkeys()
            self._start_listener()
        else:
            logging.warning("Global hotkeys not available")
    
    def _setup_hotkeys(self):
        """Настраивает глобальные хоткеи"""
        # Базовые комбинации для режима TAB
        self.bindings = [
            {
                "hotkey": "tab",
                "on_press_callback": self._on_tab_press,
                "on_release_callback": self._on_tab_release,
                "action_id": "toggle_tab_mode"
            },
            {
                "hotkey": "0",
                "on_press_callback": self._on_zero_press,
                "action_id": "recognize_heroes"
            },
            {
                "hotkey": "right",
                "on_press_callback": lambda: self._emit_action("move_cursor_right"),
                "action_id": "move_cursor_right"
            },
            {
                "hotkey": "left",
                "on_press_callback": lambda: self._emit_action("move_cursor_left"),
                "action_id": "move_cursor_left"
            },
            {
                "hotkey": "up",
                "on_press_callback": lambda: self._emit_action("move_cursor_up"),
                "action_id": "move_cursor_up"
            },
            {
                "hotkey": "down",
                "on_press_callback": lambda: self._emit_action("move_cursor_down"),
                "action_id": "move_cursor_down"
            }
        ]
        
        try:
            register_hotkeys(self.bindings)
            start_checking_hotkeys()
            logging.info("Global hotkeys registered successfully")
        except Exception as e:
            logging.error(f"Error registering hotkeys: {e}")
    
    def _start_listener(self):
        """Запускает поток для проверки хоткеев"""
        def listener_loop():
            while self._is_running:
                # Здесь можно добавить дополнительную логику если нужно
                threading.Event().wait(0.01)
        
        self._listener_thread = threading.Thread(target=listener_loop, daemon=True)
        self._listener_thread.start()
        self._is_running = True
    
    def _on_tab_press(self):
        """Обработка нажатия TAB"""
        with self._lock:
            self.hotkey_pressed.emit("toggle_tab_mode")
    
    def _on_tab_release(self):
        """Обработка отпускания TAB"""
        with self._lock:
            self.hotkey_pressed.emit("toggle_tab_mode")
    
    def _on_zero_press(self):
        """Обработка нажатия 0 (распознавание)"""
        with self._lock:
            self.hotkey_pressed.emit("recognize_heroes")
    
    def _emit_action(self, action_id: str):
        """Эмитирует сигнал о действии"""
        self.hotkey_pressed.emit(action_id)
    
    def get_current_hotkeys(self) -> Dict[str, str]:
        """Возвращает текущие настройки хоткеев"""
        return self.current_hotkeys.copy()
    
    def update_hotkeys(self, new_hotkeys: Dict[str, str]):
        """Обновляет настройки хоткеев"""
        self.current_hotkeys = new_hotkeys.copy()
        # Здесь можно добавить логику перерегистрации хоткеев если нужно
        logging.info("Hotkeys updated")
    
    def reset_to_defaults(self):
        """Сбрасывает настройки к значениям по умолчанию"""
        self.current_hotkeys = DEFAULT_HOTKEYS.copy()
        self.app_settings_manager.set_hotkeys(self.current_hotkeys)
        logging.info("Hotkeys reset to defaults")
    
    def stop(self):
        """Останавливает менеджер хоткеев"""
        self._is_running = False
        
        if GLOBAL_HOTKEYS_AVAILABLE:
            try:
                stop_checking_hotkeys()
                logging.info("Hotkey listener stopped")
            except Exception as e:
                logging.error(f"Error stopping hotkeys: {e}")
        
        if hasattr(self, '_listener_thread') and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)