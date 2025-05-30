# File: core/app_settings_manager.py
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict

from core.app_settings_keys import (
    THEME_KEY, LANGUAGE_KEY, HOTKEYS_KEY,
    SAVE_SCREENSHOT_LESS_THAN_6_KEY, SCREENSHOT_SAVE_PATH_KEY
)
# ИМПОРТИРУЕМ DEFAULT_HOTKEYS ИЗ НОВОГО ФАЙЛА
from core.hotkey_config import DEFAULT_HOTKEYS as DEFAULT_HOTKEYS_VALUES
from core.lang.translations import DEFAULT_LANGUAGE as DEFAULT_LANG_VALUE

DEFAULT_THEME_VALUE = "light" 
DEFAULT_SAVE_SCREENSHOT_VALUE = False 
DEFAULT_SCREENSHOT_PATH_VALUE = "" 

def _get_app_data_dir() -> Path:
    app_data_dir_str = ""
    if sys.platform == "win32":
        app_data_dir_str = os.getenv("APPDATA")
        if not app_data_dir_str: 
            app_data_dir_str = str(Path.home() / "AppData" / "Roaming")
    else: 
        app_data_dir_str = str(Path.home() / ".config")
    
    app_data_dir = Path(app_data_dir_str)
    app_specific_dir = app_data_dir / "RivalsCounterPeaks" 
    
    if not app_specific_dir.exists():
        try:
            app_specific_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Создана директория настроек: {app_specific_dir}")
        except OSError as e:
            logging.error(f"Не удалось создать директорию настроек {app_specific_dir}: {e}")
            if hasattr(sys, 'executable') and sys.executable:
                 fallback_dir = Path(sys.executable).parent
                 logging.warning(f"Используется fallback директория для настроек: {fallback_dir}")
                 return fallback_dir
            fallback_dir_cwd = Path.cwd()
            logging.warning(f"Используется fallback директория (CWD) для настроек: {fallback_dir_cwd}")
            return fallback_dir_cwd 
    return app_specific_dir

SETTINGS_FILE_PATH = _get_app_data_dir() / "app_settings.json"

class AppSettingsManager:
    def __init__(self):
        self.settings: Dict[str, Any] = self._load_settings_from_file()
        self._ensure_all_defaults_present()

    def _load_settings_from_file(self) -> Dict[str, Any]:
        if SETTINGS_FILE_PATH.exists():
            try:
                with open(SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                if isinstance(loaded_data, dict):
                    logging.info(f"Настройки успешно загружены из {SETTINGS_FILE_PATH}")
                    return loaded_data
                else:
                    logging.warning(f"Файл настроек {SETTINGS_FILE_PATH} имеет неверный формат (не словарь). Используются настройки по умолчанию.")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Ошибка загрузки настроек из {SETTINGS_FILE_PATH}: {e}. Используются настройки по умолчанию.")
        else:
            logging.info(f"Файл настроек {SETTINGS_FILE_PATH} не найден. Будут использованы и сохранены настройки по умолчанию.")
        return {} 

    def _ensure_all_defaults_present(self):
        changes_made = False
        if THEME_KEY not in self.settings:
            self.settings[THEME_KEY] = DEFAULT_THEME_VALUE
            changes_made = True
        if LANGUAGE_KEY not in self.settings:
            self.settings[LANGUAGE_KEY] = DEFAULT_LANG_VALUE
            changes_made = True
        
        if HOTKEYS_KEY not in self.settings or not isinstance(self.settings.get(HOTKEYS_KEY), dict):
            self.settings[HOTKEYS_KEY] = DEFAULT_HOTKEYS_VALUES.copy()
            changes_made = True
        else:
            current_config_hotkeys = self.settings[HOTKEYS_KEY]
            default_actions = set(DEFAULT_HOTKEYS_VALUES.keys())
            loaded_actions = set(current_config_hotkeys.keys())

            missing_from_config = default_actions - loaded_actions
            for action_id in missing_from_config:
                current_config_hotkeys[action_id] = DEFAULT_HOTKEYS_VALUES[action_id]
                logging.info(f"Добавлен хоткей по умолчанию для отсутствующего действия: {action_id} -> {DEFAULT_HOTKEYS_VALUES[action_id]}")
                changes_made = True
            
            extra_in_config = loaded_actions - default_actions
            for action_id in list(extra_in_config): # Используем list для возможности удаления во время итерации
                del current_config_hotkeys[action_id]
                logging.info(f"Удален устаревший/неизвестный хоткей из настроек: {action_id}")
                changes_made = True

        if SAVE_SCREENSHOT_LESS_THAN_6_KEY not in self.settings:
            self.settings[SAVE_SCREENSHOT_LESS_THAN_6_KEY] = DEFAULT_SAVE_SCREENSHOT_VALUE
            changes_made = True
        if SCREENSHOT_SAVE_PATH_KEY not in self.settings:
            self.settings[SCREENSHOT_SAVE_PATH_KEY] = DEFAULT_SCREENSHOT_PATH_VALUE
            changes_made = True

        if changes_made:
            logging.info("Обнаружены отсутствующие или устаревшие настройки, применены значения по умолчанию. Сохранение обновленных настроек.")
            self.save_settings_to_file()

    def save_settings_to_file(self):
        try:
            SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True) 
            with open(SETTINGS_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logging.info(f"Настройки сохранены в {SETTINGS_FILE_PATH}")
        except IOError as e:
            logging.error(f"Ошибка сохранения настроек в {SETTINGS_FILE_PATH}: {e}")
        except Exception as e_global:
            logging.error(f"Непредвиденная ошибка при сохранении настроек: {e_global}", exc_info=True)


    def get_setting(self, key: str, default_value: Any = None) -> Any:
        if key == HOTKEYS_KEY:
            return self.settings.get(key, default_value if default_value is not None else {}).copy()
        return self.settings.get(key, default_value)

    def set_setting(self, key: str, value: Any, auto_save: bool = True):
        self.settings[key] = value
        if auto_save:
            self.save_settings_to_file()

    def get_theme(self) -> str:
        return str(self.get_setting(THEME_KEY, DEFAULT_THEME_VALUE))

    def get_language(self) -> str:
        return str(self.get_setting(LANGUAGE_KEY, DEFAULT_LANG_VALUE))

    def get_hotkeys(self) -> Dict[str, str]:
        return dict(self.get_setting(HOTKEYS_KEY, DEFAULT_HOTKEYS_VALUES.copy()))

    def get_save_screenshot_flag(self) -> bool:
        return bool(self.get_setting(SAVE_SCREENSHOT_LESS_THAN_6_KEY, DEFAULT_SAVE_SCREENSHOT_VALUE))

    def get_screenshot_save_path(self) -> str:
        return str(self.get_setting(SCREENSHOT_SAVE_PATH_KEY, DEFAULT_SCREENSHOT_PATH_VALUE))

    def set_theme(self, theme: str, auto_save: bool = True):
        self.set_setting(THEME_KEY, theme, auto_save)

    def set_language(self, language: str, auto_save: bool = True):
        self.set_setting(LANGUAGE_KEY, language, auto_save)

    def set_hotkeys(self, hotkeys: Dict[str, str], auto_save: bool = True):
        self.set_setting(HOTKEYS_KEY, hotkeys, auto_save)

    def set_save_screenshot_flag(self, flag: bool, auto_save: bool = True):
        self.set_setting(SAVE_SCREENSHOT_LESS_THAN_6_KEY, flag, auto_save)

    def set_screenshot_save_path(self, path: str, auto_save: bool = True):
        self.set_setting(SCREENSHOT_SAVE_PATH_KEY, path, auto_save)