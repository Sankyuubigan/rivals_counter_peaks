# File: core/dialogs.py
from PySide6.QtWidgets import (QDialog, QTextBrowser, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout,
                               QLabel, QScrollArea, QWidget, QGridLayout, QLineEdit, QApplication,
                               QFileDialog)
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
import datetime 

from core.ui_components.hotkey_capture_line_edit import HotkeyCaptureLineEdit 
# PYNPUT_AVAILABLE_FOR_CAPTURE и keyboard больше не нужны здесь


HOTKEY_INPUT_FINISHED_EVENT = QEvent.Type(QEvent.User + 1) # Можно оставить, если используется где-то еще

def resource_path_dialogs(relative_path):
    # ... (без изменений) ...
    try:
        base_path = sys._MEIPASS
    except Exception: 
        base_path = os.path.abspath(os.path.dirname(__file__))
    
    lang_path_base = "" 
    if os.path.basename(base_path) == "core":
        lang_path_base = os.path.join(base_path, "lang")
    else: 
        core_sub_dir = os.path.join(base_path, "core")
        if os.path.isdir(core_sub_dir):
            lang_path_base = os.path.join(core_sub_dir, "lang")
        else: 
            logging.warning(f"Не удалось определить путь к 'core/lang' из {base_path}. Попытка использовать 'lang' относительно {base_path}.")
            lang_path_base = os.path.join(base_path, "lang")

    final_path = os.path.join(lang_path_base, relative_path)
    if not os.path.exists(final_path): 
        logging.warning(f"Файл ресурса не найден по вычисленному пути: {final_path}")
    return final_path


class BaseInfoDialog(QDialog):
    # ... (без изменений) ...
    def __init__(self, parent, window_title_key, md_filename_base):
        super().__init__(parent)
        self.parent_window = parent
        self.md_filename_base = md_filename_base 
        self.setObjectName(f"{md_filename_base.capitalize()}Dialog") 
        self.setWindowTitle(get_text(window_title_key))
        self.setGeometry(0, 0, 600, 450) 
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
        if hasattr(self.parent_window, 'logic') and self.parent_window.logic and hasattr(self.parent_window.logic, 'DEFAULT_LANGUAGE'):
             current_lang_code = self.parent_window.logic.DEFAULT_LANGUAGE
        elif hasattr(self.parent_window, 'current_language'): 
             current_lang_code = self.parent_window.current_language
        
        md_filename = f"{self.md_filename_base}_{current_lang_code.split('_')[0]}.md"
        md_filepath = resource_path_dialogs(md_filename)
        
        current_theme = "light" 
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager:
            current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'): 
            current_theme = self.parent_window.current_theme
        
        body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#ffffff", "#000000", "#333", "#007bff", "#f0f0f0")
        if current_theme == "dark":
            body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#2e2e2e", "#e0e0e0", "#cccccc", "#58a6ff", "#3c3c3c")
        
        if os.path.exists(md_filepath) and os.path.isfile(md_filepath):
            md_content = ""
            try: 
                with open(md_filepath, "r", encoding="utf-8") as f:
                    md_content = f.read()
            except IOError as e:
                 logging.error(f"IOError при чтении {md_filepath}: {e}")
                 self.text_browser.setHtml(f"<p>Error loading content: {e}</p>")
                 return

            if md_content:
                css = f"""<style>
                    body {{ font-family: sans-serif; font-size: 10pt; line-height: 1.6; 
                           background-color: {body_bg_color}; color: {body_text_color}; }}
                    h1 {{ font-size: 16pt; margin-bottom: 10px; color: {h_color}; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
                    h2 {{ font-size: 14pt; margin-top: 20px; margin-bottom: 8px; color: {h_color}; }}
                    h3 {{ font-size: 12pt; margin-top: 15px; margin-bottom: 5px; color: {h_color}; }}
                    p {{ margin-bottom: 10px; }}
                    ul, ol {{ margin-left: 20px; margin-bottom: 10px; }}
                    li {{ margin-bottom: 5px; }}
                    code {{ background-color: {code_bg_color}; padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
                    a {{ color: {link_color}; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    hr {{ border: 0; height: 1px; background: #ccc; margin: 20px 0; }}
                </style>"""
                html_content = markdown.markdown(md_content, extensions=['extra', 'sane_lists', 'nl2br'])
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

class AuthorDialog(BaseInfoDialog):
    def __init__(self, parent):
        super().__init__(parent, window_title_key='author_info_title', md_filename_base='author')


class HeroRatingDialog(QDialog):
    # ... (без изменений) ...
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
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                if screen_geometry and screen_geometry.isValid():
                    center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
                    center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

class LogDialog(QDialog):
    # ... (без изменений) ...
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
        
        self.save_button = QPushButton(get_text('save_logs_to_file_button', default_text="Сохранить логи в файл"))
        self.save_button.clicked.connect(self.save_logs_to_file)
        
        self.clear_button = QPushButton(get_text('clear_log_window_button'))
        self.clear_button.clicked.connect(self.clear_log_display)
        
        self.button_layout = QVBoxLayout() 
        self.button_layout.addWidget(self.copy_button)
        self.button_layout.addWidget(self.save_button)
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
            QMessageBox.information(self, get_text('success'), get_text('log_copy_success'))
        except pyperclip.PyperclipException as e: 
            logging.error(f"PyperclipException при копировании логов: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")
        except Exception as e: 
            logging.error(f"Неожиданная ошибка при копировании логов: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")

    @Slot()
    def save_logs_to_file(self):
        all_logs = self.log_browser.toPlainText()
        if not all_logs:
            QMessageBox.information(self, get_text('info'), get_text('log_save_no_logs', default_text="Нет логов для сохранения."))
            return
        now = datetime.datetime.now()
        default_filename = f"bugreport_{now.strftime('%Y%m%d_%H%M%S')}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            get_text('log_save_dialog_title', default_text="Сохранить логи как..."),
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path: 
            file_written_successfully = False; error_message_on_write = ""
            try: 
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(all_logs)
                file_written_successfully = True
            except IOError as e:
                error_message_on_write = str(e)
                logging.error(f"Ошибка записи логов в файл {file_path}: {e}")
            
            if file_written_successfully:
                QMessageBox.information(self, get_text('success'), get_text('log_save_success', filepath=file_path))
            else:
                QMessageBox.warning(self, get_text('error'), get_text('log_save_error_detailed', filepath=file_path, error_message=error_message_on_write))
        else:
            logging.info("Сохранение логов отменено пользователем.")

    @Slot()
    def clear_log_display(self):
        self.log_browser.clear()

    def closeEvent(self, event: QCloseEvent):
        self.hide(); event.ignore() 

class HotkeyDisplayDialog(QDialog):
    def __init__(self, parent=None): # parent должен быть MainWindow
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
    
    def _normalize_for_display_info(self, hotkey_str: str) -> str:
        # Используем ту же логику нормализации, что и в SettingsWindow
        # для консистентного отображения
        from core.settings_window import SettingsWindow # Импорт здесь, чтобы избежать цикла
        # Создаем временный экземпляр или делаем метод статическим, если возможно
        # Проще всего дублировать логику или вынести в общий util, но для простоты пока так:
        if not hotkey_str or hotkey_str == get_text('hotkey_not_set') or hotkey_str == get_text('hotkey_none'):
            return get_text('hotkey_not_set')
        
        s = hotkey_str
        s = s.replace("num_decimal", "Num Del") 
        s = s.replace("num_divide", "Num /")
        s = s.replace("num_multiply", "Num *")
        s = s.replace("num_subtract", "Num -")
        s = s.replace("num_add", "Num +")
        s = s.replace("num_", "Num ")

        key_name_replacements = {
            "up": "Up", "down": "Down", "left": "Left", "right": "Right",
            "delete": "Delete", "insert": "Insert", "home": "Home", "end": "End",
            "page_up": "PageUp", "page_down": "PageDown", "space": "Space",
            "enter": "Enter", "esc": "Esc", "backspace": "Backspace",
            "tab": "Tab", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", 
            "win": "Win", "windows": "Win" # "windows" от keyboard lib
        }
        
        parts = s.split('+')
        formatted_parts = []
        for part_str_orig in parts:
            part_str = part_str_orig.strip()
            if part_str.lower().startswith("num "):
                formatted_parts.append(part_str) 
            elif part_str.lower().startswith("keypad "): # Для формата keyboard lib
                formatted_parts.append(part_str.replace("keypad ", "Num ").capitalize())
            elif part_str.lower() in key_name_replacements:
                formatted_parts.append(key_name_replacements[part_str.lower()])
            elif part_str.lower().startswith("f") and len(part_str) > 1 and part_str[1:].isdigit(): 
                formatted_parts.append(part_str.upper()) 
            else: 
                formatted_parts.append(part_str.upper() if len(part_str) == 1 and part_str.isalpha() else part_str)
        
        return " + ".join(formatted_parts)


    def update_html_content(self):
        current_theme = "light" 
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager:
            current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'):
            current_theme = self.parent_window.current_theme
        
        body_bg_color = "white"; body_text_color = "black"; code_bg_color = "#f0f0f0"; h_color = "#333"
        if current_theme == "dark":
            body_bg_color = "#2e2e2e"; body_text_color = "#e0e0e0"; code_bg_color = "#3c3c3c"; h_color = "#cccccc"
        
        hotkeys_text_html = f"""<html><head><style>
            body {{ font-family: sans-serif; font-size: 10pt; background-color: {body_bg_color}; color: {body_text_color}; }}
            h3 {{ margin-bottom: 5px; margin-top: 10px; color: {h_color}; }}
            ul {{ margin-top: 0px; padding-left: 20px; }}
            li {{ margin-bottom: 3px; }}
            code {{ background-color: {code_bg_color}; padding: 1px 4px; border-radius: 3px; }}
        </style></head><body>
        <h3>{get_text('hotkeys_section_main')}</h3><ul>"""
        
        current_hotkeys_internal_format = {}
        # Получаем хоткеи из нового адаптера
        if hasattr(self.parent_window, 'hotkey_adapter') and self.parent_window.hotkey_adapter:
            current_hotkeys_internal_format = self.parent_window.hotkey_adapter.get_current_hotkeys_config_for_settings()
        else:
            logging.warning("HotkeyAdapter не найден в parent_window для HotkeyDisplayDialog.")

        from core.hotkey_config import HOTKEY_ACTIONS_CONFIG # Импорт здесь, чтобы избежать цикла
        
        # Используем HOTKEY_ACTIONS_CONFIG для итерации по действиям
        for action_id, config_data in HOTKEY_ACTIONS_CONFIG.items():
            desc_key_str = config_data['desc_key']
            # Получаем хоткей из загруженного конфига, используем action_id как ключ
            internal_hk_str = current_hotkeys_internal_format.get(action_id, get_text('hotkey_not_set'))
            display_hk_str = self._normalize_for_display_info(internal_hk_str) # Нормализуем для отображения
            hotkeys_text_html += f"<li><code>{display_hk_str}</code>: {get_text(desc_key_str)}</li>"

        hotkeys_text_html += f"""</ul>
        <h3>{get_text('hotkeys_section_interaction_title')}</h3><ul>
            <li><code>{get_text('hotkey_desc_lmb')}</code>: {get_text('hotkey_desc_lmb_select')}</li>
            <li><code>{get_text('hotkey_desc_rmb')}</code>: {get_text('hotkey_desc_rmb_priority')}</li>
            <li><code>{get_text('hotkey_desc_drag')}</code>: {get_text('hotkey_desc_drag_window')}</li>
            <li><code>{get_text('hotkey_desc_slider')}</code>: {get_text('hotkey_desc_slider_transparency')}</li>
        </ul></body></html>"""
        self.text_browser.setHtml(hotkeys_text_html)

    def center_on_parent(self): 
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen = self.screen()
            if screen:
                screen_geometry = screen.availableGeometry()
                if screen_geometry and screen_geometry.isValid():
                    center_point.setX(max(screen_geometry.left(),min(center_point.x(),screen_geometry.right()-self.width())))
                    center_point.setY(max(screen_geometry.top(),min(center_point.y(),screen_geometry.bottom()-self.height())))
            self.move(center_point)


# HotkeySettingsDialog удален, его функциональность перенесена в SettingsWindow

def show_about_program_info(parent):
    dialog = AboutProgramDialog(parent)
    dialog.exec()

def show_author_info(parent):
    dialog = AuthorDialog(parent)
    dialog.exec()

def show_hero_rating(parent, app_version):
    dialog = HeroRatingDialog(parent, app_version)
    dialog.exec()

def show_hotkey_display_dialog(parent):
    dialog = HotkeyDisplayDialog(parent)
    dialog.exec()

# show_hotkey_settings_dialog удалена, используется MainWindow.show_settings_window
