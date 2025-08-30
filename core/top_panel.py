# File: core/top_panel.py
from PySide6.QtWidgets import (
    QFrame, QLabel, QSlider, QPushButton, QHBoxLayout, QMenu
)
from PySide6.QtCore import Qt, QTimer
from core.lang.translations import get_text, SUPPORTED_LANGUAGES
from dialogs import show_about_program_info, show_hero_rating, show_author_info 
from typing import TYPE_CHECKING 
import logging

if TYPE_CHECKING:
    from main_window import MainWindow 
    from core.settings_window import SettingsWindow
    # Убираем импорт RecognitionManager, так как он больше не нужен здесь
    # from core.recognition import RecognitionManager 

class TopPanel:
    """Класс для создания и управления верхней панелью."""
    # Убираем rec_manager из конструктора
    def __init__(self, parent: 'MainWindow', switch_mode_callback, logic, app_version):
        self.parent = parent; self.switch_mode_callback = switch_mode_callback
        self.logic = logic; self.app_version = app_version
        # self.rec_manager = rec_manager # Убираем 
        logging.debug(f"[TopPanel] Initialized with app_version: {self.app_version}")
        
        self.top_frame = QFrame(parent); self.top_frame.setObjectName("top_frame")
        self.top_frame.setFixedHeight(36) 
        
        self.transparency_slider: QSlider | None = None;
        self.mode_label: QLabel | None = None
        self.min_button: QPushButton | None = None 
        self.middle_button: QPushButton | None = None
        self.max_button: QPushButton | None = None
        self.tray_mode_button: QPushButton | None = None
        # self.recognize_button: QPushButton | None = None # Убираем кнопку распознавания
        self.menu_button: QPushButton | None = None 
        self.version_label: QLabel | None = None
        self.close_button_min_mode: QPushButton | None = None 

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self.top_frame)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        self.transparency_slider = self._create_slider()
        layout.addWidget(self.transparency_slider)

        self.mode_label = QLabel(get_text('mode', language=self.logic.DEFAULT_LANGUAGE))
        self.mode_label.setObjectName("mode_label")
        self.min_button = self._create_mode_button('mode_min', "min")
        self.middle_button = self._create_mode_button('mode_middle', "middle")
        self.max_button = self._create_mode_button('mode_max', "max")
        
        layout.addWidget(self.mode_label)
        layout.addWidget(self.min_button)
        layout.addWidget(self.middle_button)
        layout.addWidget(self.max_button)

        self.tray_mode_button = self._create_tray_mode_button()
        layout.addWidget(self.tray_mode_button)

        # Убираем создание кнопки Распознать
        # self.recognize_button = QPushButton(get_text('recognize_button_text', default_text="Распознать"))
        # self.recognize_button.setObjectName("recognize_button")
        # self.recognize_button.clicked.connect(self.parent.action_recognize_heroes.emit)
        # layout.addWidget(self.recognize_button)


        self.menu_button = QPushButton(get_text('menu', language=self.logic.DEFAULT_LANGUAGE))
        self.menu_button.setObjectName("menu_button")
        self.menu_button.clicked.connect(self._show_main_menu)
        layout.addWidget(self.menu_button)

        layout.addStretch(1) 
        
        version_text = f"v{self.app_version}" if self.app_version and self.app_version != "dev" else "v?.?.?"
        self.version_label = QLabel(version_text)
        self.version_label.setObjectName("version_label")
        self.version_label.setToolTip(f"{get_text('version_tooltip_prefix', default_text='Версия приложения')}: {self.app_version}")
        layout.addWidget(self.version_label)

        self.close_button_min_mode = self._create_close_button_min_mode()
        layout.addWidget(self.close_button_min_mode)
        self.close_button_min_mode.hide() 

        if self.tray_mode_button:
             QTimer.singleShot(0, lambda: self._update_tray_mode_button_text_and_property())


    def _create_slider(self) -> QSlider: 
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("transparency_slider")
        slider.setRange(10, 100) 
        slider.setValue(100)    
        slider.setFixedWidth(80) 
        slider.valueChanged.connect(self.parent.handle_opacity_change) 
        return slider
    
    def _create_mode_button(self, text_key: str, mode_name: str) -> QPushButton: 
        button = QPushButton(get_text(text_key, language=self.logic.DEFAULT_LANGUAGE))
        button.setObjectName(f"{mode_name}_mode_button") 
        button.clicked.connect(lambda: self.switch_mode_callback(mode_name))
        return button
    
    def _create_tray_mode_button(self) -> QPushButton: 
        button = QPushButton() 
        button.setObjectName("tray_mode_button")
        button.setProperty("trayModeActive", False) 
        button.clicked.connect(self.parent.toggle_tray_mode) 
        return button
    
    def _update_tray_mode_button_text_and_property(self): 
        if not self.tray_mode_button or not self.parent: 
            logging.warning("[TopPanel._update_tray_mode_button_text_and_property] Кнопка 'Трей' или родительское окно не найдены.")
            return
        
        is_tray_active = getattr(self.parent, '_is_win_topmost', False)
        
        button_text_key = 'tray_mode_on' if is_tray_active else 'tray_mode_off'
        button_text = get_text(button_text_key, language=self.logic.DEFAULT_LANGUAGE)
        self.tray_mode_button.setText(button_text)
        
        current_prop = self.tray_mode_button.property("trayModeActive")
        if current_prop != is_tray_active: 
            self.tray_mode_button.setProperty("trayModeActive", is_tray_active)
            style = self.tray_mode_button.style()
            if style: 
                style.unpolish(self.tray_mode_button)
                style.polish(self.tray_mode_button)
            self.tray_mode_button.update() 
    
    def _create_close_button_min_mode(self) -> QPushButton: 
        button = QPushButton("✕") 
        button.setObjectName("close_button") 
        button.setFixedSize(24, 24) 
        button.setToolTip(get_text("close_button_tooltip", default_text="Закрыть приложение"))
        button.clicked.connect(self.parent.close) 
        return button

    def _show_main_menu(self):
        if not self.menu_button: return
        menu = QMenu(self.parent)
        current_lang = self.logic.DEFAULT_LANGUAGE

        lang_menu = QMenu(get_text('language', language=current_lang), menu)
        for lang_code, lang_name_map_or_str in SUPPORTED_LANGUAGES.items():
            lang_display_name = ""
            if isinstance(lang_name_map_or_str, str):
                lang_display_name = lang_name_map_or_str 
            elif isinstance(lang_name_map_or_str, dict): 
                lang_display_name = lang_name_map_or_str.get(current_lang, lang_code)
            else: 
                lang_display_name = lang_code 

            action = lang_menu.addAction(lang_display_name)
            action.setCheckable(True)
            action.setChecked(current_lang == lang_code)
            action.triggered.connect(lambda checked=False, lc=lang_code: self.parent.switch_language(lc) if checked else None)
        menu.addMenu(lang_menu)
        
        theme_menu = QMenu(get_text('theme_menu_title', default_text="Тема", language=current_lang), menu)
        light_theme_action = theme_menu.addAction(get_text('light_theme_action', default_text="Светлая", language=current_lang))
        dark_theme_action = theme_menu.addAction(get_text('dark_theme_action', default_text="Темная", language=current_lang))
        
        light_theme_action.setCheckable(True); dark_theme_action.setCheckable(True)
        
        current_app_theme = "light" 
        if hasattr(self.parent, 'appearance_manager') and self.parent.appearance_manager:
            current_app_theme = self.parent.appearance_manager.current_theme
        
        light_theme_action.setChecked(current_app_theme == "light")
        dark_theme_action.setChecked(current_app_theme == "dark")

        light_theme_action.triggered.connect(lambda checked=False, theme_name="light": self.parent.switch_theme(theme_name) if checked else None)
        dark_theme_action.triggered.connect(lambda checked=False, theme_name="dark": self.parent.switch_theme(theme_name) if checked else None)
        menu.addMenu(theme_menu)
        menu.addSeparator()

        rating_action = menu.addAction(get_text('hero_rating', language=current_lang))
        rating_action.triggered.connect(lambda: show_hero_rating(self.parent, self.app_version))
        
        about_program_action = menu.addAction(get_text('about_program', language=current_lang))
        about_program_action.triggered.connect(lambda: show_about_program_info(self.parent))

        author_info_action = menu.addAction(get_text('author_menu_item_text', language=current_lang))
        author_info_action.triggered.connect(lambda: show_author_info(self.parent))
        
        menu.addSeparator()

        settings_action = menu.addAction(get_text('hotkey_settings_menu_item', language=current_lang)) 
        if hasattr(self.parent, 'show_settings_window'): 
            settings_action.triggered.connect(self.parent.show_settings_window)
        else:
            settings_action.setEnabled(False)
            logging.warning("Метод show_settings_window не найден в родительском окне.")
        
        logs_action = menu.addAction(get_text('logs_menu_item', language=current_lang))
        if hasattr(self.parent, 'show_log_window'):
             logs_action.triggered.connect(self.parent.show_log_window)
        else: 
            logs_action.setEnabled(False)
            logging.warning("Метод show_log_window не найден в родительском окне.")

        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))

    def update_language(self):
        current_lang = self.logic.DEFAULT_LANGUAGE; 
        if self.mode_label: self.mode_label.setText(get_text('mode', language=current_lang))
        if self.min_button: self.min_button.setText(get_text('mode_min', language=current_lang))
        if self.middle_button: self.middle_button.setText(get_text('mode_middle', language=current_lang))
        if self.max_button: self.max_button.setText(get_text('mode_max', language=current_lang))
        if self.menu_button: self.menu_button.setText(get_text('menu', language=current_lang))
        
        # Убираем обновление текста и тултипа для recognize_button, так как ее нет
        # if self.recognize_button: 
        #     self.recognize_button.setText(get_text('recognize_button_text', default_text="Распознать"))
        #     is_models_ready = self.rec_manager._models_are_actually_ready if self.rec_manager else False
        #     if is_models_ready:
        #         self.recognize_button.setToolTip(get_text("recognize_button_tooltip", default_text="Распознать героев"))
        #     else:
        #         self.recognize_button.setToolTip(get_text("recognition_models_loading_tooltip", default_text="Модели распознавания загружаются..."))


        self._update_tray_mode_button_text_and_property() 
        
        if self.version_label:
             version_text = f"v{self.app_version}" if self.app_version and self.app_version != "dev" else "v?.?.?"
             self.version_label.setText(version_text)
             self.version_label.setToolTip(f"{get_text('version_tooltip_prefix', default_text='Версия приложения')}: {self.app_version}")
        
        if self.close_button_min_mode:
            self.close_button_min_mode.setToolTip(get_text("close_button_tooltip", default_text="Закрыть приложение"))
