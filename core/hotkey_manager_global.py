# File: core/hotkey_manager_global.py
import logging
import threading
from typing import Dict, Callable, Any
import time

from PySide6.QtCore import QObject, Signal, Slot, QMetaObject, Q_ARG

# Import global_hotkeys based on test example
try:
    from PySide6.QtCore import Qt
    from global_hotkeys import *
    GLOBAL_HOTKEYS_AVAILABLE = True
except ImportError:
    GLOBAL_HOTKEYS_AVAILABLE = False
    logging.error("HotkeyManagerGlobal: 'global_hotkeys' library not found.")

from core.app_settings_manager import AppSettingsManager
from info.translations import get_text


class HotkeyManagerGlobal(QObject):
    """Новая система хоткеев на базе global_hotkeys (замена pynput)"""

    hotkeys_updated_signal = Signal()

    def __init__(self, main_window: QObject, app_settings_manager: AppSettingsManager):
        super().__init__()
        self.main_window = main_window
        self.app_settings_manager = app_settings_manager

        self.tab_pressed = False
        self._hotkey_thread: threading.Thread = None
        self._lock = threading.Lock()

        # Регистрируем хоткеи как в тесте
        self._setup_hotkeys()

        self._start_hotkey_listener()

    def _setup_hotkeys(self):
        """Настройка глобальных хоткеев для режима таба"""
        if not GLOBAL_HOTKEYS_AVAILABLE:
            logging.error("Невозможно настроить хоткеи - global_hotkeys не найден")
            return

        # Определяем биндинги точно как в тесте
        self.bindings = [
            {
                "hotkey": "tab",
                "on_press_callback": self.on_tab_press,
                "on_release_callback": self.on_tab_release,
                "actuate_on_partial_release": False,
            },
            {
                "hotkey": "0",
                "on_press_callback": self.on_zero_press,
                "on_release_callback": None,
                "actuate_on_partial_release": False,
            },
            {
                "hotkey": "right",
                "on_press_callback": self.on_arrow_right_press,
                "on_release_callback": None,
                "actuate_on_partial_release": False,
            },
            {
                "hotkey": "left",
                "on_press_callback": self.on_arrow_left_press,
                "on_release_callback": None,
                "actuate_on_partial_release": False,
            },
            {
                "hotkey": "up",
                "on_press_callback": self.on_arrow_up_press,
                "on_release_callback": None,
                "actuate_on_partial_release": False,
            },
            {
                "hotkey": "down",
                "on_press_callback": self.on_arrow_down_press,
                "on_release_callback": None,
                "actuate_on_partial_release": False,
            }
        ]

        # Регистрируем хоткеи
        logging.info("Начинаем регистрацию глобальных хоткеев...")
        try:
            register_hotkeys(self.bindings)
            start_checking_hotkeys()
            logging.info("Глобальные хоткеи зарегистрированы: TAB (toggle), TAB+0 (распознавание), TAB+стрелки (перемещение окна)")
            logging.debug(f"Bindings registered: {len(self.bindings)} hotkeys")
            for binding in self.bindings:
                logging.debug(f"Hotkey binding: {binding['hotkey']} -> {binding.get('on_press_callback', '').__name__ if binding.get('on_press_callback') else 'None'}")
        except Exception as e:
            logging.error(f"Ошибка регистрации хоткеев: {e}", exc_info=True)

    def on_tab_press(self):
        """Обработчик нажатия TAB - вход в режим таба"""
        logging.debug(f"TAB press callback called, current tab_pressed={self.tab_pressed}")
        if not self.tab_pressed:
            with self._lock:
                self.tab_pressed = True
                logging.info("TAB нажат - переход в режим таба")

                # Запускаем режим таба через Qt поток
                logging.debug("TAB: invoking enable_tab_mode")
                try:
                    QMetaObject.invokeMethod(self.main_window, "enable_tab_mode",
                                           Qt.ConnectionType.QueuedConnection)
                    logging.debug("TAB: enable_tab_mode invokeMethod called successfully")
                except Exception as e:
                    logging.error(f"TAB: Error in QMetaObject.invokeMethod for enable_tab_mode: {e}")

    def on_tab_release(self):
        """Обработчик отпускания TAB - выход из режима таба"""
        if self.tab_pressed:
            with self._lock:
                self.tab_pressed = False
                logging.info("TAB отпущен - выход из режима таба")

                # Выключаем режим таба через Qt поток
                QMetaObject.invokeMethod(self.main_window, "disable_tab_mode",
                                       Qt.ConnectionType.QueuedConnection)

    def on_zero_press(self):
        """Обработчик нажатия 0 при зажатом TAB - запуск распознавания"""
        if self.tab_pressed:
            logging.info("TAB+0 нажат - запуск распознавания героев")

            # Запускаем распознавание через Qt сигнал
            QMetaObject.invokeMethod(self.main_window, "trigger_tab_recognition",
                                    Qt.ConnectionType.QueuedConnection)
        else:
            # TAB не зажат - игнорируем
            pass

    def on_arrow_right_press(self):
        """Обработчик нажатия Right при зажатом TAB - перемещение окна вправо"""
        logging.debug(f"TAB+Right callback called, tab_pressed={self.tab_pressed}")
        if self.tab_pressed:
            logging.info("TAB+Right нажат - перемещение окна вправо")

            # Эмитим сигналы через Qt для изменения курсора или положения окна
            logging.debug("TAB+Right: invoking _emit_action_signal_slot for move_cursor_right")
            try:
                QMetaObject.invokeMethod(self.main_window, "_emit_action_signal_slot",
                                        Qt.ConnectionType.QueuedConnection,
                                        Q_ARG(str, "move_cursor_right"))
                logging.debug("TAB+Right: QMetaObject.invokeMethod called successfully")
            except Exception as e:
                logging.error(f"TAB+Right: Error in QMetaObject.invokeMethod: {e}")
        else:
            # TAB не зажат - игнорируем
            logging.debug("TAB+Right ignored - TAB not pressed")
            pass

    def on_arrow_left_press(self):
        """Обработчик нажатия Left при зажатом TAB - перемещение окна влево"""
        logging.debug(f"TAB+Left callback called, tab_pressed={self.tab_pressed}")
        if self.tab_pressed:
            logging.info("TAB+Left нажат - перемещение окна влево")

            logging.debug("TAB+Left: invoking _emit_action_signal_slot for move_cursor_left")
            try:
                QMetaObject.invokeMethod(self.main_window, "_emit_action_signal_slot",
                                        Qt.ConnectionType.QueuedConnection,
                                        Q_ARG(str, "move_cursor_left"))
                logging.debug("TAB+Left: QMetaObject.invokeMethod called successfully")
            except Exception as e:
                logging.error(f"TAB+Left: Error in QMetaObject.invokeMethod: {e}")
        else:
            # TAB не зажат - игнорируем
            logging.debug("TAB+Left ignored - TAB not pressed")
            pass

    def on_arrow_up_press(self):
        """Обработчик нажатия Up при зажатом TAB - перемещение окна вверх"""
        logging.debug(f"TAB+Up callback called, tab_pressed={self.tab_pressed}")
        if self.tab_pressed:
            logging.info("TAB+Up нажат - перемещение окна вверх")

            logging.debug("TAB+Up: invoking _emit_action_signal_slot for move_cursor_up")
            try:
                QMetaObject.invokeMethod(self.main_window, "_emit_action_signal_slot",
                                        Qt.ConnectionType.QueuedConnection,
                                        Q_ARG(str, "move_cursor_up"))
                logging.debug("TAB+Up: QMetaObject.invokeMethod called successfully")
            except Exception as e:
                logging.error(f"TAB+Up: Error in QMetaObject.invokeMethod: {e}")
        else:
            # TAB не зажат - игнорируем
            logging.debug("TAB+Up ignored - TAB not pressed")
            pass

    def on_arrow_down_press(self):
        """Обработчик нажатия Down при зажатом TAB - перемещение окна вниз"""
        logging.debug(f"TAB+Down callback called, tab_pressed={self.tab_pressed}")
        if self.tab_pressed:
            logging.info("TAB+Down нажат - перемещение окна вниз")

            logging.debug("TAB+Down: invoking _emit_action_signal_slot for move_cursor_down")
            try:
                QMetaObject.invokeMethod(self.main_window, "_emit_action_signal_slot",
                                        Qt.ConnectionType.QueuedConnection,
                                        Q_ARG(str, "move_cursor_down"))
                logging.debug("TAB+Down: QMetaObject.invokeMethod called successfully")
            except Exception as e:
                logging.error(f"TAB+Down: Error in QMetaObject.invokeMethod: {e}")
        else:
            # TAB не зажат - игнорируем
            logging.debug("TAB+Down ignored - TAB not pressed")
            pass

    def _start_hotkey_listener(self):
        """Запуск слушателя хоткеев в отдельном потоке"""
        if GLOBAL_HOTKEYS_AVAILABLE:
            self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
            self._hotkey_thread.start()
            logging.info("Поток слушателя хоткеев запущен")

    def _hotkey_loop(self):
        """Основной цикл проверки хоткеев"""
        while True:
            time.sleep(0.01)  # Маленькая задержка

    def stop(self):
        """Остановка слушателя"""
        if GLOBAL_HOTKEYS_AVAILABLE:
            try:
                stop_checking_hotkeys()
                logging.info("Глобальные хоткеи остановлены")
            except Exception as e:
                logging.error(f"Ошибка остановки хоткеев: {e}")

        if self._hotkey_thread and self._hotkey_thread.is_alive():
            self._hotkey_thread.join(timeout=1.0)

    def is_tab_mode_active(self) -> bool:
        """Проверка активен ли режим таба"""
        return self.tab_pressed