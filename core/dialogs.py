# File: core/dialogs.py
from PySide6.QtWidgets import (QDialog, QTextBrowser, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout,
                               QLabel, QScrollArea, QWidget, QGridLayout, QLineEdit, QApplication,
                               QFileDialog) # Добавлен QFileDialog
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
import datetime # Добавлен datetime

import json # json не используется напрямую для сохранения/загрузки настроек здесь
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
        # Если приложение "заморожено" PyInstaller'ом
        base_path = sys._MEIPASS
    except Exception: 
        # Если запускается как обычный скрипт
        base_path = os.path.abspath(os.path.dirname(__file__)) # Папка core
    
    lang_path_base = "" 
    # Проверяем, находимся ли мы уже в 'core' или в корне проекта
    if os.path.basename(base_path) == "core":
        lang_path_base = os.path.join(base_path, "lang")
    else: # Предполагаем, что base_path это корень проекта
        core_sub_dir = os.path.join(base_path, "core")
        if os.path.isdir(core_sub_dir):
            lang_path_base = os.path.join(core_sub_dir, "lang")
        else: 
            # Резервный вариант, если структура неожиданная
            logging.warning(f"Не удалось определить путь к 'core/lang' из {base_path}. Попытка использовать 'lang' относительно {base_path}.")
            lang_path_base = os.path.join(base_path, "lang") # Может не сработать, если base_path не корень

    final_path = os.path.join(lang_path_base, relative_path)
    # Проверка существования файла, если путь вычислен
    if not os.path.exists(final_path): 
        logging.warning(f"Файл ресурса не найден по вычисленному пути: {final_path}")
        # Можно добавить попытку найти файл относительно текущей рабочей директории как fallback
        # cwd_fallback_path = os.path.join(os.getcwd(), "core", "lang", relative_path)
        # if os.path.exists(cwd_fallback_path):
        #     logging.info(f"Найден файл ресурса по fallback пути (CWD): {cwd_fallback_path}")
        #     return cwd_fallback_path
    return final_path


class BaseInfoDialog(QDialog): # Создадим базовый класс для общих частей
    def __init__(self, parent, window_title_key, md_filename_base):
        super().__init__(parent)
        self.parent_window = parent
        self.md_filename_base = md_filename_base # e.g., "information" or "author"
        self.setObjectName(f"{md_filename_base.capitalize()}Dialog") # Используем md_filename_base для уникальности
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
        # Получаем текущий язык из родительского окна (MainWindow)
        current_lang_code = 'ru_RU' # По умолчанию
        if hasattr(self.parent_window, 'logic') and self.parent_window.logic and hasattr(self.parent_window.logic, 'DEFAULT_LANGUAGE'):
             current_lang_code = self.parent_window.logic.DEFAULT_LANGUAGE
        elif hasattr(self.parent_window, 'current_language'): # Если язык хранится напрямую в MainWindow
             current_lang_code = self.parent_window.current_language
        
        # Формируем имя файла на основе md_filename_base и языка
        md_filename = f"{self.md_filename_base}_{current_lang_code.split('_')[0]}.md" # e.g., author_ru.md

        md_filepath = resource_path_dialogs(md_filename)
        
        # Получаем текущую тему
        current_theme = "light" # По умолчанию
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager:
            current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'): # Если тема хранится напрямую
            current_theme = self.parent_window.current_theme
        
        # Определяем цвета на основе темы
        body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#ffffff", "#000000", "#333", "#007bff", "#f0f0f0")
        if current_theme == "dark":
            body_bg_color, body_text_color, h_color, link_color, code_bg_color = ("#2e2e2e", "#e0e0e0", "#cccccc", "#58a6ff", "#3c3c3c")
        
        # Читаем и отображаем Markdown файл
        # Используем if-else для проверки существования файла, но try-except для самой операции чтения
        if os.path.exists(md_filepath) and os.path.isfile(md_filepath):
            md_content = ""
            try: # Оставляем try-except для файловой операции
                with open(md_filepath, "r", encoding="utf-8") as f:
                    md_content = f.read()
            except IOError as e:
                 logging.error(f"IOError при чтении {md_filepath}: {e}")
                 self.text_browser.setHtml(f"<p>Error loading content: {e}</p>")
                 return

            if md_content:
                # Простой CSS для лучшего отображения
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
                # Используем markdown для конвертации в HTML, nl2br для переносов строк
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
            if screen: # Проверка, что screen не None
                screen_geometry = screen.availableGeometry()
                if screen_geometry and screen_geometry.isValid(): # Дополнительные проверки
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
        self.center_on_parent() # Вызов метода центрирования
        layout = QVBoxLayout(self)
        text_browser = QTextBrowser()
        text_browser.setReadOnly(True)
        text_browser.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        # Логика подсчета рейтинга
        counter_counts = {hero: 0 for hero in heroes_bd.heroes}
        for hero_being_countered, counters_data in heroes_bd.heroes_counters.items():
            if isinstance(counters_data, dict): # Добавлена проверка типа
                for counter_hero in counters_data.get("hard", []) + counters_data.get("soft", []):
                    if counter_hero in counter_counts:
                        counter_counts[counter_hero] +=1
        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1], reverse=True)
        # Формирование текста для отображения
        rating_lines = [f"{hero} ({count})" for hero, count in sorted_heroes]
        text_browser.setText("\n".join(rating_lines))
        layout.addWidget(text_browser)
        close_button = QPushButton("OK")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    def center_on_parent(self): # Метод для центрирования окна
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text('logs_window_title'))
        self.setGeometry(150, 150, 900, 600)
        self.setModal(False) # Логи не должны блокировать основное окно
        self.layout = QVBoxLayout(self)
        self.log_browser = QTextBrowser(self)
        self.log_browser.setReadOnly(True)
        self.log_browser.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap) # Отключаем перенос строк для логов
        font = self.log_browser.font()
        font.setFamily("Courier New") # Моноширинный шрифт для логов
        font.setPointSize(10)
        self.log_browser.setFont(font)

        self.copy_button = QPushButton(get_text('copy_all_logs_button'))
        self.copy_button.clicked.connect(self.copy_logs)
        
        self.save_button = QPushButton(get_text('save_logs_to_file_button', default_text="Сохранить логи в файл"))
        self.save_button.clicked.connect(self.save_logs_to_file)
        
        self.clear_button = QPushButton(get_text('clear_log_window_button'))
        self.clear_button.clicked.connect(self.clear_log_display)
        
        self.button_layout = QVBoxLayout() # Вертикальный layout для кнопок
        self.button_layout.addWidget(self.copy_button)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.clear_button)
        self.button_layout.addStretch(1) # Растягиваем, чтобы кнопки были сверху
        
        self.main_hbox_layout = QHBoxLayout() # Горизонтальный layout для браузера и кнопок
        self.main_hbox_layout.addWidget(self.log_browser, stretch=1) # Браузер занимает большую часть
        self.main_hbox_layout.addLayout(self.button_layout) # Добавляем кнопки справа
        self.layout.addLayout(self.main_hbox_layout)

    @Slot(str)
    def append_log(self, message):
        self.log_browser.append(message)

    @Slot()
    def copy_logs(self):
        all_logs = self.log_browser.toPlainText()
        if not all_logs: # Проверка на пустые логи
            QMessageBox.information(self, get_text('info'), get_text('log_copy_no_logs'))
            return
        # Оставляем try-except для pyperclip, так как это внешняя библиотека
        try: 
            pyperclip.copy(all_logs)
            QMessageBox.information(self, get_text('success'), get_text('log_copy_success'))
        except pyperclip.PyperclipException as e: 
            logging.error(f"PyperclipException при копировании логов: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")
        except Exception as e: # Общее исключение
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
        
        # QFileDialog.getSaveFileName может вернуть пустую строку, если пользователь отменил
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            get_text('log_save_dialog_title', default_text="Сохранить логи как..."),
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path: # Если путь выбран
            file_written_successfully = False
            error_message_on_write = ""
            try: # Оставляем try-except для файловой операции open/write
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
        self.hide() # Просто скрываем окно, не закрываем его полностью
        event.ignore() # Игнорируем событие закрытия, чтобы окно не уничтожалось

class HotkeyDisplayDialog(QDialog): # Остается без изменений
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent # Сохраняем ссылку на родительское окно для доступа к темам/языку
        self.setWindowTitle(get_text('hotkeys_window_title'))
        self.setMinimumWidth(550) # Увеличим немного ширину для лучшего отображения
        self.setModal(True)
        self.layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser(self)
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(False) # Ссылки не нужны
        self.update_html_content() # Первоначальное заполнение
        self.close_button = QPushButton("OK")
        self.close_button.clicked.connect(self.accept)
        self.layout.addWidget(self.text_browser)
        self.layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)
        QTimer.singleShot(0, self.center_on_parent) # Центрируем после показа
    
    def _normalize_for_display_info(self, hotkey_str: str) -> str:
        # Простая нормализация для отображения (можно расширить)
        s = hotkey_str.replace("num_", "Num ")
        s = s.replace("decimal", "Decimal") # Num Decimal -> Num .
        s = s.replace("Num Decimal", "Num .") # Явное преобразование
        s = s.replace("divide", "/")
        s = s.replace("multiply", "*")
        s = s.replace("subtract", "-")
        s = s.replace("add", "+")
        s = s.replace("tab", "Tab") # Для клавиши Tab
        return s

    def update_html_content(self):
        # Получаем текущую тему из родительского окна
        current_theme = "light" # По умолчанию
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager:
            current_theme = self.parent_window.appearance_manager.current_theme
        elif hasattr(self.parent_window, 'current_theme'):
            current_theme = self.parent_window.current_theme
        
        # Цвета для тем
        body_bg_color = "white"; body_text_color = "black"; code_bg_color = "#f0f0f0"; h_color = "#333"
        if current_theme == "dark":
            body_bg_color = "#2e2e2e"; body_text_color = "#e0e0e0"; code_bg_color = "#3c3c3c"; h_color = "#cccccc"
        
        # Собираем HTML
        hotkeys_text_html = f"""<html><head><style>
            body {{ font-family: sans-serif; font-size: 10pt; background-color: {body_bg_color}; color: {body_text_color}; }}
            h3 {{ margin-bottom: 5px; margin-top: 10px; color: {h_color}; }}
            ul {{ margin-top: 0px; padding-left: 20px; }}
            li {{ margin-bottom: 3px; }}
            code {{ background-color: {code_bg_color}; padding: 1px 4px; border-radius: 3px; }}
        </style></head><body>
        <h3>{get_text('hotkeys_section_main')}</h3><ul>"""
        
        current_hotkeys = {}
        if hasattr(self.parent_window, 'hotkey_manager') and self.parent_window.hotkey_manager:
            current_hotkeys = self.parent_window.hotkey_manager.get_current_hotkeys_config()

        def get_display_hotkey(action_id):
            hk_str = current_hotkeys.get(action_id, get_text('hotkey_not_set'))
            return self._normalize_for_display_info(hk_str) # Используем нормализацию

        # Список действий и их ключей описания
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
            # ("toggle_mouse_ignore_independent", 'hotkey_desc_toggle_mouse_ignore'), # Удалено
            ("debug_capture", 'hotkey_desc_debug_screenshot'),
            ("decrease_opacity", 'hotkey_desc_decrease_opacity'),
            ("increase_opacity", 'hotkey_desc_increase_opacity'),
        ]
        for action_id, desc_key_str in hotkey_list_items_config:
            hotkeys_text_html += f"<li><code>{get_display_hotkey(action_id)}</code>: {get_text(desc_key_str)}</li>"

        hotkeys_text_html += f"""</ul>
        <h3>{get_text('hotkeys_section_interaction_title')}</h3><ul>
            <li><code>{get_text('hotkey_desc_lmb')}</code>: {get_text('hotkey_desc_lmb_select')}</li>
            <li><code>{get_text('hotkey_desc_rmb')}</code>: {get_text('hotkey_desc_rmb_priority')}</li>
            <li><code>{get_text('hotkey_desc_drag')}</code>: {get_text('hotkey_desc_drag_window')}</li>
            <li><code>{get_text('hotkey_desc_slider')}</code>: {get_text('hotkey_desc_slider_transparency')}</li>
        </ul></body></html>"""
        self.text_browser.setHtml(hotkeys_text_html)

    def center_on_parent(self): # Метод для центрирования окна
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

class HotkeySettingsDialog(QDialog): # Остается без изменений
    hotkey_changed_signal = Signal(str, str) # Сигнал об изменении хоткея (action_id, new_hotkey_string)
    def __init__(self, current_hotkeys: dict, hotkey_actions_config: dict, parent=None):
        super().__init__(parent)
        self.current_hotkeys_copy = dict(current_hotkeys) # Рабочая копия для изменений
        self.hotkey_actions_config = hotkey_actions_config # Конфигурация действий
        self.parent_window = parent # Для доступа к теме, если нужно
        
        self.setWindowTitle(get_text('hotkey_settings_window_title')) # Заголовок из переводов
        self.setMinimumWidth(600)
        self.setModal(True) 
        
        self.main_layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea() # Для прокрутки списка хоткеев
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget() # Контент для ScrollArea
        self.grid_layout = QGridLayout(self.scroll_widget) # Grid для отображения хоткеев
        self.grid_layout.setHorizontalSpacing(15)
        self.grid_layout.setVerticalSpacing(10)
        
        self.action_widgets: dict[str, dict] = {} # Словарь для хранения виджетов каждого действия
        self._populate_hotkey_list() # Заполняем список хоткеев
        
        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        # Кнопки управления
        self.buttons_layout = QHBoxLayout()
        self.reset_defaults_button = QPushButton(get_text('hotkey_settings_reset_defaults'))
        self.reset_defaults_button.clicked.connect(self.reset_to_defaults)
        
        self.save_button = QPushButton(get_text('hotkey_settings_save'))
        self.save_button.clicked.connect(self.save_and_close)
        
        self.cancel_button = QPushButton(get_text('hotkey_settings_cancel'))
        self.cancel_button.clicked.connect(self.reject) # self.reject() закроет диалог без сохранения
        
        self.buttons_layout.addWidget(self.reset_defaults_button)
        self.buttons_layout.addStretch(1) # Растягиватель, чтобы кнопки были справа
        self.buttons_layout.addWidget(self.save_button)
        self.buttons_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.buttons_layout)
        
        QTimer.singleShot(0, self.center_on_parent)

    def _normalize_for_display(self, hotkey_str: str) -> str:
        # Нормализация строки хоткея для отображения пользователю
        if not hotkey_str or hotkey_str == get_text('hotkey_not_set') or hotkey_str == get_text('hotkey_none'):
            return get_text('hotkey_not_set')
        
        s = hotkey_str
        # Замены для NumPad клавиш
        s = s.replace("num_decimal", "Num Del") 
        s = s.replace("num_divide", "Num /")
        s = s.replace("num_multiply", "Num *")
        s = s.replace("num_subtract", "Num -")
        s = s.replace("num_add", "Num +")
        s = s.replace("num_", "Num ") # Общее для Num 0-9

        # Замены для других специальных клавиш и модификаторов (капитализация)
        key_name_replacements = {
            "up": "Up", "down": "Down", "left": "Left", "right": "Right",
            "delete": "Delete", "insert": "Insert", "home": "Home", "end": "End",
            "page_up": "PageUp", "page_down": "PageDown", "space": "Space",
            "enter": "Enter", "esc": "Esc", "backspace": "Backspace",
            "tab": "Tab", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"
            # Добавьте другие по необходимости
        }
        
        parts = s.split('+')
        formatted_parts = []
        for part_str_orig in parts:
            part_str = part_str_orig.strip() # Убираем лишние пробелы, если есть
            if part_str.lower().startswith("num "): # Уже обработанные Num клавиши
                formatted_parts.append(part_str) 
            elif part_str.lower() in key_name_replacements:
                formatted_parts.append(key_name_replacements[part_str.lower()])
            elif part_str.lower().startswith("f") and len(part_str) > 1 and part_str[1:].isdigit(): # F-клавиши (F1, F2, ...)
                formatted_parts.append(part_str.upper()) 
            else: # Обычные символьные клавиши или неизвестные (оставляем как есть или делаем upper для одиночных букв)
                formatted_parts.append(part_str.upper() if len(part_str) == 1 and part_str.isalpha() else part_str)
        
        return " + ".join(formatted_parts)


    def _populate_hotkey_list(self):
        # Очищаем grid layout перед заполнением
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self.action_widgets.clear() # Очищаем словарь виджетов

        row = 0
        for action_id, config in self.hotkey_actions_config.items():
            desc_key = config['desc_key']
            description = get_text(desc_key, default_text=action_id) # Используем action_id как fallback
            
            current_hotkey_str_internal = self.current_hotkeys_copy.get(action_id, get_text('hotkey_not_set'))
            display_hotkey_str = self._normalize_for_display(current_hotkey_str_internal)

            desc_label = QLabel(description)
            hotkey_label = QLabel(f"<code>{display_hotkey_str}</code>") # Используем RichText для code
            hotkey_label.setTextFormat(Qt.TextFormat.RichText) 
            
            change_button = QPushButton(get_text('hotkey_settings_change_btn'))
            change_button.setProperty("action_id", action_id) # Сохраняем ID действия в кнопке
            change_button.clicked.connect(self.on_change_hotkey_button_clicked)

            self.grid_layout.addWidget(desc_label, row, 0, Qt.AlignmentFlag.AlignLeft)
            self.grid_layout.addWidget(hotkey_label, row, 1, Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(change_button, row, 2, Qt.AlignmentFlag.AlignRight)
            
            self.action_widgets[action_id] = {'desc': desc_label, 'hotkey': hotkey_label, 'button': change_button}
            row += 1
        
        # Настройка растяжения колонок
        self.grid_layout.setColumnStretch(0, 2) # Описание действия
        self.grid_layout.setColumnStretch(1, 1) # Текущий хоткей
        self.grid_layout.setColumnStretch(2, 0) # Кнопка "Изменить"


    def on_change_hotkey_button_clicked(self):
        sender_button = self.sender()
        if not sender_button: return
        action_id = sender_button.property("action_id")
        if not action_id or action_id not in self.action_widgets: return

        # Визуальное обозначение, что мы ожидаем ввод
        current_theme = "light"; text_color_during_capture = "orange"
        if hasattr(self.parent_window, 'appearance_manager') and self.parent_window.appearance_manager:
             current_theme = self.parent_window.appearance_manager.current_theme
        if current_theme == "dark": text_color_during_capture = "#FFA500" # Яркий оранжевый для темной темы
        
        self.action_widgets[action_id]['hotkey'].setText(f"<i>{get_text('hotkey_settings_press_keys')}</i>")
        self.action_widgets[action_id]['hotkey'].setStyleSheet(f"font-style:italic;color:{text_color_during_capture};")
        
        # Создаем диалог для захвата хоткея
        capture_dialog = QDialog(self)
        capture_dialog.setWindowTitle(get_text('hotkey_settings_capture_title'))
        capture_dialog.setModal(True)
        dialog_layout = QVBoxLayout(capture_dialog)
        
        action_desc = get_text(self.hotkey_actions_config[action_id]['desc_key'])
        info_label = QLabel(get_text('hotkey_settings_press_new_hotkey_for', action=action_desc))
        dialog_layout.addWidget(info_label)

        hotkey_input_field = HotkeyCaptureLineEdit(action_id, capture_dialog) # Передаем action_id
        dialog_layout.addWidget(hotkey_input_field)
        
        cancel_btn = QPushButton(get_text('hotkey_settings_cancel_capture'))
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Чтобы не перехватывал фокус с поля ввода
        cancel_btn.clicked.connect(capture_dialog.reject)
        dialog_layout.addWidget(cancel_btn)

        hotkey_input_field.setFocus() # Устанавливаем фокус на поле ввода
        
        # Локальные слоты для обработки сигналов от HotkeyCaptureLineEdit
        @Slot(str, str)
        def on_captured_locally(captured_action_id: str, key_str_internal: str):
            if captured_action_id == action_id: # Убедимся, что это для нужного действия
                self.update_hotkey_for_action(action_id, key_str_internal)
        
        @Slot(str)
        def on_canceled_or_rejected_locally(canceled_action_id: str):
            # Этот слот вызывается, если HotkeyCaptureLineEdit сам отменил ввод (напр. Escape)
            # или если весь диалог capture_dialog был закрыт через reject() (напр. кнопка Отмена)
            if canceled_action_id == action_id:
                self.cancel_hotkey_capture(action_id)
        
        hotkey_input_field.hotkey_captured.connect(on_captured_locally)
        hotkey_input_field.capture_canceled.connect(on_canceled_or_rejected_locally)
        
        # Если диалог capture_dialog закрывается (не через accept/reject от HotkeyCaptureLineEdit),
        # также считаем это отменой ввода для текущего action_id.
        # Используем finished, так как он срабатывает и при accept, и при reject диалога.
        # Если finished был вызван accept() от HotkeyCaptureLineEdit, on_captured_locally уже сработал.
        # Если finished был вызван reject() от HotkeyCaptureLineEdit или кнопки "Отмена ввода",
        # on_canceled_or_rejected_locally должен сработать.
        # Этот дополнительный finished.connect нужен для случая, если диалог закрывается системно (крестик),
        # что эквивалентно reject().
        def handle_dialog_finished(result_code):
            if hotkey_input_field.text() == f"<i>{get_text('hotkey_settings_press_keys')}</i>": # Если ввод не завершился
                on_canceled_or_rejected_locally(action_id)

        capture_dialog.finished.connect(handle_dialog_finished)
        capture_dialog.exec() # Показываем модальный диалог
        
        # Отсоединяем локальные слоты, чтобы избежать множественных вызовов при повторном открытии
        # Оборачиваем в try-except, так как hotkey_input_field может быть уже удален
        try:
            if hotkey_input_field:
                hotkey_input_field.hotkey_captured.disconnect(on_captured_locally)
                hotkey_input_field.capture_canceled.disconnect(on_canceled_or_rejected_locally)
            if capture_dialog:
                 capture_dialog.finished.disconnect(handle_dialog_finished)
        except RuntimeError:
            pass # Объект мог быть уже удален

    @Slot(str, str)
    def update_hotkey_for_action(self, action_id: str, new_hotkey_str_internal: str): 
        if action_id in self.action_widgets:
            logging.info(f"Updating hotkey (dialog temp) for {action_id} to internal '{new_hotkey_str_internal}'")
            self.current_hotkeys_copy[action_id] = new_hotkey_str_internal # Обновляем временную копию
            display_str = self._normalize_for_display(new_hotkey_str_internal)
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>")
            self.action_widgets[action_id]['hotkey'].setStyleSheet("") # Сбрасываем стиль

    @Slot(str)
    def cancel_hotkey_capture(self, action_id: str):
        # Вызывается, если ввод хоткея был отменен
        if action_id in self.action_widgets:
            original_hotkey_internal = self.current_hotkeys_copy.get(action_id, get_text('hotkey_not_set'))
            display_str = self._normalize_for_display(original_hotkey_internal)
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{display_str}</code>")
            self.action_widgets[action_id]['hotkey'].setStyleSheet("") # Сбрасываем стиль
    
    def reset_to_defaults(self):
        # Используем DEFAULT_HOTKEYS_VALUES из hotkey_config.py
        if hasattr(self.parent_window, 'hotkey_manager') and self.parent_window.hotkey_manager:
            default_hotkeys_internal = self.parent_window.hotkey_manager.get_default_hotkeys_config() # Получаем из менеджера
            self.current_hotkeys_copy = dict(default_hotkeys_internal)
            self._populate_hotkey_list() # Перерисовываем список с новыми значениями
            QMessageBox.information(self, get_text('hotkey_settings_defaults_reset_title'), get_text('hotkey_settings_defaults_reset_msg'))
    
    def save_and_close(self):
        # Проверка на дубликаты перед сохранением
        if hasattr(self.parent_window, 'hotkey_manager') and self.parent_window.hotkey_manager:
            hotkey_map: dict[str, str] = {} # hotkey_string -> action_id
            duplicates_found: list[str] = []
            
            for action_id, hotkey_str_internal in self.current_hotkeys_copy.items():
                # Пропускаем неназначенные хоткеи
                if not hotkey_str_internal or \
                   hotkey_str_internal == get_text('hotkey_none') or \
                   hotkey_str_internal == get_text('hotkey_not_set'):
                    continue
                
                if hotkey_str_internal in hotkey_map: # Если такой хоткей уже есть в карте
                    # Получаем описания действий для сообщения об ошибке
                    action_desc1_key = self.hotkey_actions_config.get(action_id, {}).get('desc_key', action_id)
                    action_desc2_key = self.hotkey_actions_config.get(hotkey_map[hotkey_str_internal], {}).get('desc_key', hotkey_map[hotkey_str_internal])
                    action_desc1 = get_text(action_desc1_key)
                    action_desc2 = get_text(action_desc2_key)
                    
                    display_duplicate_str = self._normalize_for_display(hotkey_str_internal)
                    duplicates_found.append(f"'{display_duplicate_str}' ({get_text('sw_for_action_text', default_text='для')}: '{action_desc1}' {get_text('sw_and_text', default_text='и')} '{action_desc2}')")
                else:
                    hotkey_map[hotkey_str_internal] = action_id
            
            if duplicates_found:
                QMessageBox.warning(self, get_text('hotkey_settings_duplicate_title'),
                                    get_text('hotkey_settings_duplicate_message') + "\n- " + "\n- ".join(duplicates_found))
                return # Не сохраняем и не закрываем, если есть дубликаты
            
            # Если дубликатов нет, сохраняем
            logging.info(f"HotkeySettingsDialog: Сохранение хоткеев: {self.current_hotkeys_copy}")
            self.parent_window.hotkey_manager.save_hotkeys_to_settings(self.current_hotkeys_copy) # Используем метод для сохранения в AppSettingsManager
            self.accept() # self.accept() закроет диалог и вернет QDialog.Accepted
        else:
            logging.error("HotkeyManager не найден в родительском окне. Сохранение невозможно.")
            QMessageBox.critical(self, get_text('error'), "Ошибка: Менеджер горячих клавиш не доступен.")


    def center_on_parent(self): # Метод для центрирования окна
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
    
def show_about_program_info(parent):
    dialog = AboutProgramDialog(parent)
    dialog.exec()

def show_author_info(parent): # Новая функция
    dialog = AuthorDialog(parent)
    dialog.exec()

def show_hero_rating(parent, app_version):
    dialog = HeroRatingDialog(parent, app_version)
    dialog.exec()

def show_hotkey_display_dialog(parent):
    # Создаем диалог каждый раз, чтобы он подхватывал актуальные хоткеи и тему
    dialog = HotkeyDisplayDialog(parent)
    dialog.exec()

def show_hotkey_settings_dialog(current_hotkeys: dict, hotkey_actions_config: dict, parent_window: QWidget) -> bool:
    """
    Показывает диалог настроек горячих клавиш.
    Возвращает True, если настройки были сохранены (OK/Apply), False иначе.
    """
    dialog = HotkeySettingsDialog(current_hotkeys, hotkey_actions_config, parent_window)
    return dialog.exec() == QDialog.Accepted # Возвращаем результат выполнения диалога
