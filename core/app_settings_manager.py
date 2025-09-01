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
from core.hotkey_config import DEFAULT_HOTKEYS as DEFAULT_HOTKEYS_VALUES
from info.translations import DEFAULT_LANGUAGE as DEFAULT_LANG_VALUE

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
    
    fallback_needed = False
    if not app_specific_dir.exists():
        logging.info(f"Директория настроек {app_specific_dir} не существует. Попытка создать...")
        try:
            app_specific_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Создана директория настроек: {app_specific_dir}")
        except OSError as e: 
            logging.error(f"Не удалось создать директорию настроек {app_specific_dir}: {e}")
            fallback_needed = True
            
    elif not app_specific_dir.is_dir():
        logging.error(f"Путь для настроек {app_specific_dir} существует, но не является директорией. Попытка использовать fallback.")
        fallback_needed = True

    if fallback_needed:
        fallback_dir_candidate = None
        if hasattr(sys, 'executable') and sys.executable:
             fallback_dir_candidate = Path(sys.executable).parent
        
        if fallback_dir_candidate is None or not fallback_dir_candidate.is_dir():
            fallback_dir_candidate = Path.cwd()
            logging.warning(f"Используется fallback директория (CWD) для настроек: {fallback_dir_candidate}")
        else:
            logging.warning(f"Используется fallback директория для настроек: {fallback_dir_candidate}")
        return fallback_dir_candidate

    return app_specific_dir

SETTINGS_FILE_PATH = _get_app_data_dir() / "app_settings.json"

class AppSettingsManager:
    def __init__(self):
        self.settings: Dict[str, Any] = self._load_settings_from_file()
        self._ensure_all_defaults_present()

    def _load_settings_from_file(self) -> Dict[str, Any]:
        loaded_data = {}
        if SETTINGS_FILE_PATH.exists():
            if SETTINGS_FILE_PATH.is_file():
                try: 
                    with open(SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
                        loaded_data_json = json.load(f)
                    if isinstance(loaded_data_json, dict):
                        logging.info(f"Настройки успешно загружены из {SETTINGS_FILE_PATH}")
                        loaded_data = loaded_data_json
                    else:
                        logging.warning(f"Файл настроек {SETTINGS_FILE_PATH} имеет неверный формат (не словарь). Используются настройки по умолчанию.")
                except (json.JSONDecodeError, IOError) as e:
                    logging.error(f"Ошибка загрузки настроек из {SETTINGS_FILE_PATH}: {e}. Используются настройки по умолчанию.")
            else:
                logging.warning(f"Путь к настройкам {SETTINGS_FILE_PATH} существует, но не является файлом. Используются настройки по умолчанию.")
        else:
            logging.info(f"Файл настроек {SETTINGS_FILE_PATH} не найден. Будут использованы и сохранены настройки по умолчанию.")
        return loaded_data

    def _ensure_all_defaults_present(self):
        changes_made = False
        if THEME_KEY not in self.settings:
            self.settings[THEME_KEY] = DEFAULT_THEME_VALUE
            changes_made = True
        if LANGUAGE_KEY not in self.settings:
            self.settings[LANGUAGE_KEY] = DEFAULT_LANG_VALUE
            changes_made = True
        
        current_config_hotkeys = self.settings.get(HOTKEYS_KEY)
        if not isinstance(current_config_hotkeys, dict): 
            self.settings[HOTKEYS_KEY] = DEFAULT_HOTKEYS_VALUES.copy()
            changes_made = True
        else: 
            default_actions = set(DEFAULT_HOTKEYS_VALUES.keys())
            loaded_actions = set(current_config_hotkeys.keys())

            missing_from_config = default_actions - loaded_actions
            for action_id in missing_from_config:
                current_config_hotkeys[action_id] = DEFAULT_HOTKEYS_VALUES[action_id]
                logging.info(f"Добавлен хоткей по умолчанию для отсутствующего действия: {action_id} -> {DEFAULT_HOTKEYS_VALUES[action_id]}")
                changes_made = True
            
            extra_in_config = loaded_actions - default_actions
            if extra_in_config: 
                for action_id in list(extra_in_config): 
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
        # try-except оставлен для критической операции I/O
        try:
            parent_dir = SETTINGS_FILE_PATH.parent
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
            elif not parent_dir.is_dir():
                logging.error(f"Не удалось сохранить настройки: путь {parent_dir} не является директорией.")
                return

            with open(SETTINGS_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logging.info(f"Настройки сохранены в {SETTINGS_FILE_PATH}")
        except IOError as e:
            logging.error(f"Ошибка сохранения настроек в {SETTINGS_FILE_PATH}: {e}")
        except Exception as e_global:
            logging.error(f"Непредвиденная ошибка при сохранении настроек: {e_global}", exc_info=True)


    def get_setting(self, key: str, default_value: Any = None) -> Any:
        if key == HOTKEYS_KEY:
            hotkeys_data = self.settings.get(key, default_value if default_value is not None else {})
            if isinstance(hotkeys_data, dict):
                return hotkeys_data.copy()
            if isinstance(default_value, dict):
                return default_value.copy()
            return default_value
        return self.settings.get(key, default_value)

    def set_setting(self, key: str, value: Any, auto_save: bool = True):
        self.settings[key] = value
        if auto_save:
            self.save_settings_to_file()

    def get_theme(self) -> str:
        theme_val = self.get_setting(THEME_KEY, DEFAULT_THEME_VALUE)
        return str(theme_val) if theme_val is not None else DEFAULT_THEME_VALUE

    def get_language(self) -> str:
        lang_val = self.get_setting(LANGUAGE_KEY, DEFAULT_LANG_VALUE)
        return str(lang_val) if lang_val is not None else DEFAULT_LANG_VALUE

    def get_hotkeys(self) -> Dict[str, str]:
        hotkeys_data = self.get_setting(HOTKEYS_KEY, DEFAULT_HOTKEYS_VALUES)
        if isinstance(hotkeys_data, dict):
            return {str(k): str(v) for k, v in hotkeys_data.items()}
        return DEFAULT_HOTKEYS_VALUES.copy()

    def get_save_screenshot_flag(self) -> bool:
        flag_val = self.get_setting(SAVE_SCREENSHOT_LESS_THAN_6_KEY, DEFAULT_SAVE_SCREENSHOT_VALUE)
        return bool(flag_val)

    def get_screenshot_save_path(self) -> str:
        path_val = self.get_setting(SCREENSHOT_SAVE_PATH_KEY, DEFAULT_SCREENSHOT_PATH_VALUE)
        return str(path_val) if path_val is not None else DEFAULT_SCREENSHOT_PATH_VALUE

    def set_theme(self, theme: str, auto_save: bool = True):
        self.set_setting(THEME_KEY, theme, auto_save)

    def set_language(self, language: str, auto_save: bool = True):
        self.set_setting(LANGUAGE_KEY, language, auto_save)

    def set_hotkeys(self, hotkeys: Dict[str, str], auto_save: bool = True):
        if isinstance(hotkeys, dict):
            self.set_setting(HOTKEYS_KEY, {str(k): str(v) for k, v in hotkeys.items()}, auto_save)
        else:
            logging.warning(f"Попытка установить некорректный тип для хоткеев: {type(hotkeys)}. Используются значения по умолчанию.")
            self.set_setting(HOTKEYS_KEY, DEFAULT_HOTKEYS_VALUES.copy(), auto_save)

    def set_save_screenshot_flag(self, flag: bool, auto_save: bool = True):
        self.set_setting(SAVE_SCREENSHOT_LESS_THAN_6_KEY, bool(flag), auto_save)

    def set_screenshot_save_path(self, path: str, auto_save: bool = True):
        self.set_setting(SCREENSHOT_SAVE_PATH_KEY, str(path), auto_save)