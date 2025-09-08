# File: core/hotkey_manager.py
import logging
from typing import Dict
from PySide6.QtCore import QObject, Signal, QTimer
try:
    from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys
    GLOBAL_HOTKEYS_AVAILABLE = True
except ImportError:
    GLOBAL_HOTKEYS_AVAILABLE = False
    logging.error("HotkeyManager: 'global_hotkeys' library not found.")
from core.app_settings_manager import AppSettingsManager
import threading
import time

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
        self.tab_press_time = 0
        self.recognition_timer = QTimer()
        self.recognition_timer.setSingleShot(True)
        self.recognition_timer.timeout.connect(self._on_recognition_timer_timeout)
        self.bindings = []
        if GLOBAL_HOTKEYS_AVAILABLE:
            self._setup_and_register_hotkeys()
        else:
            logging.error("Global hotkeys are not available. The application will not respond to hotkeys.")
    def _setup_and_register_hotkeys(self):
        """Настраивает и регистрирует глобальные хоткеи."""
        logging.info("Setting up and registering global hotkeys...")
        
        # Используем простые символы для Numpad-клавиш, т.к. это стандарт для библиотеки global_hotkeys.
        self.bindings = [
            {
                "hotkey": "tab",
                "on_press_callback": self._on_tab_press,
                "on_release_callback": self._on_tab_release
            },
            {
                "hotkey": "/", # Numpad Divide
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
            },
            {
                "hotkey": "0", # Numpad 0
                "on_press_callback": lambda: self._emit_if_tab_pressed("toggle_selection"),
                "on_release_callback": None
            },
            {
                "hotkey": "-", # Numpad Subtract
                "on_press_callback": lambda: self._emit_if_tab_pressed("clear_all"),
                "on_release_callback": None
            },
            {
                "hotkey": "1", # Numpad 1
                "on_press_callback": lambda: self._emit_if_tab_pressed("copy_team"),
                "on_release_callback": None
            },
            {
                "hotkey": "3", # Numpad 3
                "on_press_callback": lambda: self._emit_if_tab_pressed("debug_capture"),
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
            self.tab_pressed = True
            self.tab_press_time = time.time()  # Используем реальное время
            logging.info("[HotkeyManager] TAB pressed")
            # ИЗМЕНЕНО: Сразу отправляем сигнал для показа трей окна
            self.hotkey_triggered.emit("enter_tab_mode")
            # Запускаем QTimer через сигнал в главном потоке
            self.hotkey_triggered.emit("start_recognition_timer")
    def _on_tab_release(self):
        with self._lock:
            self.tab_pressed = False
            logging.info("[HotkeyManager] TAB released")
            # Останавливаем таймер, если Tab был отпущен раньше 100мс
            if self.recognition_timer.isActive():
                self.recognition_timer.stop()
            # Эмитируем сигнал в основной поток GUI
            self.hotkey_triggered.emit("exit_tab_mode")
    def _on_recognition_timer_timeout(self):
        """Вызывается, когда истекает 100мс после нажатия Tab"""
        with self._lock:
            if self.tab_pressed:
                current_time = time.time()
                elapsed = (current_time - self.tab_press_time) * 1000  # в миллисекундах
                logging.info(f"[HotkeyManager] Recognition timer triggered after {elapsed:.1f}ms - emitting recognize_heroes")
                self.hotkey_triggered.emit("recognize_heroes")
    def _emit_if_tab_pressed(self, action_id: str):
        with self._lock:
            if self.tab_pressed:
                logging.info(f"[HotkeyManager] Emitting action: {action_id}")
                self.hotkey_triggered.emit(action_id)
            else:
                logging.debug(f"[HotkeyManager] TAB not pressed, ignoring action: {action_id}")
                # ДОБАВЛЕНИЕ ЛОГИРОВАНИЯ: Для отладки проблемы с распознаванием
                if action_id == "recognize_heroes":
                    logging.warning(f"[HotkeyManager] RECOGNIZE_HEROES TRIGGERED WITHOUT TAB! Tab pressed: {self.tab_pressed}")
    def start_recognition_timer_in_main_thread(self):
        """Запускает таймер в главном потоке"""
        logging.info("[HotkeyManager] Starting recognition timer in main thread")
        self.recognition_timer.start(200)
    def stop(self):
        if not self._is_running:
            return
            
        self._is_running = False
        if self.recognition_timer.isActive():
            self.recognition_timer.stop()
        if GLOBAL_HOTKEYS_AVAILABLE:
            try:
                stop_checking_hotkeys()
                logging.info("Hotkey listener stopped successfully.")
            except Exception as e:
                logging.error(f"Error stopping global hotkeys listener: {e}")