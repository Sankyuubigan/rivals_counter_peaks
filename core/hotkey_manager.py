# File: core/hotkey_manager.py
import logging
from typing import Dict
from PySide6.QtCore import QObject, Signal
from core.app_settings_manager import AppSettingsManager
import threading
import time

class HotkeyManager(QObject):
    hotkey_triggered = Signal(str)
    def __init__(self, app_settings_manager: AppSettingsManager):
        super().__init__()
        self.app_settings_manager = app_settings_manager
        self._is_running = False
        self._lock = threading.Lock()
        self.tab_pressed = False
        self.listener = None
        self._setup_and_register_hotkeys()
        
    def _setup_and_register_hotkeys(self):
        self._setup_pynput_hotkeys()
        
    def _setup_pynput_hotkeys(self):
        try:
            from pynput import keyboard
            hotkeys = self.app_settings_manager.get_hotkeys()
            self.hotkey_combinations = {}
            self.hotkey_combinations[keyboard.Key.tab] = self._on_tab_press
            
            key_mapping = {
                "move_cursor_right": (keyboard.Key.right, "move_cursor_right"),
                "move_cursor_left": (keyboard.Key.left, "move_cursor_left"),
                "move_cursor_up": (keyboard.Key.up, "move_cursor_up"),
                "move_cursor_down": (keyboard.Key.down, "move_cursor_down"),
                "toggle_selection": (keyboard.KeyCode.from_char('2'), "toggle_selection"),
                "copy_team": (keyboard.KeyCode.from_char('1'), "copy_team"),
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
                    if key == keyboard.Key.tab:
                        with self._lock:
                            if not self.tab_pressed:
                                self.tab_pressed = True
                                self.hotkey_triggered.emit("enter_tab_mode")
                    elif key in self.hotkey_combinations:
                        self.hotkey_combinations[key]()
                except AttributeError: pass
                    
            def on_release(key):
                if key == keyboard.Key.tab:
                    with self._lock:
                        self.tab_pressed = False
                        self.hotkey_triggered.emit("exit_tab_mode")
            
            self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.listener.start()
            self._is_running = True
            
        except ImportError:
            logging.error("pynput not available.")
            
    def _on_tab_press(self):
        with self._lock:
            if not self.tab_pressed:
                self.tab_pressed = True
                self.hotkey_triggered.emit("enter_tab_mode")
                
    def _emit_if_tab_pressed(self, action_id: str):
        with self._lock:
            if self.tab_pressed:
                self.hotkey_triggered.emit(action_id)
                
    def stop(self):
        if not self._is_running: return
        self._is_running = False
        if self.listener:
            try: self.listener.stop()
            except Exception: pass
                
    def reregister_hotkeys(self):
        if self._is_running:
            self.stop()
            self._setup_and_register_hotkeys()