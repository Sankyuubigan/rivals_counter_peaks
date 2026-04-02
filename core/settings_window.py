import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QGridLayout, QLabel, QScrollArea, QMessageBox, QFrame, QComboBox, QCheckBox)
from PySide6.QtCore import Qt, Signal, Slot
from info.translations import get_text
from core.hotkey_config import HOTKEY_ACTIONS_CONFIG, DEFAULT_HOTKEYS
from core.app_settings_manager import AppSettingsManager
from core.ui_components.hotkey_capture_widget import HotkeyCaptureWidget

class SettingsWindow(QWidget):
    settings_applied_signal = Signal()
    def __init__(self, app_settings_manager: AppSettingsManager, parent=None): 
        super().__init__(parent)
        self.app_settings_manager = app_settings_manager
        self.parent_window = parent 
        self.temp_hotkeys = {}
        self.hotkey_widgets = {}
        self._init_ui()
        self._load_settings_and_populate_ui()
        
    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        self._create_algorithm_settings(content_layout)
        self._create_tray_settings(content_layout)
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
        
    def _create_hotkeys_settings(self, layout: QVBoxLayout):
        title_label = QLabel(f"<b>{get_text('sw_hotkeys_tab_title')}</b>")
        layout.addWidget(title_label)
        
        info_label = QLabel("Примечание: Для действий в режиме TAB требуется зажать клавишу TAB и нажать дополнительную клавишу")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px; margin: 5px;")
        layout.addWidget(info_label)
        
        self.hotkeys_grid_layout = QGridLayout()
        layout.addLayout(self.hotkeys_grid_layout)

    def _create_algorithm_settings(self, layout: QVBoxLayout):
        """Создаёт секцию настройки алгоритма подбора контрпиков."""
        title_label = QLabel(f"<b>{get_text('algorithm_setting', default_text='Алгоритм подбора контрпиков')}</b>")
        layout.addWidget(title_label)

        algo_layout = QHBoxLayout()
        algo_label = QLabel(get_text("algorithm_setting", default_text="Алгоритм:"))
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItem(get_text("algorithm_statistics", default_text="Статистика"), "statistics")
        self.algorithm_combo.addItem(get_text("algorithm_manual", default_text="Ручной"), "manual")
        self.algorithm_combo.setToolTip(get_text("algorithm_setting_desc", default_text="Статистика — автоматический подбор на основе данных matchups. Ручной — выбор контрпиков вручную (в разработке)"))

        algo_layout.addWidget(algo_label)
        algo_layout.addWidget(self.algorithm_combo)
        algo_layout.addStretch(1)
        layout.addLayout(algo_layout)

        desc_label = QLabel(get_text("algorithm_setting_desc", default_text="Статистика — автоматический подбор на основе данных matchups. Ручной — выбор контрпиков вручную (в разработке)"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 10px; margin: 5px;")
        layout.addWidget(desc_label)
    
    def _create_tray_settings(self, layout: QVBoxLayout):
        """Создаёт секцию настроек трей-окна."""
        title_label = QLabel(f"<b>{get_text('tray_settings_title', default_text='Трей')}</b>")
        layout.addWidget(title_label)
        
        tray_layout = QVBoxLayout()
        tray_layout.setSpacing(8)
        
        self.tray_hide_allies_checkbox = QCheckBox(
            get_text("tray_hide_allies", default_text="Не повторять союзных героев в списке контрпиков")
        )
        self.tray_hide_allies_checkbox.setToolTip(
            get_text("tray_hide_allies_desc", default_text="Скрывать героев из списка контрпиков, которые уже есть в команде союзников")
        )
        tray_layout.addWidget(self.tray_hide_allies_checkbox)
        
        self.tray_show_rating_checkbox = QCheckBox(
            get_text("tray_show_rating", default_text="Показать рейтинг на иконках контрпиков")
        )
        self.tray_show_rating_checkbox.setToolTip(
            get_text("tray_show_rating_desc", default_text="Отображать числовой рейтинг на иконках героев в списке контрпиков")
        )
        tray_layout.addWidget(self.tray_show_rating_checkbox)
        
        layout.addLayout(tray_layout)
        
        desc_label = QLabel(get_text("tray_settings_desc", default_text="Настройки отображения окна, которое появляется при нажатии TAB"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 10px; margin: 5px;")
        layout.addWidget(desc_label)
        
    def _load_settings_and_populate_ui(self):
        self.temp_hotkeys = self.app_settings_manager.get_hotkeys()
        self._populate_hotkey_list_ui()
        # Загружаем текущий алгоритм
        current_algo = self.app_settings_manager.get_algorithm()
        index = self.algorithm_combo.findData(current_algo)
        if index >= 0:
            self.algorithm_combo.setCurrentIndex(index)
        # Загружаем настройки трея
        self.tray_hide_allies_checkbox.setChecked(self.app_settings_manager.get_tray_hide_allies())
        self.tray_show_rating_checkbox.setChecked(self.app_settings_manager.get_tray_show_rating())
        
    def _populate_hotkey_list_ui(self):
        for i in reversed(range(self.hotkeys_grid_layout.count())): 
            widget = self.hotkeys_grid_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
        self.hotkey_widgets.clear()
        
        for row, (action_id, config) in enumerate(HOTKEY_ACTIONS_CONFIG.items()):
            desc = get_text(config['desc_key'])
            hotkey = self.temp_hotkeys.get(action_id, "")
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            hotkey_widget = HotkeyCaptureWidget(hotkey)
            hotkey_widget.hotkey_changed.connect(lambda hk, aid=action_id: self._on_hotkey_changed(aid, hk))
            self.hotkeys_grid_layout.addWidget(desc_label, row, 0)
            self.hotkeys_grid_layout.addWidget(hotkey_widget, row, 1)
            self.hotkey_widgets[action_id] = hotkey_widget
            
    def _on_hotkey_changed(self, action_id: str, hotkey: str):
        self.temp_hotkeys[action_id] = hotkey
        
    def _reset_all_settings_to_defaults(self):
        self.temp_hotkeys = DEFAULT_HOTKEYS.copy()
        self._populate_hotkey_list_ui()
        QMessageBox.information(self, "Info", get_text('sw_all_settings_reset_msg'))
        
    @Slot()
    def _apply_settings(self):
        self.app_settings_manager.set_hotkeys(self.temp_hotkeys)
        # Сохраняем выбранный алгоритм
        selected_algo = self.algorithm_combo.currentData()
        self.app_settings_manager.set_algorithm(selected_algo)
        # Сохраняем настройки трея
        self.app_settings_manager.set_tray_hide_allies(self.tray_hide_allies_checkbox.isChecked())
        self.app_settings_manager.set_tray_show_rating(self.tray_show_rating_checkbox.isChecked())
        if hasattr(self.parent_window, 'hotkey_manager'):
            self.parent_window.hotkey_manager.reregister_hotkeys()
        self.settings_applied_signal.emit()
        QMessageBox.information(self, "Success", get_text("sw_settings_applied_msg"))

    def update_language_and_theme(self):
        """Обновляет тексты при смене языка."""
        # Обновляем заголовки
        for i in reversed(range(self.main_layout.count())):
            widget = self.main_layout.itemAt(i).widget()
            # Пропускаем скролл и кнопки
        # Обновляем алгоритм
        self.algorithm_combo.setItemText(0, get_text("algorithm_statistics", default_text="Статистика"))
        self.algorithm_combo.setItemText(1, get_text("algorithm_manual", default_text="Ручной"))
        self.algorithm_combo.setToolTip(get_text("algorithm_setting_desc", default_text=""))