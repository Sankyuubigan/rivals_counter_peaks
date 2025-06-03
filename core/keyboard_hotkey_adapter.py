# File: core/keyboard_hotkey_adapter.py
import logging
import threading
from typing import Dict, Callable, Any, Tuple

from PySide6.QtCore import QObject, Signal, Slot, QMetaObject, Q_ARG, Qt

from core.hotkey_config import HOTKEY_ACTIONS_CONFIG
from core.lang.translations import get_text

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
    logging.info("Библиотека 'keyboard' успешно импортирована.")
except ImportError:
    KEYBOARD_AVAILABLE = False
    keyboard = None
    logging.error("Библиотека 'keyboard' НЕ найдена. Глобальные горячие клавиши будут НЕ доступны.")
except Exception as e_imp:
    KEYBOARD_AVAILABLE = False
    keyboard = None
    logging.error(f"Ошибка при импорте библиотеки 'keyboard': {e_imp}")

class KeyboardHotkeyAdapter(QObject):
    hotkeys_updated_signal = Signal()
    _hook_installed_globally = False

    def __init__(self, main_window: QObject):
        super().__init__()
        self.main_window = main_window
        self._current_hotkeys_config: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._is_active = False
        self._tab_is_pressed = False
        self._tab_combo_map: Dict[Tuple[str, bool], str] = {}

        if KEYBOARD_AVAILABLE and not KeyboardHotkeyAdapter._hook_installed_globally:
            if hasattr(keyboard, 'hook'):
                try:
                    keyboard.hook(self._global_key_event_handler)
                    KeyboardHotkeyAdapter._hook_installed_globally = True
                    logging.info("[KHA Init] Глобальный хук keyboard.hook УСТАНОВЛЕН.")
                except Exception as e:
                    logging.error(f"[KHA Init] Ошибка при установке глобального keyboard.hook: {e}")
            else:
                logging.error("[KHA Init] Функция 'hook' отсутствует в модуле 'keyboard'.")
        elif not KEYBOARD_AVAILABLE:
            logging.warning("KeyboardHotkeyAdapter: Библиотека 'keyboard' недоступна.")

    def _global_key_event_handler(self, event: keyboard.KeyboardEvent):
        if self._is_active:
            self._on_key_event(event)

    def _get_key_tuple_for_map(self, internal_key_part: str) -> Tuple[str, bool, bool]:
        """
        Преобразует внутреннее имя клавиши (из hotkey_config) в кортеж
        (имя_клавиши_от_keyboard, ожидаемый_флаг_is_keypad) для использования в качестве ключа карты.
        Возвращает (keyboard_name, is_keypad_expected, success_flag).
        """
        key_part_lower = internal_key_part.lower()

        # Numpad цифры (NumLock ON) - keyboard.name вернет просто цифру, is_keypad=True
        if key_part_lower.startswith("num_") and len(key_part_lower) == 5 and key_part_lower[4].isdigit():
            return (key_part_lower[4], True, True)  # e.g., ('0', True), ('1', True)

        # Numpad операторы
        # keyboard.name для них - это сам символ, is_keypad=True
        numpad_ops_map = {
            "num_divide": ("/", True),
            "num_multiply": ("*", True),
            "num_subtract": ("-", True), # keyboard.name для Numpad Minus это '-' (с is_keypad=True)
            "num_add": ("+", True),      # keyboard.name для Numpad Plus это '+' (с is_keypad=True)
            "num_decimal": (".", True),   # keyboard.name для Numpad Decimal это '.' (с is_keypad=True)
        }
        if key_part_lower in numpad_ops_map:
            kb_name, is_kp = numpad_ops_map[key_part_lower]
            return (kb_name, is_kp, True)

        # Клавиши стрелок (не Numpad) - is_keypad=False
        arrow_map = {
            "up": ("up", False), "down": ("down", False),
            "left": ("left", False), "right": ("right", False)
        }
        if key_part_lower in arrow_map:
            kb_name, is_kp = arrow_map[key_part_lower]
            return (kb_name, is_kp, True)

        # Другие стандартные клавиши - is_keypad обычно False
        standard_keys_map = {
             "tab": ("tab", False), # Tab сам по себе
             "esc": ("escape", False), "del": ("delete", False), "ins": ("insert", False),
             "pgup": ("page up", False), "pgdn": ("page down", False),
             "printscreen": ("print screen", False), "scrolllock": ("scroll lock", False),
             "pausebreak": ("pause", False), "enter": ("enter", False), "space": ("space", False),
             "backspace": ("backspace", False)
             # F-клавиши
        }
        for i in range(1, 13):
            standard_keys_map[f"f{i}"] = (f"f{i}", False)

        if key_part_lower in standard_keys_map:
            kb_name, is_kp = standard_keys_map[key_part_lower]
            return (kb_name, is_kp, True)

        # Если это одна буква или цифра (не Numpad, не F-клавиша)
        if len(key_part_lower) == 1 and key_part_lower.isalnum():
            return (key_part_lower, False, True) # is_keypad=False для основных букв/цифр

        logging.warning(f"[KHA _get_key_tuple] Не удалось определить кортеж для карты для ключа '{internal_key_part}'")
        return (key_part_lower, False, False) # Возвращаем как есть, is_keypad=False по умолчанию, неуспех

    def _build_tab_combo_map(self):
        self._tab_combo_map.clear()
        logging.debug("[KHA] Building Tab Combo Map...")
        for action_id, hotkey_str_internal in self._current_hotkeys_config.items():
            hotkey_str_lower = hotkey_str_internal.lower().strip()
            if hotkey_str_lower.startswith("tab+"):
                parts = hotkey_str_lower.split('+', 1)
                if len(parts) == 2:
                    internal_key_part = parts[1].strip()
                    # Получаем (keyboard_event_name, expected_is_keypad, success)
                    kb_name_for_map, is_keypad_expected, success = self._get_key_tuple_for_map(internal_key_part)

                    if success:
                        combo_key_tuple = (kb_name_for_map, is_keypad_expected)
                        if combo_key_tuple == ("tab", False): # Предотвращаем Tab+Tab
                             logging.warning(f"  [TabMap] Конфликт: Попытка зарегистрировать Tab+Tab для '{action_id}'. Пропуск.")
                             continue
                        self._tab_combo_map[combo_key_tuple] = action_id
                        logging.info(f"  [TabMap] Mapped ComboKey {combo_key_tuple} to action '{action_id}' (Original internal key part: '{internal_key_part}').")
                    else:
                        logging.warning(f"  [TabMap] Не удалось получить корректный кортеж для ключа '{internal_key_part}' (для Tab-комбинации действия '{action_id}').")
        logging.debug(f"[KHA] Tab Combo Map built with {len(self._tab_combo_map)} entries: {self._tab_combo_map}")


    def _on_key_event(self, event: keyboard.KeyboardEvent):
        event_type = event.event_type
        # Приводим имя клавиши к нижнему регистру для консистентности, если оно есть
        key_name = event.name.lower() if event.name else ""
        is_keypad = event.is_keypad
        scan_code = event.scan_code

        logging.debug(f"[KHA Event] Active: {self._is_active}. Type: {event_type}, Name: '{key_name}', IsKeypad: {is_keypad}, ScanCode: {scan_code}, TabPressed: {self._tab_is_pressed}")

        if key_name == "tab": # Сравниваем с нижним регистром
            self._tab_is_pressed = (event_type == keyboard.KEY_DOWN)
            logging.debug(f"  Tab state updated to: {'PRESSED' if self._tab_is_pressed else 'RELEASED'}")
            return

        if event_type == keyboard.KEY_DOWN and self._tab_is_pressed:
            current_key_tuple = (key_name, is_keypad)
            logging.debug(f"  Checking Tab combo map for: {current_key_tuple}")

            if current_key_tuple in self._tab_combo_map:
                action_id = self._tab_combo_map[current_key_tuple]
                logging.info(f">>> KHA MANUAL HOTKEY: Tab + ('{key_name}', isKP={is_keypad}) -> Action: '{action_id}'")
                self._execute_action_thread_safe(action_id)
            else:
                logging.debug(f"  Combo {current_key_tuple} not found in Tab combo map.")


    def load_and_register_hotkeys(self, hotkey_config_map: Dict[str, str]):
        logging.info(f"KHA: Загрузка и подготовка хоткеев.")
        with self._lock:
            self._current_hotkeys_config = hotkey_config_map.copy()
            self._build_tab_combo_map()
        self.hotkeys_updated_signal.emit()

    def _execute_action_thread_safe(self, action_id: str):
        if not self.main_window:
            logging.warning(f"KHA_EXEC: main_window был удален, действие '{action_id}' не может быть выполнено.")
            return
        try:
            if hasattr(self.main_window, '_emit_action_signal_slot') and callable(getattr(self.main_window, '_emit_action_signal_slot')):
                QMetaObject.invokeMethod(
                    self.main_window, "_emit_action_signal_slot",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, action_id)
                )
            else:
                logging.error(f"KHA_EXEC: Слот '_emit_action_signal_slot' не найден или не является вызываемым в main_window для '{action_id}'.")
        except RuntimeError as e: logging.error(f"KHA_EXEC: RuntimeError при вызове _emit_action_signal_slot для '{action_id}': {e}")
        except Exception as e_invoke: logging.error(f"KHA_EXEC: Неожиданная ошибка при QMetaObject.invokeMethod для '{action_id}': {e_invoke}", exc_info=True)

    def start_listening(self):
        logging.info("KHA: Активация обработчика хоткеев.")
        with self._lock:
            if self._is_active:
                logging.info("KHA: Обработчик уже активен.")
                return
            if KeyboardHotkeyAdapter._hook_installed_globally:
                self._is_active = True
                logging.info("KHA: Обработчик хоткеев отмечен как АКТИВНЫЙ.")
            elif KEYBOARD_AVAILABLE and hasattr(keyboard, 'hook'):
                try:
                    keyboard.hook(self._global_key_event_handler)
                    KeyboardHotkeyAdapter._hook_installed_globally = True
                    self._is_active = True
                    logging.info("[KHA StartListen] Глобальный хук keyboard.hook УСТАНОВЛЕН и обработчик АКТИВИРОВАН.")
                except Exception as e:
                    logging.error(f"[KHA StartListen] Ошибка при установке глобального keyboard.hook: {e}")
            else:
                logging.warning("KHA: Глобальный хук не установлен и не может быть установлен. Обработчик не будет активен.")

    def stop_listening(self, is_internal_restart=False):
        logging.info(f"KHA: Деактивация обработчика хоткеев (internal_restart={is_internal_restart}).")
        with self._lock:
            if not self._is_active and not is_internal_restart:
                logging.info("KHA: Обработчик уже неактивен.")
                return
            self._is_active = False
            self._tab_is_pressed = False
            logging.info("KHA: Обработчик хоткеев отмечен как НЕАКТИВНЫЙ. Состояние Tab сброшено.")

    def shutdown_hook(self):
        if KEYBOARD_AVAILABLE and KeyboardHotkeyAdapter._hook_installed_globally:
            if hasattr(keyboard, 'unhook_all'):
                try:
                    keyboard.unhook_all()
                    logging.info("[KHA Shutdown] Все хуки keyboard.hook удалены через unhook_all().")
                except Exception as e:
                    logging.error(f"[KHA Shutdown] Ошибка при вызове keyboard.unhook_all(): {e}")
            KeyboardHotkeyAdapter._hook_installed_globally = False

    def clear_pressed_keys_state(self):
        logging.debug("KHA: clear_pressed_keys_state вызван. Сброс состояния Tab.")
        self._tab_is_pressed = False

    def get_current_hotkeys_config_for_settings(self) -> Dict[str, str]:
        with self._lock:
            return self._current_hotkeys_config.copy()

    def get_default_hotkeys_config_for_settings(self) -> Dict[str, str]:
        from core.hotkey_config import DEFAULT_HOTKEYS
        return DEFAULT_HOTKEYS.copy()
