# File: core/appearance_manager.py
import logging
from PySide6.QtWidgets import QApplication, QDialog 
from info.translations import SUPPORTED_LANGUAGES, set_language as set_global_language, get_text
from core.app_settings_manager import AppSettingsManager
from info.translations import DEFAULT_LANGUAGE as DEFAULT_LANG_VALUE

class AppearanceManager:
    def __init__(self, main_window, app_settings_manager: AppSettingsManager):
        self.mw = main_window
        self.app_settings_manager = app_settings_manager
        
        self.current_theme = self.app_settings_manager.get_theme()
        self.current_language = self.app_settings_manager.get_language()
        
        if self.current_language not in SUPPORTED_LANGUAGES:
            logging.warning(f"Загружен неподдерживаемый язык '{self.current_language}', используется язык по умолчанию '{DEFAULT_LANG_VALUE}'.")
            self.current_language = DEFAULT_LANG_VALUE
            self.app_settings_manager.set_language(self.current_language) 
        
        set_global_language(self.current_language)
        if hasattr(self.mw, 'logic') and self.mw.logic: 
            self.mw.logic.DEFAULT_LANGUAGE = self.current_language
        logging.info(f"AppearanceManager инициализирован. Тема: {self.current_theme}, Язык: {self.current_language}")

    def _update_language_and_theme_for_all_components(self):
        """Централизованный метод для обновления всех UI компонентов."""
        logging.debug("Обновление языка и темы для всех компонентов...")
        
        # Обновление заголовка главного окна
        try:
            if hasattr(self.mw, 'mode') and self.mw.mode != "min": 
                app_ver = getattr(self.mw, 'app_version', '?.?.?')
                self.mw.setWindowTitle(f"{get_text('title')} v{app_ver}") 
        except RuntimeError:
            logging.warning("MainWindow было удалено до обновления заголовка.")
            return

        # Обновление вкладок
        if hasattr(self.mw, 'tab_widget'):
            # TODO: Добавить логику обновления заголовков вкладок, если они не обновляются автоматически
            pass

        # Обновление специфичных для языка/темы виджетов внутри вкладок
        if hasattr(self.mw, 'settings_tab') and hasattr(self.mw.settings_tab, 'update_language_and_theme'):
             self.mw.settings_tab.update_language_and_theme()
        
        if hasattr(self.mw, 'tier_list_tab') and hasattr(self.mw.tier_list_tab, 'update_language_and_theme'):
             self.mw.tier_list_tab.update_language_and_theme()

        # Обновление правой панели (если она создана)
        if hasattr(self.mw, 'right_panel_instance') and self.mw.right_panel_instance:
            self.mw.right_panel_instance.update_language()

        # Обновление UI через UiUpdater
        if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
            self.mw.ui_updater.update_ui_after_logic_change()
            if hasattr(self.mw, 'hotkey_cursor_index') and self.mw.hotkey_cursor_index != -1:
                 self.mw.ui_updater.update_hotkey_highlight()

    def switch_language(self, lang_code: str):
        if lang_code not in SUPPORTED_LANGUAGES:
            logging.warning(f"Попытка переключиться на неподдерживаемый язык: {lang_code}")
            return
        if self.current_language == lang_code:
            return

        logging.info(f"Переключение языка на: {lang_code}")
        self.current_language = lang_code
        set_global_language(self.current_language)
        
        if hasattr(self.mw, 'logic') and self.mw.logic:
            self.mw.logic.DEFAULT_LANGUAGE = self.current_language
        
        self.app_settings_manager.set_language(self.current_language)
        self._update_language_and_theme_for_all_components()

    def switch_theme(self, theme_name: str):
        if theme_name not in ["light", "dark"]:
            logging.warning(f"Неизвестная тема: {theme_name}. Переключение отменено.")
            return
        
        if self.current_theme == theme_name:
            logging.debug(f"Тема уже установлена: {theme_name}. Принудительное обновление.")
        else:
            logging.info(f"Переключение темы на: {theme_name}")
            self.current_theme = theme_name
            self.app_settings_manager.set_theme(self.current_theme)

        self._apply_qss_theme_globally(self.current_theme)
        self._update_language_and_theme_for_all_components()

    def _apply_qss_theme_globally(self, theme_name: str, on_startup=False):
        """Применяет QSS стиль ко всему приложению."""
        logging.info(f"AppearanceManager: Применение QSS темы: {theme_name}")
        light_qss = """
            QMainWindow, QDialog, QWidget { background-color: #f0f0f0; color: black; }
            QTextBrowser { background-color: white; color: black; border: 1px solid #cccccc; }
            QLabel { color: black; }
            QPushButton { background-color: #e1e1e1; border: 1px solid #adadad; color: black; padding: 3px; border-radius: 3px; }
            QPushButton:hover { background-color: #ebebeb; }
            QPushButton:pressed { background-color: #d1d1d1; }
            QListWidget { background-color: white; border: 1px solid #d3d3d3; color: black; }
            QListWidget::item { color: black; border-radius: 4px; border: 1px solid transparent; background-color: transparent; text-align: center; }
            QListWidget::item:selected { background-color: #FFD700; color: white; border: 4px solid #FF4500; }
            QListWidget::item:!selected:hover { background-color: #e0f7ff; border: 1px solid #cceeff; }
            QMenu { background-color: #f8f8f8; border: 1px solid #cccccc; color: black; }
            QMenu::item:selected { background-color: #3399ff; color: white; }
            QLineEdit { background-color: white; color: black; border: 1px solid #cccccc; padding: 2px; border-radius: 3px;}
            QComboBox { background-color: white; color: black; border: 1px solid #cccccc; padding: 2px; border-radius: 3px; }
            QComboBox QAbstractItemView { background-color: white; color: black; selection-background-color: #3399ff; }
            QCheckBox { color: black; }
            QTabWidget::pane { border: 1px solid #cccccc; background-color: #f0f0f0;}
            QTabBar::tab { background: #e1e1e1; border: 1px solid #adadad; padding: 5px; color: black; border-bottom: none; }
            QTabBar::tab:selected { background: #f0f0f0; }
            QTabBar::tab:!selected:hover { background: #ebebeb; }
            QFrame#left_frame_container { background-color: #f7f7f7; }
        """
        dark_qss = """
            QMainWindow, QDialog, QWidget { background-color: #2e2e2e; color: #e0e0e0; }
            QTextBrowser { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; }
            QLabel { color: #e0e0e0; }
            QPushButton { background-color: #484848; border: 1px solid #5a5a5a; color: #e0e0e0; padding: 3px; border-radius: 3px; }
            QPushButton:hover { background-color: #585858; }
            QPushButton:pressed { background-color: #383838; }
            QListWidget { background-color: #252525; border: 1px solid #454545; color: #d0d0d0; }
            QListWidget::item { color: #d0d0d0; border-radius: 4px; border: 1px solid transparent; background-color: transparent; text-align: center;}
            QListWidget::item:selected { background-color: #FFD700; color: white; border: 4px solid #FF4500; }
            QListWidget::item:!selected:hover { background-color: #3a3a3a; border: 1px solid #4f4f4f; }
            QMenu { background-color: #383838; border: 1px solid #4f4f4f; color: #e0e0e0; }
            QMenu::item:selected { background-color: #0078d7; color: white; }
            QLineEdit { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; padding: 2px; border-radius: 3px;}
            QComboBox { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; padding: 2px; border-radius: 3px; }
            QComboBox QAbstractItemView { background-color: #252525; color: #d0d0d0; selection-background-color: #0078d7; }
            QCheckBox { color: #e0e0e0; }
            QTabWidget::pane { border: 1px solid #454545; background-color: #2e2e2e;}
            QTabBar::tab { background: #484848; border: 1px solid #5a5a5a; padding: 5px; color: #e0e0e0; border-bottom: none; }
            QTabBar::tab:selected { background: #2e2e2e; }
            QTabBar::tab:!selected:hover { background: #585858; }
            QFrame#left_frame_container { background-color: #2a2a2a; }
        """
        qss = light_qss if theme_name == "light" else dark_qss
        
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)