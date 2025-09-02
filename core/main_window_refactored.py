"""
Рефакторинговая версия MainWindow
"""
import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
from core.ui_base import BaseWindow
from core.window_manager import WindowManager
from core.ui_state_manager import UIStateManager, UIState
from core.event_bus import event_bus
from core.image_manager import ImageManager
from core.hotkey_manager import HotkeyManager
from core.app_settings_manager import AppSettingsManager
from core.recognition import RecognitionManager
from core.action_controller import ActionController
from core.ui_updater import UiUpdater
# Импорты панелей
from core.top_panel import TopPanel
from core.left_panel import LeftPanel
from core.right_panel import RightPanel
from core.config import USE_REFACTORED_ARCHITECTURE

class MainWindowRefactored(BaseWindow):
    """Рефакторинговая версия главного окна"""
    
    def __init__(self, logic_instance, app_version: str = "1.0.0"):
        super().__init__()
        
        # Основные компоненты
        self.logic = logic_instance
        self.app_version = app_version
        self.logic.main_window = self
        
        # Менеджеры
        self.settings_manager = AppSettingsManager()
        self.image_manager = ImageManager(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        self.hotkey_manager = HotkeyManager(self, self.settings_manager)
        self.window_manager = WindowManager(self)
        self.ui_state_manager = UIStateManager()
        
        # UI компоненты
        self.top_panel: Optional[TopPanel] = None
        self.left_panel: Optional[LeftPanel] = None
        self.right_panel: Optional[RightPanel] = None
        self.ui_updater: Optional[UiUpdater] = None
        
        # Состояние
        self.hotkey_cursor_index = -1
        self.hero_items: Dict[str, Any] = {}
        
        # Распознавание
        self.recognition_manager = RecognitionManager(self, self.logic, None)
        
        # Инициализация
        self._init_ui()
        self._connect_signals()
        self._load_settings()
        
        self.logger.info("MainWindow initialized successfully")
    
    def _setup_ui(self):
        """Настройка UI"""
        super()._setup_ui()
        
        # Создаем панели
        self.top_panel = TopPanel(self, self.change_mode, self.logic, self.app_version)
        self.left_panel = LeftPanel(self.main_widget)
        self.right_panel = RightPanel(self, "middle")
        
        # Добавляем панели в основной layout
        self.main_layout.addWidget(self.top_panel)
        
        # Создаем контейнер для основного контента
        self.content_container = QWidget()
        self.content_layout = QHBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.content_layout.addWidget(self.left_panel)
        self.content_layout.addWidget(self.right_panel, stretch=1)
        
        self.main_layout.addWidget(self.content_container)
        
        # Инициализируем UI updater
        self.ui_updater = UiUpdater(self)
    
    def _connect_signals(self):
        """Подключение сигналов"""
        super()._connect_signals()
        
        # Сигналы от менеджера хоткеев
        self.hotkey_manager.hotkey_pressed.connect(self._on_hotkey_pressed)
        
        # Сигналы от EventBus
        event_bus.subscribe("ui_state_changed", self._on_ui_state_changed)
        event_bus.subscribe("recognition_completed", self._on_recognition_completed)
        
        # Сигналы от action controller
        self.action_controller = ActionController(self)
    
    def _load_settings(self):
        """Загрузка настроек"""
        # Устанавливаем тему
        theme = self.settings_manager.get_theme()
        self.switch_theme(theme)
        
        # Устанавливаем язык
        language = self.settings_manager.get_language()
        self.switch_language(language)
        
        # Восстанавливаем геометрию
        geometry = self.settings_manager.get_tab_geometry()
        if geometry:
            self.window_manager.set_window_geometry(QRect(
                geometry['x'], geometry['y'],
                geometry['width'], geometry['height']
            ))
    
    def _on_hotkey_pressed(self, action_id: str):
        """Обработка нажатия хоткея"""
        self.logger.debug(f"Hotkey pressed: {action_id}")
        
        # Маршрутизация действий
        action_routes = {
            "move_cursor_up": lambda: self.action_controller.handle_move_cursor('up'),
            "move_cursor_down": lambda: self.action_controller.handle_move_cursor('down'),
            "move_cursor_left": lambda: self.action_controller.handle_move_cursor('left'),
            "move_cursor_right": lambda: self.action_controller.handle_move_cursor('right'),
            "toggle_selection": self.action_controller.handle_toggle_selection,
            "toggle_mode": self.toggle_mode,
            "recognize_heroes": self.trigger_recognition,
            "clear_all": self.action_controller.handle_clear_all,
            "copy_team": self.action_controller.handle_copy_team,
            "debug_capture": self.action_controller.handle_debug_capture,
            "decrease_opacity": self.decrease_opacity,
            "increase_opacity": self.increase_opacity,
            "toggle_tab_mode": self.ui_state_manager.toggle_tab_mode
        }
        
        if action_id in action_routes:
            action_routes[action_id]()
    
    def _on_ui_state_changed(self, new_state: UIState, data: Optional[Dict[str, Any]]):
        """Обработка изменения состояния UI"""
        self.logger.info(f"UI state changed to: {new_state.value}")
        
        # Обновляем UI в соответствии с новым состоянием
        if self.ui_updater:
            self.ui_updater.update_interface_for_mode(new_state.value)
    
    def _on_recognition_completed(self, recognized_heroes: list):
        """Обработка завершения распознавания"""
        self.logger.info(f"Recognition completed: {recognized_heroes}")
        
        # Обновляем выбранных героев
        if recognized_heroes and hasattr(self.logic, 'set_selection'):
            self.logic.set_selection(set(recognized_heroes))
            
            # Обновляем UI
            if self.ui_updater:
                self.ui_updater.update_ui_after_logic_change()
    
    def change_mode(self, mode: str):
        """Сменить режим приложения"""
        self.logger.info(f"Changing mode to: {mode}")
        
        # Уведомляем о смене режима
        event_bus.emit("mode_changed", mode)
    
    def switch_theme(self, theme: str):
        """Переключить тему"""
        self.logger.info(f"Switching theme to: {theme}")
        
        # Сохраняем настройку
        self.settings_manager.set_theme(theme)
        
        # Уведомляем об изменении темы
        event_bus.emit("theme_changed", theme)
    
    def switch_language(self, language: str):
        """Переключить язык"""
        self.logger.info(f"Switching language to: {language}")
        
        # Сохраняем настройку
        self.settings_manager.set_language(language)
        
        # Уведомляем об изменении языка
        event_bus.emit("language_changed", language)
    
    def trigger_recognition(self):
        """Запустить распознавание"""
        self.logger.info("Triggering recognition")
        
        if hasattr(self.recognition_manager, 'recognize_heroes_signal'):
            self.recognition_manager.recognize_heroes_signal.emit()
    
    def decrease_opacity(self):
        """Уменьшить прозрачность"""
        current_opacity = self.windowOpacity()
        new_opacity = max(0.1, current_opacity - 0.1)
        self.setWindowOpacity(new_opacity)
    
    def increase_opacity(self):
        """Увеличить прозрачность"""
        current_opacity = self.windowOpacity()
        new_opacity = min(1.0, current_opacity + 0.1)
        self.setWindowOpacity(new_opacity)
    
    def show_settings(self):
        """Показать окно настроек"""
        from core.settings_window import SettingsWindow
        
        settings_window = SettingsWindow(self.settings_manager, self)
        settings_window.settings_applied_signal.connect(self._on_settings_applied)
        settings_window.exec()
    
    def _on_settings_applied(self):
        """Обработка применения настроек"""
        self.logger.info("Settings applied")
        
        # Перезагружаем настройки
        self._load_settings()
        
        # Уведомляем об изменении настроек
        event_bus.emit("settings_changed", "all", None)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.logger.info("Closing application")
        
        # Сохраняем текущую позицию
        self.window_manager.save_current_position()
        
        # Останавливаем сервисы
        if hasattr(self, 'hotkey_manager'):
            self.hotkey_manager.stop()
        
        if hasattr(self, 'recognition_manager'):
            self.recognition_manager.stop_recognition()
        
        # Сохраняем настройки
        self.settings_manager.save_settings()
        
        super().closeEvent(event)
    
    def showEvent(self, event):
        """Обработка показа окна"""
        super().showEvent(event)
        
        # Центрируем окно при первом показе
        if not self.window_manager.mode_positions:
            self.window_manager.center_on_screen()
    
    def keyPressEvent(self, event):
        """Обработка нажатия клавиш"""
        # Блокируем обработку Tab для предотвращения потери фокуса
        if event.key() == Qt.Key_Tab:
            return
        
        super().keyPressEvent(event)