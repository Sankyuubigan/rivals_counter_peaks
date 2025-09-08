import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional
from core.app_settings_keys import *
# Значения по умолчанию
DEFAULT_THEME = "light"
DEFAULT_LANGUAGE = "ru_RU"
DEFAULT_HOTKEYS = {
    "move_cursor_up": "tab+up",
    "move_cursor_down": "tab+down",
    "move_cursor_left": "tab+left",
    "move_cursor_right": "tab+right",
    "toggle_selection": "tab+num_0",
    "recognize_heroes": "tab+num_divide",
    "clear_all": "tab+num_subtract",
    "copy_team": "tab+num_1",
    "debug_capture": "tab+num_3",
}
DEFAULT_SAVE_SCREENSHOT = False
DEFAULT_SCREENSHOT_PATH = ""
# Новое значение по умолчанию для минимального количества распознанных героев
DEFAULT_MIN_RECOGNIZED_HEROES = 0
# ИЗМЕНЕНО: Высота по умолчанию для окна трея сделана более адекватной
DEFAULT_TAB_GEOMETRY = {"x": 100, "y": 100, "width": 800, "height": 80}
class AppSettingsManager:
    """Расширенный менеджер настроек приложения"""
    
    def __init__(self):
        self.settings_file_path = self._get_settings_file_path()
        self.settings: Dict[str, Any] = self._load_settings()
        self._ensure_defaults()
    
    def _get_settings_file_path(self) -> Path:
        """Определяет путь к файлу настроек"""
        if sys.platform == "win32":
            base_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base_dir = Path.home() / ".config"
        
        app_dir = base_dir / "RivalsCounterPeaks"
        app_dir.mkdir(parents=True, exist_ok=True)
        
        return app_dir / "app_settings.json"
    
    def _load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла"""
        if not self.settings_file_path.exists():
            return {}
        
        try:
            with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading settings: {e}")
            return {}
    
    def _ensure_defaults(self):
        """Проверяет и устанавливает значения по умолчанию"""
        defaults = {
            THEME_KEY: DEFAULT_THEME,
            LANGUAGE_KEY: DEFAULT_LANGUAGE,
            HOTKEYS_KEY: DEFAULT_HOTKEYS,
            SAVE_SCREENSHOT_LESS_THAN_6_KEY: DEFAULT_SAVE_SCREENSHOT,
            SCREENSHOT_SAVE_PATH_KEY: DEFAULT_SCREENSHOT_PATH,
            MIN_RECOGNIZED_HEROES_KEY: DEFAULT_MIN_RECOGNIZED_HEROES,
            TAB_WINDOW_GEOMETRY_KEY: DEFAULT_TAB_GEOMETRY
        }
        
        changed = False
        
        for key, default_value in defaults.items():
            if key not in self.settings:
                self.settings[key] = default_value
                changed = True
        
        # Особая проверка для хоткеев
        if HOTKEYS_KEY in self.settings:
            current_hotkeys = self.settings[HOTKEYS_KEY]
            if not isinstance(current_hotkeys, dict):
                self.settings[HOTKEYS_KEY] = DEFAULT_HOTKEYS.copy()
                changed = True
            else:
                # Проверяем наличие всех действий
                for action in DEFAULT_HOTKEYS:
                    if action not in current_hotkeys:
                        current_hotkeys[action] = DEFAULT_HOTKEYS[action]
                        changed = True
                # Удаляем устаревшие действия
                for action in list(current_hotkeys.keys()):
                    if action not in DEFAULT_HOTKEYS:
                        del current_hotkeys[action]
                        changed = True
        
        if changed:
            self.save_settings()
    
    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            self.settings_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logging.info("Settings saved successfully")
        except IOError as e:
            logging.error(f"Error saving settings: {e}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Получает значение настройки"""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any, save: bool = True):
        """Устанавливает значение настройки"""
        self.settings[key] = value
        if save:
            self.save_settings()
    
    # Удобные методы для доступа к конкретным настройкам
    def get_theme(self) -> str:
        return self.get_setting(THEME_KEY, DEFAULT_THEME)
    
    def set_theme(self, theme: str, save: bool = True):
        self.set_setting(THEME_KEY, theme, save)
    
    def get_language(self) -> str:
        return self.get_setting(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    
    def set_language(self, language: str, save: bool = True):
        self.set_setting(LANGUAGE_KEY, language, save)
    
    def get_hotkeys(self) -> Dict[str, str]:
        return self.get_setting(HOTKEYS_KEY, DEFAULT_HOTKEYS).copy()
    
    def set_hotkeys(self, hotkeys: Dict[str, str], save: bool = True):
        self.set_setting(HOTKEYS_KEY, hotkeys.copy(), save)
    
    def get_save_screenshot_flag(self) -> bool:
        return self.get_setting(SAVE_SCREENSHOT_LESS_THAN_6_KEY, DEFAULT_SAVE_SCREENSHOT)
    
    def set_save_screenshot_flag(self, flag: bool, save: bool = True):
        self.set_setting(SAVE_SCREENSHOT_LESS_THAN_6_KEY, flag, save)
    
    def get_screenshot_path(self) -> str:
        return self.get_setting(SCREENSHOT_SAVE_PATH_KEY, DEFAULT_SCREENSHOT_PATH)
    
    def set_screenshot_path(self, path: str, save: bool = True):
        self.set_setting(SCREENSHOT_SAVE_PATH_KEY, path, save)
    
    # Новый метод для получения минимального количества распознанных героев
    def get_min_recognized_heroes(self) -> int:
        return self.get_setting(MIN_RECOGNIZED_HEROES_KEY, DEFAULT_MIN_RECOGNIZED_HEROES)
    
    # Новый метод для установки минимального количества распознанных героев
    def set_min_recognized_heroes(self, min_heroes: int, save: bool = True):
        self.set_setting(MIN_RECOGNIZED_HEROES_KEY, min_heroes, save)
    
    def get_tab_geometry(self) -> Dict[str, int]:
        return self.get_setting(TAB_WINDOW_GEOMETRY_KEY, DEFAULT_TAB_GEOMETRY).copy()
    def set_tab_geometry(self, geometry: Dict[str, int], save: bool = True):
        self.set_setting(TAB_WINDOW_GEOMETRY_KEY, geometry.copy(), save)
    # Алиасы для поддержки существующего кода
    def get_tab_window_geometry(self) -> Dict[str, int]:
        return self.get_tab_geometry()
    def set_tab_window_geometry(self, geometry: Dict[str, int], save: bool = True):
        self.set_tab_geometry(geometry, save)