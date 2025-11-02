# File: core/hotkey_manager.py
import logging
from typing import Dict
from PySide6.QtCore import QObject, Signal, QTimer
from core.app_settings_manager import AppSettingsManager
import threading
import time

class HotkeyManager(QObject):
    """
    Менеджер горячих клавиш на базе pynput.
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
        self.listener = None
        self._setup_and_register_hotkeys()
        
    def _setup_and_register_hotkeys(self):
        """Настраивает и регистрирует глобальные хоткеи."""
        logging.info("Setting up and registering global hotkeys...")
        self._setup_pynput_hotkeys()
        
    def _setup_pynput_hotkeys(self):
        """Настраивает хоткеи с использованием pynput"""
        try:
            from pynput import keyboard
            
            # Получаем хоткеи из настроек
            hotkeys = self.app_settings_manager.get_hotkeys()
            
            # Создаем словарь комбинаций клавиш
            self.hotkey_combinations = {}
            
            # Tab
            self.hotkey_combinations[keyboard.Key.tab] = self._on_tab_press
            
            # Остальные хоткеи
            key_mapping = {
                "recognize_heroes": (keyboard.KeyCode.from_char('/'), "recognize_heroes"),
                "move_cursor_right": (keyboard.Key.right, "move_cursor_right"),
                "move_cursor_left": (keyboard.Key.left, "move_cursor_left"),
                "move_cursor_up": (keyboard.Key.up, "move_cursor_up"),
                "move_cursor_down": (keyboard.Key.down, "move_cursor_down"),
                "toggle_selection": (keyboard.KeyCode.from_char('2'), "toggle_selection"),
                "copy_team": (keyboard.KeyCode.from_char('1'), "copy_team"),
                "debug_capture": (keyboard.KeyCode.from_char('3'), "debug_capture"),
                "cycle_map_forward": (keyboard.KeyCode.from_char('8'), "cycle_map_forward"),
                "cycle_map_backward": (keyboard.KeyCode.from_char('9'), "cycle_map_backward"),
                "reset_map": (keyboard.KeyCode.from_char('0'), "reset_map"),
                "clear_all": (keyboard.Key.delete, "clear_all"),
            }
            
            for action, (key, action_id) in key_mapping.items():
                hotkey_str = hotkeys.get(action, f"tab+{action_id.split('_')[-1]}")
                if "tab+" in hotkey_str:
                    self.hotkey_combinations[key] = lambda a=action_id: self._emit_if_tab_pressed(a)
            
            def on_press(key):
                try:
                    # Проверяем нажатие Tab
                    if key == keyboard.Key.tab:
                        with self._lock:
                            if not self.tab_pressed:
                                self.tab_pressed = True
                                self.tab_press_time = time.time()
                                self.hotkey_triggered.emit("enter_tab_mode")
                                self.hotkey_triggered.emit("start_recognition_timer")
                    # Проверяем другие клавиши
                    elif key in self.hotkey_combinations:
                        self.hotkey_combinations[key]()
                except AttributeError:
                    pass
                    
            def on_release(key):
                if key == keyboard.Key.tab:
                    with self._lock:
                        self.tab_pressed = False
                        if self.recognition_timer.isActive():
                            self.recognition_timer.stop()
                        self.hotkey_triggered.emit("exit_tab_mode")
            
            # Регистрируем слушателя
            self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.listener.start()
            self._is_running = True
            logging.info("Hotkey listener started with pynput")
            
        except ImportError:
            logging.error("pynput not available. Please install it with: pip install pynput")
        except Exception as e:
            logging.error(f"Failed to setup hotkeys: {e}", exc_info=True)
            
    def _on_tab_press(self):
        with self._lock:
            if not self.tab_pressed:
                self.tab_pressed = True
                self.tab_press_time = time.time()
                logging.info("[HotkeyManager] TAB pressed")
                self.hotkey_triggered.emit("enter_tab_mode")
                self.hotkey_triggered.emit("start_recognition_timer")
                
    def _on_tab_release(self):
        with self._lock:
            self.tab_pressed = False
            logging.info("[HotkeyManager] TAB released")
            if self.recognition_timer.isActive():
                self.recognition_timer.stop()
            self.hotkey_triggered.emit("exit_tab_mode")
            
    def _on_recognition_timer_timeout(self):
        """Вызывается, когда истекает 200мс после нажатия Tab"""
        with self._lock:
            if self.tab_pressed:
                current_time = time.time()
                elapsed = (current_time - self.tab_press_time) * 1000
                logging.info(f"[HotkeyManager] Recognition timer triggered after {elapsed:.1f}ms - emitting recognize_heroes")
                self.hotkey_triggered.emit("recognize_heroes")
                
    def _emit_if_tab_pressed(self, action_id: str):
        with self._lock:
            if self.tab_pressed:
                logging.info(f"[HotkeyManager] Emitting action: {action_id}")
                self.hotkey_triggered.emit(action_id)
            else:
                logging.debug(f"[HotkeyManager] TAB not pressed, ignoring action: {action_id}")
                
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
        
        # Останавливаем слушатель
        if self.listener:
            try:
                self.listener.stop()
                logging.info("Hotkey listener stopped.")
            except Exception as e:
                logging.error(f"Error stopping hotkey listener: {e}")
                
    def reregister_hotkeys(self):
        """Перерегистрирует хоткеи после изменения в настройках"""
        if self._is_running:
            self.stop()
            self._setup_and_register_hotkeys()
            logging.info("Hotkeys re-registered after settings change")