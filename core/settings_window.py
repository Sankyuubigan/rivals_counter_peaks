# File: core/settings_window.py
import logging
import re 
import sys 
from pathlib import Path 

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QWidget,
                               QGridLayout, QLabel, QScrollArea, QMessageBox, QCheckBox, QLineEdit,
                               QFileDialog)
from PySide6.QtCore import Qt, Signal, Slot, QTimer # QTimer пока оставим, может понадобиться для другого

from core.lang.translations import get_text
from core.hotkey_config import HOTKEY_ACTIONS_CONFIG, DEFAULT_HOTKEYS as DEFAULT_HOTKEYS_VALUES
from core.ui_components.hotkey_capture_line_edit import HotkeyCaptureLineEdit
from core.app_settings_manager import AppSettingsManager
from core.app_settings_manager import DEFAULT_SAVE_SCREENSHOT_VALUE, DEFAULT_SCREENSHOT_PATH_VALUE


class SettingsWindow(QDialog):
    settings_applied_signal = Signal()

    def __init__(self, app_settings_manager: AppSettingsManager, parent=None):
        super().__init__(parent)
        self.app_settings_manager = app_settings_manager
        self.parent_window = parent 

        self.temp_hotkeys: dict[str, str] = {}
        self.temp_save_screenshot_flag: bool = False
        self.temp_screenshot_path: str = ""

        self.setWindowTitle(get_text('hotkey_settings_menu_item')) 
        self.setMinimumWidth(650)
        self.setMinimumHeight(450)
        self.setModal(True) 

        self._init_ui()
        # ИЗМЕНЕНИЕ: Убираем QTimer.singleShot. Загрузка будет в open/exec.
        # QTimer.singleShot(0, self._load_settings_and_populate_ui)


    def _load_settings_and_populate_ui(self):
        """Загружает настройки и заполняет UI. Вызывается из open/exec."""
        logging.debug("SettingsWindow: _load_settings_and_populate_ui CALLED")
        self._load_settings_into_dialog()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        self._create_general_tab() 
        self._create_hotkeys_tab() 

        self.main_layout.addWidget(self.tab_widget)

        self.buttons_layout = QHBoxLayout()
        self.reset_all_button = QPushButton(get_text('hotkey_settings_reset_defaults')) 
        self.reset_all_button.clicked.connect(self._reset_all_settings_to_defaults)

        self.apply_button = QPushButton(get_text('sw_apply_button', default_text="Применить")) 
        self.apply_button.clicked.connect(lambda: self._apply_settings(show_message=True)) 

        self.ok_button = QPushButton(get_text('hotkey_settings_save')) 
        self.ok_button.clicked.connect(self._ok_and_save_settings)

        self.cancel_button = QPushButton(get_text('hotkey_settings_cancel')) 
        self.cancel_button.clicked.connect(self.reject) 

        self.buttons_layout.addWidget(self.reset_all_button)
        self.buttons_layout.addStretch(1)
        self.buttons_layout.addWidget(self.apply_button)
        self.buttons_layout.addWidget(self.ok_button)
        self.buttons_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.buttons_layout)

    def _load_settings_into_dialog(self):
        logging.debug("SettingsWindow: _load_settings_into_dialog START")
        self.temp_hotkeys = self.app_settings_manager.get_hotkeys()
        self.temp_save_screenshot_flag = self.app_settings_manager.get_save_screenshot_flag()
        self.temp_screenshot_path = self.app_settings_manager.get_screenshot_save_path()
        logging.debug(f"  Loaded temp_hotkeys: {len(self.temp_hotkeys)} items")

        self._populate_hotkey_list_ui() # Этот вызов теперь должен быть безопаснее

        if hasattr(self, 'save_screenshots_checkbox'):
            self.save_screenshots_checkbox.setChecked(self.temp_save_screenshot_flag)
        
        if hasattr(self, 'path_line_edit'):
            display_path = self.temp_screenshot_path
            tooltip_path = self.temp_screenshot_path
            if not self.temp_screenshot_path:
                display_path = get_text("sw_default_path_text", default_text="По умолчанию (рядом с программой)")
                tooltip_path = get_text("sw_default_path_tooltip", default_text="Скриншоты будут сохраняться в папку, откуда запущена программа")
            self.path_line_edit.setText(display_path)
            self.path_line_edit.setToolTip(tooltip_path)
        logging.debug("SettingsWindow: _load_settings_into_dialog END")

    def _create_hotkeys_tab(self):
        self.hotkeys_tab = QWidget()
        hotkeys_tab_layout = QVBoxLayout(self.hotkeys_tab)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.hotkeys_grid_layout = QGridLayout(scroll_widget) 
        self.hotkeys_grid_layout.setHorizontalSpacing(15)
        self.hotkeys_grid_layout.setVerticalSpacing(10)
        
        self.hotkey_action_widgets: dict[str, dict] = {} 

        scroll_area.setWidget(scroll_widget)
        hotkeys_tab_layout.addWidget(scroll_area)
        self.tab_widget.addTab(self.hotkeys_tab, get_text("sw_hotkeys_tab_title", default_text="Горячие клавиши"))

    def _populate_hotkey_list_ui(self):
        logging.debug(f"SettingsWindow: _populate_hotkey_list_ui START. Current grid items: {self.hotkeys_grid_layout.count()}")
        
        # Улучшенная очистка
        while self.hotkeys_grid_layout.count() > 0:
            for i in range(self.hotkeys_grid_layout.count()):
                item = self.hotkeys_grid_layout.itemAt(i)
                if item is not None:
                    widget = item.widget()
                    if widget is not None:
                        logging.debug(f"  Removing widget from grid at index {i}: {type(widget)}")
                        widget.deleteLater()
                        # self.hotkeys_grid_layout.removeWidget(widget) # Не нужно, если удаляем через takeAt
                    else: # Если это layout item
                        layout_in_item = item.layout()
                        if layout_in_item is not None:
                            logging.debug(f"  Removing layout from grid at index {i}")
                            # Очищаем вложенный layout перед удалением
                            while layout_in_item.count():
                                sub_item = layout_in_item.takeAt(0)
                                if sub_item and sub_item.widget():
                                    sub_item.widget().deleteLater()
                            layout_in_item.deleteLater()
                    # Удаляем сам элемент из grid layout
                    taken_item = self.hotkeys_grid_layout.takeAt(i)
                    if taken_item:
                        del taken_item # Попытка освободить память
                    break # Выходим из внутреннего цикла, чтобы re-evaluate grid_layout.count()
            else: # Если внутренний цикл не нашел элементов для удаления
                break
        
        self.hotkey_action_widgets.clear()
        logging.debug(f"SettingsWindow: Grid layout cleared. Items now: {self.hotkeys_grid_layout.count()}")


        row = 0
        logging.debug(f"  HOTKEY_ACTIONS_CONFIG содержит {len(HOTKEY_ACTIONS_CONFIG)} элементов.")
        for action_id, config in HOTKEY_ACTIONS_CONFIG.items():
            logging.debug(f"  Обработка action_id: {action_id}, строка: {row}")
            desc_key = config['desc_key']
            description = get_text(desc_key, default_text=action_id) 
            
            current_hotkey_str_internal = self.temp_hotkeys.get(action_id, get_text('hotkey_not_set'))
            display_hotkey_str = self._normalize_hotkey_for_display(current_hotkey_str_internal)

            desc_label = QLabel(description)
            hotkey_label = QLabel(f"<code>{display_hotkey_str}</code>")
            hotkey_label.setTextFormat(Qt.TextFormat.RichText) 
            
            change_button = QPushButton(get_text('hotkey_settings_change_btn')) 
            change_button.setProperty("action_id", action_id) 
            change_button.clicked.connect(self._on_change_hotkey_button_clicked)

            self.hotkeys_grid_layout.addWidget(desc_label, row, 0, Qt.AlignmentFlag.AlignLeft)
            self.hotkeys_grid_layout.addWidget(hotkey_label, row, 1, Qt.AlignmentFlag.AlignCenter)
            self.hotkeys_grid_layout.addWidget(change_button, row, 2, Qt.AlignmentFlag.AlignRight)
            
            self.hotkey_action_widgets[action_id] = {'desc': desc_label, 'hotkey': hotkey_label, 'button': change_button}
            row += 1
        
        self.hotkeys_grid_layout.setColumnStretch(0, 2) 
        self.hotkeys_grid_layout.setColumnStretch(1, 1) 
        self.hotkeys_grid_layout.setColumnStretch(2, 0) 
        logging.debug(f"SettingsWindow: _populate_hotkey_list_ui END. Grid items: {self.hotkeys_grid_layout.count()}, Widgets stored: {len(self.hotkey_action_widgets)}")


    def _normalize_hotkey_for_display(self, hotkey_str: str) -> str:
        if not hotkey_str or hotkey_str == get_text('hotkey_not_set') or hotkey_str == get_text('hotkey_none'):
            return get_text('hotkey_not_set')
        
        s = hotkey_str
        s = s.replace("num_", "Num ")
        s = s.replace("decimal", "Del") 
        if "Num Del" in s and "Tab" in s : 
            s = s.replace("Num Del", "Num .")

        key_name_replacements = {
            "up": "Up", "down": "Down", "left": "Left", "right": "Right",
            "delete": "Delete", "insert": "Insert", "home": "Home", "end": "End",
            "page_up": "PageUp", "page_down": "PageDown", "space": "Space",
            "enter": "Enter", "esc": "Esc", "backspace": "Backspace",
            "tab": "Tab", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"
        }
        def replace_func(match):
            return key_name_replacements.get(match.group(0).lower(), match.group(0))

        pattern = r'\b(' + '|'.join(re.escape(k) for k in key_name_replacements.keys()) + r')\b'
        s = re.sub(pattern, replace_func, s, flags=re.IGNORECASE)
        
        parts = s.split('+')
        formatted_parts = []
        for part_str in parts:
            stripped_part = part_str.strip()
            if stripped_part.lower() in ["tab", "win", "ctrl", "alt", "shift"]:
                formatted_parts.append(stripped_part.capitalize())
            elif stripped_part.lower().startswith("num ") and len(stripped_part) > 4:
                formatted_parts.append(stripped_part) 
            elif stripped_part.lower().startswith("f") and len(stripped_part) > 1 and stripped_part[1:].isdigit(): 
                formatted_parts.append(stripped_part.upper())
            else: 
                formatted_parts.append(stripped_part.upper())
        
        return " + ".join(formatted_parts)


    def _on_change_hotkey_button_clicked(self):
        sender_button = self.sender()
        if not sender_button: return
        action_id = sender_button.property("action_id")
        if not action_id or action_id not in self.hotkey_action_widgets:
            return

        appearance_manager = getattr(self.parent_window, 'appearance_manager', None)
        current_theme = appearance_manager.current_theme if appearance_manager else "light"
        text_color_during_capture = "orange" if current_theme == "light" else "#FFA500"
        
        self.hotkey_action_widgets[action_id]['hotkey'].setText(f"<i>{get_text('hotkey_settings_press_keys')}</i>")
        self.hotkey_action_widgets[action_id]['hotkey'].setStyleSheet(f"font-style:italic;color:{text_color_during_capture};")

        capture_dialog = QDialog(self)
        capture_dialog.setWindowTitle(get_text('hotkey_settings_capture_title'))
        capture_dialog.setModal(True)
        dialog_layout = QVBoxLayout(capture_dialog)
        
        action_desc_key = HOTKEY_ACTIONS_CONFIG[action_id]['desc_key']
        action_desc_text = get_text(action_desc_key)
        info_label = QLabel(get_text('hotkey_settings_press_new_hotkey_for', action=action_desc_text))
        dialog_layout.addWidget(info_label)

        hotkey_input_field = HotkeyCaptureLineEdit(action_id, capture_dialog)
        dialog_layout.addWidget(hotkey_input_field)
        
        cancel_capture_btn = QPushButton(get_text('hotkey_settings_cancel_capture'))
        cancel_capture_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus) 
        cancel_capture_btn.clicked.connect(capture_dialog.reject)
        dialog_layout.addWidget(cancel_capture_btn)

        hotkey_input_field.setFocus() 
        
        @Slot(str, str)
        def on_hotkey_captured_locally(captured_action_id: str, new_hotkey_internal: str):
            if captured_action_id == action_id:
                self.temp_hotkeys[action_id] = new_hotkey_internal 
                display_str = self._normalize_hotkey_for_display(new_hotkey_internal)
                self.hotkey_action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>")
                self.hotkey_action_widgets[action_id]['hotkey'].setStyleSheet("") 

        @Slot(str)
        def on_capture_canceled_locally(canceled_action_id: str):
            if canceled_action_id == action_id:
                original_hotkey = self.temp_hotkeys.get(action_id, get_text('hotkey_not_set'))
                display_str = self._normalize_hotkey_for_display(original_hotkey)
                self.hotkey_action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>")
                self.hotkey_action_widgets[action_id]['hotkey'].setStyleSheet("")

        hotkey_input_field.hotkey_captured.connect(on_hotkey_captured_locally)
        hotkey_input_field.capture_canceled.connect(on_capture_canceled_locally)
        
        result = capture_dialog.exec()
        if result == QDialog.Accepted:
             logging.debug(f"Hotkey capture dialog accepted for {action_id}")
        else:
             logging.debug(f"Hotkey capture dialog rejected or canceled for {action_id}")
             on_capture_canceled_locally(action_id) 


        try:
            if hotkey_input_field:
                hotkey_input_field.hotkey_captured.disconnect(on_hotkey_captured_locally)
                hotkey_input_field.capture_canceled.disconnect(on_capture_canceled_locally)
        except RuntimeError:
            logging.debug("Ошибка отсоединения сигналов от HotkeyCaptureLineEdit.")

    def _create_general_tab(self): 
        self.general_tab = QWidget()
        general_layout = QVBoxLayout(self.general_tab)
        
        self.save_screenshots_checkbox = QCheckBox(get_text("sw_save_less_than_6_label", default_text="Сохранять скриншоты экрана, если распознано < 6 героев"))
        self.save_screenshots_checkbox.stateChanged.connect(self._on_save_screenshot_checkbox_changed)
        general_layout.addWidget(self.save_screenshots_checkbox)

        path_label = QLabel(get_text("sw_save_path_label", default_text="Папка для сохранения скриншотов:"))
        general_layout.addWidget(path_label)
        
        path_selection_layout = QHBoxLayout()
        self.path_line_edit = QLineEdit()
        self.path_line_edit.setReadOnly(True) 
        self.path_line_edit.setPlaceholderText(get_text("sw_default_path_text", default_text="По умолчанию (рядом с программой)"))
        
        browse_button = QPushButton(get_text("sw_browse_button_text", default_text="Обзор..."))
        browse_button.clicked.connect(self._browse_save_directory)
        
        path_selection_layout.addWidget(self.path_line_edit, 1) 
        path_selection_layout.addWidget(browse_button)
        general_layout.addLayout(path_selection_layout)
        
        general_layout.addStretch(1) 
        self.tab_widget.addTab(self.general_tab, get_text("sw_general_tab_title", default_text="Общие"))

    @Slot(int)
    def _on_save_screenshot_checkbox_changed(self, state: int):
        self.temp_save_screenshot_flag = (state == Qt.CheckState.Checked.value)

    @Slot()
    def _browse_save_directory(self):
        current_path_for_dialog = self.temp_screenshot_path
        if not current_path_for_dialog: 
            if hasattr(sys, 'executable') and sys.executable:
                current_path_for_dialog = str(Path(sys.executable).parent)
            else:
                current_path_for_dialog = str(Path.home())

        directory = QFileDialog.getExistingDirectory(
            self,
            get_text("sw_select_dir_dialog_title", default_text="Выберите папку для сохранения скриншотов"),
            current_path_for_dialog
        )
        if directory: 
            self.temp_screenshot_path = directory
            self.path_line_edit.setText(directory)
            self.path_line_edit.setToolTip(directory)

    def _reset_all_settings_to_defaults(self):
        self.temp_hotkeys = DEFAULT_HOTKEYS_VALUES.copy()
        self._populate_hotkey_list_ui() 
        
        self.temp_save_screenshot_flag = DEFAULT_SAVE_SCREENSHOT_VALUE
        self.temp_screenshot_path = DEFAULT_SCREENSHOT_PATH_VALUE
        
        self.save_screenshots_checkbox.setChecked(self.temp_save_screenshot_flag)
        display_path = self.temp_screenshot_path if self.temp_screenshot_path else get_text("sw_default_path_text")
        tooltip_path = self.temp_screenshot_path if self.temp_screenshot_path else get_text("sw_default_path_tooltip")
        self.path_line_edit.setText(display_path)
        self.path_line_edit.setToolTip(tooltip_path)
        
        QMessageBox.information(self, 
                                get_text('hotkey_settings_defaults_reset_title'), 
                                get_text('sw_all_settings_reset_msg', default_text="Все настройки сброшены к значениям по умолчанию."))

    def _apply_settings(self, show_message: bool = True) -> bool:
        hotkey_map: dict[str, str] = {}
        duplicates_found: list[str] = []
        for action_id, hotkey_str_internal in self.temp_hotkeys.items():
            if not hotkey_str_internal or \
               hotkey_str_internal == get_text('hotkey_none') or \
               hotkey_str_internal == get_text('hotkey_not_set'):
                continue
            
            if hotkey_str_internal in hotkey_map:
                desc_key1 = HOTKEY_ACTIONS_CONFIG.get(action_id, {}).get('desc_key', action_id)
                desc_key2 = HOTKEY_ACTIONS_CONFIG.get(hotkey_map[hotkey_str_internal], {}).get('desc_key', hotkey_map[hotkey_str_internal])
                action_desc1 = get_text(desc_key1)
                action_desc2 = get_text(desc_key2)
                display_duplicate_str = self._normalize_hotkey_for_display(hotkey_str_internal)
                duplicates_found.append(f"'{display_duplicate_str}' ({get_text('sw_for_action_text', default_text='для')}: '{action_desc1}' {get_text('sw_and_text', default_text='и')} '{action_desc2}')")
            else:
                hotkey_map[hotkey_str_internal] = action_id
        
        if duplicates_found:
            QMessageBox.warning(self, get_text('hotkey_settings_duplicate_title'),
                                get_text('hotkey_settings_duplicate_message') + "\n- " + "\n- ".join(duplicates_found))
            return False 

        self.app_settings_manager.set_hotkeys(self.temp_hotkeys, auto_save=False)
        self.app_settings_manager.set_save_screenshot_flag(self.temp_save_screenshot_flag, auto_save=False)
        self.app_settings_manager.set_screenshot_save_path(self.temp_screenshot_path, auto_save=False)
        self.app_settings_manager.save_settings_to_file() 

        self.settings_applied_signal.emit() 
        if show_message:
             QMessageBox.information(self, get_text("sw_settings_applied_title", default_text="Настройки применены"),
                                    get_text("sw_settings_applied_msg", default_text="Изменения успешно применены."))
        return True

    def _ok_and_save_settings(self):
        if self._apply_settings(show_message=False): 
            self.accept() 

    def open(self): 
        logging.debug("SettingsWindow: open() called. Reloading settings into dialog.")
        self._load_settings_and_populate_ui() 
        super().open()

    def exec(self): 
        logging.debug("SettingsWindow: exec() called. Reloading settings into dialog.")
        self._load_settings_and_populate_ui() 
        return super().exec()
