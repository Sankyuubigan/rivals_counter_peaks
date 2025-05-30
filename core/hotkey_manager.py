# File: core/hotkey_manager.py
import logging
import threading
from typing import Dict, Callable, Any, Set
import time
import os
import sys
import re 

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QMetaObject, Q_ARG, Qt

from core.app_settings_manager import AppSettingsManager 
from core.lang.translations import get_text
from core.hotkey_parser_utils import (
    parse_hotkey_string, 
    normalize_string_for_storage,
    normalize_key_object,
    get_key_object_id,
    get_pynput_key_to_string_map,
    PYNPUT_AVAILABLE_PARSER
)
from core.hotkey_config import DEFAULT_HOTKEYS, HOTKEY_ACTIONS_CONFIG

try:
    from pynput import keyboard 
    PYNPUT_AVAILABLE_LISTENER = True
except ImportError:
    PYNPUT_AVAILABLE_LISTENER = False
    keyboard = None 
    logging.error("HotkeyManager: 'pynput' library not found. Global hotkeys will be disabled.")

PYNPUT_AVAILABLE = PYNPUT_AVAILABLE_PARSER and PYNPUT_AVAILABLE_LISTENER


class HotkeyManager(QObject):
    hotkeys_updated_signal = Signal() 

    def __init__(self, main_window: QObject, app_settings_manager: AppSettingsManager):
        super().__init__()
        self.main_window = main_window
        self.app_settings_manager = app_settings_manager 
        
        self._current_hotkeys: Dict[str, str] = {} 
        self._parsed_hotkeys: Dict[str, Dict[str, Any]] = {}
        self._pynput_listener: Any = None 
        self._pressed_keys: Set[Any] = set() 
        self._lock = threading.Lock() 

        self.load_hotkeys_from_settings() 

    def load_hotkeys_from_settings(self):
        logging.info("HM: Загрузка хоткеев из AppSettingsManager...")
        loaded_hotkeys = self.app_settings_manager.get_hotkeys() 
        
        self._current_hotkeys = {
            action: normalize_string_for_storage(hk_string)
            for action, hk_string in loaded_hotkeys.items()
        }
        logging.info(f"HM: Загружено и нормализовано хоткеев: {len(self._current_hotkeys)}")

        if PYNPUT_AVAILABLE:
            self._update_parsed_hotkeys()
        self.hotkeys_updated_signal.emit()


    def save_hotkeys_to_settings(self, hotkeys_to_save: Dict[str, str]):
        logging.info(f"HM: Сохранение хоткеев в AppSettingsManager: {hotkeys_to_save}")
        
        normalized_to_save = {
            action: normalize_string_for_storage(hk_string)
            for action, hk_string in hotkeys_to_save.items()
        }
        
        self.app_settings_manager.set_hotkeys(normalized_to_save) 
        
        self._current_hotkeys = normalized_to_save.copy() 
        if PYNPUT_AVAILABLE:
            self._update_parsed_hotkeys() 
            self.reregister_all_hotkeys_listener() 
        self.hotkeys_updated_signal.emit()

    def _update_parsed_hotkeys(self):
        if not PYNPUT_AVAILABLE:
            logging.warning("HM: Pynput недоступен, парсинг хоткеев невозможен.")
            return
        
        with self._lock:
            self._parsed_hotkeys.clear()
            parsed_count = 0
            unparsed_count = 0
            logging.debug(f"HM: Обновление парсинга для {len(self._current_hotkeys)} хоткеев.")
            for action_id, hotkey_str in self._current_hotkeys.items():
                if not hotkey_str or hotkey_str.lower() == 'none' or hotkey_str.lower() == get_text('hotkey_not_set').lower():
                    logging.debug(f"HM: Хоткей для '{action_id}' не назначен ('{hotkey_str}'), пропуск парсинга.")
                    continue

                parsed = parse_hotkey_string(hotkey_str, get_text) 
                if parsed:
                    config = HOTKEY_ACTIONS_CONFIG.get(action_id, {})
                    parsed['suppress_flag_from_config'] = config.get('suppress', False) 
                    parsed['action_id'] = action_id 
                    self._parsed_hotkeys[action_id] = parsed
                    parsed_count +=1
                    logging.debug(f"HM: Успешно распарсен хоткей '{hotkey_str}' для '{action_id}'. Результат: {parsed}")
                else:
                    unparsed_count +=1
                    logging.warning(f"HM: Не удалось распарсить строку хоткея '{hotkey_str}' для действия '{action_id}'. Хоткей будет проигнорирован.")
            logging.info(f"HM: Парсинг хоткеев завершен. Успешно: {parsed_count}, Ошибок: {unparsed_count}.")
            if unparsed_count > 0:
                 logging.warning(f"HM: {unparsed_count} хоткеев не были распарсены и не будут работать.")


    def on_press(self, key):
        if not PYNPUT_AVAILABLE or not keyboard: return True 
        
        normalized_key_obj = normalize_key_object(key)
        key_id_pressed = get_key_object_id(normalized_key_obj)
        
        logging.debug(f"HM: KeyPress: Raw='{key}', NormObj='{normalized_key_obj}', ID='{key_id_pressed}'")

        with self._lock:
            self._pressed_keys.add(key_id_pressed)
            current_pressed_ids_repr = sorted([str(k_id) for k_id in self._pressed_keys])
            logging.debug(f"HM: Pressed keys IDs: {current_pressed_ids_repr}")

            for action_id, parsed_combo in self._parsed_hotkeys.items():
                if key_id_pressed == parsed_combo['main_key_id'] and \
                   parsed_combo['keys_ids'].issubset(self._pressed_keys) and \
                   self._pressed_keys == parsed_combo['keys_ids']: 
                    
                    original_hotkey_str = self._current_hotkeys.get(action_id, "N/A")
                    logging.info(f"HM: Хоткей СРАБОТАЛ: '{original_hotkey_str}' для действия '{action_id}'. Нажатые ID: {current_pressed_ids_repr}")
                    
                    if hasattr(self.main_window, '_emit_action_signal_slot'): 
                        QMetaObject.invokeMethod(self.main_window, "_emit_action_signal_slot",
                                                 Qt.ConnectionType.QueuedConnection,
                                                 Q_ARG(str, action_id))
                    else:
                        signal_config = HOTKEY_ACTIONS_CONFIG.get(action_id)
                        if signal_config and hasattr(self.main_window, signal_config['signal_name']):
                             getattr(self.main_window, signal_config['signal_name']).emit()
                        else:
                             logging.error(f"HM: Не найден слот или сигнал для действия {action_id} в main_window.")
        return True 


    def on_release(self, key):
        if not PYNPUT_AVAILABLE or not keyboard: return True
        
        normalized_key_obj = normalize_key_object(key)
        key_id_released = get_key_object_id(normalized_key_obj)
        logging.debug(f"HM: KeyRelease: Raw='{key}', NormObj='{normalized_key_obj}', ID='{key_id_released}'")

        with self._lock:
            if key_id_released in self._pressed_keys:
                self._pressed_keys.remove(key_id_released)
                logging.debug(f"HM: Released key ID '{key_id_released}'. Remaining pressed: {sorted([str(k_id) for k_id in self._pressed_keys])}")
            else:
                logging.debug(f"HM: Released key ID '{key_id_released}' not found in _pressed_keys (возможно, отпущена до регистрации).")
        return True


    def reregister_all_hotkeys_listener(self): 
        logging.info("HM: Запрос на перерегистрацию всех хоткеев (перезапуск слушателя).")
        if not PYNPUT_AVAILABLE:
            logging.warning("HM: Pynput недоступен. Перерегистрация хоткеев невозможна.")
            return
        self.stop_listening(is_internal_restart=True) 
        self.start_listening()


    def start_listening(self):
        logging.info("HM: Попытка запуска слушателя хоткеев...")
        if not PYNPUT_AVAILABLE or not keyboard:
            logging.warning("HM: Pynput недоступен, запуск слушателя отменен.")
            return

        if self._pynput_listener is not None:
            if self._pynput_listener.is_alive():
                logging.info("HM: Слушатель pynput уже активен. Перезапуск не требуется.")
                return
            else: 
                logging.warning("HM: Экземпляр слушателя pynput существует, но не активен. Попытка остановить и перезапустить.")
                self.stop_listening(is_internal_restart=True) 

        if not self._parsed_hotkeys and self._current_hotkeys:
            logging.info("HM: _parsed_hotkeys пуст, вызов _update_parsed_hotkeys перед стартом слушателя.")
            self._update_parsed_hotkeys()
        
        if not self._parsed_hotkeys:
            logging.warning("HM: Нет распарсенных хоткеев. Слушатель запустится, но не будет реагировать.")

        try:
            logging.info("HM: Создание нового экземпляра pynput.Listener...")
            self._pynput_listener = keyboard.Listener( 
                on_press=self.on_press,
                on_release=self.on_release,
                suppress=False 
            )
            self._pynput_listener.daemon = True 
            self._pynput_listener.start()
            logging.info("HM: pynput.Listener.start() вызван.")
            
            # Проверка активности слушателя после короткой паузы
            QTimer.singleShot(200, self._check_listener_status) # Используем QTimer для проверки из Qt потока

        except Exception as e:
            logging.error(f"HM: КРИТИЧЕСКАЯ ОШИБКА при создании или запуске слушателя pynput: {e}", exc_info=True)
            self._pynput_listener = None

    def _check_listener_status(self):
        """Проверяет и логирует статус слушателя pynput."""
        if self._pynput_listener is not None:
            if self._pynput_listener.is_alive():
                logging.info("HM: Слушатель pynput УСПЕШНО ЗАПУЩЕН и активен (проверка через 200мс).")
            else: 
                logging.error("HM: Слушатель pynput НЕ АКТИВЕН через 200мс после вызова start(). Возможна проблема инициализации.")
                # Можно попробовать еще раз, или сообщить о проблеме
                # self._pynput_listener = None # Сбросить, если не запустился
        else:
            logging.error("HM: Экземпляр слушателя pynput отсутствует при проверке статуса.")


    def stop_listening(self, is_internal_restart=False):
        logging.info(f"HM: Попытка остановки слушателя хоткеев (is_internal_restart={is_internal_restart}).")
        if not PYNPUT_AVAILABLE:
            logging.debug("HM: Pynput недоступен, остановка слушателя не требуется.")
            return

        listener_instance = self._pynput_listener
        if listener_instance is not None:
            is_alive_before_stop = hasattr(listener_instance, 'is_alive') and listener_instance.is_alive()
            logging.info(f"HM: Слушатель существует. Активен перед stop(): {is_alive_before_stop}")
            
            if is_alive_before_stop: 
                logging.debug(f"HM: Вызов stop() для слушателя: {listener_instance}")
                try:
                    listener_instance.stop() 
                    # Поток pynput может не сразу завершиться. Join с таймаутом.
                    if hasattr(listener_instance, 'join') and callable(listener_instance.join):
                         logging.debug("HM: Вызов join() для потока слушателя...")
                         listener_instance.join(timeout=1.0) # Увеличил таймаут
                         if listener_instance.is_alive():
                             logging.warning("HM: Поток слушателя pynput не завершился после stop() и join(1.0s).")
                         else:
                             logging.info("HM: Поток слушателя pynput успешно завершен (join).")
                except Exception as e:
                    logging.warning(f"HM: Исключение при остановке/завершении слушателя pynput: {e}", exc_info=True)
            else:
                logging.debug("HM: Экземпляр слушателя pynput не был активен при вызове stop_listening.")
            
            self._pynput_listener = None 
            logging.info("HM: Экземпляр слушателя pynput очищен (_pynput_listener = None).")
        else:
            logging.debug("HM: Активного экземпляра слушателя pynput для остановки не найдено.")
        
        with self._lock: 
            self._pressed_keys.clear()
            
        if not is_internal_restart: 
            logging.info("HM: Слушатель хоткеев полностью остановлен.")
        else:
            logging.info("HM: Слушатель хоткеев остановлен в рамках внутреннего перезапуска.")


    def get_current_hotkeys_config(self) -> Dict[str, str]:
        return self._current_hotkeys.copy()

    def get_default_hotkeys_config(self) -> Dict[str, str]:
        return DEFAULT_HOTKEYS.copy()

    def get_actions_config(self) -> Dict[str, Any]:
        return HOTKEY_ACTIONS_CONFIG.copy()
