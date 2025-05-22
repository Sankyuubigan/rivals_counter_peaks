# File: core/top_panel.py
from PySide6.QtWidgets import (
    QFrame, QLabel, QSlider, QPushButton, QHBoxLayout, QMenu
)
from PySide6.QtCore import Qt, QTimer
from core.lang.translations import get_text, SUPPORTED_LANGUAGES
# ИЗМЕНЕНО: show_hotkey_info_dialog вместо _show_hotkeys_dialog в MainWindow
from dialogs import show_about_program_info, show_hero_rating
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from main_window import MainWindow

class TopPanel:
    """Класс для создания и управления верхней панелью."""
    def __init__(self, parent: 'MainWindow', switch_mode_callback, logic, app_version):
        self.parent = parent; self.switch_mode_callback = switch_mode_callback
        self.logic = logic; self.app_version = app_version
        logging.debug(f"[TopPanel] Initialized with app_version: {self.app_version}")
        self.top_frame = QFrame(parent); self.top_frame.setObjectName("top_frame")
        self.top_frame.setStyleSheet("""
            QFrame#top_frame { background-color: lightgray; }
            QPushButton#tray_mode_button { font-size: 10pt; padding: 2px; border: 1px solid #555555; background-color: #888888; color: white; border-radius: 4px; min-width: 90px; min-height: 22px; }
            QPushButton#tray_mode_button:hover { background-color: #A9A9A9; }
            QPushButton#tray_mode_button[trayModeActive="true"] { border-color: #388E3C; background-color: #4CAF50; }
            QPushButton#tray_mode_button[trayModeActive="true"]:hover { background-color: #45a049; }
            QPushButton#menu_button { font-size: 10pt; padding: 2px 8px; min-height: 22px; border: 1px solid #777; border-radius: 4px; background-color: #e0e0e0; }
            QPushButton#menu_button:hover { background-color: #d0d0d0; }
        """)
        self.top_frame.setFixedHeight(40)
        self.transparency_slider: QSlider | None = None;
        self.mode_label: QLabel | None = None
        self.min_button: QPushButton | None = None; self.middle_button: QPushButton | None = None
        self.max_button: QPushButton | None = None
        self.tray_mode_button: QPushButton | None = None
        self.menu_button: QPushButton | None = None
        self.rating_button: QPushButton | None = None
        self.about_program_button: QPushButton | None = None
        self.version_label: QLabel | None = None; self.close_button: QPushButton | None = None
        self._setup_ui()

    def _setup_ui(self):
        # ... (код создания слайдера, кнопок режимов, кнопки Трей - без изменений)
        layout = QHBoxLayout(self.top_frame); layout.setContentsMargins(5, 2, 5, 2); layout.setSpacing(5)
        self.transparency_slider = self._create_slider(); layout.addWidget(self.transparency_slider)
        self.mode_label = QLabel(get_text('mode', language=self.logic.DEFAULT_LANGUAGE)); self.mode_label.setObjectName("mode_label"); self.mode_label.setStyleSheet("font-size: 10pt;")
        self.min_button = self._create_mode_button('mode_min', "min"); self.middle_button = self._create_mode_button('mode_middle', "middle"); self.max_button = self._create_mode_button('mode_max', "max")
        layout.addWidget(self.mode_label); layout.addWidget(self.min_button); layout.addWidget(self.middle_button); layout.addWidget(self.max_button)
        self.tray_mode_button = self._create_tray_mode_button(); layout.addWidget(self.tray_mode_button)

        self.menu_button = QPushButton(get_text('menu', language=self.logic.DEFAULT_LANGUAGE))
        self.menu_button.setObjectName("menu_button")
        self.menu_button.clicked.connect(self._show_main_menu)
        self.menu_button.setVisible(False)
        layout.addWidget(self.menu_button)
        layout.addStretch(1)
        self.rating_button = self._create_info_button('hero_rating', lambda: show_hero_rating(self.parent, self.app_version))
        self.about_program_button = self._create_info_button('about_program', lambda: show_about_program_info(self.parent))
        layout.addWidget(self.rating_button); layout.addWidget(self.about_program_button)
        version_text = f"v{self.app_version}" if self.app_version and self.app_version != "dev" else "v?.?.?"
        self.version_label = QLabel(version_text); self.version_label.setObjectName("version_label")
        self.version_label.setStyleSheet("font-size: 9pt; color: grey; margin-left: 10px; margin-right: 5px;"); self.version_label.setToolTip(f"Application version: {self.app_version}")
        logging.debug(f"[TopPanel._setup_ui] Creating version_label with text: '{version_text}' (raw version: {self.app_version})")
        layout.addWidget(self.version_label)
        self.close_button = self._create_close_button(); layout.addWidget(self.close_button)
        if self.tray_mode_button:
             QTimer.singleShot(0, lambda: self._update_tray_mode_button_text_and_property())

    def _create_slider(self) -> QSlider: # ... (без изменений)
        slider = QSlider(Qt.Orientation.Horizontal); slider.setObjectName("transparency_slider"); slider.setRange(10, 100); slider.setValue(100); slider.setFixedWidth(100)
        slider.setStyleSheet(""" QSlider { height: 15px; } QSlider::groove:horizontal { border: 1px solid #999; height: 6px; background: #d3d3d3; margin: 0px; border-radius: 3px;} QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; } QSlider::handle:horizontal:hover { background: #45a049; }""")
        slider.valueChanged.connect(lambda val: self.parent.setWindowOpacity(val / 100.0)); return slider
    def _create_mode_button(self, text_key: str, mode_name: str) -> QPushButton: # ... (без изменений)
        button = QPushButton(get_text(text_key, language=self.logic.DEFAULT_LANGUAGE)); button.setObjectName(f"{mode_name}_mode_button"); button.setStyleSheet("font-size: 10pt; padding: 2px;")
        button.clicked.connect(lambda: self.switch_mode_callback(mode_name)); return button
    def _create_tray_mode_button(self) -> QPushButton: # ... (без изменений)
        button = QPushButton(); button.setObjectName("tray_mode_button"); button.setMinimumSize(90, 22); button.setProperty("trayModeActive", False); button.clicked.connect(self.parent.toggle_tray_mode); return button
    def _update_tray_mode_button_text_and_property(self): # ... (без изменений)
        if not self.tray_mode_button or not self.parent: logging.warning("[TopPanel._update_tray_mode_button_text_and_property] Button or parent not found."); return
        try:
            is_tray_active = self.parent._is_win_topmost; logging.debug(f"[TopPanel._update_tray_mode_button_text_and_property] Updating for state: {is_tray_active}")
            button_text_key = 'tray_mode_on' if is_tray_active else 'tray_mode_off'; button_text = get_text(button_text_key, language=self.logic.DEFAULT_LANGUAGE); self.tray_mode_button.setText(button_text); logging.debug(f"[TopPanel._update_tray_mode_button_text_and_property] Text set to: '{button_text}'")
            current_prop = self.tray_mode_button.property("trayModeActive")
            if current_prop != is_tray_active:
                self.tray_mode_button.setProperty("trayModeActive", is_tray_active); logging.debug(f"[TopPanel._update_tray_mode_button_text_and_property] Property 'trayModeActive' set to: {is_tray_active}"); self.tray_mode_button.style().unpolish(self.tray_mode_button); self.tray_mode_button.style().polish(self.tray_mode_button); self.tray_mode_button.update(); logging.debug("[TopPanel._update_tray_mode_button_text_and_property] Style re-polished.")
            else: logging.debug(f"[TopPanel._update_tray_mode_button_text_and_property] Property 'trayModeActive' already '{current_prop}'.")
        except Exception as e: logging.error(f"[TopPanel._update_tray_mode_button_text_and_property] Error: {e}", exc_info=True)
    def _create_info_button(self, text_key: str, callback) -> QPushButton: # ... (без изменений)
        button = QPushButton(get_text(text_key, language=self.logic.DEFAULT_LANGUAGE)); button.setObjectName(f"{text_key}_button"); button.setStyleSheet("font-size: 10pt; padding: 2px;"); button.clicked.connect(callback); button.setVisible(False); return button
    def _create_close_button(self) -> QPushButton: # ... (без изменений)
        button = QPushButton("X"); button.setObjectName("close_button"); button.setFixedSize(25, 25); button.setStyleSheet(""" QPushButton#close_button { font-size: 10pt; font-weight: bold; padding: 1px; color: black; background-color: #ff605c; border-radius: 5px; margin-left: 5px; border: 1px solid #E04340; } QPushButton#close_button:hover { background-color: #e04340; } QPushButton#close_button:pressed { background-color: #c0302c; } """); button.clicked.connect(self.parent.close); button.setVisible(False); return button

    def _show_main_menu(self):
        if not self.menu_button: return
        menu = QMenu(self.parent)
        current_lang = self.logic.DEFAULT_LANGUAGE

        lang_menu = QMenu(get_text('language', language=current_lang), menu)
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            action = lang_menu.addAction(lang_name)
            action.setCheckable(True)
            action.setChecked(current_lang == lang_code)
            action.triggered.connect(lambda checked=False, lc=lang_code: self.parent.switch_language(lc))
        menu.addMenu(lang_menu)
        menu.addSeparator()

        rating_action = menu.addAction(get_text('hero_rating', language=current_lang))
        rating_action.triggered.connect(lambda: show_hero_rating(self.parent, self.app_version))
        about_program_action = menu.addAction(get_text('about_program', language=current_lang))
        about_program_action.triggered.connect(lambda: show_about_program_info(self.parent))
        menu.addSeparator()

        # ИЗМЕНЕНО: Пункт меню для НАСТРОЙКИ хоткеев
        hotkey_settings_action = menu.addAction(get_text('hotkey_settings_menu_item', language=current_lang))
        if hasattr(self.parent, 'show_hotkey_settings_window'):
            hotkey_settings_action.triggered.connect(self.parent.show_hotkey_settings_window)
        else:
            hotkey_settings_action.setEnabled(False)
            logging.warning("Method show_hotkey_settings_window not found in parent.")

        # Старый пункт для отображения хоткеев (можно оставить или убрать)
        # hotkeys_info_action = menu.addAction(get_text('hotkeys_menu_item', language=current_lang) + " (Info)")
        # if hasattr(self.parent, '_show_hotkey_info_dialog'):
        #     hotkeys_info_action.triggered.connect(self.parent._show_hotkey_info_dialog)
        # else: hotkeys_info_action.setEnabled(False)


        logs_action = menu.addAction(get_text('logs_menu_item', language=current_lang))
        if hasattr(self.parent, 'show_log_window'):
             logs_action.triggered.connect(self.parent.show_log_window)
        else: logs_action.setEnabled(False)

        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))

    def update_language(self):
        # ... (обновление текстов кнопок и лейблов без изменений в логике)
        current_lang = self.logic.DEFAULT_LANGUAGE; logging.debug(f"[TopPanel.update_language] Updating texts for language: {current_lang}")
        if self.mode_label: self.mode_label.setText(get_text('mode', language=current_lang))
        if self.min_button: self.min_button.setText(get_text('mode_min', language=current_lang))
        if self.middle_button: self.middle_button.setText(get_text('mode_middle', language=current_lang))
        if self.max_button: self.max_button.setText(get_text('mode_max', language=current_lang))
        if self.menu_button: self.menu_button.setText(get_text('menu', language=current_lang))
        self._update_tray_mode_button_text_and_property()
        if self.about_program_button: self.about_program_button.setText(get_text('about_program', language=current_lang))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating', language=current_lang))
        if self.version_label:
             version_text = f"v{self.app_version}" if self.app_version and self.app_version != "dev" else "v?.?.?"
             self.version_label.setText(version_text); self.version_label.setToolTip(f"Application version: {self.app_version}")
        else: logging.warning("[TopPanel.update_language] version_label is None")
