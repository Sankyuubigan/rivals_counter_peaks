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
from core.lang.translations import get_text


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
            }
        ]

        # Регистрируем хоткеи
        try:
            register_hotkeys(self.bindings)
            start_checking_hotkeys()
            logging.info("Глобальные хоткеи зарегистрированы: TAB (toggle), TAB+0 (распознавание)")
        except Exception as e:
            logging.error(f"Ошибка регистрации хоткеев: {e}")

    def on_tab_press(self):
        """Обработчик нажатия TAB - вход в режим таба"""
        if not self.tab_pressed:
            with self._lock:
                self.tab_pressed = True
                logging.info("TAB нажат - переход в режим таба")

                # Запускаем режим таба через Qt поток
                QMetaObject.invokeMethod(self.main_window, "enable_tab_mode",
                                       Qt.ConnectionType.QueuedConnection)

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