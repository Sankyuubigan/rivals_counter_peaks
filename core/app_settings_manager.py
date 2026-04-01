import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional
from core.app_settings_keys import *

DEFAULT_THEME = "light"
DEFAULT_LANGUAGE = "ru_RU"
DEFAULT_HOTKEYS = {
    "move_cursor_up": "tab+up",
    "move_cursor_down": "tab+down",
    "move_cursor_left": "tab+left",
    "move_cursor_right": "tab+right",
    "toggle_selection": "tab+num_0",
    "clear_all": "tab+num_subtract",
    "copy_team": "tab+num_1",
}
DEFAULT_TAB_GEOMETRY = {"x": 100, "y": 100, "width": 800, "height": 80}
DEFAULT_FAVORITE_HEROES = []
DEFAULT_ALGORITHM = "statistics"  # "statistics" или "manual"

class AppSettingsManager:
    def __init__(self):
        self.settings_file_path = self._get_settings_file_path()
        self.settings: Dict[str, Any] = self._load_settings()
        self._ensure_defaults()
    
    def _get_settings_file_path(self) -> Path:
        if sys.platform == "win32":
            base_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base_dir = Path.home() / ".config"
        app_dir = base_dir / "RivalsCounterPeaks"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "app_settings.json"
    
    def _load_settings(self) -> Dict[str, Any]:
        if not self.settings_file_path.exists(): return {}
        try:
            with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError) as e:
            return {}
    
    def _ensure_defaults(self):
        defaults = {
            THEME_KEY: DEFAULT_THEME,
            LANGUAGE_KEY: DEFAULT_LANGUAGE,
            HOTKEYS_KEY: DEFAULT_HOTKEYS,
            TAB_WINDOW_GEOMETRY_KEY: DEFAULT_TAB_GEOMETRY,
            FAVORITE_HEROES_KEY: DEFAULT_FAVORITE_HEROES,
            ALGORITHM_KEY: DEFAULT_ALGORITHM,
        }
        changed = False
        for key, default_value in defaults.items():
            if key not in self.settings:
                self.settings[key] = default_value
                changed = True
        
        if HOTKEYS_KEY in self.settings:
            current_hotkeys = self.settings[HOTKEYS_KEY]
            if not isinstance(current_hotkeys, dict):
                self.settings[HOTKEYS_KEY] = DEFAULT_HOTKEYS.copy()
                changed = True
            else:
                for action in DEFAULT_HOTKEYS:
                    if action not in current_hotkeys:
                        current_hotkeys[action] = DEFAULT_HOTKEYS[action]
                        changed = True
                for action in list(current_hotkeys.keys()):
                    if action not in DEFAULT_HOTKEYS:
                        del current_hotkeys[action]
                        changed = True
        if changed: self.save_settings()
    
    def save_settings(self):
        try:
            self.settings_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except IOError as e:
            logging.error(f"Error saving settings: {e}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any, save: bool = True):
        self.settings[key] = value
        if save: self.save_settings()
    
    def get_theme(self) -> str: return self.get_setting(THEME_KEY, DEFAULT_THEME)
    def set_theme(self, theme: str, save: bool = True): self.set_setting(THEME_KEY, theme, save)
    def get_language(self) -> str: return self.get_setting(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    def set_language(self, language: str, save: bool = True): self.set_setting(LANGUAGE_KEY, language, save)
    def get_hotkeys(self) -> Dict[str, str]: return self.get_setting(HOTKEYS_KEY, DEFAULT_HOTKEYS).copy()
    def set_hotkeys(self, hotkeys: Dict[str, str], save: bool = True): self.set_setting(HOTKEYS_KEY, hotkeys.copy(), save)
    def get_tab_geometry(self) -> Dict[str, int]: return self.get_setting(TAB_WINDOW_GEOMETRY_KEY, DEFAULT_TAB_GEOMETRY).copy()
    def set_tab_geometry(self, geometry: Dict[str, int], save: bool = True): self.set_setting(TAB_WINDOW_GEOMETRY_KEY, geometry.copy(), save)
    def get_tab_window_geometry(self) -> Dict[str, int]: return self.get_tab_geometry()
    def set_tab_window_geometry(self, geometry: Dict[str, int], save: bool = True): self.set_tab_geometry(geometry, save)
    
    def get_favorite_heroes(self) -> list:
        return self.get_setting(FAVORITE_HEROES_KEY, DEFAULT_FAVORITE_HEROES).copy()
    
    def set_favorite_heroes(self, heroes: list, save: bool = True):
        self.set_setting(FAVORITE_HEROES_KEY, list(heroes), save)
    
    def get_algorithm(self) -> str:
        return self.get_setting(ALGORITHM_KEY, DEFAULT_ALGORITHM)
    
    def set_algorithm(self, algorithm: str, save: bool = True):
        self.set_setting(ALGORITHM_KEY, algorithm, save)