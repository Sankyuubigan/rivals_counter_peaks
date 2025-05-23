# File: core/dialogs.py
from PySide6.QtWidgets import (QDialog, QTextBrowser, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout,
                               QLabel, QScrollArea, QWidget, QGridLayout, QLineEdit, QApplication)
from PySide6.QtCore import Qt, Slot, QTimer, QEvent, QKeyCombination, Signal, QObject
from PySide6.QtGui import QKeySequence, QCloseEvent
from database import heroes_bd
from core.lang.translations import get_text
import pyperclip
import logging
import os
import sys
import markdown
import re 

import json

try:
    from pynput import keyboard 
    PYNPUT_AVAILABLE_FOR_CAPTURE = True
except ImportError:
    PYNPUT_AVAILABLE_FOR_CAPTURE = False
    keyboard = None 

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
        if current_lang_code.startswith('en'): md_filename_key = "information_en.md"
        md_filepath = resource_path_dialogs(md_filename_key)
        current_theme = "light"
        if hasattr(self.parent_window, 'appearance_manager'): current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'): current_theme = self.parent_window.current_theme
        body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#ffffff", "#000000", "#333", "#007bff", "#f0f0f0")
        if current_theme == "dark": body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#2e2e2e", "#e0e0e0", "#cccccc", "#58a6ff", "#3c3c3c")
        if os.path.exists(md_filepath):
            try:
                with open(md_filepath, "r", encoding="utf-8") as f: md_content = f.read()
                css = f"<style>body{{font-family:sans-serif;font-size:10pt;line-height:1.6;background-color:{body_bg_color};color:{body_text_color}}}h1{{font-size:16pt;margin-bottom:10px;color:{h_color};border-bottom:1px solid #ccc;padding-bottom:5px}}h2{{font-size:14pt;margin-top:20px;margin-bottom:8px;color:{h_color}}}h3{{font-size:12pt;margin-top:15px;margin-bottom:5px;color:{h_color}}}p{{margin-bottom:10px}}ul,ol{{margin-left:20px;margin-bottom:10px}}li{{margin-bottom:5px}}code{{background-color:{code_bg_color};padding:2px 4px;border-radius:3px;font-family:monospace}}a{{color:{link_color};text-decoration:none}}a:hover{{text-decoration:underline}}hr{{border:0;height:1px;background:#ccc;margin:20px 0}}</style>"
                html_content = markdown.markdown(md_content, extensions=['extra', 'sane_lists'])
                self.text_browser.setHtml(css + html_content)
            except Exception as e: logging.error(f"Error loading/parsing {md_filepath}: {e}")
        else: logging.warning(f"Markdown file not found: {md_filepath}")

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
                    if counter_hero in counter_counts: counter_counts[counter_hero] +=1
        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1], reverse=True)
        rating_lines = [f"{hero} ({count})" for hero, count in sorted_heroes]
        text_browser.setText("\n".join(rating_lines))
        layout.addWidget(text_browser)
        close_button = QPushButton("OK"); close_button.clicked.connect(self.accept); layout.addWidget(close_button)
    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry(); center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry:
                center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text('logs_window_title')); self.setGeometry(150, 150, 900, 600); self.setModal(False)
        self.layout = QVBoxLayout(self); self.log_browser = QTextBrowser(self); self.log_browser.setReadOnly(True)
        self.log_browser.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap); font = self.log_browser.font()
        font.setFamily("Courier New"); font.setPointSize(10); self.log_browser.setFont(font)
        self.copy_button = QPushButton(get_text('copy_all_logs_button')); self.copy_button.clicked.connect(self.copy_logs)
        self.clear_button = QPushButton(get_text('clear_log_window_button')); self.clear_button.clicked.connect(self.clear_log_display)
        self.button_layout = QVBoxLayout(); self.button_layout.addWidget(self.copy_button); self.button_layout.addWidget(self.clear_button)
        self.button_layout.addStretch(1); self.main_hbox_layout = QHBoxLayout(); self.main_hbox_layout.addWidget(self.log_browser, stretch=1)
        self.main_hbox_layout.addLayout(self.button_layout); self.layout.addLayout(self.main_hbox_layout)
    @Slot(str)
    def append_log(self, message): self.log_browser.append(message)
    @Slot()
    def copy_logs(self):
        all_logs = self.log_browser.toPlainText()
        if not all_logs: QMessageBox.information(self, get_text('info'), get_text('log_copy_no_logs')); return
        try: pyperclip.copy(all_logs)
        except Exception as e: logging.error(f"Error copying logs: {e}"); QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")
    @Slot()
    def clear_log_display(self): self.log_browser.clear()
    def closeEvent(self, event: QCloseEvent): self.hide(); event.ignore()

class HotkeyDisplayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.parent_window = parent; self.setWindowTitle(get_text('hotkeys_window_title')); self.setMinimumWidth(550); self.setModal(True)
        self.layout = QVBoxLayout(self); self.text_browser = QTextBrowser(self); self.text_browser.setReadOnly(True); self.text_browser.setOpenExternalLinks(False)
        self.update_html_content(); self.close_button = QPushButton("OK"); self.close_button.clicked.connect(self.accept)
        self.layout.addWidget(self.text_browser); self.layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight); QTimer.singleShot(0, self.center_on_parent)
    
    def _normalize_for_display_info(self, hotkey_str: str) -> str:
        s = hotkey_str.replace("num_", "Num ")
        s = s.replace("decimal", "Decimal") 
        s = s.replace("Num Decimal", "Num .") 
        s = s.replace("divide", "/")
        s = s.replace("multiply", "*")
        s = s.replace("subtract", "-")
        s = s.replace("add", "+")
        return s

    def update_html_content(self):
        current_theme = "light"
        if hasattr(self.parent_window, 'appearance_manager'): current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'): current_theme = self.parent_window.current_theme
        body_bg_color, body_text_color, code_bg_color, h_color = ("white", "black", "#f0f0f0", "#333")
        if current_theme == "dark": body_bg_color, body_text_color, code_bg_color, h_color = ("#2e2e2e", "#e0e0e0", "#3c3c3c", "#cccccc")
        
        hotkeys_text_html = f"<html><head><style>body{{font-family:sans-serif;font-size:10pt;background-color:{body_bg_color};color:{body_text_color}}}h3{{margin-bottom:5px;margin-top:10px;color:{h_color}}}ul{{margin-top:0px;padding-left:20px}}li{{margin-bottom:3px}}code{{background-color:{code_bg_color};padding:1px 4px;border-radius:3px}}</style></head><body><h3>{get_text('hotkeys_section_main')}</h3><ul>"
        
        current_hotkeys = {}
        if hasattr(self.parent_window, 'hotkey_manager'):
            current_hotkeys = self.parent_window.hotkey_manager.get_current_hotkeys()

        def get_display_hotkey(action_id):
            hk_str = current_hotkeys.get(action_id, get_text('hotkey_not_set'))
            return self._normalize_for_display_info(hk_str)

        hotkey_list_items_config = [
            ("move_cursor_up", 'hotkey_desc_navigation_up'),
            ("move_cursor_down", 'hotkey_desc_navigation_down'),
            ("move_cursor_left", 'hotkey_desc_navigation_left'),
            ("move_cursor_right", 'hotkey_desc_navigation_right'),
            ("toggle_selection", 'hotkey_desc_select'),
            ("toggle_mode", 'hotkey_desc_toggle_mode'),
            ("recognize_heroes", 'hotkey_desc_recognize'),
            ("clear_all", 'hotkey_desc_clear'),
            ("copy_team", 'hotkey_desc_copy_team'),
            ("toggle_tray_mode", 'hotkey_desc_toggle_tray'),
            ("toggle_mouse_ignore_independent", 'hotkey_desc_toggle_mouse_ignore'),
            ("debug_capture", 'hotkey_desc_debug_screenshot'),
        ]
        for action_id, desc_key_str in hotkey_list_items_config:
            hotkeys_text_html += f"<li><code>{get_display_hotkey(action_id)}</code>: {get_text(desc_key_str)}</li>"

        hotkeys_text_html += f"</ul><h3>{get_text('hotkeys_section_interaction_title')}</h3><ul><li><code>{get_text('hotkey_desc_lmb')}</code>:{get_text('hotkey_desc_lmb_select')}</li><li><code>{get_text('hotkey_desc_rmb')}</code>:{get_text('hotkey_desc_rmb_priority')}</li><li><code>{get_text('hotkey_desc_drag')}</code>:{get_text('hotkey_desc_drag_window')}</li><li><code>{get_text('hotkey_desc_slider')}</code>:{get_text('hotkey_desc_slider_transparency')}</li></ul></body></html>"
        self.text_browser.setHtml(hotkeys_text_html)

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry(); center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry:
                center_point.setX(max(screen_geometry.left(),min(center_point.x(),screen_geometry.right()-self.width())))
                center_point.setY(max(screen_geometry.top(),min(center_point.y(),screen_geometry.bottom()-self.height())))
            self.move(center_point)

class HotkeySettingsDialog(QDialog):
    hotkey_changed_signal = Signal(str, str)
    def __init__(self, current_hotkeys, hotkey_actions_config, parent=None):
        super().__init__(parent); self.current_hotkeys_copy = dict(current_hotkeys); self.hotkey_actions_config = hotkey_actions_config; self.parent_window = parent
        self.setWindowTitle(get_text('hotkey_settings_window_title')); self.setMinimumWidth(600); self.setModal(True) 
        # installEventFilter(self) был удален, так как он перехватывал Tab глобально для диалога,
        # теперь HotkeyCaptureLineEdit сам обрабатывает Tab, если он в фокусе.
        self.main_layout = QVBoxLayout(self); self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget(); self.grid_layout = QGridLayout(self.scroll_widget); self.grid_layout.setHorizontalSpacing(15); self.grid_layout.setVerticalSpacing(10)
        self.action_widgets = {}; self._populate_hotkey_list(); self.scroll_area.setWidget(self.scroll_widget); self.main_layout.addWidget(self.scroll_area)
        self.buttons_layout = QHBoxLayout(); self.reset_defaults_button = QPushButton(get_text('hotkey_settings_reset_defaults')); self.reset_defaults_button.clicked.connect(self.reset_to_defaults)
        self.save_button = QPushButton(get_text('hotkey_settings_save')); self.save_button.clicked.connect(self.save_and_close)
        self.cancel_button = QPushButton(get_text('hotkey_settings_cancel')); self.cancel_button.clicked.connect(self.reject)
        self.buttons_layout.addWidget(self.reset_defaults_button); self.buttons_layout.addStretch(1); self.buttons_layout.addWidget(self.save_button); self.buttons_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.buttons_layout); QTimer.singleShot(0, self.center_on_parent)

    def _normalize_for_display(self, hotkey_str: str) -> str:
        s = hotkey_str.replace("num_", "Num ")
        s = s.replace("decimal", "Decimal") 
        s = s.replace("Num Decimal", "Num .") 
        s = s.replace("divide", "/")
        s = s.replace("multiply", "*")
        s = s.replace("subtract", "-")
        s = s.replace("add", "+")
        return s

    def _populate_hotkey_list(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()
        self.action_widgets.clear(); row = 0
        for action_id, config in self.hotkey_actions_config.items():
            desc_key = config['desc_key']; description = get_text(desc_key)
            current_hotkey_str_internal = self.current_hotkeys_copy.get(action_id, get_text('hotkey_not_set'))
            display_hotkey_str = self._normalize_for_display(current_hotkey_str_internal)

            desc_label = QLabel(description); hotkey_label = QLabel(f"<code>{display_hotkey_str}</code>"); hotkey_label.setTextFormat(Qt.TextFormat.RichText)
            change_button = QPushButton(get_text('hotkey_settings_change_btn')); change_button.setProperty("action_id", action_id); change_button.clicked.connect(self.on_change_hotkey_button_clicked)
            self.grid_layout.addWidget(desc_label, row, 0, Qt.AlignmentFlag.AlignLeft); self.grid_layout.addWidget(hotkey_label, row, 1, Qt.AlignmentFlag.AlignCenter); self.grid_layout.addWidget(change_button, row, 2, Qt.AlignmentFlag.AlignRight)
            self.action_widgets[action_id] = {'desc': desc_label, 'hotkey': hotkey_label, 'button': change_button}; row += 1
        self.grid_layout.setColumnStretch(0, 2); self.grid_layout.setColumnStretch(1, 1); self.grid_layout.setColumnStretch(2, 0)

    def on_change_hotkey_button_clicked(self):
        sender_button = self.sender(); action_id = sender_button.property("action_id") if sender_button else None
        if not action_id or action_id not in self.action_widgets: return
        current_theme = "light"; text_color_during_capture = "orange"
        if hasattr(self.parent_window, 'appearance_manager'): current_theme = self.parent_window.appearance_manager.current_theme
        if current_theme == "dark": text_color_during_capture = "#FFA500"
        self.action_widgets[action_id]['hotkey'].setText(f"<i>{get_text('hotkey_settings_press_keys')}</i>"); self.action_widgets[action_id]['hotkey'].setStyleSheet(f"font-style:italic;color:{text_color_during_capture};")
        
        capture_dialog = QDialog(self); capture_dialog.setWindowTitle(get_text('hotkey_settings_capture_title')); capture_dialog.setModal(True)
        dialog_layout = QVBoxLayout(capture_dialog); action_desc = get_text(self.hotkey_actions_config[action_id]['desc_key'])
        info_label = QLabel(get_text('hotkey_settings_press_new_hotkey_for').format(action=action_desc)); dialog_layout.addWidget(info_label)
        hotkey_input_field = HotkeyCaptureLineEdit(action_id, capture_dialog); hotkey_input_field.setObjectName("HotkeyCaptureLineEdit"); dialog_layout.addWidget(hotkey_input_field)
        cancel_btn = QPushButton(get_text('hotkey_settings_cancel_capture')); cancel_btn.clicked.connect(capture_dialog.reject); dialog_layout.addWidget(cancel_btn)
        hotkey_input_field.setFocus()
        
        def on_captured(act_id, key_str_internal): 
            if act_id == action_id: 
                self.update_hotkey_for_action(act_id, key_str_internal)
                capture_dialog.accept()
        
        def on_canceled_or_rejected():
            if hotkey_input_field and hotkey_input_field.action_id == action_id: 
                self.cancel_hotkey_capture(action_id)
        
        hotkey_input_field.hotkey_captured.connect(on_captured); capture_dialog.rejected.connect(on_canceled_or_rejected); capture_dialog.exec()
        
        try:
            if hotkey_input_field: hotkey_input_field.hotkey_captured.disconnect(on_captured)
        except RuntimeError: pass 
        try: capture_dialog.rejected.disconnect(on_canceled_or_rejected)
        except RuntimeError: pass 

    @Slot(str, str)
    def update_hotkey_for_action(self, action_id: str, new_hotkey_str_internal: str): 
        if action_id in self.action_widgets:
            logging.info(f"Updating hotkey (dialog) for {action_id} to internal '{new_hotkey_str_internal}'")
            self.current_hotkeys_copy[action_id] = new_hotkey_str_internal 
            display_str = self._normalize_for_display(new_hotkey_str_internal)
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>"); self.action_widgets[action_id]['hotkey'].setStyleSheet("")

    @Slot(str)
    def cancel_hotkey_capture(self, action_id: str):
        if action_id in self.action_widgets:
            original_hotkey_internal = self.current_hotkeys_copy.get(action_id, get_text('hotkey_not_set'))
            display_str = self._normalize_for_display(original_hotkey_internal)
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>"); self.action_widgets[action_id]['hotkey'].setStyleSheet("")
    
    def reset_to_defaults(self):
        if self.parent_window and hasattr(self.parent_window, 'hotkey_manager'):
            default_hotkeys_internal = self.parent_window.hotkey_manager.get_default_hotkeys() 
            self.current_hotkeys_copy = dict(default_hotkeys_internal)
            self._populate_hotkey_list()
            QMessageBox.information(self, get_text('hotkey_settings_defaults_reset_title'), get_text('hotkey_settings_defaults_reset_msg'))
    
    def save_and_close(self):
        if self.parent_window and hasattr(self.parent_window, 'hotkey_manager'):
            hotkey_map = {}
            duplicates = []
            for action_id, hotkey_str_internal in self.current_hotkeys_copy.items():
                if hotkey_str_internal == get_text('hotkey_none') or hotkey_str_internal == get_text('hotkey_not_set') or not hotkey_str_internal: continue
                
                if hotkey_str_internal in hotkey_map:
                    action_desc1 = get_text(self.hotkey_actions_config.get(action_id, {}).get('desc_key', action_id))
                    action_desc2 = get_text(self.hotkey_actions_config.get(hotkey_map[hotkey_str_internal], {}).get('desc_key', hotkey_map[hotkey_str_internal]))
                    display_duplicate_str = self._normalize_for_display(hotkey_str_internal)
                    duplicates.append(f"'{display_duplicate_str}' for '{action_desc1}' and '{action_desc2}'")
                else: hotkey_map[hotkey_str_internal] = action_id
            
            if duplicates:
                QMessageBox.warning(self, get_text('hotkey_settings_duplicate_title'), get_text('hotkey_settings_duplicate_message') + "\n- " + "\n- ".join(duplicates))
                return
            
            logging.debug(f"HotkeySettingsDialog: About to save hotkeys: {self.current_hotkeys_copy}")
            self.parent_window.hotkey_manager.save_hotkeys(self.current_hotkeys_copy) 
            self.accept()

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry(); center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry: center_point.setX(max(screen_geometry.left(),min(center_point.x(),screen_geometry.right()-self.width()))); center_point.setY(max(screen_geometry.top(),min(center_point.y(),screen_geometry.bottom()-self.height())))
            self.move(center_point)
    
    # eventFilter удален отсюда

class HotkeyCaptureLineEdit(QLineEdit):
    hotkey_captured = Signal(str, str) 
    capture_canceled = Signal(str)

    def __init__(self, action_id, parent_dialog):
        super().__init__(parent_dialog)
        self.action_id = action_id
        self.setReadOnly(True)
        self.setObjectName("HotkeyCaptureLineEdit")
        self._pressed_modifier_parts = [] # Список строк для модификаторов (e.g., ["ctrl", "tab"])
        self._main_key_capture_info = {}   # Словарь для основной клавиши: {'qt_key':..., 'is_keypad':..., 'event_text':..., 'pynput_str':..., 'display_str':...}
        self._reset_internal_capture_state()

    def _reset_field_to_prompt(self):
        self.setText(get_text('hotkey_settings_press_keys'))
        text_color = "gray"
        # ... (код определения цвета для темы)
        parent_main_window = self.window() # QWidget.window() возвращает окно верхнего уровня
        if parent_main_window and hasattr(parent_main_window, 'appearance_manager') and parent_main_window.appearance_manager.current_theme == "dark":
            text_color = "#888888"
        elif parent_main_window and hasattr(parent_main_window, 'current_theme') and parent_main_window.current_theme == "dark":
             text_color = "#888888"
        self.setStyleSheet(f"font-style: italic; color: {text_color};")

    def focusInEvent(self, event: QEvent):
        self._reset_internal_capture_state()
        QTimer.singleShot(0, self.deselect)
        super().focusInEvent(event)

    def _reset_internal_capture_state(self):
        self._pressed_modifier_parts = []
        self._main_key_capture_info = {}
        self._reset_field_to_prompt()

    def keyPressEvent(self, event: QEvent.KeyPress):
        event.accept()
        pressed_key_qt = event.key()
        qt_app_mods = QApplication.keyboardModifiers() # Используем это для стандартных модификаторов

        # Отмена по Escape
        if pressed_key_qt == Qt.Key_Escape and not self._pressed_modifier_parts and not self._main_key_capture_info:
            logging.info(f"Hotkey capture for '{self.action_id}' canceled by Escape.")
            self.capture_canceled.emit(self.action_id)
            self._reset_internal_capture_state()
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().reject()
            return

        # Обработка стандартных модификаторов (они уже учтены в qt_app_mods)
        is_standard_modifier_key = pressed_key_qt in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta)

        if pressed_key_qt == Qt.Key_Tab:
            if "tab" not in self._pressed_modifier_parts:
                self._pressed_modifier_parts.append("tab")
        elif not is_standard_modifier_key and not self._main_key_capture_info: # Основная клавиша
            self._main_key_capture_info = {
                'qt_key': pressed_key_qt,
                'is_keypad': bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier),
                'event_text': event.text(),
                'pynput_str': self._qt_key_to_pynput_str(pressed_key_qt, 
                                                        bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier), 
                                                        event.text()),
                'display_str': self._qt_key_to_display_str(pressed_key_qt, 
                                                           bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier))
            }
        
        # Обновляем список _pressed_modifier_parts стандартными модификаторами, если они еще не там
        # (это больше для отображения, pynput-строка будет использовать актуальные qt_app_mods при формировании)
        current_qt_mod_parts = []
        if qt_app_mods & Qt.KeyboardModifier.ControlModifier: current_qt_mod_parts.append("ctrl")
        if qt_app_mods & Qt.KeyboardModifier.AltModifier: current_qt_mod_parts.append("alt")
        if qt_app_mods & Qt.KeyboardModifier.ShiftModifier: current_qt_mod_parts.append("shift")
        if qt_app_mods & Qt.KeyboardModifier.MetaModifier: current_qt_mod_parts.append("win")
        
        # Добавляем Qt модификаторы, если они еще не в списке (на случай если Tab был нажат первым)
        for mod_part in current_qt_mod_parts:
            if mod_part not in self._pressed_modifier_parts:
                 # Пытаемся сохранить порядок: Ctrl, Alt, Shift, Win, Tab
                if mod_part == "ctrl": self._pressed_modifier_parts.insert(0, mod_part)
                elif mod_part == "alt": 
                    idx = self._pressed_modifier_parts.index("ctrl") + 1 if "ctrl" in self._pressed_modifier_parts else 0
                    self._pressed_modifier_parts.insert(idx, mod_part)
                elif mod_part == "shift":
                    idx = 0
                    if "alt" in self._pressed_modifier_parts: idx = self._pressed_modifier_parts.index("alt") + 1
                    elif "ctrl" in self._pressed_modifier_parts: idx = self._pressed_modifier_parts.index("ctrl") + 1
                    self._pressed_modifier_parts.insert(idx, mod_part)
                elif mod_part == "win":
                    idx = 0
                    if "shift" in self._pressed_modifier_parts: idx = self._pressed_modifier_parts.index("shift") + 1
                    elif "alt" in self._pressed_modifier_parts: idx = self._pressed_modifier_parts.index("alt") + 1
                    elif "ctrl" in self._pressed_modifier_parts: idx = self._pressed_modifier_parts.index("ctrl") + 1
                    self._pressed_modifier_parts.insert(idx, mod_part)


        self._update_display_text_while_capturing()

    def keyReleaseEvent(self, event: QEvent.KeyRelease):
        event.accept()
        if event.isAutoRepeat(): return

        released_key_qt = event.key()
        
        # Если отпущена основная клавиша И она была зафиксирована
        if self._main_key_capture_info and released_key_qt == self._main_key_capture_info.get('qt_key'):
            final_hotkey_str = self._generate_pynput_compatible_string()
            self._emit_or_cancel(final_hotkey_str)
            return

        # Если отпущен Tab
        if released_key_qt == Qt.Key_Tab:
            if "tab" in self._pressed_modifier_parts:
                self._pressed_modifier_parts.remove("tab")
            # Если Tab был единственной "клавишей" (нет основной, нет других модификаторов Qt)
            if not self._main_key_capture_info and not (QApplication.keyboardModifiers() & ~Qt.KeyboardModifier.KeypadModifier): # ~KeypadModifier чтобы не считать его за "другой"
                self._main_key_capture_info = { # Считаем Tab основной
                    'qt_key': Qt.Key_Tab, 'is_keypad': False, 'event_text': '',
                    'pynput_str': "tab", 'display_str': "Tab"
                }
                final_hotkey_str = self._generate_pynput_compatible_string()
                self._emit_or_cancel(final_hotkey_str)
                return
        
        # Если отпущен стандартный модификатор
        is_standard_modifier_key = released_key_qt in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta)
        if is_standard_modifier_key:
            mod_map = {Qt.Key_Control: "ctrl", Qt.Key_Shift: "shift", Qt.Key_Alt: "alt", Qt.Key_Meta: "win"}
            mod_str = mod_map.get(released_key_qt)
            if mod_str in self._pressed_modifier_parts:
                self._pressed_modifier_parts.remove(mod_str)
            
            # Если это был последний модификатор и нет основной клавиши
            if not self._pressed_modifier_parts and not self._main_key_capture_info and \
               QApplication.keyboardModifiers() == Qt.KeyboardModifier.NoModifier: # Проверяем актуальные модификаторы Qt
                self._reset_internal_capture_state()

        self._update_display_text_while_capturing()

    def _emit_or_cancel(self, hotkey_str):
        if hotkey_str and hotkey_str.strip() not in ["", "+"] and not hotkey_str.strip().endswith("+"):
            logging.info(f"Hotkey captured for {self.action_id}: {hotkey_str} (internal pynput format)")
            self.hotkey_captured.emit(self.action_id, hotkey_str)
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().accept()
        else:
            logging.warning(f"Hotkey capture for '{self.action_id}' resulted in invalid string: '{hotkey_str}'. Canceling.")
            self.capture_canceled.emit(self.action_id)
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().reject()
        self._reset_internal_capture_state()

    def _update_display_text_while_capturing(self):
        display_parts = [part.capitalize() for part in self._pressed_modifier_parts]
        
        is_complete_combo = False
        if self._main_key_capture_info:
            display_parts.append(self._main_key_capture_info.get('display_str', ''))
            is_complete_combo = True
        elif "tab" in self._pressed_modifier_parts and not any(m in self._pressed_modifier_parts for m in ["ctrl", "alt", "shift", "win"]):
            # Если только Tab нажат, он считается "основной" клавишей для отображения
            # display_parts уже содержит "Tab"
            is_complete_combo = True


        current_display_text = "+".join(filter(None, display_parts))

        if not current_display_text:
            self._reset_field_to_prompt()
            return

        if not is_complete_combo and current_display_text:
            current_display_text += " + ..."
            self.setStyleSheet(f"font-style: italic; color: {'#888888' if self.window().appearance_manager.current_theme == 'dark' else 'gray'};")
        else:
            self.setStyleSheet("font-style: normal;")
        
        self.setText(current_display_text)


    def _qt_key_to_pynput_str(self, qt_key, is_keypad, event_text) -> str:
        if is_keypad:
            if Qt.Key_0 <= qt_key <= Qt.Key_9: return f"num_{qt_key - Qt.Key_0}"
            if qt_key == Qt.Key_Period: return "num_decimal"
            if qt_key == Qt.Key_Asterisk: return "num_multiply"
            if qt_key == Qt.Key_Plus: return "num_add"
            if qt_key == Qt.Key_Minus: return "num_subtract"
            if qt_key == Qt.Key_Slash: return "num_divide"
        
        qt_to_pynput_map = {
            Qt.Key_Tab: "tab", Qt.Key_Return: "enter", Qt.Key_Enter: "enter", Qt.Key_Escape: "esc",
            Qt.Key_Space: "space", Qt.Key_Backspace: "backspace", Qt.Key_Delete: "delete",
            Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
            Qt.Key_Home: "home", Qt.Key_End: "end", Qt.Key_PageUp: "page_up", Qt.Key_PageDown: "page_down",
            Qt.Key_Insert: "insert",
            Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3", Qt.Key_F4: "f4", Qt.Key_F5: "f5",
            Qt.Key_F6: "f6", Qt.Key_F7: "f7", Qt.Key_F8: "f8", Qt.Key_F9: "f9", Qt.Key_F10: "f10",
            Qt.Key_F11: "f11", Qt.Key_F12: "f12",
            # Символы, которые могут быть неоднозначны с numpad при простом QKeySequence.PortableText
            Qt.Key_Slash: "/", Qt.Key_Asterisk: "*", Qt.Key_Minus: "-", Qt.Key_Plus: "+", Qt.Key_Period: "."
        }
        if qt_key in qt_to_pynput_map: return qt_to_pynput_map[qt_key]

        if Qt.Key_0 <= qt_key <= Qt.Key_9: return str(qt_key - Qt.Key_0)
        if Qt.Key_A <= qt_key <= Qt.Key_Z: return chr(qt_key).lower()
        
        # Для остальных символов используем event_text, если он есть и это один символ
        if event_text and len(event_text) == 1 and not event_text.isspace() and not event_text.isalnum():
            return event_text.lower()
            
        # Крайний случай, пытаемся получить из QKeySequence
        portable_text = QKeySequence(qt_key).toString(QKeySequence.PortableText).lower()
        if portable_text and not any(mod in portable_text for mod in ["ctrl", "alt", "shift", "meta", "tab"]):
            return portable_text
        return "" # Не удалось определить

    def _qt_key_to_display_str(self, qt_key, is_keypad) -> str:
        if is_keypad:
            if Qt.Key_0 <= qt_key <= Qt.Key_9: return f"Num {qt_key - Qt.Key_0}"
            if qt_key == Qt.Key_Period: return "Num ."
            if qt_key == Qt.Key_Asterisk: return "Num *"
            if qt_key == Qt.Key_Plus: return "Num +"
            if qt_key == Qt.Key_Minus: return "Num -"
            if qt_key == Qt.Key_Slash: return "Num /"
        
        # Для отображения используем NativeText, он обычно более читаем
        native_text = QKeySequence(qt_key).toString(QKeySequence.NativeText)
        if native_text: return native_text
        
        # Fallback для букв и цифр, если NativeText пуст (маловероятно)
        if Qt.Key_A <= qt_key <= Qt.Key_Z: return chr(qt_key)
        if Qt.Key_0 <= qt_key <= Qt.Key_9: return str(qt_key - Qt.Key_0)
        return "?"


    def _generate_pynput_compatible_string(self) -> str:
        # Собираем строку на основе _pressed_modifier_parts и _main_key_capture_info
        # Используем актуальные Qt-модификаторы для Ctrl, Alt, Shift, Win
        active_qt_mods = QApplication.keyboardModifiers()
        
        final_parts = []
        if active_qt_mods & Qt.KeyboardModifier.ControlModifier: final_parts.append("ctrl")
        if active_qt_mods & Qt.KeyboardModifier.AltModifier: final_parts.append("alt")
        if active_qt_mods & Qt.KeyboardModifier.ShiftModifier: final_parts.append("shift")
        if active_qt_mods & Qt.KeyboardModifier.MetaModifier: final_parts.append("win")

        # Добавляем Tab, если он был нажат как модификатор (т.е. есть основная клавиша)
        # или если Tab - это и есть основная клавиша, но нет других Qt-модификаторов
        if "tab" in self._pressed_modifier_parts:
            # Если Tab - единственная часть в _pressed_modifier_parts и нет основной клавиши И нет Qt-модов,
            # то Tab сам по себе и не должен добавляться здесь как модификатор.
            # Он будет добавлен как основная часть ниже, если _main_key_capture_info['pynput_str'] == "tab".
            # Если Tab с другими Qt-модами, то он модификатор.
            # Если Tab с основной клавишей, то он модификатор.
            if self._main_key_capture_info or \
               any(m in final_parts for m in ["ctrl", "alt", "shift", "win"]):
                 if "tab" not in final_parts : final_parts.append("tab")


        if self._main_key_capture_info and self._main_key_capture_info.get('pynput_str'):
            main_key_str = self._main_key_capture_info['pynput_str']
            # Если main_key_str это "tab" и "tab" уже есть в final_parts как модификатор, не добавляем его снова
            if not (main_key_str == "tab" and "tab" in final_parts and len(final_parts) > 1):
                 final_parts.append(main_key_str)
        
        return "+".join(final_parts)

def show_about_program_info(parent): dialog = AboutProgramDialog(parent); dialog.exec()
def show_hero_rating(parent, app_version): dialog = HeroRatingDialog(parent, app_version); dialog.exec()
def show_hotkey_display_dialog(parent): dialog = HotkeyDisplayDialog(parent); dialog.exec()
def show_hotkey_settings_dialog(current_hotkeys, hotkey_actions_config, parent_window):
    dialog = HotkeySettingsDialog(current_hotkeys, hotkey_actions_config, parent_window)
    return dialog.exec() == QDialog.Accepted
