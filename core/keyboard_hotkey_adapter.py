# File: core/keyboard_hotkey_adapter.py
import logging
import threading
from typing import Dict, Callable, Any

from PySide6.QtCore import QObject, Signal, Slot, QMetaObject, Q_ARG, Qt

from core.hotkey_config import HOTKEY_ACTIONS_CONFIG
from core.lang.translations import get_text

try:
    import keyboard # Новая библиотека
    KEYBOARD_AVAILABLE = True
    logging.info("Библиотека 'keyboard' успешно импортирована.")
except ImportError:
    KEYBOARD_AVAILABLE = False
    keyboard = None
    logging.error("Библиотека 'keyboard' НЕ найдена. Глобальные горячие клавиши будут НЕ доступны.")
except Exception as e_imp: # Перехват других возможных ошибок импорта
    KEYBOARD_AVAILABLE = False
    keyboard = None
    logging.error(f"Ошибка при импорте библиотеки 'keyboard': {e_imp}")


class KeyboardHotkeyAdapter(QObject):
    hotkeys_updated_signal = Signal() 

    def __init__(self, main_window: QObject):
        super().__init__()
        self.main_window = main_window
        self._current_hotkeys_config: Dict[str, str] = {} 
        self._registered_keyboard_lib_hotkeys: Dict[str, str] = {} 
        self._lock = threading.Lock()
        self._is_active = False 

        if not KEYBOARD_AVAILABLE:
            logging.warning("KeyboardHotkeyAdapter: Библиотека 'keyboard' недоступна. Функциональность будет ограничена.")

    def _normalize_hotkey_string_for_keyboard_lib(self, internal_hotkey_str: str) -> str:
        if not internal_hotkey_str:
            return ""
        s = internal_hotkey_str.lower().strip()
        
        replacements = {
            "num_0": "num 0", "num_1": "num 1", "num_2": "num 2", "num_3": "num 3", "num_4": "num 4",
            "num_5": "num 5", "num_6": "num 6", "num_7": "num 7", "num_8": "num 8", "num_9": "num 9",
            
            "num_decimal": "decimal",    # Numpad . (оставляем как есть, так как "tab+decimal" регистрировался успешно)
            "num_divide": "/",          # ИЗМЕНЕНИЕ: Numpad / -> "/"
            "num_multiply": "*",        # ИЗМЕНЕНИЕ: Numpad * -> "*"
            "num_subtract": "subtract",  
            "num_add": "add",           

            "win": "windows", "esc": "escape", "del": "delete", "ins": "insert",
            "pgup": "page up", "pgdn": "page down", "printscreen": "print screen",
            "scrolllock": "scroll lock", "pausebreak": "pause",
        }
        for i in range(1, 13): replacements[f"f{i}"] = f"f{i}"

        known_keys_direct_mapping = [
            "ctrl", "alt", "shift", "windows", "escape", "delete", "insert", 
            "space", "enter", "tab", "up", "down", "left", "right", "home", "end", 
            "page up", "page down", "print screen", "scroll lock", "pause",
            "decimal", "subtract", "add",
            "/", "*" # Добавляем сами символы как известные, если они не были заменены
        ]
        
        parts = s.split('+')
        normalized_parts = []
        for part_orig in parts:
            part = part_orig.strip()
            if not part: continue

            if part in replacements:
                normalized_parts.append(replacements[part])
                continue
            
            if part.startswith("num ") and len(part) > 4 and part[4:].isdigit():
                 normalized_parts.append(part) 
                 continue

            if part in known_keys_direct_mapping:
                 normalized_parts.append(part)
                 continue
            
            normalized_parts.append(part.lower())
        
        final_str = "+".join(normalized_parts)
        logging.debug(f"KHA_NORM: Input='{internal_hotkey_str}', Normalized_for_keyboard_lib='{final_str}'")
        return final_str

    def load_and_register_hotkeys(self, hotkey_config_map: Dict[str, str]):
        logging.info(f"KHA_LRH_ENTRY: Вход в load_and_register_hotkeys. KEYBOARD_AVAILABLE: {KEYBOARD_AVAILABLE}") 
        if not KEYBOARD_AVAILABLE:
            logging.warning("KHA_LRH: 'keyboard' недоступна, выход из регистрации.")
            self._current_hotkeys_config = hotkey_config_map.copy()
            self.hotkeys_updated_signal.emit()
            return

        logging.debug(f"KHA_LRH: Перед self._lock. KEYBOARD_AVAILABLE: {KEYBOARD_AVAILABLE}") 
        with self._lock:
            logging.info(f"KHA_LRH: === ВНУТРИ LOCK: ЗАПУСК load_and_register_hotkeys ({len(hotkey_config_map)} хоткеев) ===") 
            
            logging.info("KHA_LRH_DEBUG: Вызов _unregister_all_keyboard_lib_hotkeys АКТИВЕН.")
            self._unregister_all_keyboard_lib_hotkeys()

            self._current_hotkeys_config = hotkey_config_map.copy()
            successfully_registered = 0; failed_to_register = 0
            registration_errors = [] 

            for action_id, internal_hotkey_str in self._current_hotkeys_config.items():
                logging.debug(f"KHA_LRH_LOOP: Обработка action_id='{action_id}', internal_str='{internal_hotkey_str}'")
                if not internal_hotkey_str or \
                   internal_hotkey_str.lower() == 'none' or \
                   internal_hotkey_str.lower() == get_text('hotkey_not_set').lower() or \
                   internal_hotkey_str.lower() == get_text('hotkey_none').lower():
                    logging.debug(f"KHA_LRH_LOOP: Хоткей для '{action_id}' не назначен, пропуск.")
                    continue

                keyboard_lib_format_str = self._normalize_hotkey_string_for_keyboard_lib(internal_hotkey_str)
                if not keyboard_lib_format_str:
                    logging.warning(f"KHA_LRH_LOOP: Не удалось нормализовать '{internal_hotkey_str}' для '{action_id}'.")
                    failed_to_register += 1
                    registration_errors.append(f"'{action_id}': Нормализация '{internal_hotkey_str}' -> Пусто")
                    continue
                
                action_config = HOTKEY_ACTIONS_CONFIG.get(action_id)
                if not action_config:
                    logging.warning(f"KHA_LRH_LOOP: Конфигурация для '{action_id}' не найдена.")
                    failed_to_register += 1
                    registration_errors.append(f"'{action_id}': Нет конфигурации в HOTKEY_ACTIONS_CONFIG")
                    continue
                
                suppress_original_event = True 
                callback_func = lambda bound_action_id=action_id: self._execute_action_thread_safe(bound_action_id)
                
                logging.debug(f"KHA_LRH_REG: Попытка регистрации: keyboard.add_hotkey('{keyboard_lib_format_str}', ..., suppress={suppress_original_event}) для '{action_id}'")
                try:
                    # Исправляем возможную проблему с передачей callback_func.
                    # Иногда lambda может захватывать последнее значение action_id из цикла.
                    # Создадим функцию-обертку для надежного захвата.
                    def create_callback(act_id):
                        return lambda: self._execute_action_thread_safe(act_id)

                    final_callback = create_callback(action_id)
                    keyboard.add_hotkey(keyboard_lib_format_str, final_callback, suppress=suppress_original_event)
                    
                    self._registered_keyboard_lib_hotkeys[keyboard_lib_format_str] = action_id
                    logging.info(f"KHA_LRH_REG: УСПЕХ: '{keyboard_lib_format_str}' для '{action_id}'.")
                    successfully_registered += 1
                except Exception as e:
                    logging.error(f"KHA_LRH_REG: ОШИБКА РЕГИСТРАЦИИ '{keyboard_lib_format_str}' для '{action_id}': {e}", exc_info=False) 
                    failed_to_register += 1
                    registration_errors.append(f"'{action_id}': '{keyboard_lib_format_str}' -> {type(e).__name__}: {str(e)[:100]}")

            logging.info(f"KHA_LRH: === ВНУТРИ LOCK: ЗАВЕРШЕНИЕ load_and_register_hotkeys. Успешно: {successfully_registered}, Ошибок: {failed_to_register} ===")
            if failed_to_register > 0:
                logging.warning(f"KHA_LRH: Ошибки при регистрации хоткеев:")
                for err_entry in registration_errors:
                    logging.warning(f"    - {err_entry}")
        logging.info("KHA_LRH_EXIT: Выход из load_and_register_hotkeys.") 
        self.hotkeys_updated_signal.emit()

    def _execute_action_thread_safe(self, action_id: str):
        logging.info(f"KHA_EXEC: Хоткей сработал! Действие: '{action_id}' (Вызвано из потока 'keyboard')")
        if not self.main_window: 
            logging.warning(f"KHA_EXEC: main_window был удален, действие '{action_id}' не может быть выполнено.")
            return
        try:
            QMetaObject.invokeMethod(
                self.main_window, "_emit_action_signal_slot",
                Qt.ConnectionType.QueuedConnection, Q_ARG(str, action_id)
            )
        except RuntimeError as e: logging.error(f"KHA_EXEC: RuntimeError при вызове _emit_action_signal_slot для '{action_id}': {e}")
        except Exception as e_invoke: logging.error(f"KHA_EXEC: Неожиданная ошибка при QMetaObject.invokeMethod для '{action_id}': {e_invoke}", exc_info=True)

    def _unregister_all_keyboard_lib_hotkeys(self):
        logging.info("KHA_UNREG_ENTRY: Вход в _unregister_all_keyboard_lib_hotkeys.")
        if not KEYBOARD_AVAILABLE: 
            logging.debug("KHA_UNREG: 'keyboard' недоступна, выход.")
            return
        
        logging.debug(f"KHA_UNREG: Перед проверкой _registered_keyboard_lib_hotkeys (len: {len(self._registered_keyboard_lib_hotkeys)})")
        if not self._registered_keyboard_lib_hotkeys:
            logging.info("KHA_UNREG: Нет зарегистрированных хоткеев для удаления. Пропуск операций с библиотекой 'keyboard'.")
            self._registered_keyboard_lib_hotkeys.clear() 
            logging.info("KHA_UNREG_EXIT: Выход из _unregister_all_keyboard_lib_hotkeys (нечего было удалять).")
            return 
            
        logging.info(f"KHA_UNREG: Начало удаления {len(self._registered_keyboard_lib_hotkeys)} хоткеев...")
        keys_to_unhook = list(self._registered_keyboard_lib_hotkeys.keys())
        unhooked_count = 0; failed_unhook_count = 0
            
        for i, hotkey_str in enumerate(keys_to_unhook):
            logging.debug(f"KHA_UNREG_LOOP: {i+1}/{len(keys_to_unhook)} Попытка удаления '{hotkey_str}'...")
            try:
                keyboard.remove_hotkey(hotkey_str) 
                logging.debug(f"KHA_UNREG_LOOP: УСПЕХ удаления '{hotkey_str}'.")
                unhooked_count +=1
            except Exception as e_rem: 
                if isinstance(e_rem, (ValueError, KeyError)) and "is not registered" in str(e_rem).lower():
                    logging.warning(f"KHA_UNREG_LOOP: Попытка удалить хоткей '{hotkey_str}', который не был зарегистрирован: {e_rem}")
                else:
                    logging.error(f"KHA_UNREG_LOOP: ОШИБКА при удалении '{hotkey_str}': {e_rem}", exc_info=True)
                failed_unhook_count += 1
            
        self._registered_keyboard_lib_hotkeys.clear()
        logging.info(f"KHA_UNREG: Завершено. Удалено: {unhooked_count}, Ошибок/Пропущено: {failed_unhook_count}.")
        logging.info("KHA_UNREG_EXIT: Выход из _unregister_all_keyboard_lib_hotkeys (после удаления).")


    def start_listening(self):
        logging.info("KHA_START_LISTEN_ENTRY: Вход в start_listening.")
        if not KEYBOARD_AVAILABLE:
            logging.warning("KHA_START_LISTEN: 'keyboard' недоступна.")
            return
        with self._lock:
            logging.debug("KHA_START_LISTEN: Внутри lock.")
            if self._is_active:
                logging.info("KHA_START_LISTEN: Адаптер уже активен.")
                return
            if not self._current_hotkeys_config:
                logging.warning("KHA_START_LISTEN: Конфигурация хоткеев не загружена.")
                return
            if not self._registered_keyboard_lib_hotkeys and self._current_hotkeys_config:
                logging.info("KHA_START_LISTEN: Конфигурация есть, но хоткеи не зарегистрированы. Попытка регистрации...")
                self.load_and_register_hotkeys(dict(self._current_hotkeys_config)) 
            self._is_active = True
            logging.info("KHA_START_LISTEN: Адаптер горячих клавиш ('keyboard') активирован.")
        logging.info("KHA_START_LISTEN_EXIT: Выход из start_listening.")

    def stop_listening(self, is_internal_restart=False):
        logging.info(f"KHA_STOP_LISTEN_ENTRY: Вход в stop_listening (internal_restart={is_internal_restart}).")
        if not KEYBOARD_AVAILABLE:
            logging.debug("KHA_STOP_LISTEN: 'keyboard' недоступна.")
            return
        with self._lock:
            logging.debug(f"KHA_STOP_LISTEN: Внутри lock. _is_active={self._is_active}")
            if not self._is_active and not is_internal_restart: 
                logging.info("KHA_STOP_LISTEN: Адаптер уже неактивен.")
                return
            logging.info("KHA_STOP_LISTEN: Вызов _unregister_all_keyboard_lib_hotkeys.")
            self._unregister_all_keyboard_lib_hotkeys()
            logging.info("KHA_STOP_LISTEN: _unregister_all_keyboard_lib_hotkeys завершен.")
            self._is_active = False
        log_msg = "остановлен в рамках внутреннего перезапуска" if is_internal_restart else "деактивирован (все хоткеи удалены)"
        logging.info(f"KHA_STOP_LISTEN: Адаптер горячих клавиш ('keyboard') {log_msg}.")
        logging.info("KHA_STOP_LISTEN_EXIT: Выход из stop_listening.")

    def clear_pressed_keys_state(self):
        if not KEYBOARD_AVAILABLE: return
        logging.debug("KHA: clear_pressed_keys_state вызван. Для 'keyboard' обычно не требуется.")

    def get_current_hotkeys_config_for_settings(self) -> Dict[str, str]:
        with self._lock:
            return self._current_hotkeys_config.copy()

    def get_default_hotkeys_config_for_settings(self) -> Dict[str, str]:
        from core.hotkey_config import DEFAULT_HOTKEYS 
        return DEFAULT_HOTKEYS.copy()