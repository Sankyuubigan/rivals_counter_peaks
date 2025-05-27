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
from core.ui_components.hotkey_capture_line_edit import HotkeyCaptureLineEdit 

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
    
    lang_path_base = "" 
    if base_path.endswith("core"):
        lang_path_base = os.path.join(base_path, "lang")
    else:
        core_sub_dir = os.path.join(base_path, "core")
        if os.path.isdir(core_sub_dir):
            lang_path_base = os.path.join(core_sub_dir, "lang")
        else: 
            logging.warning(f"Не удалось определить путь к 'core/lang' из {base_path}. Попытка использовать 'lang' напрямую.")
            lang_path_base = os.path.join(base_path, "lang") 

    final_path = os.path.join(lang_path_base, relative_path)
    if not os.path.exists(final_path): 
        logging.warning(f"Файл ресурса не найден по вычисленному пути: {final_path}")
    return final_path


class BaseInfoDialog(QDialog): # Создадим базовый класс для общих частей
    def __init__(self, parent, window_title_key, md_filename_base):
        super().__init__(parent)
        self.parent_window = parent
        self.md_filename_base = md_filename_base # e.g., "information" or "author"
        self.setObjectName(f"{md_filename_base.capitalize()}Dialog")
        self.setWindowTitle(get_text(window_title_key))
        self.setGeometry(0, 0, 600, 450) # Немного уменьшим размер по умолчанию
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.update_content_theme() # Вызовем сразу

        self.close_button = QPushButton("OK")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.text_browser)
        layout.addWidget(self.close_button)

    def update_content_theme(self):
        current_lang_code = 'ru_RU'
        if hasattr(self.parent_window, 'logic') and hasattr(self.parent_window.logic, 'DEFAULT_LANGUAGE'):
             current_lang_code = self.parent_window.logic.DEFAULT_LANGUAGE
        
        # Формируем имя файла на основе md_filename_base и языка
        md_filename = f"{self.md_filename_base}_{current_lang_code.split('_')[0]}.md" # e.g., author_ru.md

        md_filepath = resource_path_dialogs(md_filename)
        
        current_theme = "light"
        if hasattr(self.parent_window, 'appearance_manager'): current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'): current_theme = self.parent_window.current_theme
        
        body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#ffffff", "#000000", "#333", "#007bff", "#f0f0f0")
        if current_theme == "dark": body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#2e2e2e", "#e0e0e0", "#cccccc", "#58a6ff", "#3c3c3c")
        
        if os.path.exists(md_filepath):
            md_content = ""
            try: 
                with open(md_filepath, "r", encoding="utf-8") as f: md_content = f.read()
            except IOError as e:
                 logging.error(f"IOError при чтении {md_filepath}: {e}")
                 self.text_browser.setHtml(f"<p>Error loading content: {e}</p>")
                 return

            if md_content:
                css = f"<style>body{{font-family:sans-serif;font-size:10pt;line-height:1.6;background-color:{body_bg_color};color:{body_text_color}}}h1{{font-size:16pt;margin-bottom:10px;color:{h_color};border-bottom:1px solid #ccc;padding-bottom:5px}}h2{{font-size:14pt;margin-top:20px;margin-bottom:8px;color:{h_color}}}h3{{font-size:12pt;margin-top:15px;margin-bottom:5px;color:{h_color}}}p{{margin-bottom:10px}}ul,ol{{margin-left:20px;margin-bottom:10px}}li{{margin-bottom:5px}}code{{background-color:{code_bg_color};padding:2px 4px;border-radius:3px;font-family:monospace}}a{{color:{link_color};text-decoration:none}}a:hover{{text-decoration:underline}}hr{{border:0;height:1px;background:#ccc;margin:20px 0}}</style>"
                html_content = markdown.markdown(md_content, extensions=['extra', 'sane_lists', 'nl2br']) # Добавлен nl2br для переносов строк
                self.text_browser.setHtml(css + html_content)
            else:
                logging.warning(f"Файл {md_filepath} пуст.")
                self.text_browser.setHtml(f"<p>Content file is empty: {md_filename}</p>")
        else: 
            logging.warning(f"Markdown file not found: {md_filepath}")
            self.text_browser.setHtml(f"<p>Content file not found: {md_filename}</p>")

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                if screen_geometry and screen_geometry.isValid(): 
                    center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                    center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

class AboutProgramDialog(BaseInfoDialog):
    def __init__(self, parent):
        super().__init__(parent, window_title_key='about_program', md_filename_base='information')

class AuthorDialog(BaseInfoDialog): # Новый класс
    def __init__(self, parent):
        super().__init__(parent, window_title_key='author_info_title', md_filename_base='author')


class HeroRatingDialog(QDialog): # Остается без изменений
    def __init__(self, parent, app_version):
        super().__init__(parent)
        self.setWindowTitle(get_text('hero_rating_title', version=app_version)) # Используется свой ключ для заголовка
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
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                if screen_geometry and screen_geometry.isValid():
                    center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                    center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

class LogDialog(QDialog): # Остается без изменений
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
        if not all_logs: 
            QMessageBox.information(self, get_text('info'), get_text('log_copy_no_logs'))
            return
        try: 
            pyperclip.copy(all_logs)
        except pyperclip.PyperclipException as e: 
            logging.error(f"PyperclipException при копировании логов: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")
        except Exception as e: 
            logging.error(f"Неожиданная ошибка при копировании логов: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")

    @Slot()
    def clear_log_display(self): self.log_browser.clear()
    def closeEvent(self, event: QCloseEvent): self.hide(); event.ignore()

class HotkeyDisplayDialog(QDialog): # Остается без изменений
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
        s = s.replace("tab", "Tab") 
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
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                if screen_geometry and screen_geometry.isValid():
                    center_point.setX(max(screen_geometry.left(),min(center_point.x(),screen_geometry.right()-self.width())))
                    center_point.setY(max(screen_geometry.top(),min(center_point.y(),screen_geometry.bottom()-self.height())))
            self.move(center_point)

class HotkeySettingsDialog(QDialog): # Остается без изменений
    hotkey_changed_signal = Signal(str, str)
    def __init__(self, current_hotkeys, hotkey_actions_config, parent=None):
        super().__init__(parent); self.current_hotkeys_copy = dict(current_hotkeys); self.hotkey_actions_config = hotkey_actions_config; self.parent_window = parent
        self.setWindowTitle(get_text('hotkey_settings_window_title')); self.setMinimumWidth(600); self.setModal(True) 
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
        s = s.replace("Num Decimal", "Num Del") 
        s = s.replace("divide", "/")
        s = s.replace("multiply", "*")
        s = s.replace("subtract", "-")
        s = s.replace("add", "+")
        s = s.replace("tab", "Tab") 
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
        cancel_btn = QPushButton(get_text('hotkey_settings_cancel_capture')); 
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus); 
        cancel_btn.clicked.connect(capture_dialog.reject); dialog_layout.addWidget(cancel_btn)
        hotkey_input_field.setFocus(); 
        
        def on_captured(act_id, key_str_internal): 
            if act_id == action_id: 
                self.update_hotkey_for_action(act_id, key_str_internal)
        
        def on_canceled_or_rejected():
            if hotkey_input_field and hotkey_input_field.action_id == action_id: 
                self.cancel_hotkey_capture(action_id)
        
        hotkey_input_field.hotkey_captured.connect(on_captured); 
        capture_dialog.finished.connect(on_canceled_or_rejected); 
        capture_dialog.exec()
        
        try:
            if hotkey_input_field: hotkey_input_field.hotkey_captured.disconnect(on_captured)
        except RuntimeError: pass 
        try: 
            if capture_dialog: capture_dialog.finished.disconnect(on_canceled_or_rejected)
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
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                if screen_geometry and screen_geometry.isValid():
                    center_point.setX(max(screen_geometry.left(),min(center_point.x(),screen_geometry.right()-self.width()))); center_point.setY(max(screen_geometry.top(),min(center_point.y(),screen_geometry.bottom()-self.height())))
            self.move(center_point)
    
def show_about_program_info(parent): dialog = AboutProgramDialog(parent); dialog.exec()
def show_author_info(parent): dialog = AuthorDialog(parent); dialog.exec() # Новая функция
def show_hero_rating(parent, app_version): dialog = HeroRatingDialog(parent, app_version); dialog.exec()
def show_hotkey_display_dialog(parent): dialog = HotkeyDisplayDialog(parent); dialog.exec()
def show_hotkey_settings_dialog(current_hotkeys, hotkey_actions_config, parent_window):
    dialog = HotkeySettingsDialog(current_hotkeys, hotkey_actions_config, parent_window)
    return dialog.exec() == QDialog.Accepted
