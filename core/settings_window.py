# File: core/settings_window.py
import logging
import re 
import sys 
from pathlib import Path 

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QWidget,
                               QGridLayout, QLabel, QScrollArea, QMessageBox, QCheckBox, QLineEdit,
                               QFileDialog)
from PySide6.QtCore import Qt, Signal, Slot, QTimer 

from core.lang.translations import get_text
from core.hotkey_config import HOTKEY_ACTIONS_CONFIG, DEFAULT_HOTKEYS as DEFAULT_HOTKEYS_VALUES_INTERNAL
from core.ui_components.hotkey_capture_line_edit import HotkeyCaptureLineEdit
from core.app_settings_manager import AppSettingsManager
from core.app_settings_manager import DEFAULT_SAVE_SCREENSHOT_VALUE, DEFAULT_SCREENSHOT_PATH_VALUE


class SettingsWindow(QDialog):
    settings_applied_signal = Signal()

    def __init__(self, app_settings_manager: AppSettingsManager, parent=None): 
        super().__init__(parent)
        self.app_settings_manager = app_settings_manager
        self.parent_window = parent 
        logging.info("[SettingsWindow] Initializing...")

        self.temp_hotkeys: dict[str, str] = {}
        self.temp_save_screenshot_flag: bool = False
        self.temp_screenshot_path: str = ""

        self.setWindowTitle(get_text('hotkey_settings_menu_item')) 
        self.setMinimumWidth(650)
        self.setMinimumHeight(450)
        self.setModal(True) 

        # Эти атрибуты будут пересоздаваться в _create_hotkeys_tab_content
        self.hotkeys_grid_layout: QGridLayout | None = None 
        self.scroll_widget_content_hotkeys: QWidget | None = None
        self.hotkeys_scroll_area: QScrollArea | None = None # Добавим сам QScrollArea как атрибут

        self.hotkey_action_widgets: dict[str, dict] = {} 

        self._init_ui()
        logging.info("[SettingsWindow] Initialization complete.")


    def _load_settings_and_populate_ui(self):
        logging.info("[SettingsWindow] _load_settings_and_populate_ui CALLED")
        
        self.temp_hotkeys = self.app_settings_manager.get_hotkeys() 
        self.temp_save_screenshot_flag = self.app_settings_manager.get_save_screenshot_flag()
        self.temp_screenshot_path = self.app_settings_manager.get_screenshot_save_path()
        
        logging.debug(f"  Loaded temp_hotkeys (internal format): {len(self.temp_hotkeys)} items")
        logging.debug(f"  Loaded temp_save_screenshot_flag: {self.temp_save_screenshot_flag}")
        logging.debug(f"  Loaded temp_screenshot_path: '{self.temp_screenshot_path}'")

        self._populate_hotkey_list_ui() # Это вызовет _create_hotkeys_tab_content, если нужно

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
        logging.info("[SettingsWindow] _load_settings_and_populate_ui END")


    def _init_ui(self):
        logging.debug("[SettingsWindow] _init_ui: Start")
        self.main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        self._create_general_tab() 
        self._create_hotkeys_tab_structure() # Создаем структуру вкладки хоткеев
        
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
        logging.debug("[SettingsWindow] _init_ui: End.")

    def _create_hotkeys_tab_structure(self):
        """Создает базовую структуру вкладки хоткеев (ScrollArea). Содержимое будет создаваться позже."""
        self.hotkeys_tab = QWidget()
        hotkeys_tab_layout = QVBoxLayout(self.hotkeys_tab)
        self.hotkeys_scroll_area = QScrollArea(); self.hotkeys_scroll_area.setWidgetResizable(True)
        hotkeys_tab_layout.addWidget(self.hotkeys_scroll_area)
        self.tab_widget.addTab(self.hotkeys_tab, get_text("sw_hotkeys_tab_title", default_text="Горячие клавиши"))

    def _create_hotkeys_tab_content(self):
        """Создает или пересоздает содержимое вкладки хоткеев (GridLayout и его виджеты)."""
        logging.debug("[SettingsWindow] _create_hotkeys_tab_content CALLED")
        
        # Если уже есть старый контент, удаляем его
        if self.scroll_widget_content_hotkeys:
            self.scroll_widget_content_hotkeys.deleteLater()
            self.scroll_widget_content_hotkeys = None
            self.hotkeys_grid_layout = None # Старый layout будет удален вместе с виджетом
            self.hotkey_action_widgets.clear()

        self.scroll_widget_content_hotkeys = QWidget()
        self.hotkeys_grid_layout = QGridLayout(self.scroll_widget_content_hotkeys)
        self.hotkeys_grid_layout.setHorizontalSpacing(15)
        self.hotkeys_grid_layout.setVerticalSpacing(10)
        
        if self.hotkeys_scroll_area: # Проверка что scroll_area существует
            self.hotkeys_scroll_area.setWidget(self.scroll_widget_content_hotkeys)
        else:
            logging.error("[SettingsWindow] hotkeys_scroll_area is None, cannot set widget content!")

    def _populate_hotkey_list_ui(self):
        logging.info(f"[SettingsWindow] _populate_hotkey_list_ui START.")
        
        # Пересоздаем содержимое вкладки хоткеев
        self._create_hotkeys_tab_content()
        
        if not self.hotkeys_grid_layout: # Дополнительная проверка
            logging.error("[SettingsWindow] hotkeys_grid_layout is None in _populate_hotkey_list_ui after _create_hotkeys_tab_content. Aborting population.")
            return

        self.hotkey_action_widgets.clear() # Очищаем словарь ссылок
        logging.debug(f"  Grid layout and widget dict re-created/cleared. Widgets in dict now: {len(self.hotkey_action_widgets)}")

        row = 0
        for action_id, config in HOTKEY_ACTIONS_CONFIG.items():
            desc_key = config['desc_key']
            description = get_text(desc_key, default_text=action_id) 
            
            current_hotkey_internal = self.temp_hotkeys.get(action_id, get_text('hotkey_not_set'))
            display_hotkey_str = self._normalize_hotkey_for_display(current_hotkey_internal)

            desc_label = QLabel(description); desc_label.setObjectName(f"desc_label_{action_id}")
            hotkey_label = QLabel(f"<code>{display_hotkey_str}</code>"); hotkey_label.setObjectName(f"hotkey_label_{action_id}")
            hotkey_label.setTextFormat(Qt.TextFormat.RichText) 
            
            change_button = QPushButton(get_text('hotkey_settings_change_btn')); change_button.setObjectName(f"change_button_{action_id}")
            change_button.setProperty("action_id", action_id) 
            change_button.clicked.connect(self._on_change_hotkey_button_clicked)

            self.hotkeys_grid_layout.addWidget(desc_label, row, 0, Qt.AlignmentFlag.AlignLeft)
            self.hotkeys_grid_layout.addWidget(hotkey_label, row, 1, Qt.AlignmentFlag.AlignCenter)
            self.hotkeys_grid_layout.addWidget(change_button, row, 2, Qt.AlignmentFlag.AlignRight)
            
            self.hotkey_action_widgets[action_id] = {'desc': desc_label, 'hotkey': hotkey_label, 'button': change_button}
            row += 1
        
        self.hotkeys_grid_layout.setColumnStretch(0, 2); self.hotkeys_grid_layout.setColumnStretch(1, 1); self.hotkeys_grid_layout.setColumnStretch(2, 0) 
        
        if self.scroll_widget_content_hotkeys:
             self.scroll_widget_content_hotkeys.adjustSize()
             self.scroll_widget_content_hotkeys.updateGeometry()
        logging.info(f"[SettingsWindow] _populate_hotkey_list_ui END. Widgets in dict: {len(self.hotkey_action_widgets)}")

    # ... (остальные методы без изменений, кроме _clear_layout, который больше не нужен) ...

    def _normalize_hotkey_for_display(self, internal_hotkey_str: str) -> str:
        if not internal_hotkey_str or \
           internal_hotkey_str.lower() == get_text('hotkey_not_set').lower() or \
           internal_hotkey_str.lower() == get_text('hotkey_none').lower(): 
            return get_text('hotkey_not_set') 
        
        s = internal_hotkey_str 
        
        s = s.replace("num_decimal", "Num Del") 
        s = s.replace("num_divide", "Num /")
        s = s.replace("num_multiply", "Num *")
        s = s.replace("num_subtract", "Num -")
        s = s.replace("num_add", "Num +")
        for i in range(10):
            s = s.replace(f"num_{i}", f"Num {i}")

        key_name_replacements_for_display = {
            "up": "Up", "down": "Down", "left": "Left", "right": "Right",
            "delete": "Delete", "insert": "Insert", "home": "Home", "end": "End",
            "page_up": "PageUp", "page_down": "PageDown", "space": "Space",
            "enter": "Enter", "esc": "Esc", "backspace": "Backspace",
            "tab": "Tab", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", 
            "win": "Win", 
        }
        
        parts = s.split('+')
        formatted_parts = []
        for part_str in parts:
            part_str_stripped = part_str.strip()
            if part_str_stripped.startswith("num "): 
                formatted_parts.append(part_str_stripped) 
            elif part_str_stripped in key_name_replacements_for_display:
                formatted_parts.append(key_name_replacements_for_display[part_str_stripped])
            elif part_str_stripped.startswith("f") and len(part_str_stripped) > 1 and part_str_stripped[1:].isdigit(): 
                formatted_parts.append(part_str_stripped.upper()) 
            else: 
                formatted_parts.append(part_str_stripped.upper() if len(part_str_stripped) == 1 and part_str_stripped.isalpha() else part_str_stripped)
        
        return " + ".join(formatted_parts)


    def _on_change_hotkey_button_clicked(self):
        sender_button = self.sender()
        if not sender_button: return
        action_id = sender_button.property("action_id")
        logging.info(f"[SettingsWindow] Change hotkey for action_id: {action_id}")
        if not action_id or action_id not in self.hotkey_action_widgets: return

        appearance_manager = getattr(self.parent_window, 'appearance_manager', None)
        current_theme = appearance_manager.current_theme if appearance_manager else "light"
        text_color_capture = "orange" if current_theme == "light" else "#FFA500"
        
        self.hotkey_action_widgets[action_id]['hotkey'].setText(f"<i>{get_text('hotkey_settings_press_keys')}</i>")
        self.hotkey_action_widgets[action_id]['hotkey'].setStyleSheet(f"font-style:italic;color:{text_color_capture};")

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
        
        cancel_btn = QPushButton(get_text('hotkey_settings_cancel_capture'))
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus) 
        cancel_btn.clicked.connect(capture_dialog.reject)
        dialog_layout.addWidget(cancel_btn)
        hotkey_input_field.setFocus() 
        
        hotkey_input_field.hotkey_captured.connect(
            lambda aid, hk_str: self.update_temp_hotkey_and_ui(aid, hk_str)
        )
        hotkey_input_field.capture_canceled.connect(
            lambda aid: self.revert_hotkey_display_on_cancel(aid)
        )
        
        result = capture_dialog.exec()
        if result == QDialog.Accepted:
             logging.debug(f"  Hotkey capture dialog accepted for {action_id}")
        else:
             logging.debug(f"  Hotkey capture dialog rejected or canceled for {action_id}")
             self.revert_hotkey_display_on_cancel(action_id)

        try:
            if hotkey_input_field: 
                hotkey_input_field.hotkey_captured.disconnect()
                hotkey_input_field.capture_canceled.disconnect()
        except RuntimeError: 
            pass


    @Slot(str, str)
    def update_temp_hotkey_and_ui(self, action_id: str, new_hotkey_internal_format: str):
        if action_id in self.hotkey_action_widgets:
            logging.info(f"  SettingsWindow: Временное обновление хоткея для {action_id} на '{new_hotkey_internal_format}'")
            self.temp_hotkeys[action_id] = new_hotkey_internal_format 
            display_str = self._normalize_hotkey_for_display(new_hotkey_internal_format)
            self.hotkey_action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>")
            self.hotkey_action_widgets[action_id]['hotkey'].setStyleSheet("") 


    @Slot(str)
    def revert_hotkey_display_on_cancel(self, action_id: str):
        if action_id in self.hotkey_action_widgets:
            logging.info(f"  SettingsWindow: Отмена ввода хоткея для {action_id}")
            original_hotkey_internal = self.temp_hotkeys.get(action_id, get_text('hotkey_not_set'))
            display_str = self._normalize_hotkey_for_display(original_hotkey_internal)
            self.hotkey_action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>")
            self.hotkey_action_widgets[action_id]['hotkey'].setStyleSheet("")


    def _create_general_tab(self): 
        self.general_tab = QWidget()
        general_layout = QVBoxLayout(self.general_tab)
        
        self.save_screenshots_checkbox = QCheckBox(get_text("sw_save_less_than_6_label"))
        self.save_screenshots_checkbox.setObjectName("save_screenshots_checkbox")
        self.save_screenshots_checkbox.stateChanged.connect(self._on_save_screenshot_checkbox_changed)
        general_layout.addWidget(self.save_screenshots_checkbox)

        path_label = QLabel(get_text("sw_save_path_label"))
        general_layout.addWidget(path_label)
        
        path_selection_layout = QHBoxLayout()
        self.path_line_edit = QLineEdit()
        self.path_line_edit.setObjectName("path_line_edit")
        self.path_line_edit.setReadOnly(True) 
        self.path_line_edit.setPlaceholderText(get_text("sw_default_path_text"))
        
        browse_button = QPushButton(get_text("sw_browse_button_text"))
        browse_button.clicked.connect(self._browse_save_directory)
        
        path_selection_layout.addWidget(self.path_line_edit, 1) 
        path_selection_layout.addWidget(browse_button)
        general_layout.addLayout(path_selection_layout)
        
        general_layout.addStretch(1) 
        self.tab_widget.addTab(self.general_tab, get_text("sw_general_tab_title"))


    @Slot(int)
    def _on_save_screenshot_checkbox_changed(self, state: int):
        self.temp_save_screenshot_flag = (state == Qt.CheckState.Checked.value)
        logging.debug(f"Флаг сохранения скриншотов изменен на: {self.temp_save_screenshot_flag}")

    @Slot()
    def _browse_save_directory(self):
        current_path = self.temp_screenshot_path
        if not current_path: 
            if hasattr(sys, 'executable') and sys.executable: current_path = str(Path(sys.executable).parent)
            else: current_path = str(Path.home())

        directory = QFileDialog.getExistingDirectory(self, get_text("sw_select_dir_dialog_title"), current_path)
        if directory: 
            self.temp_screenshot_path = directory
            self.path_line_edit.setText(directory); self.path_line_edit.setToolTip(directory)
            logging.info(f"Выбрана папка для сохранения скриншотов: {directory}")


    def _reset_all_settings_to_defaults(self):
        logging.info("[SettingsWindow] Сброс всех настроек к значениям по умолчанию.")
        self.temp_hotkeys = DEFAULT_HOTKEYS_VALUES_INTERNAL.copy()
        self._populate_hotkey_list_ui() # Перезаполнит UI
        
        self.temp_save_screenshot_flag = DEFAULT_SAVE_SCREENSHOT_VALUE
        self.temp_screenshot_path = DEFAULT_SCREENSHOT_PATH_VALUE
        
        self.save_screenshots_checkbox.setChecked(self.temp_save_screenshot_flag)
        display_path = self.temp_screenshot_path if self.temp_screenshot_path else get_text("sw_default_path_text")
        tooltip_path = self.temp_screenshot_path if self.temp_screenshot_path else get_text("sw_default_path_tooltip")
        self.path_line_edit.setText(display_path)
        self.path_line_edit.setToolTip(tooltip_path)
        
        QMessageBox.information(self, get_text('hotkey_settings_defaults_reset_title'), 
                                get_text('sw_all_settings_reset_msg'))
        logging.info("  Сброс всех настроек завершен.")


    def _apply_settings(self, show_message: bool = True) -> bool:
        logging.info("[SettingsWindow] Применение настроек...")
        hotkey_usage_map: dict[str, str] = {} 
        duplicates_info: list[str] = []
        
        for action_id, internal_hk_str in self.temp_hotkeys.items():
            if not internal_hk_str or \
               internal_hk_str.lower() == get_text('hotkey_none').lower() or \
               internal_hk_str.lower() == get_text('hotkey_not_set').lower():
                continue 
            
            if internal_hk_str in hotkey_usage_map: 
                existing_action_id = hotkey_usage_map[internal_hk_str]
                desc_key1 = HOTKEY_ACTIONS_CONFIG.get(action_id, {}).get('desc_key', action_id)
                desc_key2 = HOTKEY_ACTIONS_CONFIG.get(existing_action_id, {}).get('desc_key', existing_action_id)
                action_desc1_text = get_text(desc_key1)
                action_desc2_text = get_text(desc_key2)
                display_duplicate_hotkey = self._normalize_hotkey_for_display(internal_hk_str)
                duplicates_info.append(f"'{display_duplicate_hotkey}' ({get_text('sw_for_action_text')}: '{action_desc1_text}' {get_text('sw_and_text')} '{action_desc2_text}')")
            else:
                hotkey_usage_map[internal_hk_str] = action_id
        
        if duplicates_info:
            logging.warning(f"Найдены дублирующиеся хоткеи: {', '.join(duplicates_info)}")
            QMessageBox.warning(self, get_text('hotkey_settings_duplicate_title'),
                                get_text('hotkey_settings_duplicate_message') + "\n- " + "\n- ".join(duplicates_info))
            return False 

        self.app_settings_manager.set_hotkeys(self.temp_hotkeys, auto_save=False)
        self.app_settings_manager.set_save_screenshot_flag(self.temp_save_screenshot_flag, auto_save=False)
        self.app_settings_manager.set_screenshot_save_path(self.temp_screenshot_path, auto_save=False)
        self.app_settings_manager.save_settings_to_file() 
        logging.info("  Настройки сохранены в AppSettingsManager и записаны в файл.")

        self.settings_applied_signal.emit() 
        if show_message:
             QMessageBox.information(self, get_text("sw_settings_applied_title"),
                                    get_text("sw_settings_applied_msg"))
        logging.info("Применение настроек успешно завершено.")
        return True


    def _ok_and_save_settings(self):
        logging.info("[SettingsWindow] Нажата кнопка OK.")
        if self._apply_settings(show_message=False): 
            self.accept() 
            logging.info("  Настройки применены, диалог закрыт (Accepted).")
        else:
            logging.warning("  Настройки не были применены из-за ошибок (например, дубликаты). Диалог не закрыт.")


    def open(self): 
        logging.info("[SettingsWindow] open() called. Загрузка настроек в диалог.")
        self._load_settings_and_populate_ui() 
        super().open()

    def exec(self): 
        logging.info("[SettingsWindow] exec() called. Загрузка настроек в диалог.")
        self._load_settings_and_populate_ui() 
        return super().exec()

    def update_theme_dependent_elements(self):
        logging.debug("[SettingsWindow] update_theme_dependent_elements called.")
        if self.parent_window and hasattr(self.parent_window, 'appearance_manager'):
            appearance_manager = self.parent_window.appearance_manager
            current_theme = appearance_manager.current_theme if appearance_manager else "light"
            text_color_capture = "orange" if current_theme == "light" else "#FFA500"
            
            for action_id in self.hotkey_action_widgets:
                if action_id in self.hotkey_action_widgets and 'hotkey' in self.hotkey_action_widgets[action_id]: 
                    hotkey_label_widget = self.hotkey_action_widgets[action_id]['hotkey']
                    if "<i>" in hotkey_label_widget.text(): 
                        hotkey_label_widget.setStyleSheet(f"font-style:italic;color:{text_color_capture};")
                    else:
                        hotkey_label_widget.setStyleSheet("") 
        logging.debug("[SettingsWindow] update_theme_dependent_elements finished.")
