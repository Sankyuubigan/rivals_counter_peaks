"""
Рефакторинговая версия MainWindow, использующая менеджеры, событийную модель и интерфейс на вкладках.
"""
import logging
import sys
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextBrowser, QStatusBar)
from PySide6.QtCore import Slot, Qt, QObject
from PySide6.QtGui import QCloseEvent

# Основные компоненты и менеджеры
from core.logic import CounterpickLogic
from core.app_settings_manager import AppSettingsManager
from core.image_manager import ImageManager
from core.hotkey_manager import HotkeyManager
from core.recognition import RecognitionManager
from core.action_controller import ActionController
from core.ui_updater import UiUpdater
from core.mode_manager import ModeManager
from core.tab_mode_manager import TrayModeManager
from core.event_bus import event_bus
from core.log_handler import QLogHandler
from core.utils import normalize_hero_name

# UI панели и вкладки
from core.left_panel import create_left_panel
from core.right_panel import RightPanel
from core.settings_window import SettingsWindow
from core.dialogs import LogDialog
from info.translations import get_text
import markdown

class InfoTab(QWidget):
    """Виджет-вкладка для отображения markdown контента."""
    def __init__(self, md_file_base_name: str, parent=None):
        super().__init__(parent)
        self.md_file_base_name = md_file_base_name
        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        layout.addWidget(self.text_browser)
        self.update_content()

    def update_content(self):
        lang_code = "ru" 
        md_filename = f"{self.md_file_base_name}_{lang_code}.md"
        
        try:
            from core.utils import resource_path
            md_filepath = resource_path(os.path.join('info', md_filename))
            with open(md_filepath, "r", encoding="utf-8") as f:
                md_content = f.read()
            html = markdown.markdown(md_content)
            self.text_browser.setHtml(html)
        except Exception as e:
            logging.error(f"Failed to load info tab content for {self.md_file_base_name}: {e}")
            self.text_browser.setText(f"Error loading content: {e}")


class MainWindowRefactored(QMainWindow):
    """
    Основное окно приложения, построенное по модульному принципу.
    """
    
    def __init__(self, logic_instance: CounterpickLogic, log_handler: QLogHandler, app_version: str = "1.0.0"):
        super().__init__()
        logging.info("Initializing MainWindowRefactored...")

        self.logic = logic_instance
        self.app_version = app_version
        self.logic.main_window = self
        self.log_handler = log_handler # Сохраняем переданный обработчик

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.settings_manager = AppSettingsManager()
        self.image_manager = ImageManager(project_root)
        self.hotkey_manager = HotkeyManager(self.settings_manager)
        self.mode_manager = ModeManager(self)
        self.recognition_manager = RecognitionManager(self, self.logic, None)
        self.tab_mode_manager = TrayModeManager(self)
        
        self.action_controller = ActionController(self)
        self.ui_updater = UiUpdater(self)
        
        self.mode = self.mode_manager.current_mode
        self.hotkey_cursor_index = -1
        self.hero_items = {}
        
        self._init_ui()
        self._connect_signals()
        self._load_initial_state()

        logging.info("MainWindowRefactored initialized successfully.")

    def _init_ui(self):
        self.setWindowTitle(f"Rivals Counter Peaks v{self.app_version}")
        self.resize(1100, 800)
        
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        # Система вкладок теперь является основным элементом навигации
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # 1. Вкладка "Контрпики"
        self._create_counter_pick_tab()

        # 2. Вкладка "Настройки"
        self.settings_tab = SettingsWindow(self.settings_manager, self)
        self.tab_widget.addTab(self.settings_tab, get_text("sw_settings_tab_title", default_text="Настройки"))

        # 3. Вкладка "Логи"
        self.log_tab = LogDialog(self)
        self.tab_widget.addTab(self.log_tab, get_text("logs_window_title"))
        
        # ИСПРАВЛЕНИЕ БАГА С ЛОГАМИ: Подключаем переданный обработчик
        if self.log_handler and hasattr(self.log_handler, 'message_logged'):
            self.log_handler.message_logged.connect(self.log_tab.append_log)
            logging.info("Successfully connected QLogHandler to the log tab.")
        else:
            logging.warning("Log handler was not provided or is invalid.")

        # 4. Вкладка "О программе"
        self.about_tab = InfoTab("information")
        self.tab_widget.addTab(self.about_tab, get_text("about_program"))

        # 5. Вкладка "Об авторе"
        self.author_tab = InfoTab("author")
        self.tab_widget.addTab(self.author_tab, get_text("author_info_title"))

        # Строка состояния для версии
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"v{self.app_version}")

    def _create_counter_pick_tab(self):
        """Создает содержимое для основной вкладки 'Контрпики'."""
        self.counter_pick_tab = QWidget()
        self.counter_pick_layout = QHBoxLayout(self.counter_pick_tab)
        self.counter_pick_layout.setContentsMargins(0, 0, 0, 0)
        self.counter_pick_layout.setSpacing(0)
        self.tab_widget.addTab(self.counter_pick_tab, get_text("counter_picks_tab_title", default_text="Контрпики"))

    def _connect_signals(self):
        """Подключает все необходимые сигналы и слоты."""
        self.hotkey_manager.hotkey_triggered.connect(self._on_hotkey_pressed)
        self.recognition_manager.recognition_complete_signal.connect(self._on_recognition_complete)

    def _load_initial_state(self):
        self.ui_updater.update_interface_for_mode(self.mode)

    @Slot(str)
    def _on_hotkey_pressed(self, action_id: str):
        logging.debug(f"Hotkey event received in main thread: {action_id}")
        
        actions = {
            "enter_tab_mode": lambda: (
                self.tab_mode_manager.enable(),
                self.recognition_manager.recognize_heroes_signal.emit()
            ),
            "exit_tab_mode": self.tab_mode_manager.disable,
            "recognize_heroes": self.recognition_manager.recognize_heroes_signal.emit,
            "move_cursor_up": lambda: self.action_controller.handle_move_cursor('up'),
            "move_cursor_down": lambda: self.action_controller.handle_move_cursor('down'),
            "move_cursor_left": lambda: self.action_controller.handle_move_cursor('left'),
            "move_cursor_right": lambda: self.action_controller.handle_move_cursor('right'),
            "toggle_selection": self.action_controller.handle_toggle_selection,
            "clear_all": self.action_controller.handle_clear_all,
            "copy_team": self.action_controller.handle_copy_team,
            "debug_capture": self.action_controller.handle_debug_capture,
        }
        
        action = actions.get(action_id)
        if action:
            action()

    @Slot(list)
    def _on_recognition_complete(self, recognized_heroes: list):
        logging.info(f"Recognition completed with heroes: {recognized_heroes}")
        # ИСПРАВЛЕНИЕ: Нормализуем имена героев, полученные после распознавания
        normalized_heroes = {normalize_hero_name(h) for h in recognized_heroes if h}
        logging.info(f"Normalized recognized heroes to: {normalized_heroes}")
        self.logic.set_selection(normalized_heroes)
        self.ui_updater.update_ui_after_logic_change()

    def change_mode(self, new_mode: str):
        logging.debug(f"change_mode called with {new_mode}, but window modes are removed.")
        pass
            
    def show_tab(self, tab_name: str):
        """Переключается на указанную вкладку."""
        tabs = {
            "settings": self.settings_tab,
            "logs": self.log_tab,
            "about": self.about_tab,
            "author": self.author_tab,
        }
        tab_widget = tabs.get(tab_name)
        if tab_widget:
            self.tab_widget.setCurrentWidget(tab_widget)
            
    def closeEvent(self, event: QCloseEvent):
        logging.info("Closing application...")
        self.hotkey_manager.stop()
        self.recognition_manager.stop_recognition()
        self.settings_manager.save_settings()
        QApplication.instance().quit()
        super().closeEvent(event)