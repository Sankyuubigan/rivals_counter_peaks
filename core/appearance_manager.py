# File: core/appearance_manager.py
import logging
import json
from PySide6.QtWidgets import QApplication, QDialog 

from core.lang.translations import SUPPORTED_LANGUAGES, set_language as set_global_language, get_text
from core.utils import get_settings_path 

class AppearanceManager:
    def __init__(self, main_window):
        self.mw = main_window
        self.current_theme = "light" 
        self.current_language = "ru_RU" 

        self._load_settings()

    def _get_app_settings_path(self):
        app_data_dir = get_settings_path().parent 
        return app_data_dir / "app_settings.json"

    def _load_settings(self):
        settings_file = self._get_app_settings_path()
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self.current_theme = settings.get("theme", "light")
                loaded_lang = settings.get("language", "ru_RU")
                if loaded_lang in SUPPORTED_LANGUAGES:
                    self.current_language = loaded_lang
                else:
                    logging.warning(f"Loaded unsupported language '{loaded_lang}', falling back to ru_RU.")
                    self.current_language = "ru_RU"
                
                set_global_language(self.current_language) 
                if hasattr(self.mw, 'logic') and self.mw.logic: 
                    self.mw.logic.DEFAULT_LANGUAGE = self.current_language

                logging.info(f"Appearance settings loaded. Theme: {self.current_theme}, Language: {self.current_language}")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading appearance settings from {settings_file}: {e}. Using defaults.")
                self._set_defaults_and_apply()
        else:
            logging.info("Appearance settings file not found. Using default settings.")
            self._set_defaults_and_apply()

    def _set_defaults_and_apply(self):
        self.current_theme = "light"
        self.current_language = "ru_RU"
        set_global_language(self.current_language)
        if hasattr(self.mw, 'logic') and self.mw.logic:
            self.mw.logic.DEFAULT_LANGUAGE = self.current_language


    def _save_settings(self):
        settings_file = self._get_app_settings_path()
        settings_to_save = {
            "theme": self.current_theme,
            "language": self.current_language
        }
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
            logging.info(f"Appearance settings saved to {settings_file}")
        except IOError as e:
            logging.error(f"Error saving appearance settings to {settings_file}: {e}")

    def switch_language(self, lang_code: str):
        if lang_code not in SUPPORTED_LANGUAGES:
            logging.warning(f"Unsupported language code: {lang_code}")
            return
        if self.current_language == lang_code:
            return

        logging.info(f"Switching language to: {lang_code}")
        self.current_language = lang_code
        set_global_language(self.current_language)
        if hasattr(self.mw, 'logic') and self.mw.logic:
            self.mw.logic.DEFAULT_LANGUAGE = self.current_language
        
        self._save_settings()
        self.update_main_window_language_texts() 
        
        if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
            self.mw.ui_updater.update_ui_after_logic_change() 
            if hasattr(self.mw, 'hotkey_cursor_index') and self.mw.hotkey_cursor_index != -1:
                 self.mw.ui_updater.update_hotkey_highlight()


    def update_main_window_language_texts(self):
        logging.debug("AppearanceManager: Updating language texts in MainWindow")
        mw = self.mw 
        if not mw: 
            logging.error("AppearanceManager: MainWindow (self.mw) is None. Cannot update texts.")
            return 

        try:
            if mw.mode != "min": 
                 mw.setWindowTitle(f"{get_text('title')} v{mw.app_version}") 
        except RuntimeError: 
            logging.warning("AppearanceManager: MainWindow was deleted before setWindowTitle could be called.")
            return

        if hasattr(mw, 'top_panel_instance') and mw.top_panel_instance:
            mw.top_panel_instance.update_language()
        
        if hasattr(mw, 'right_panel_instance') and mw.right_panel_instance and \
           hasattr(mw, 'right_panel_widget') and mw.right_panel_widget and \
           mw.right_panel_widget.isVisible():
            try:
                mw.right_panel_instance.update_language()
                list_widget = getattr(mw, 'right_list_widget', None) 
                hero_items_dict = getattr(mw, 'hero_items', {})  
                if list_widget and hero_items_dict:
                    focused_tooltip_base = None
                    current_focused_item = None
                    if hasattr(mw, 'hotkey_cursor_index') and \
                       mw.hotkey_cursor_index is not None and \
                       0 <= mw.hotkey_cursor_index < list_widget.count():
                        current_item_candidate = list_widget.item(mw.hotkey_cursor_index)
                        if current_item_candidate and hasattr(mw.right_panel_instance, 'HERO_NAME_ROLE'):
                            current_focused_item = current_item_candidate
                            focused_tooltip_base = current_item_candidate.data(mw.right_panel_instance.HERO_NAME_ROLE) 
                    
                    for hero, item in hero_items_dict.items():
                        if item: item.setToolTip(hero) 
                    
                    if focused_tooltip_base and current_focused_item:
                        current_focused_item.setToolTip(f">>> {focused_tooltip_base} <<<")
            except RuntimeError:
                 logging.warning("AppearanceManager: Right panel widget was deleted during language update.")
        
        if hasattr(mw, 'result_label') and mw.result_label and \
           hasattr(mw, 'logic') and mw.logic and \
           hasattr(mw.logic, 'selected_heroes') and \
           not mw.logic.selected_heroes:
            try:
                mw.result_label.setText(get_text('no_heroes_selected'))
            except RuntimeError: 
                logging.warning("AppearanceManager: mw.result_label was deleted before setText could be called.")

        
        if hasattr(self.mw, 'hotkey_display_dialog') and self.mw.hotkey_display_dialog and self.mw.hotkey_display_dialog.isVisible():
            try:
                self.mw.hotkey_display_dialog.update_html_content()
            except RuntimeError:
                 logging.warning("AppearanceManager: hotkey_display_dialog was deleted during language update.")
        
        if hasattr(self.mw, 'findChild'): 
            try:
                about_dialog = self.mw.findChild(QDialog, "AboutProgramDialog") 
                if about_dialog and hasattr(about_dialog, 'update_content_theme'):
                    about_dialog.update_content_theme()
            except RuntimeError:
                 logging.warning("AppearanceManager: MainWindow or AboutDialog was deleted during language update for AboutDialog.")


    def switch_theme(self, theme_name: str):
        if theme_name not in ["light", "dark"]:
            logging.warning(f"Unknown theme: {theme_name}"); return
        
        if self.current_theme == theme_name: 
            logging.debug(f"Theme already set to {theme_name}. Forcing UI component update for consistency.")
        else:
            logging.info(f"Switching theme to: {theme_name}")
            self.current_theme = theme_name
            self._save_settings() 

        self._apply_qss_theme(self.current_theme) 
        
        self.update_main_window_language_texts() 
        
        if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
            self.mw.ui_updater.update_interface_for_mode() 
            self.mw.ui_updater._update_counterpick_display() 
        
        if hasattr(self.mw, 'hotkey_display_dialog') and self.mw.hotkey_display_dialog and self.mw.hotkey_display_dialog.isVisible():
            try:
                self.mw.hotkey_display_dialog.update_html_content()
            except RuntimeError:
                logging.warning("AppearanceManager: hotkey_display_dialog was deleted during theme switch.")

        if hasattr(self.mw, 'findChild'):
            try:
                about_dialog = self.mw.findChild(QDialog, "AboutProgramDialog") 
                if about_dialog and hasattr(about_dialog, 'update_content_theme'):
                    about_dialog.update_content_theme()
            except RuntimeError:
                 logging.warning("AppearanceManager: MainWindow or AboutDialog was deleted during theme switch for AboutDialog.")


    def _apply_qss_theme(self, theme_name: str, on_startup=False):
        logging.info(f"AppearanceManager: Applying QSS theme: {theme_name}")
        light_qss = """
            QMainWindow, QDialog { background-color: #f0f0f0; }
            QWidget { color: black; } 
            QTextBrowser { background-color: white; color: black; border: 1px solid #cccccc; }
            QLabel { color: black; }
            QPushButton { background-color: #e1e1e1; border: 1px solid #adadad; color: black; padding: 3px; border-radius: 3px; }
            QPushButton:hover { background-color: #ebebeb; }
            QPushButton:pressed { background-color: #d1d1d1; }
            QListWidget { background-color: white; border: 1px solid #d3d3d3; color: black; }
            QListWidget::item { color: black; border-radius: 4px; border: 1px solid transparent; background-color: transparent; text-align: center; }
            QListWidget::item:selected { background-color: #3399ff; color: white; border: 1px solid #2d8ae5; }
            QListWidget::item:!selected:hover { background-color: #e0f7ff; border: 1px solid #cceeff; }
            QListWidget QAbstractItemView { background-color: white; } /* Viewport для QListWidget */
            QMenu { background-color: #f8f8f8; border: 1px solid #cccccc; color: black; }
            QMenu::item:selected { background-color: #3399ff; color: white; }
            QScrollArea { border: none; background-color: transparent; }
            QLineEdit { background-color: white; color: black; border: 1px solid #cccccc; padding: 2px; border-radius: 3px;}
            QComboBox { background-color: white; color: black; border: 1px solid #cccccc; padding: 2px; border-radius: 3px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: white; color: black; selection-background-color: #3399ff; selection-color: white; border: 1px solid #cccccc; }
            
            QWidget#main_widget { background-color: #f0f0f0; } 
            QFrame#top_frame { background-color: #e0e0e0; border-bottom: 1px solid #c0c0c0; }
            QFrame#left_panel_container_frame { background-color: #f7f7f7; } 
            QFrame#result_frame { background-color: transparent; } 
            QFrame#right_frame { background-color: #f7f7f7 !important; } 
            QWidget#right_list_widget { background-color: white !important; } 
            QLabel#selected_heroes_label { color: #333333; margin: 2px; }
            QLabel#mode_label { margin-left:5px; color: black;} 
            QLabel#version_label { color: #555555; margin-left: 10px; margin-right: 5px; }
            QPushButton#copy_button, QPushButton#clear_button { min-height: 24px; }
            QPushButton#tray_mode_button { font-size: 9pt; padding: 2px 5px; border: 1px solid #777; background-color: #d0d0d0; color: black; border-radius: 4px; min-width: 80px; min-height: 20px; }
            QPushButton#tray_mode_button:hover { background-color: #c0c0c0; }
            QPushButton#tray_mode_button[trayModeActive="true"] { border-color: #388E3C; background-color: #4CAF50; color: white; }
            QPushButton#tray_mode_button[trayModeActive="true"]:hover { background-color: #45a049; }
            QPushButton#menu_button { font-size: 9pt; padding: 2px 8px; min-height: 20px; border: 1px solid #999; border-radius: 4px; background-color: #e8e8e8; color: black;} 
            QPushButton#menu_button:hover { background-color: #d8d8d8; }
            QPushButton#close_button { font-size: 10pt; font-weight: bold; padding: 1px; color: #5e0000; background-color: #ffc0bc; border-radius: 12px; margin-left: 5px; border: 1px solid #E08080; width:24px; height:24px; } QPushButton#close_button:hover { background-color: #ff908c; } QPushButton#close_button:pressed { background-color: #ff706c; }
            QSlider::groove:horizontal { border: 1px solid #bbb; height: 5px; background: #ccc; margin: 0px; border-radius: 2px;} 
            QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 10px; height: 10px; margin: -3px 0; border-radius: 5px; } 
            QSlider::handle:horizontal:hover { background: #45a049; }
            QWidget#icons_scroll_content { background-color: #e9e9e9; } 
            QScrollArea#icons_scroll_area { background-color: #e9e9e9; }
            QWidget#enemies_widget { border: 2px solid red; border-radius: 4px; padding: 1px; background-color: #ffeeee; }
            QLabel#horizontal_info_label { color: #666666; }
            HotkeyCaptureLineEdit { color: black; background-color: white; }
            QFrame#result_frame QLabel { color: black !important; } 
            QFrame#result_frame QFrame QLabel { color: black !important; }
        """
        dark_qss = """
            QMainWindow, QDialog { background-color: #2e2e2e; }
            QWidget { color: #e0e0e0; }
            QTextBrowser { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; }
            QLabel { color: #e0e0e0; }
            QPushButton { background-color: #484848; border: 1px solid #5a5a5a; color: #e0e0e0; padding: 3px; border-radius: 3px; }
            QPushButton:hover { background-color: #585858; }
            QPushButton:pressed { background-color: #383838; }
            QListWidget { background-color: #252525 !important; border: 1px solid #454545; color: #d0d0d0; }
            QListWidget::item { color: #d0d0d0; border-radius: 4px; border: 1px solid transparent; background-color: transparent; text-align: center;}
            QListWidget::item:selected { background-color: #0078d7; color: white; border: 1px solid #005394; }
            QListWidget::item:!selected:hover { background-color: #3a3a3a; border: 1px solid #4f4f4f; }
            QListWidget QAbstractItemView { 
                background-color: #252525; /* Фон для области просмотра элементов */
                color: #d0d0d0; 
                selection-background-color: #0078d7; 
                selection-color: white; 
                border: 1px solid #454545; /* Граница для области просмотра */
            }
            QMenu { background-color: #383838; border: 1px solid #4f4f4f; color: #e0e0e0; }
            QMenu::item:selected { background-color: #0078d7; color: white; }
            QScrollArea { border: none; background-color: transparent; }
            QLineEdit { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; padding: 2px; border-radius: 3px;}
            QComboBox { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; padding: 2px; border-radius: 3px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #252525; color: #d0d0d0; selection-background-color: #0078d7; selection-color: white; border: 1px solid #454545; }

            QWidget#main_widget { background-color: #2e2e2e; } 
            QFrame#top_frame { background-color: #202020; border-bottom: 1px solid #353535; }
            QFrame#left_panel_container_frame { background-color: #2a2a2a; } 
            QFrame#result_frame { background-color: transparent; } 
            QFrame#right_frame { background-color: #2a2a2a !important; } 
            QWidget#right_list_widget { background-color: #252525 !important; } 
            QLabel#selected_heroes_label { color: #b0b0b0; margin: 2px; }
            QLabel#mode_label { color: #c0c0c0; margin-left:5px; }
            QLabel#version_label { color: #888888; margin-left: 10px; margin-right: 5px; }
            QPushButton#copy_button, QPushButton#clear_button { min-height: 24px; }
            QPushButton#tray_mode_button { font-size: 9pt; padding: 2px 5px; border: 1px solid #606060; background-color: #404040; color: #d0d0d0; border-radius: 4px; min-width: 80px; min-height: 20px; }
            QPushButton#tray_mode_button:hover { background-color: #505050; }
            QPushButton#tray_mode_button[trayModeActive="true"] { border-color: #4CAF50; background-color: #388E3C; color: white; } 
            QPushButton#tray_mode_button[trayModeActive="true"]:hover { background-color: #45a049; }
            QPushButton#menu_button { font-size: 9pt; padding: 2px 8px; min-height: 20px; border: 1px solid #555; border-radius: 4px; background-color: #383838; color: #e0e0e0;} 
            QPushButton#menu_button:hover { background-color: #484848; }
            QPushButton#close_button { font-size: 10pt; font-weight: bold; padding: 1px; color: #ff8080; background-color: #5e2020; border-radius: 12px; margin-left: 5px; border: 1px solid #a05050; width:24px; height:24px; } QPushButton#close_button:hover { background-color: #7e3030; } QPushButton#close_button:pressed { background-color: #9e4040; }
            QSlider::groove:horizontal { border: 1px solid #444; height: 5px; background: #383838; margin: 0px; border-radius: 2px;} 
            QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 10px; height: 10px; margin: -3px 0; border-radius: 5px; } 
            QSlider::handle:horizontal:hover { background: #45a049; }
            QWidget#icons_scroll_content { background-color: #222222; } 
            QScrollArea#icons_scroll_area { background-color: #222222; }
            QWidget#enemies_widget { border: 2px solid #CC0000; border-radius: 4px; padding: 1px; background-color: #402020; }
            QLabel#horizontal_info_label { color: #999999; }
            HotkeyCaptureLineEdit { color: #e0e0e0; background-color: #3c3c3c; }
            QFrame#result_frame QLabel { color: #e0e0e0 !important; } 
            QFrame#result_frame QFrame QLabel { color: #e0e0e0 !important; }
        """
        qss = light_qss if theme_name == "light" else dark_qss
        
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
        
        if not on_startup and hasattr(self.mw, 'ui_updater'):
             logging.debug("Requesting UI update after theme change (not on startup)")