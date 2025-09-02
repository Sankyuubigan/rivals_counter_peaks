# File: core/appearance_manager.py
import logging
# json не используется напрямую, AppSettingsManager управляет JSON
from PySide6.QtWidgets import QApplication, QDialog 
from info.translations import SUPPORTED_LANGUAGES, set_language as set_global_language, get_text
# Вместо utils.get_settings_path используем AppSettingsManager
from core.app_settings_manager import AppSettingsManager
from info.translations import DEFAULT_LANGUAGE as DEFAULT_LANG_VALUE
from core.app_settings_manager import DEFAULT_THEME

class AppearanceManager:
    def __init__(self, main_window, app_settings_manager: AppSettingsManager):
        self.mw = main_window
        self.app_settings_manager = app_settings_manager
        
        self.current_theme = self.app_settings_manager.get_theme()
        self.current_language = self.app_settings_manager.get_language()
        # Применяем загруженный язык глобально
        if self.current_language not in SUPPORTED_LANGUAGES:
            logging.warning(f"Загружен неподдерживаемый язык '{self.current_language}', используется язык по умолчанию '{DEFAULT_LANG_VALUE}'.")
            self.current_language = DEFAULT_LANG_VALUE
            self.app_settings_manager.set_language(self.current_language) # Сохраняем исправленное значение
        
        set_global_language(self.current_language)
        if hasattr(self.mw, 'logic') and self.mw.logic: 
            self.mw.logic.DEFAULT_LANGUAGE = self.current_language
        logging.info(f"AppearanceManager инициализирован. Тема: {self.current_theme}, Язык: {self.current_language}")

    def switch_language(self, lang_code: str):
        if lang_code not in SUPPORTED_LANGUAGES:
            logging.warning(f"Попытка переключиться на неподдерживаемый язык: {lang_code}")
            return
        if self.current_language == lang_code:
            logging.debug(f"Язык уже установлен: {lang_code}.")
            return
        logging.info(f"Переключение языка на: {lang_code}")
        self.current_language = lang_code
        set_global_language(self.current_language) # Устанавливаем глобально для get_text
        
        if hasattr(self.mw, 'logic') and self.mw.logic: # Обновляем язык в логике, если есть
            self.mw.logic.DEFAULT_LANGUAGE = self.current_language
        
        self.app_settings_manager.set_language(self.current_language) # Сохраняем настройку
        
        self.update_main_window_language_texts() # Обновляем тексты в UI
        
        # Дополнительные обновления UI, которые могут зависеть от языка
        if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
            self.mw.ui_updater.update_ui_after_logic_change() # Обновит метки и т.д.
            if hasattr(self.mw, 'hotkey_cursor_index') and self.mw.hotkey_cursor_index != -1:
                 self.mw.ui_updater.update_hotkey_highlight() # Обновит тултипы с фокусом

    def update_main_window_language_texts(self):
        """Обновляет все тексты в главном окне и его компонентах на текущий язык."""
        logging.debug("AppearanceManager: Обновление текстов в MainWindow...")
        mw = self.mw 
        if not mw: 
            logging.error("AppearanceManager: MainWindow (self.mw) is None. Обновление текстов невозможно.")
            return 
        try:
            if hasattr(mw, 'mode') and mw.mode != "min": 
                 # Убедимся, что app_version существует
                 app_ver = getattr(mw, 'app_version', '?.?.?')
                 mw.setWindowTitle(f"{get_text('title')} v{app_ver}") 
        except RuntimeError: # Если окно уже удалено
            logging.warning("AppearanceManager: MainWindow было удалено до вызова setWindowTitle.")
            return # Дальнейшие действия бессмысленны
        # Обновление TopPanel
        if hasattr(mw, 'top_panel_instance') and mw.top_panel_instance:
            try:
                mw.top_panel_instance.update_language()
            except RuntimeError:
                logging.warning("AppearanceManager: TopPanel был удален во время обновления языка.")
        
        # Обновление RightPanel (если существует и видим)
        if hasattr(mw, 'right_panel_instance') and mw.right_panel_instance and \
           hasattr(mw, 'right_panel_widget') and mw.right_panel_widget and \
           mw.right_panel_widget.isVisible():
            try:
                mw.right_panel_instance.update_language()
                # Обновление тултипов в списке героев (если необходимо)
                list_widget = getattr(mw, 'right_list_widget', None) 
                hero_items_dict = getattr(mw, 'hero_items', {})  
                if list_widget and hero_items_dict:
                    focused_tooltip_base = None
                    current_focused_item_row = -1
                    if hasattr(mw, 'hotkey_cursor_index'):
                        current_focused_item_row = mw.hotkey_cursor_index
                    
                    for hero, item_widget in hero_items_dict.items():
                        if item_widget: 
                            item_widget.setToolTip(hero) # Базовый тултип - имя героя
                            # Если элемент под курсором хоткея, добавляем маркеры
                            if list_widget.row(item_widget) == current_focused_item_row and mw.mode != 'min':
                                item_widget.setToolTip(f">>> {hero} <<<")
            except RuntimeError:
                 logging.warning("AppearanceManager: RightPanel был удален во время обновления языка.")
        
        # Обновление result_label, если нет выбранных героев
        if hasattr(mw, 'result_label') and mw.result_label and \
           hasattr(mw, 'logic') and mw.logic and \
           hasattr(mw.logic, 'selected_heroes') and \
           not mw.logic.selected_heroes: # Только если список пуст
            try:
                mw.result_label.setText(get_text('no_heroes_selected'))
            except RuntimeError: 
                logging.warning("AppearanceManager: mw.result_label был удален.")
        # Обновление открытых диалоговых окон, если они поддерживают это
        if hasattr(mw, 'hotkey_display_dialog') and mw.hotkey_display_dialog and mw.hotkey_display_dialog.isVisible():
            try:
                mw.hotkey_display_dialog.update_html_content()
            except RuntimeError:
                 logging.warning("AppearanceManager: hotkey_display_dialog был удален.")
        
        # Обновление AboutProgramDialog и AuthorDialog, если они открыты
        # Используем findChild для поиска, так как они могут быть не прямыми атрибутами
        if hasattr(mw, 'findChild'): 
            try:
                # Имена объектов задаются в dialogs.py при создании
                about_dialog = mw.findChild(QDialog, "informationDialog") # Имя объекта из BaseInfoDialog
                if about_dialog and hasattr(about_dialog, 'update_content_theme') and about_dialog.isVisible():
                    about_dialog.update_content_theme()
                
                author_dialog = mw.findChild(QDialog, "authorDialog") # Имя объекта из BaseInfoDialog
                if author_dialog and hasattr(author_dialog, 'update_content_theme') and author_dialog.isVisible():
                    author_dialog.update_content_theme()
            except RuntimeError:
                 logging.warning("AppearanceManager: Ошибка при обновлении языка для открытых диалогов (возможно, были удалены).")

    def switch_theme(self, theme_name: str):
        if theme_name not in ["light", "dark"]:
            logging.warning(f"Неизвестная тема: {theme_name}. Переключение отменено.")
            return
        
        if self.current_theme == theme_name: 
            logging.debug(f"Тема уже установлена: {theme_name}. Принудительное обновление UI для консистентности.")
        else:
            logging.info(f"Переключение темы на: {theme_name}")
            self.current_theme = theme_name
            self.app_settings_manager.set_theme(self.current_theme) # Сохраняем настройку
        self._apply_qss_theme_globally(self.current_theme) 
        
        # После применения QSS, нужно обновить специфичные для темы элементы UI,
        # которые могут не полностью перерисоваться только от QSS.
        # Обновление текстов (некоторые цвета могут быть в HTML в диалогах)
        self.update_main_window_language_texts() 
        
        if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
            # Эти методы должны корректно учитывать текущую тему при перерисовке
            self.mw.ui_updater.update_interface_for_mode() 
            self.mw.ui_updater._update_counterpick_display() # Обновит цвета рамок и фона в списке контрпиков
            self.mw.ui_updater.update_hotkey_highlight() # Обновит цвет рамки фокуса хоткея
        
        # Обновление открытых диалоговых окон
        if hasattr(self.mw, 'hotkey_display_dialog') and self.mw.hotkey_display_dialog and self.mw.hotkey_display_dialog.isVisible():
            try: self.mw.hotkey_display_dialog.update_html_content() # Перегенерирует HTML с новыми цветами
            except RuntimeError: logging.warning("AppearanceManager: hotkey_display_dialog был удален при смене темы.")
        if hasattr(self.mw, 'findChild'):
            try:
                about_dialog = self.mw.findChild(QDialog, "informationDialog")
                if about_dialog and hasattr(about_dialog, 'update_content_theme') and about_dialog.isVisible():
                    about_dialog.update_content_theme()
                
                author_dialog = self.mw.findChild(QDialog, "authorDialog")
                if author_dialog and hasattr(author_dialog, 'update_content_theme') and author_dialog.isVisible():
                    author_dialog.update_content_theme()
            except RuntimeError: logging.warning("AppearanceManager: Ошибка при обновлении темы для открытых диалогов.")
        
        # Обновление SettingsWindow, если оно открыто
        # SettingsWindow должно само подписаться на сигнал изменения темы или иметь метод для обновления
        if hasattr(self.mw, 'settings_window_instance') and self.mw.settings_window_instance and self.mw.settings_window_instance.isVisible():
             if hasattr(self.mw.settings_window_instance, 'update_theme_dependent_elements'):
                 self.mw.settings_window_instance.update_theme_dependent_elements()

    def _apply_qss_theme_globally(self, theme_name: str, on_startup=False):
        """Применяет QSS стиль ко всему приложению."""
        logging.info(f"AppearanceManager: Применение QSS темы: {theme_name}")
        # Строки QSS остаются те же, что и в вашем предыдущем коде
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
            QListWidget QAbstractItemView { background-color: white; } 
            QMenu { background-color: #f8f8f8; border: 1px solid #cccccc; color: black; }
            QMenu::item:selected { background-color: #3399ff; color: white; }
            QScrollArea { border: none; background-color: transparent; }
            QLineEdit { background-color: white; color: black; border: 1px solid #cccccc; padding: 2px; border-radius: 3px;}
            QComboBox { background-color: white; color: black; border: 1px solid #cccccc; padding: 2px; border-radius: 3px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: white; color: black; selection-background-color: #3399ff; selection-color: white; border: 1px solid #cccccc; }
            QCheckBox { color: black; }
            QTabWidget::pane { border: 1px solid #cccccc; background-color: #f0f0f0;}
            QTabBar::tab { background: #e1e1e1; border: 1px solid #adadad; padding: 5px; color: black; border-bottom: none; }
            QTabBar::tab:selected { background: #f0f0f0; }
            QTabBar::tab:!selected:hover { background: #ebebeb; }
            
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
            QWidget#enemies_widget { border: 2px solid red; border-radius: 4px; padding: 2px; background-color: #ffeeee; }
            QLabel#horizontal_info_label { color: #666666; }
            HotkeyCaptureLineEdit { color: black; background-color: white; }
            QFrame#result_frame QLabel { color: black !important; } 
            QFrame#result_frame QFrame QLabel { color: black !important; }
            QWidget#tab_enemies_container { border: 2px solid red; border-radius: 4px; padding: 2px; background-color: transparent; }
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
                background-color: #252525 !important; 
                color: #d0d0d0; 
                selection-background-color: #0078d7; 
                selection-color: white; 
                border: 1px solid #454545;
            }
            QMenu { background-color: #383838; border: 1px solid #4f4f4f; color: #e0e0e0; }
            QMenu::item:selected { background-color: #0078d7; color: white; }
            QScrollArea { border: none; background-color: transparent; }
            QLineEdit { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; padding: 2px; border-radius: 3px;}
            QComboBox { background-color: #252525; color: #d0d0d0; border: 1px solid #454545; padding: 2px; border-radius: 3px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #252525; color: #d0d0d0; selection-background-color: #0078d7; selection-color: white; border: 1px solid #454545; }
            QCheckBox { color: #e0e0e0; }
            QTabWidget::pane { border: 1px solid #454545; background-color: #2e2e2e;}
            QTabBar::tab { background: #484848; border: 1px solid #5a5a5a; padding: 5px; color: #e0e0e0; border-bottom: none; }
            QTabBar::tab:selected { background: #2e2e2e; }
            QTabBar::tab:!selected:hover { background: #585858; }
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
            QWidget#enemies_widget { border: 2px solid #CC0000; border-radius: 4px; padding: 2px; background-color: #402020; }
            QLabel#horizontal_info_label { color: #999999; }
            HotkeyCaptureLineEdit { color: #e0e0e0; background-color: #3c3c3c; }
            QFrame#result_frame QLabel { color: #e0e0e0 !important; } 
            QFrame#result_frame QFrame QLabel { color: #e0e0e0 !important; }
            QWidget#tab_enemies_container { border: 2px solid #CC0000; border-radius: 4px; padding: 2px; background-color: transparent; }
        """
        qss = light_qss if theme_name == "light" else dark_qss
        
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
            # Это обновит стиль для всех виджетов.
            # Для виджетов, которые динамически меняют свои свойства, влияющие на стиль
            # (например, QPushButton с property trayModeActive), может потребоваться
            # style().unpolish(widget); style().polish(widget); widget.update()
            # Это обычно делается в методе, который изменяет свойство.
        
        # Если это не первоначальный запуск, и UI уже существует,
        # можно дополнительно обновить UI для учета изменений темы.
        if not on_startup and hasattr(self.mw, 'ui_updater'):
             logging.debug("AppearanceManager: Запрос обновления UI после смены темы (не при запуске)")
             # Обновление UiUpdater может быть избыточным, если QSS покрывает все.
             # Но если есть элементы, цвет которых задается не через QSS, их нужно обновить.
             # self.mw.ui_updater.update_interface_for_mode() # Это может быть слишком много
             # self.mw.ui_updater._update_counterpick_display() # Этот точно нужен для цветов рамок