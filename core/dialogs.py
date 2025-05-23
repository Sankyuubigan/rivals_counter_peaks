# File: core/dialogs.py
from PySide6.QtWidgets import (QDialog, QTextBrowser, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout,
                               QLabel, QScrollArea, QWidget, QGridLayout, QLineEdit, QApplication) 
from PySide6.QtCore import Qt, Slot, QTimer, QEvent, QKeyCombination, Signal, QObject
# ИЗМЕНЕНО: Добавлен QCloseEvent
from PySide6.QtGui import QKeySequence, QCloseEvent 
from database import heroes_bd
from core.lang.translations import get_text
import pyperclip
import logging
import os
import sys 
import markdown

import json

HOTKEY_INPUT_FINISHED_EVENT = QEvent.Type(QEvent.User + 1)

def resource_path_dialogs(relative_path):
    try:
        base_path = sys._MEIPASS 
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__)) 
    if base_path.endswith("core"): 
        lang_path_base = os.path.join(base_path, "lang")
    else: 
        lang_path_base = os.path.join(base_path, "core", "lang")
    return os.path.join(lang_path_base, relative_path)


class AboutProgramDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent 
        self.setObjectName("AboutProgramDialog") 
        self.setWindowTitle(get_text('about_program'))
        self.setGeometry(0, 0, 700, 550)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.update_content_theme() 

        self.close_button = QPushButton("OK")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.text_browser)
        layout.addWidget(self.close_button)

    def update_content_theme(self):
        current_lang_code = 'ru_RU'
        if hasattr(self.parent_window, 'logic') and hasattr(self.parent_window.logic, 'DEFAULT_LANGUAGE'):
             current_lang_code = self.parent_window.logic.DEFAULT_LANGUAGE

        md_filename_key = "information_ru.md"
        if current_lang_code.startswith('en'):
            md_filename_key = "information_en.md"
        
        md_filepath = resource_path_dialogs(md_filename_key)
        logging.debug(f"Attempting to load markdown for AboutDialog from: {md_filepath}")
        
        current_theme = "light"
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager: 
            current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'): 
            current_theme = self.parent_window.current_theme


        body_bg_color = "#ffffff"
        body_text_color = "#000000"
        h_color = "#333"
        link_color = "#007bff"
        code_bg_color = "#f0f0f0"

        if current_theme == "dark":
            body_bg_color = "#2e2e2e"
            body_text_color = "#e0e0e0"
            h_color = "#cccccc"
            link_color = "#58a6ff" 
            code_bg_color = "#3c3c3c"


        if os.path.exists(md_filepath):
            md_content = ""
            try:
                with open(md_filepath, "r", encoding="utf-8") as f:
                    md_content = f.read()
                css = f"""
                <style>
                    body {{ 
                        font-family: sans-serif; font-size: 10pt; line-height: 1.6; 
                        background-color: {body_bg_color}; color: {body_text_color}; 
                    }}
                    h1 {{ font-size: 16pt; margin-bottom: 10px; color: {h_color}; border-bottom: 1px solid #ccc; padding-bottom: 5px;}}
                    h2 {{ font-size: 14pt; margin-top: 20px; margin-bottom: 8px; color: {h_color};}}
                    h3 {{ font-size: 12pt; margin-top: 15px; margin-bottom: 5px; color: {h_color};}}
                    p {{ margin-bottom: 10px; }}
                    ul, ol {{ margin-left: 20px; margin-bottom: 10px; }}
                    li {{ margin-bottom: 5px; }}
                    code {{ background-color: {code_bg_color}; padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
                    a {{ color: {link_color}; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    hr {{ border: 0; height: 1px; background: #ccc; margin: 20px 0; }}
                </style>
                """
                html_content = markdown.markdown(md_content, extensions=['extra', 'sane_lists'])
                self.text_browser.setHtml(css + html_content)
            except Exception as e:
                logging.error(f"Error loading or parsing {md_filepath}: {e}")
                self.text_browser.setPlainText(f"Error loading content for {md_filename_key}: {e}")
        else:
            logging.warning(f"Markdown file not found: {md_filepath} (searched for {md_filename_key})")
            self.text_browser.setPlainText(f"Information file not found: {md_filename_key}")


    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry: 
                center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)


class HeroRatingDialog(QDialog): 
    def __init__(self, parent, app_version):
        super().__init__(parent)
        self.setWindowTitle(get_text('hero_rating_title', version=app_version)) 
        self.setGeometry(0, 0, 400, 600)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        text_browser = QTextBrowser()
        text_browser.setReadOnly(True)
        text_browser.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)

        counter_counts = {hero: 0 for hero in heroes_bd.heroes}
        for hero_being_countered, counters_data in heroes_bd.heroes_counters.items():
            if isinstance(counters_data, dict):
                for counter_hero in counters_data.get("hard", []) + counters_data.get("soft", []):
                    if counter_hero in counter_counts:
                        counter_counts[counter_hero] +=1
        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1], reverse=True) 
        rating_lines = [f"{hero} ({count})" for hero, count in sorted_heroes]
        text_browser.setText("\n".join(rating_lines))
        layout.addWidget(text_browser)

        close_button = QPushButton("OK")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry:
                center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text('logs_window_title'))
        self.setGeometry(150, 150, 900, 600)
        self.setModal(False)

        self.layout = QVBoxLayout(self)
        self.log_browser = QTextBrowser(self)
        self.log_browser.setReadOnly(True)
        self.log_browser.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        font = self.log_browser.font()
        font.setFamily("Courier New")
        font.setPointSize(10)
        self.log_browser.setFont(font)

        self.copy_button = QPushButton(get_text('copy_all_logs_button'))
        self.copy_button.clicked.connect(self.copy_logs)

        self.clear_button = QPushButton(get_text('clear_log_window_button'))
        self.clear_button.clicked.connect(self.clear_log_display)

        self.button_layout = QVBoxLayout()
        self.button_layout.addWidget(self.copy_button)
        self.button_layout.addWidget(self.clear_button)
        self.button_layout.addStretch(1)

        self.main_hbox_layout = QHBoxLayout()
        self.main_hbox_layout.addWidget(self.log_browser, stretch=1)
        self.main_hbox_layout.addLayout(self.button_layout)
        self.layout.addLayout(self.main_hbox_layout)

    @Slot(str)
    def append_log(self, message):
        self.log_browser.append(message)

    @Slot()
    def copy_logs(self):
        all_logs = self.log_browser.toPlainText()
        if not all_logs:
            QMessageBox.information(self, get_text('info'), get_text('log_copy_no_logs'))
            return
        try: 
            pyperclip.copy(all_logs)
            logging.info("Logs copied to clipboard.")
        except pyperclip.PyperclipException as e:
            logging.error(f"Pyperclip error copying logs: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")
        except Exception as e: 
            logging.error(f"Unexpected error copying logs: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")

    @Slot()
    def clear_log_display(self):
        self.log_browser.clear()
        logging.info("Log display cleared by user.")

    def closeEvent(self, event: QCloseEvent):
        logging.debug("LogDialog close event: hiding window.")
        self.hide()
        event.ignore()


class HotkeyDisplayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent 
        self.setWindowTitle(get_text('hotkeys_window_title'))
        self.setMinimumWidth(550)
        self.setModal(True)

        self.layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser(self)
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(False)
        
        self.update_html_content() 

        self.close_button = QPushButton("OK")
        self.close_button.clicked.connect(self.accept)
        self.layout.addWidget(self.text_browser)
        self.layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)
        QTimer.singleShot(0, self.center_on_parent)

    def update_html_content(self):
        current_theme = "light"
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager:
            current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'):
             current_theme = self.parent_window.current_theme
        
        body_bg_color = "white"
        body_text_color = "black"
        code_bg_color = "#f0f0f0"
        h_color = "#333"

        if current_theme == "dark":
            body_bg_color = "#2e2e2e"
            body_text_color = "#e0e0e0"
            code_bg_color = "#3c3c3c"
            h_color = "#cccccc"

        hotkeys_text_html = f"""
        <html><head><style> 
            body {{ 
                font-family: sans-serif; font-size: 10pt; 
                background-color: {body_bg_color}; color: {body_text_color}; 
            }} 
            h3 {{ margin-bottom: 5px; margin-top: 10px; color: {h_color}; }} 
            ul {{ margin-top: 0px; padding-left: 20px; }} 
            li {{ margin-bottom: 3px; }} 
            code {{ background-color: {code_bg_color}; padding: 1px 4px; border-radius: 3px; }} 
        </style></head><body>
            <h3>{get_text('hotkeys_section_main')}</h3><ul>
                <li><code>Tab + ↑/↓/←/→</code>: {get_text('hotkey_desc_navigation')}</li>
                <li><code>Tab + Num 0</code>: {get_text('hotkey_desc_select')}</li>
                <li><code>Tab + Num . (Точка/Del)</code>: {get_text('hotkey_desc_toggle_mode')}</li>
                <li><code>Tab + Num /</code>: {get_text('hotkey_desc_recognize')}</li>
                <li><code>Tab + Num -</code>: {get_text('hotkey_desc_clear')}</li>
                <li><code>Tab + Num 1</code>: {get_text('hotkey_desc_copy_team')}</li>
                <li><code>Tab + Num 7</code>: {get_text('hotkey_desc_toggle_tray')}</li>
                <li><code>Tab + Num 9</code>: {get_text('hotkey_desc_toggle_mouse_ignore')}</li>
                <li><code>Tab + Num 3</code>: {get_text('hotkey_desc_debug_screenshot')}</li></ul>
            <h3>{get_text('hotkeys_section_interaction_title')}</h3><ul>
                <li><code>{get_text('hotkey_desc_lmb')}</code>: {get_text('hotkey_desc_lmb_select')}</li>
                <li><code>{get_text('hotkey_desc_rmb')}</code>: {get_text('hotkey_desc_rmb_priority')}</li>
                <li><code>{get_text('hotkey_desc_drag')}</code>: {get_text('hotkey_desc_drag_window')}</li>
                <li><code>{get_text('hotkey_desc_slider')}</code>: {get_text('hotkey_desc_slider_transparency')}</li></ul>
        </body></html>"""
        self.text_browser.setHtml(hotkeys_text_html)


    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry:
                center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

class HotkeySettingsDialog(QDialog):
    hotkey_changed_signal = Signal(str, str) 

    def __init__(self, current_hotkeys, hotkey_actions_config, parent=None):
        super().__init__(parent)
        self.current_hotkeys_copy = dict(current_hotkeys) 
        self.hotkey_actions_config = hotkey_actions_config
        self.parent_window = parent
        self.setWindowTitle(get_text('hotkey_settings_window_title'))
        self.setMinimumWidth(600); self.setModal(True)
        
        self.installEventFilter(self) 

        self.main_layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget(); self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setHorizontalSpacing(15); self.grid_layout.setVerticalSpacing(10)
        self.action_widgets = {}
        self._populate_hotkey_list()
        self.scroll_area.setWidget(self.scroll_widget); self.main_layout.addWidget(self.scroll_area)
        
        self.buttons_layout = QHBoxLayout()
        self.reset_defaults_button = QPushButton(get_text('hotkey_settings_reset_defaults'))
        self.reset_defaults_button.clicked.connect(self.reset_to_defaults)
        self.save_button = QPushButton(get_text('hotkey_settings_save'))
        self.save_button.clicked.connect(self.save_and_close)
        self.cancel_button = QPushButton(get_text('hotkey_settings_cancel'))
        self.cancel_button.clicked.connect(self.reject) 
        
        self.buttons_layout.addWidget(self.reset_defaults_button); self.buttons_layout.addStretch(1)
        self.buttons_layout.addWidget(self.save_button); self.buttons_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.buttons_layout)
        QTimer.singleShot(0, self.center_on_parent)

    def _populate_hotkey_list(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()
        self.action_widgets.clear(); row = 0
        for action_id, config in self.hotkey_actions_config.items():
            desc_key = config['desc_key']; description = get_text(desc_key)
            current_hotkey_str = self.current_hotkeys_copy.get(action_id, get_text('hotkey_not_set')) 
            desc_label = QLabel(description); hotkey_label = QLabel(f"<code>{current_hotkey_str}</code>")
            hotkey_label.setTextFormat(Qt.TextFormat.RichText)
            change_button = QPushButton(get_text('hotkey_settings_change_btn'))
            change_button.setProperty("action_id", action_id)
            change_button.clicked.connect(self.on_change_hotkey_button_clicked)
            self.grid_layout.addWidget(desc_label, row, 0, Qt.AlignmentFlag.AlignLeft)
            self.grid_layout.addWidget(hotkey_label, row, 1, Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(change_button, row, 2, Qt.AlignmentFlag.AlignRight)
            self.action_widgets[action_id] = {'desc': desc_label, 'hotkey': hotkey_label, 'button': change_button}
            row += 1
        self.grid_layout.setColumnStretch(0, 2); self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setColumnStretch(2, 0)

    def on_change_hotkey_button_clicked(self):
        sender_button = self.sender()
        if not sender_button: return
        action_id = sender_button.property("action_id")
        if not action_id or action_id not in self.action_widgets: return

        logging.debug(f"Change hotkey requested for action: {action_id}")
        
        current_theme = "light"
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager:
            current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'):
             current_theme = self.parent_window.current_theme
        text_color_during_capture = "orange"
        if current_theme == "dark":
             text_color_during_capture = "#FFA500" 

        self.action_widgets[action_id]['hotkey'].setText(f"<i>{get_text('hotkey_settings_press_keys')}</i>")
        self.action_widgets[action_id]['hotkey'].setStyleSheet(f"font-style: italic; color: {text_color_during_capture};")
        
        capture_dialog = QDialog(self)
        capture_dialog.setWindowTitle(get_text('hotkey_settings_capture_title'))
        capture_dialog.setModal(True)
        
        dialog_layout = QVBoxLayout(capture_dialog)
        
        action_desc = get_text(self.hotkey_actions_config[action_id]['desc_key'])
        info_label = QLabel(get_text('hotkey_settings_press_new_hotkey_for').format(action=action_desc))
        dialog_layout.addWidget(info_label)
        
        hotkey_input_field = HotkeyCaptureLineEdit(action_id, capture_dialog) 
        hotkey_input_field.setObjectName("HotkeyCaptureLineEdit") 
        dialog_layout.addWidget(hotkey_input_field)
        
        cancel_btn = QPushButton(get_text('hotkey_settings_cancel_capture'))
        cancel_btn.clicked.connect(capture_dialog.reject) 
        dialog_layout.addWidget(cancel_btn)
        
        hotkey_input_field.setFocus()
        
        def on_captured(act_id, key_str):
            if act_id == action_id:
                self.update_hotkey_for_action(act_id, key_str) 
                capture_dialog.accept()
        
        def on_canceled_or_rejected(): 
            if hotkey_input_field and hotkey_input_field.action_id == action_id:
                self.cancel_hotkey_capture(action_id) 

        hotkey_input_field.hotkey_captured.connect(on_captured)
        capture_dialog.rejected.connect(on_canceled_or_rejected)
        
        capture_dialog.exec()

        try:
            if hotkey_input_field: 
                 hotkey_input_field.hotkey_captured.disconnect(on_captured)
        except RuntimeError: pass 
        try:
             capture_dialog.rejected.disconnect(on_canceled_or_rejected)
        except RuntimeError: pass

    @Slot(str, str)
    def update_hotkey_for_action(self, action_id: str, new_hotkey_str: str):
        if action_id in self.action_widgets:
            logging.info(f"Updating hotkey (in dialog copy) for {action_id} to {new_hotkey_str}")
            self.current_hotkeys_copy[action_id] = new_hotkey_str 
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{new_hotkey_str}</code>")
            self.action_widgets[action_id]['hotkey'].setStyleSheet("") 

    @Slot(str)
    def cancel_hotkey_capture(self, action_id: str):
        if action_id in self.action_widgets:
            original_hotkey = self.current_hotkeys_copy.get(action_id, get_text('hotkey_not_set'))
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{original_hotkey}</code>")
            self.action_widgets[action_id]['hotkey'].setStyleSheet("") 
            logging.debug(f"Hotkey capture canceled/reverted for {action_id}, to {original_hotkey}")

    def reset_to_defaults(self):
        if self.parent_window and hasattr(self.parent_window, 'hotkey_manager'):
            default_hotkeys = self.parent_window.hotkey_manager.get_default_hotkeys()
            self.current_hotkeys_copy = dict(default_hotkeys) 
            self._populate_hotkey_list() 
            QMessageBox.information(self, get_text('hotkey_settings_defaults_reset_title'), get_text('hotkey_settings_defaults_reset_msg'))
        else:
            logging.error("Hotkey manager not found in parent window for resetting defaults.")

    def save_and_close(self):
        if self.parent_window and hasattr(self.parent_window, 'hotkey_manager'):
            hotkey_map = {}; duplicates = []
            for action_id, hotkey_str in self.current_hotkeys_copy.items(): 
                if hotkey_str == get_text('hotkey_none') or hotkey_str == get_text('hotkey_not_set'): continue
                if hotkey_str in hotkey_map:
                    action_desc1 = get_text(self.hotkey_actions_config.get(action_id, {}).get('desc_key', action_id))
                    action_desc2 = get_text(self.hotkey_actions_config.get(hotkey_map[hotkey_str], {}).get('desc_key', hotkey_map[hotkey_str]))
                    duplicates.append(f"'{hotkey_str}' for '{action_desc1}' and '{action_desc2}'")
                else: hotkey_map[hotkey_str] = action_id
            if duplicates:
                QMessageBox.warning(self, get_text('hotkey_settings_duplicate_title'), get_text('hotkey_settings_duplicate_message') + "\n- " + "\n- ".join(duplicates)); return
            
            self.parent_window.hotkey_manager.save_hotkeys(self.current_hotkeys_copy) 
            self.accept() 
        else: logging.error("Hotkey manager not found in parent window for saving.")

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry:
                center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key_event = event # QKeyEvent(event)
            if key_event.key() == Qt.Key_Tab:
                # Проверяем, не находится ли фокус в HotkeyCaptureLineEdit
                focus_widget = QApplication.focusWidget()
                if isinstance(focus_widget, HotkeyCaptureLineEdit):
                    logging.debug(f"HotkeySettingsDialog.eventFilter: Tab pressed in HotkeyCaptureLineEdit, event not consumed by dialog's filter.")
                    return False # Позволяем HotkeyCaptureLineEdit или MainWindow.eventFilter обработать

                logging.debug(f"HotkeySettingsDialog.eventFilter: Tab key consumed for watched: {watched.objectName() if hasattr(watched, 'objectName') else type(watched)}")
                return True 
        return super().eventFilter(watched, event)


class HotkeyCaptureLineEdit(QLineEdit):
    hotkey_captured = Signal(str, str)  
    capture_canceled = Signal(str)      

    def __init__(self, action_id, parent_dialog): 
        super().__init__(parent_dialog)
        self.action_id = action_id
        self.setReadOnly(True)
        self.setObjectName("HotkeyCaptureLineEdit") 
        
        self._current_qt_modifiers = Qt.KeyboardModifier.NoModifier
        self._current_qt_key = Qt.Key.Key_unknown
        self._keypad_modifier_active_on_press = False 
        self._reset_field_to_prompt() 

    def _reset_field_to_prompt(self):
        self.setText(get_text('hotkey_settings_press_keys'))
        text_color = "gray" 
        parent_main_window = None
        current_parent = self.parent()
        while current_parent:
            if hasattr(current_parent, 'parent_window') and current_parent.parent_window is not None: 
                parent_main_window = current_parent.parent_window
                break
            if hasattr(current_parent, 'appearance_manager'): 
                parent_main_window = current_parent
                break
            current_parent = current_parent.parent()

        if parent_main_window and hasattr(parent_main_window, 'appearance_manager') and parent_main_window.appearance_manager:
            if parent_main_window.appearance_manager.current_theme == "dark":
                text_color = "#888888"
        elif parent_main_window and hasattr(parent_main_window, 'current_theme'): 
             if parent_main_window.current_theme == "dark":
                text_color = "#888888"
        self.setStyleSheet(f"font-style: italic; color: {text_color};")

    def focusInEvent(self, event: QEvent): # QFocusEvent
        self._reset_state_and_field()
        logging.debug(f"HotkeyCaptureLineEdit for {self.action_id} received focus.")
        QTimer.singleShot(0, self.deselect)
        super().focusInEvent(event)

    def _reset_state_and_field(self):
        self._current_qt_modifiers = Qt.KeyboardModifier.NoModifier
        self._current_qt_key = Qt.Key.Key_unknown
        self._keypad_modifier_active_on_press = False
        self._reset_field_to_prompt()

    def keyPressEvent(self, event: QEvent.KeyPress): # QKeyEvent
        current_key = event.key()
        app_mods = QApplication.keyboardModifiers() 
        current_event_mods = event.modifiers() 
        
        logging.debug(f"HotkeyCaptureLineEdit.keyPressEvent: key={current_key}, text='{event.text()}', mods={current_event_mods}, app_mods={app_mods}, keypad_mod_active={bool(current_event_mods & Qt.KeyboardModifier.KeypadModifier)}")

        if current_key == Qt.Key_Escape and app_mods == Qt.KeyboardModifier.NoModifier :
            logging.debug(f"Hotkey capture canceled by Escape for {self.action_id}")
            self.capture_canceled.emit(self.action_id) 
            self._reset_state_and_field() 
            if self.parent() and isinstance(self.parent(), QDialog):
                self.parent().reject() 
            return

        if current_key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            self._current_qt_key = Qt.Key.Key_unknown 
            self._current_qt_modifiers = app_mods 
            self._keypad_modifier_active_on_press = False 
        else: 
            self._current_qt_key = current_key
            self._current_qt_modifiers = app_mods 
            self._keypad_modifier_active_on_press = bool(current_event_mods & Qt.KeyboardModifier.KeypadModifier)
        
        self._update_display_text()
        event.accept() 

    def keyReleaseEvent(self, event: QEvent.KeyRelease): # QKeyEvent
        if event.isAutoRepeat():
            event.accept()
            return

        released_key = event.key()
        logging.debug(f"HotkeyCaptureLineEdit.keyReleaseEvent: key={released_key}, _current_qt_key={self._current_qt_key}, _current_qt_mods={self._current_qt_modifiers}")
        
        is_finalizing_key_release = (self._current_qt_key != Qt.Key.Key_unknown and released_key == self._current_qt_key)
        
        is_single_modifier_release_and_empty = (
            self._current_qt_key == Qt.Key.Key_unknown and 
            released_key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta) and 
            QApplication.keyboardModifiers() == Qt.KeyboardModifier.NoModifier 
        )

        if is_finalizing_key_release or is_single_modifier_release_and_empty:
            final_hotkey_str = self._generate_keyboard_lib_string(
                self._current_qt_modifiers, 
                self._current_qt_key,       
                self._keypad_modifier_active_on_press 
            )
            
            if not final_hotkey_str or final_hotkey_str.strip() == "" or final_hotkey_str.strip() == "+": 
                logging.debug(f"Hotkey capture resulted in invalid string ('{final_hotkey_str}') for {self.action_id}. Canceling.")
                self.capture_canceled.emit(self.action_id)
                if self.parent() and isinstance(self.parent(), QDialog):
                     self.parent().reject()
            else:
                logging.info(f"Hotkey captured for {self.action_id}: {final_hotkey_str}")
                self.hotkey_captured.emit(self.action_id, final_hotkey_str)
                if self.parent() and isinstance(self.parent(), QDialog): 
                     self.parent().accept()
            
            self._reset_state_and_field() 
            event.accept()
            return

        if released_key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            self._current_qt_modifiers = QApplication.keyboardModifiers() 
            if self._current_qt_key == Qt.Key.Key_unknown and self._current_qt_modifiers == Qt.KeyboardModifier.NoModifier:
                 self._reset_state_and_field() 
            else: 
                 self._update_display_text() 
        
        event.accept()

    def _update_display_text(self):
        display_str = self._generate_keyboard_lib_string(
            self._current_qt_modifiers, 
            self._current_qt_key, 
            self._keypad_modifier_active_on_press, 
            for_display=True 
        )
        
        if not display_str or display_str.strip() == "" or display_str.strip() == "+":
            self._reset_field_to_prompt()
        else:
            self.setText(display_str)
            self.setStyleSheet("font-style: normal;") 

    def _generate_keyboard_lib_string(self, qt_app_modifiers: Qt.KeyboardModifier, 
                                      qt_key_enum: Qt.Key, 
                                      keypad_modifier_was_active_on_press: bool, 
                                      for_display=False) -> str:
        parts = []
        
        if qt_app_modifiers & Qt.KeyboardModifier.ControlModifier: parts.append("ctrl")
        if qt_app_modifiers & Qt.KeyboardModifier.AltModifier: parts.append("alt")
        if qt_app_modifiers & Qt.KeyboardModifier.ShiftModifier: parts.append("shift")
        if qt_app_modifiers & Qt.KeyboardModifier.MetaModifier: parts.append("win")
        
        key_str_for_lib = ""
        is_key_a_qt_modifier_type = qt_key_enum in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta)

        if qt_key_enum != Qt.Key.Key_unknown and not is_key_a_qt_modifier_type:
            if keypad_modifier_was_active_on_press: 
                if Qt.Key_0 <= qt_key_enum <= Qt.Key_9: key_str_for_lib = "num " + str(qt_key_enum - Qt.Key_0)
                elif qt_key_enum == Qt.Key_Period: key_str_for_lib = "num ." 
                elif qt_key_enum == Qt.Key_Asterisk: key_str_for_lib = "num *"
                elif qt_key_enum == Qt.Key_Plus: key_str_for_lib = "num +"
                elif qt_key_enum == Qt.Key_Minus: key_str_for_lib = "num -"
                elif qt_key_enum == Qt.Key_Slash: key_str_for_lib = "num /"
                else: 
                    seq = QKeySequence(qt_key_enum)
                    key_str_for_lib = seq.toString(QKeySequence.PortableText).lower() if not seq.isEmpty() else ""
            
            if not key_str_for_lib: 
                if Qt.Key_0 <= qt_key_enum <= Qt.Key_9: key_str_for_lib = str(qt_key_enum - Qt.Key_0)
                elif Qt.Key_A <= qt_key_enum <= Qt.Key_Z: key_str_for_lib = chr(qt_key_enum).lower()
                elif Qt.Key_F1 <= qt_key_enum <= Qt.Key_F24: key_str_for_lib = "f" + str(qt_key_enum - Qt.Key_F1 + 1)
                elif qt_key_enum == Qt.Key_Tab: key_str_for_lib = "tab"
                elif qt_key_enum == Qt.Key_Return or qt_key_enum == Qt.Key_Enter: key_str_for_lib = "enter"
                elif qt_key_enum == Qt.Key_Escape: key_str_for_lib = "esc"
                elif qt_key_enum == Qt.Key_Space: key_str_for_lib = "space"
                elif qt_key_enum == Qt.Key_Backspace: key_str_for_lib = "backspace"
                elif qt_key_enum == Qt.Key_Delete: key_str_for_lib = "delete"
                elif qt_key_enum == Qt.Key_Insert: key_str_for_lib = "insert"
                elif qt_key_enum == Qt.Key_Home: key_str_for_lib = "home"
                elif qt_key_enum == Qt.Key_End: key_str_for_lib = "end"
                elif qt_key_enum == Qt.Key_PageUp: key_str_for_lib = "page up"
                elif qt_key_enum == Qt.Key_PageDown: key_str_for_lib = "page down"
                elif qt_key_enum == Qt.Key_Up: key_str_for_lib = "up"
                elif qt_key_enum == Qt.Key_Down: key_str_for_lib = "down"
                elif qt_key_enum == Qt.Key_Left: key_str_for_lib = "left"
                elif qt_key_enum == Qt.Key_Right: key_str_for_lib = "right"
                elif qt_key_enum == Qt.Key_Print: key_str_for_lib = "print screen"
                elif qt_key_enum == Qt.Key_ScrollLock: key_str_for_lib = "scroll lock"
                elif qt_key_enum == Qt.Key_Pause: key_str_for_lib = "pause"
                elif qt_key_enum == Qt.Key_CapsLock: key_str_for_lib = "caps lock"
                elif qt_key_enum == Qt.Key_NumLock: key_str_for_lib = "num lock"
                else:
                    seq = QKeySequence(qt_key_enum)
                    temp_key_str = seq.toString(QKeySequence.PortableText).lower() if not seq.isEmpty() else ""
                    
                    simple_map = {
                        Qt.Key_Comma: ",", Qt.Key_Period: ".", Qt.Key_Slash: "/",
                        Qt.Key_Backslash: "\\", Qt.Key_Semicolon: ";", Qt.Key_Apostrophe: "'",
                        Qt.Key_BracketLeft: "[", Qt.Key_BracketRight: "]",
                        Qt.Key_Minus: "-", Qt.Key_Equal: "=", Qt.Key_Plus: "+",
                    }
                    if qt_key_enum in simple_map:
                        key_str_for_lib = simple_map[qt_key_enum]
                    else: 
                        key_str_for_lib = temp_key_str
                        if key_str_for_lib == "del": key_str_for_lib = "delete" 
                        if key_str_for_lib == "escape": key_str_for_lib = "esc"
            
            if key_str_for_lib:
                parts.append(key_str_for_lib)

        if not parts: return ""
        
        if for_display and (qt_key_enum == Qt.Key.Key_unknown or is_key_a_qt_modifier_type) and len(parts) > 0:
            return "+".join(parts) + "+" 
        
        return "+".join(parts)


def show_about_program_info(parent):
    dialog = AboutProgramDialog(parent)
    dialog.exec()

def show_hero_rating(parent, app_version): 
    dialog = HeroRatingDialog(parent, app_version)
    dialog.exec()

def show_hotkey_display_dialog(parent):
    dialog = HotkeyDisplayDialog(parent)
    dialog.exec()

def show_hotkey_settings_dialog(current_hotkeys, hotkey_actions_config, parent_window):
    dialog = HotkeySettingsDialog(current_hotkeys, hotkey_actions_config, parent_window)
    return dialog.exec() == QDialog.Accepted 