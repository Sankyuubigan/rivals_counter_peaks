# File: core/dialogs.py
from PySide6.QtWidgets import (QDialog, QTextBrowser, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout,
                               QLabel, QScrollArea, QWidget, QGridLayout, QLineEdit)
# ИЗМЕНЕНО: Добавлен импорт Signal
from PySide6.QtCore import Qt, Slot, QTimer, QEvent, QKeyCombination, Signal
from PySide6.QtGui import QKeySequence
from database import heroes_bd
from core.lang.translations import get_text
import pyperclip
import logging
import os
import sys # Добавлен sys для resource_path_dialogs
import markdown

# Импорты для настроек хоткеев
import json
# from core.utils import resource_path as app_resource_path # Не используется здесь

# Идентификатор для кастомного события при изменении хоткея
HOTKEY_INPUT_FINISHED_EVENT = QEvent.Type(QEvent.User + 1)

def resource_path_dialogs(relative_path):
    try:
        base_path = sys._MEIPASS # Используем sys здесь
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, "lang", relative_path)


class AboutProgramDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('about_program'))
        self.setGeometry(0, 0, 700, 550)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)

        current_lang_code = 'ru_RU'
        if hasattr(parent, 'logic') and hasattr(parent.logic, 'DEFAULT_LANGUAGE'):
             current_lang_code = parent.logic.DEFAULT_LANGUAGE

        md_filename_key = "information_ru.md"
        if current_lang_code.startswith('en'):
            md_filename_key = "information_en.md"

        md_filepath = resource_path_dialogs(md_filename_key)
        logging.debug(f"Attempting to load markdown from: {md_filepath}")

        if os.path.exists(md_filepath):
            md_content = ""
            try: # Оставим try-except для чтения файла, т.к. это I/O операция
                with open(md_filepath, "r", encoding="utf-8") as f:
                    md_content = f.read()
                css = """<style> body { font-family: sans-serif; font-size: 10pt; line-height: 1.6; } h1 { font-size: 16pt; margin-bottom: 10px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px;} h2 { font-size: 14pt; margin-top: 20px; margin-bottom: 8px; color: #444;} h3 { font-size: 12pt; margin-top: 15px; margin-bottom: 5px; color: #555;} p { margin-bottom: 10px; } ul, ol { margin-left: 20px; margin-bottom: 10px; } li { margin-bottom: 5px; } code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: monospace; } a { color: #007bff; text-decoration: none; } a:hover { text-decoration: underline; } hr { border: 0; height: 1px; background: #ccc; margin: 20px 0; } </style> """
                html_content = markdown.markdown(md_content, extensions=['extra', 'sane_lists'])
                self.text_browser.setHtml(css + html_content)
            except Exception as e: # Ошибка парсинга markdown или чтения файла
                logging.error(f"Error loading or parsing {md_filepath}: {e}")
                self.text_browser.setPlainText(f"Error loading content for {md_filename_key}: {e}")
        else:
            logging.warning(f"Markdown file not found: {md_filepath} (searched for {md_filename_key})")
            self.text_browser.setPlainText(f"Information file not found: {md_filename_key}")

        self.close_button = QPushButton("OK")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.text_browser)
        layout.addWidget(self.close_button)

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            if screen_geometry: # Проверка, что screen() вернул валидный объект
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
        for counters_list in heroes_bd.heroes_counters.values():
            for counter_hero in counters_list:
                if counter_hero in counter_counts:
                     counter_counts[counter_hero] += 1

        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1])
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
        try: # Оставим try-except для pyperclip, так как он может бросать свои исключения
            pyperclip.copy(all_logs)
            logging.info("Logs copied to clipboard.")
        except pyperclip.PyperclipException as e:
            logging.error(f"Pyperclip error copying logs: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")
        except Exception as e: # Общий на случай других проблем с буфером
            logging.error(f"Unexpected error copying logs: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")

    @Slot()
    def clear_log_display(self):
        self.log_browser.clear()
        logging.info("Log display cleared by user.")

    def closeEvent(self, event):
        logging.debug("LogDialog close event: hiding window.")
        self.hide()
        event.ignore()


class HotkeyDisplayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text('hotkeys_window_title'))
        self.setMinimumWidth(550)
        self.setModal(True)

        self.layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser(self)
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(False)
        hotkeys_text_html = f"""
        <html><head><style> body {{ font-family: sans-serif; font-size: 10pt; }} h3 {{ margin-bottom: 5px; margin-top: 10px; }} ul {{ margin-top: 0px; padding-left: 20px; }} li {{ margin-bottom: 3px; }} code {{ background-color: #f0f0f0; padding: 1px 4px; border-radius: 3px; }} </style></head><body>
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
        self.close_button = QPushButton("OK")
        self.close_button.clicked.connect(self.accept)
        self.layout.addWidget(self.text_browser)
        self.layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)
        QTimer.singleShot(0, self.center_on_parent)

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
        self.current_hotkeys = dict(current_hotkeys)
        self.hotkey_actions_config = hotkey_actions_config
        self.parent_window = parent
        self.setWindowTitle(get_text('hotkey_settings_window_title'))
        self.setMinimumWidth(600); self.setModal(True)
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
            current_hotkey_str = self.current_hotkeys.get(action_id, get_text('hotkey_not_set'))
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
        self.action_widgets[action_id]['hotkey'].setText(f"<i>{get_text('hotkey_settings_press_keys')}</i>")
        self.action_widgets[action_id]['hotkey'].setStyleSheet("font-style: italic; color: orange;")
        
        # Используем HotkeyCaptureLineEdit в модальном диалоге
        capture_dialog = QDialog(self)
        capture_dialog.setWindowTitle(get_text('hotkey_settings_capture_title'))
        capture_dialog.setModal(True)
        dialog_layout = QVBoxLayout(capture_dialog)
        
        action_desc = get_text(self.hotkey_actions_config[action_id]['desc_key'])
        info_label = QLabel(get_text('hotkey_settings_press_new_hotkey_for').format(action=action_desc))
        dialog_layout.addWidget(info_label)
        
        hotkey_input_field = HotkeyCaptureLineEdit(action_id, capture_dialog) # родитель - capture_dialog
        dialog_layout.addWidget(hotkey_input_field)
        
        cancel_btn = QPushButton(get_text('hotkey_settings_cancel_capture'))
        cancel_btn.clicked.connect(capture_dialog.reject)
        dialog_layout.addWidget(cancel_btn)
        
        hotkey_input_field.setFocus()
        
        # Локальные слоты для обработки результата от HotkeyCaptureLineEdit
        def on_captured(act_id, key_str):
            if act_id == action_id:
                self.update_hotkey_for_action(act_id, key_str)
                capture_dialog.accept()
        
        def on_canceled(act_id):
            if act_id == action_id:
                self.cancel_hotkey_capture(act_id)
                capture_dialog.reject()

        hotkey_input_field.hotkey_captured.connect(on_captured)
        hotkey_input_field.capture_canceled.connect(on_canceled)
        
        capture_dialog.exec() # Показываем диалог ввода хоткея

        # После закрытия диалога ввода, отсоединяем временные слоты
        if hotkey_input_field: # Проверка, что он еще существует
            hotkey_input_field.hotkey_captured.disconnect(on_captured)
            hotkey_input_field.capture_canceled.disconnect(on_canceled)


    @Slot(str, str)
    def update_hotkey_for_action(self, action_id: str, new_hotkey_str: str):
        if action_id in self.action_widgets:
            logging.info(f"Updating hotkey for {action_id} to {new_hotkey_str}")
            self.current_hotkeys[action_id] = new_hotkey_str
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{new_hotkey_str}</code>")
            self.action_widgets[action_id]['hotkey'].setStyleSheet("")

    @Slot(str)
    def cancel_hotkey_capture(self, action_id: str):
        if action_id in self.action_widgets and self.parent_window and hasattr(self.parent_window, 'hotkey_manager'):
            # Получаем оригинальный хоткей из менеджера (сохраненный или дефолтный)
            # или из self.current_hotkeys, если он там уже был до попытки изменения.
            original_hotkey = self.current_hotkeys.get(action_id)
            if not original_hotkey: # Если вдруг в current_hotkeys нет (не должно быть)
                 original_hotkey = self.parent_window.hotkey_manager.get_hotkey_for_action(action_id) or get_text('hotkey_not_set')
            
            self.action_widgets[action_id]['hotkey'].setText(f"<code>{original_hotkey}</code>")
            self.action_widgets[action_id]['hotkey'].setStyleSheet("")
            logging.debug(f"Hotkey capture canceled for {action_id}, reverted to {original_hotkey}")

    def reset_to_defaults(self):
        if self.parent_window and hasattr(self.parent_window, 'hotkey_manager'):
            default_hotkeys = self.parent_window.hotkey_manager.get_default_hotkeys()
            self.current_hotkeys = dict(default_hotkeys)
            self._populate_hotkey_list()
            QMessageBox.information(self, get_text('hotkey_settings_defaults_reset_title'), get_text('hotkey_settings_defaults_reset_msg'))
        else:
            logging.error("Hotkey manager not found in parent window for resetting defaults.")

    def save_and_close(self):
        if self.parent_window and hasattr(self.parent_window, 'hotkey_manager'):
            hotkey_map = {}; duplicates = []
            for action_id, hotkey_str in self.current_hotkeys.items():
                if hotkey_str == get_text('hotkey_none') or hotkey_str == get_text('hotkey_not_set'): continue
                if hotkey_str in hotkey_map:
                    action_desc1 = get_text(self.hotkey_actions_config.get(action_id, {}).get('desc_key', action_id))
                    action_desc2 = get_text(self.hotkey_actions_config.get(hotkey_map[hotkey_str], {}).get('desc_key', hotkey_map[hotkey_str]))
                    duplicates.append(f"'{hotkey_str}' for '{action_desc1}' and '{action_desc2}'")
                else: hotkey_map[hotkey_str] = action_id
            if duplicates:
                QMessageBox.warning(self, get_text('hotkey_settings_duplicate_title'), get_text('hotkey_settings_duplicate_message') + "\n- " + "\n- ".join(duplicates)); return
            for action_id, new_hotkey_str in self.current_hotkeys.items():
                self.hotkey_changed_signal.emit(action_id, new_hotkey_str)
            self.parent_window.hotkey_manager.save_hotkeys(self.current_hotkeys)
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

class HotkeyCaptureLineEdit(QLineEdit):
    hotkey_captured = Signal(str, str)
    capture_canceled = Signal(str)

    def __init__(self, action_id, parent_dialog):
        super().__init__(parent_dialog)
        self.action_id = action_id
        self.setReadOnly(True)
        self.setText(get_text('hotkey_settings_press_keys_field'))
        self.setStyleSheet("font-style: italic; color: gray;")
        self._pressed_keys_qt = set() # Для хранения кодов Qt.Key + Qt.KeyboardModifier

    def keyPressEvent(self, event: QEvent.KeyPress):
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key_unknown:
            super().keyPressEvent(event)
            return

        # Сохраняем полную комбинацию (клавиша + модификаторы)
        # QKeyCombination хранит это удобно.
        # Но для преобразования в строку для `keyboard` нам нужен свой формат.
        
        current_combination = modifiers | Qt.KeyboardModifier(key) # Объединяем модификаторы и клавишу
        
        # Игнорируем нажатие только модификаторов, если еще не было основной клавиши
        is_only_modifier_press = key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta) and \
                                 not (modifiers & ~ (Qt.KeyboardModifier.ControlModifier |
                                                      Qt.KeyboardModifier.ShiftModifier |
                                                      Qt.KeyboardModifier.AltModifier |
                                                      Qt.KeyboardModifier.MetaModifier)) # Убедимся, что это ТОЛЬКО модификатор
        
        if is_only_modifier_press and not self._pressed_keys_qt:
            self._pressed_keys_qt.add(current_combination) # Сохраняем модификатор как часть комбинации
            self._update_text_from_pressed()
            return

        if key == Qt.Key_Escape:
            if not modifiers: # Чистый Escape отменяет ввод
                logging.debug(f"Hotkey capture canceled by Escape for {self.action_id}")
                self.capture_canceled.emit(self.action_id)
                # Родительский диалог должен закрыться сам, если это был reject()
                if self.parent() and isinstance(self.parent(), QDialog):
                    self.parent().reject()
                return
            # Если Escape с модификаторами, то это может быть валидный хоткей
        
        self._pressed_keys_qt.add(current_combination)
        self._update_text_from_pressed()

    def keyReleaseEvent(self, event: QEvent.KeyRelease):
        if not self._pressed_keys_qt or event.isAutoRepeat():
            super().keyReleaseEvent(event)
            return

        released_key = event.key()
        # Если отпущена не-модификаторная клавиша, или если это последняя отпущенная клавиша
        is_modifier_released = released_key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta)
        
        # Завершаем ввод, если отпущена основная клавиша (не модификатор)
        # или если остался только один элемент в _pressed_keys_qt, который является отпущенной клавишей
        # Это позволяет корректно обрабатывать отпускание последней клавиши, даже если это модификатор.
        should_finalize = not is_modifier_released or \
                          (len(self._pressed_keys_qt) == 1 and (event.modifiers() | Qt.KeyboardModifier(released_key)) in self._pressed_keys_qt)

        if should_finalize:
            final_str = self._convert_pressed_to_keyboard_str()
            logging.info(f"Hotkey captured for {self.action_id}: {final_str} (from Qt pressed: {self._pressed_keys_qt})")
            self.hotkey_captured.emit(self.action_id, final_str)
            self._pressed_keys_qt.clear()
            if self.parent() and isinstance(self.parent(), QDialog):
                self.parent().accept()
        else:
            # Если отпущен модификатор, но еще есть другие нажатые клавиши
            key_to_remove = event.modifiers() | Qt.KeyboardModifier(released_key)
            if key_to_remove in self._pressed_keys_qt:
                self._pressed_keys_qt.remove(key_to_remove)
            self._update_text_from_pressed() # Обновить отображение оставшихся нажатых

        super().keyReleaseEvent(event)

    def _update_text_from_pressed(self):
        current_text = self._convert_pressed_to_keyboard_str()
        self.setText(current_text if current_text else "...")
        self.setStyleSheet("font-style: normal; color: black;")
        
    def _convert_pressed_to_keyboard_str(self) -> str:
        if not self._pressed_keys_qt:
            return get_text('hotkey_none')

        # Извлекаем все уникальные модификаторы и клавиши
        all_modifiers = Qt.KeyboardModifier(0)
        main_keys_codes = [] # Коды основных клавиш (не модификаторов)
        
        for comb in self._pressed_keys_qt:
            key_part = Qt.Key(int(comb) & ~0xFE000000) # Извлекаем код клавиши без модификаторов Qt::KeyboardModifierMask
            mod_part = Qt.KeyboardModifier(int(comb) & 0xFE000000) # Извлекаем только модификаторы
            all_modifiers |= mod_part
            if key_part not in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_unknown, 0):
                if key_part not in main_keys_codes:
                     main_keys_codes.append(key_part)
        
        # Если нажаты только модификаторы, пока не формируем строку
        if not main_keys_codes and all_modifiers:
            # Отображаем только модификаторы, если они есть
            parts = []
            if all_modifiers & Qt.KeyboardModifier.ControlModifier: parts.append("ctrl")
            if all_modifiers & Qt.KeyboardModifier.AltModifier: parts.append("alt")
            if all_modifiers & Qt.KeyboardModifier.ShiftModifier: parts.append("shift")
            if all_modifiers & Qt.KeyboardModifier.MetaModifier: parts.append("win") # "meta" или "win"
            return "+".join(parts) + "+" if parts else "..."


        # Формируем строку для библиотеки `keyboard`
        # Приоритет основной клавиши: последняя нажатая не-модификатор
        main_key_to_convert = main_keys_codes[-1] if main_keys_codes else Qt.Key(0)
        
        parts = []
        if all_modifiers & Qt.KeyboardModifier.ControlModifier: parts.append("ctrl")
        if all_modifiers & Qt.KeyboardModifier.AltModifier: parts.append("alt")
        if all_modifiers & Qt.KeyboardModifier.ShiftModifier: parts.append("shift")
        if all_modifiers & Qt.KeyboardModifier.MetaModifier: parts.append("win")

        if int(main_key_to_convert) != 0:
            key_str = QKeySequence(main_key_to_convert).toString(QKeySequence.PortableText)
            
            # Адаптация для `keyboard`
            if key_str.startswith("Num+") and len(key_str) > 4: key_str = "num " + key_str[4:].lower()
            elif key_str.lower() == "decimal": key_str = "num ."
            elif key_str.lower() == "multiply": key_str = "num *"
            elif key_str.lower() == "add": key_str = "num +"
            elif key_str.lower() == "subtract": key_str = "num -"
            elif key_str.lower() == "divide": key_str = "num /"
            elif key_str.lower() == "escape": key_str = "esc"
            elif key_str.lower() == "print": key_str = "print screen" # или просто "print" в зависимости от keyboard
            elif key_str.lower() == "del": key_str = "delete"
            elif key_str.lower() == "ins": key_str = "insert"
            # ... другие возможные преобразования ...
            else: key_str = key_str.lower()
            
            if key_str: parts.append(key_str)

        return "+".join(parts) if parts else get_text('hotkey_none')


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