import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QGridLayout, QLabel, QScrollArea, QMessageBox, QCheckBox, QLineEdit,
                               QFileDialog, QFrame, QSpinBox, QFormLayout)
from PySide6.QtCore import Qt, Signal, Slot
from info.translations import get_text
from core.hotkey_config import HOTKEY_ACTIONS_CONFIG, DEFAULT_HOTKEYS
from core.app_settings_manager import AppSettingsManager, DEFAULT_SAVE_SCREENSHOT, DEFAULT_SCREENSHOT_PATH, DEFAULT_MIN_RECOGNIZED_HEROES
class SettingsWindow(QWidget):
    """Виджет настроек, предназначенный для встраивания во вкладку."""
    settings_applied_signal = Signal()
    def __init__(self, app_settings_manager: AppSettingsManager, parent=None): 
        super().__init__(parent)
        self.app_settings_manager = app_settings_manager
        self.parent_window = parent 
        
        self.temp_hotkeys = {}
        self.hotkey_action_widgets = {}
        self._init_ui()
        self._load_settings_and_populate_ui()
    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        self._create_general_settings(content_layout)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(separator)
        self._create_hotkeys_settings(content_layout)
        
        content_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)
        self.main_layout.addWidget(scroll_area)
        buttons_layout = QHBoxLayout()
        reset_button = QPushButton(get_text('hotkey_settings_reset_defaults'))
        reset_button.clicked.connect(self._reset_all_settings_to_defaults)
        
        apply_button = QPushButton(get_text('sw_apply_button'))
        apply_button.clicked.connect(self._apply_settings)
        
        buttons_layout.addWidget(reset_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(apply_button)
        self.main_layout.addLayout(buttons_layout)
    def _create_general_settings(self, layout: QVBoxLayout):
        title_label = QLabel(f"<b>{get_text('sw_general_tab_title')}</b>")
        layout.addWidget(title_label)
        
        self.save_screenshots_checkbox = QCheckBox(get_text("sw_save_less_than_6_label"))
        self.path_line_edit = QLineEdit()
        self.path_line_edit.setReadOnly(True)
        browse_button = QPushButton(get_text("sw_browse_button_text"))
        browse_button.clicked.connect(self._browse_save_directory)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_line_edit, 1)
        path_layout.addWidget(browse_button)
        layout.addWidget(self.save_screenshots_checkbox)
        layout.addWidget(QLabel(get_text("sw_save_path_label")))
        layout.addLayout(path_layout)
        
        # Добавляем настройку минимального количества распознанных героев
        min_heroes_label = QLabel(get_text("sw_min_recognized_heroes_label", default_text="Минимум распознанных героев:"))
        self.min_heroes_spinbox = QSpinBox()
        self.min_heroes_spinbox.setMinimum(0)
        self.min_heroes_spinbox.setMaximum(6)
        self.min_heroes_spinbox.setValue(DEFAULT_MIN_RECOGNIZED_HEROES)
        min_heroes_layout = QHBoxLayout()
        min_heroes_layout.addWidget(min_heroes_label)
        min_heroes_layout.addWidget(self.min_heroes_spinbox)
        min_heroes_layout.addStretch(1)
        layout.addLayout(min_heroes_layout)
    def _create_hotkeys_settings(self, layout: QVBoxLayout):
        title_label = QLabel(f"<b>{get_text('sw_hotkeys_tab_title')}</b>")
        layout.addWidget(title_label)
        
        self.hotkeys_grid_layout = QGridLayout()
        layout.addLayout(self.hotkeys_grid_layout)
    def _load_settings_and_populate_ui(self):
        self.temp_hotkeys = self.app_settings_manager.get_hotkeys()
        self.temp_save_screenshot_flag = self.app_settings_manager.get_save_screenshot_flag()
        self.temp_screenshot_path = self.app_settings_manager.get_screenshot_path()
        self.temp_min_recognized_heroes = self.app_settings_manager.get_min_recognized_heroes()
        
        self._populate_hotkey_list_ui()
        self.save_screenshots_checkbox.setChecked(self.temp_save_screenshot_flag)
        self.path_line_edit.setText(self.temp_screenshot_path or get_text("sw_default_path_text"))
        self.min_heroes_spinbox.setValue(self.temp_min_recognized_heroes)
    def _populate_hotkey_list_ui(self):
        for i in reversed(range(self.hotkeys_grid_layout.count())): 
            widget = self.hotkeys_grid_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
        self.hotkey_action_widgets.clear()
        for row, (action_id, config) in enumerate(HOTKEY_ACTIONS_CONFIG.items()):
            desc = get_text(config['desc_key'])
            hotkey = self.temp_hotkeys.get(action_id, "")
            display_hotkey = self._normalize_hotkey_for_display(hotkey)
            desc_label = QLabel(desc)
            hotkey_label = QLabel(f"<code>{display_hotkey}</code>")
            hotkey_label.setTextFormat(Qt.TextFormat.RichText)
            
            # ИЗМЕНЕНИЕ: Кнопка "Изменить" удалена, т.к. виджет для захвата удален.
            # В будущем здесь можно будет реализовать новый механизм.
            
            self.hotkeys_grid_layout.addWidget(desc_label, row, 0)
            self.hotkeys_grid_layout.addWidget(hotkey_label, row, 1)
            
            self.hotkey_action_widgets[action_id] = {'hotkey_label': hotkey_label}
    def _normalize_hotkey_for_display(self, internal_str: str) -> str:
        if not internal_str: return get_text('hotkey_not_set')
        return " + ".join(p.strip().capitalize() for p in internal_str.split('+'))
    @Slot()
    def _browse_save_directory(self):
        directory = QFileDialog.getExistingDirectory(self, get_text("sw_select_dir_dialog_title"))
        if directory:
            self.temp_screenshot_path = directory
            self.path_line_edit.setText(directory)
    def _reset_all_settings_to_defaults(self):
        self.temp_hotkeys = DEFAULT_HOTKEYS.copy()
        self.temp_save_screenshot_flag = DEFAULT_SAVE_SCREENSHOT
        self.temp_screenshot_path = DEFAULT_SCREENSHOT_PATH
        self.temp_min_recognized_heroes = DEFAULT_MIN_RECOGNIZED_HEROES
        self._populate_hotkey_list_ui()
        self.save_screenshots_checkbox.setChecked(self.temp_save_screenshot_flag)
        self.path_line_edit.setText(self.temp_screenshot_path or get_text("sw_default_path_text"))
        self.min_heroes_spinbox.setValue(self.temp_min_recognized_heroes)
        QMessageBox.information(self, "Info", get_text('sw_all_settings_reset_msg'))
    @Slot()
    def _apply_settings(self):
        self.app_settings_manager.set_hotkeys(self.temp_hotkeys)
        self.app_settings_manager.set_save_screenshot_flag(self.save_screenshots_checkbox.isChecked())
        self.app_settings_manager.set_screenshot_path(self.temp_screenshot_path)
        self.app_settings_manager.set_min_recognized_heroes(self.min_heroes_spinbox.value())
        
        self.settings_applied_signal.emit()
        QMessageBox.information(self, "Success", get_text("sw_settings_applied_msg"))