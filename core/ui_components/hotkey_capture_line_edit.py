# File: core/ui_components/hotkey_capture_line_edit.py
import logging
from typing import Dict, Any 
from PySide6.QtWidgets import QLineEdit, QApplication, QDialog
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QKeySequence
from info.translations import get_text
from core.hotkey_parser_utils import normalize_string_for_storage


class HotkeyCaptureLineEdit(QLineEdit):
    hotkey_captured = Signal(str, str) 
    capture_canceled = Signal(str)

    def __init__(self, action_id, parent_dialog):
        super().__init__(parent_dialog)
        self.action_id = action_id
        self.setReadOnly(True)
        self.setObjectName("HotkeyCaptureLineEdit")
        self._pressed_modifier_parts = [] 
        self._main_key_capture_info = {}   
        self._reset_internal_capture_state()

    def _reset_field_to_prompt(self):
        self.setText(get_text('hotkey_settings_press_keys'))
        text_color = "gray"
        parent_window_candidate = self
        while parent_window_candidate.parent() is not None:
            parent_window_candidate = parent_window_candidate.parent()
            if hasattr(parent_window_candidate, 'appearance_manager') and \
               hasattr(parent_window_candidate.appearance_manager, 'current_theme'):
                break
        if hasattr(parent_window_candidate, 'appearance_manager') and \
           hasattr(parent_window_candidate.appearance_manager, 'current_theme') and \
           parent_window_candidate.appearance_manager.current_theme == "dark":
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
        pressed_key_qt = event.key()
        event_text = event.text()
        # Фиксируем модификаторы ДО обработки текущего нажатия
        qt_app_mods_before_press_enum = QApplication.keyboardModifiers() 
        
        logging.debug(f"[HCL.keyPress] START - Key: {QKeySequence(pressed_key_qt).toString()}, Text: '{event_text}', QtMods (before): {qt_app_mods_before_press_enum}")
        logging.debug(f"[HCL.keyPress] Before - ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")

        if pressed_key_qt == Qt.Key_Escape and not self._pressed_modifier_parts and not self._main_key_capture_info:
            event.accept(); self.capture_canceled.emit(self.action_id); self._reset_internal_capture_state()
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().reject()
            return

        is_standard_modifier_key_being_pressed = pressed_key_qt in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta)
        
        event.accept() 

        # 1. Обработка основной клавиши
        if not is_standard_modifier_key_being_pressed: # Если нажата НЕ стандартная модификаторная клавиша
            # Эта клавиша становится основной. Это перезапишет Tab, если он был временной основной.
            self._main_key_capture_info = self._get_key_info_for_internal_format(
                pressed_key_qt,
                bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier), # Используем event.modifiers() для Numpad
                event_text
            )
            logging.debug(f"[HCL.keyPress] Main key captured/updated: {self._main_key_capture_info}")
        
        # 2. Обновление списка активных модификаторов (_pressed_modifier_parts)
        # Используем qt_app_mods_before_press_enum, так как они были активны ДО нажатия текущей клавиши,
        # ИЛИ текущую нажатую, если это модификатор
        
        current_active_mods_set = set()
        # Стандартные модификаторы, которые были зажаты *до* или *во время* нажатия текущей клавиши
        if qt_app_mods_before_press_enum & Qt.KeyboardModifier.ControlModifier or pressed_key_qt == Qt.Key_Control: current_active_mods_set.add("ctrl")
        if qt_app_mods_before_press_enum & Qt.KeyboardModifier.AltModifier or pressed_key_qt == Qt.Key_Alt: current_active_mods_set.add("alt")
        if qt_app_mods_before_press_enum & Qt.KeyboardModifier.ShiftModifier or pressed_key_qt == Qt.Key_Shift: current_active_mods_set.add("shift")
        if qt_app_mods_before_press_enum & Qt.KeyboardModifier.MetaModifier or pressed_key_qt == Qt.Key_Meta: current_active_mods_set.add("win")
        
        # Обработка Tab как модификатора
        if pressed_key_qt == Qt.Key_Tab: # Если текущая нажатая клавиша - Tab
            if "tab" not in self._pressed_modifier_parts: # Добавляем его, если еще не было
                self._pressed_modifier_parts.append("tab")
        # Если Tab уже был в _pressed_modifier_parts (нажат ранее), он должен остаться
        # (если только он не был отпущен, что обрабатывается в keyReleaseEvent)
        
        # Собираем _pressed_modifier_parts из current_active_mods_set и отдельно добавленного Tab
        new_pressed_modifier_parts_list = []
        for mod_key_str in ["ctrl", "alt", "shift", "win"]: 
            if mod_key_str in current_active_mods_set:
                new_pressed_modifier_parts_list.append(mod_key_str)
        
        if "tab" in self._pressed_modifier_parts and "tab" not in new_pressed_modifier_parts_list :
             new_pressed_modifier_parts_list.append("tab")
            
        self._pressed_modifier_parts = new_pressed_modifier_parts_list
        
        # Если основная клавиша (main_key_capture_info) оказалась одной из стандартных модификаторов или Tab,
        # это означает, что нажата только эта клавиша-модификатор. В этом случае _main_key_capture_info
        # должно быть пустым, так как это еще не полная комбинация.
        if self._main_key_capture_info:
            main_key_internal = self._main_key_capture_info.get('internal_format_str')
            if main_key_internal in ["ctrl", "alt", "shift", "win", "tab"]:
                # Если Tab - основная клавиша, но есть и другие модификаторы, то Tab - модификатор
                if main_key_internal == "tab" and len(self._pressed_modifier_parts) > 1:
                    self._main_key_capture_info = {} # Сбрасываем main_key, если Tab - часть более сложной комбинации
                elif main_key_internal != "tab": # Ctrl, Alt, Shift, Win не могут быть main_key
                    self._main_key_capture_info = {}


        logging.debug(f"[HCL.keyPress] After logic - ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")
        self._update_display_text_while_capturing()


    def keyReleaseEvent(self, event: QEvent.KeyRelease):
        event.accept()
        if event.isAutoRepeat(): return

        released_key_qt = event.key()
        logging.debug(f"[HCL.keyRelease] START - Released Key: {QKeySequence(released_key_qt).toString()}")
        logging.debug(f"[HCL.keyRelease] Before - ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")
        
        hotkey_completed_this_release = False

        # Если отпущена основная клавиша (которая не является стандартным модификатором И не Tab)
        if self._main_key_capture_info and \
           released_key_qt == self._main_key_capture_info.get('qt_key') and \
           self._main_key_capture_info.get('internal_format_str') not in ["ctrl", "alt", "shift", "win", "tab"]:
            final_hotkey_str = self._generate_internal_format_string()
            logging.info(f"[HCL.keyRelease] Main key (non-mod, non-tab) '{self._main_key_capture_info.get('display_str')}' released. Final: '{final_hotkey_str}'")
            self._emit_or_cancel(final_hotkey_str)
            hotkey_completed_this_release = True
        # Если отпущена клавиша Tab
        elif released_key_qt == Qt.Key_Tab:
            # Tab считается завершающей клавишей, если:
            # 1. Он был основной клавишей (self._main_key_capture_info['internal_format_str'] == 'tab')
            # 2. ИЛИ если Tab был последним отпущенным модификатором, и других основных клавиш нет.
            is_tab_main_key = self._main_key_capture_info and self._main_key_capture_info.get('internal_format_str') == 'tab'
            
            if is_tab_main_key:
                if "tab" in self._pressed_modifier_parts: self._pressed_modifier_parts.remove("tab") # Он был и там, и там
                final_hotkey_str = self._generate_internal_format_string()
                logging.info(f"[HCL.keyRelease] Tab released as main key. Final: '{final_hotkey_str}'")
                self._emit_or_cancel(final_hotkey_str)
                hotkey_completed_this_release = True
            elif "tab" in self._pressed_modifier_parts: # Tab был просто модификатором
                 self._pressed_modifier_parts.remove("tab")
                 logging.debug("[HCL.keyRelease] Tab released as modifier.")
                 # Если это был последний активный модификатор и есть основная клавиша, но она еще не отпущена,
                 # то комбинация еще не завершена. Просто обновляем отображение.
                 if self._main_key_capture_info and not hotkey_completed_this_release:
                     self._update_display_text_while_capturing()


        # Если отпущена стандартная клавиша-модификатор (Ctrl, Alt, Shift, Win)
        elif released_key_qt in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            released_mod_str_map = {Qt.Key_Control: "ctrl", Qt.Key_Shift: "shift", Qt.Key_Alt: "alt", Qt.Key_Meta: "win"}
            released_mod_str = released_mod_str_map.get(released_key_qt)
            if released_mod_str and released_mod_str in self._pressed_modifier_parts:
                self._pressed_modifier_parts.remove(released_mod_str)
                logging.debug(f"[HCL.keyRelease] Standard modifier '{released_mod_str}' released.")
            # Если это был последний активный модификатор и есть основная клавиша, но она еще не отпущена,
            # комбинация не завершена. Обновляем отображение.
            if self._main_key_capture_info and not hotkey_completed_this_release:
                 self._update_display_text_while_capturing()
        

        # Обновление состояния, если хоткей еще не завершен
        if not hotkey_completed_this_release:
            # Проверяем, остались ли какие-либо модификаторы или основная клавиша
            if not self._main_key_capture_info and not self._pressed_modifier_parts and \
               QApplication.keyboardModifiers() == Qt.KeyboardModifier.NoModifier: # Проверяем и реальные модификаторы Qt
                logging.debug("[HCL.keyRelease] No active main key or modifiers left. Resetting state.")
                self._reset_internal_capture_state()
            elif self._main_key_capture_info or self._pressed_modifier_parts : # Если что-то еще активно
                logging.debug(f"[HCL.keyRelease] Hotkey not completed. Updating display. ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")
                self._update_display_text_while_capturing()
            else: # Все отпущено, но не было валидной основной клавиши (например, только модификаторы)
                logging.debug("[HCL.keyRelease] All keys released, but no valid main key was captured. Resetting.")
                self._reset_internal_capture_state()

        else: # hotkey_completed_this_release is True
            logging.debug(f"[HCL.keyRelease] Hotkey completed. State will be reset by _emit_or_cancel.")


    def _emit_or_cancel(self, internal_format_hotkey_str):
        logging.debug(f"[HCL._emit_or_cancel] Attempting for internal_format: '{internal_format_hotkey_str}', action: {self.action_id}")
        normalized_for_storage = normalize_string_for_storage(internal_format_hotkey_str)
        valid_hotkey = False
        if normalized_for_storage:
            if normalized_for_storage.strip() and normalized_for_storage.strip() != "+" and \
               not normalized_for_storage.strip().endswith("+") and \
               not normalized_for_storage.strip().startswith("+"):
                valid_hotkey = True
        if valid_hotkey:
            logging.info(f"[HCL._emit_or_cancel] VALID Hotkey captured for {self.action_id}: '{normalized_for_storage}' (Internal: '{internal_format_hotkey_str}'). Emitting signal.")
            self.hotkey_captured.emit(self.action_id, normalized_for_storage)
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().accept()
        else:
            logging.warning(f"[HCL._emit_or_cancel] INVALID Hotkey capture for '{self.action_id}' (Internal: '{internal_format_hotkey_str}', Normalized: '{normalized_for_storage}'). Canceling input.")
            self.capture_canceled.emit(self.action_id)
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().reject()
        self._reset_internal_capture_state()

    def _update_display_text_while_capturing(self):
        display_parts = []
        display_order_mods = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win", "tab": "Tab"}
        active_display_mods = []
        
        # Собираем модификаторы для отображения
        temp_mods_for_display = self._pressed_modifier_parts[:] # Копия
        
        main_key_display_str = ""
        is_complete_combo = False

        if self._main_key_capture_info and self._main_key_capture_info.get('display_str'):
            main_key_display_str = self._main_key_capture_info['display_str']
            # Если основная клавиша - это Tab, и он уже есть в temp_mods_for_display (как модификатор),
            # то не добавляем его еще раз как основную клавишу в display_parts.
            if main_key_display_str == "Tab" and "tab" in temp_mods_for_display:
                pass # Уже учтен как модификатор
            elif main_key_display_str: # Если это любая другая основная клавиша
                display_parts.append(main_key_display_str)
            is_complete_combo = True

        # Добавляем модификаторы перед основной клавишей (если она есть)
        # или если основной клавиши нет, но есть модификаторы (например, только "Ctrl+Alt")
        for mod_internal, mod_display in display_order_mods.items():
            if mod_internal in temp_mods_for_display:
                 # Если Tab является основной клавишей, он уже будет в display_parts (если не был отфильтрован выше)
                 # Не добавляем его снова из temp_mods_for_display, если он уже там как main_key_display_str
                if not (mod_internal == "tab" and main_key_display_str == "Tab" and "Tab" in display_parts):
                    display_parts.insert(0, mod_display) # Вставляем в начало для порядка Ctrl+Alt+Shift+Key

        # Удаляем дубликаты, если они как-то образовались (особенно для Tab)
        seen_display = set()
        unique_display_parts = [x for x in display_parts if not (x in seen_display or seen_display.add(x))]
        current_display_text = " + ".join(filter(None, unique_display_parts))


        if not current_display_text:
            self._reset_field_to_prompt(); return
        
        text_color = "inherit"; font_style = "normal"
        if not is_complete_combo and current_display_text:
            current_display_text += " + ..."
            font_style = "italic"
            # ... (код для определения text_color в зависимости от темы)
            parent_window_candidate = self
            while parent_window_candidate.parent() is not None:
                parent_window_candidate = parent_window_candidate.parent()
                if hasattr(parent_window_candidate, 'appearance_manager') and \
                   hasattr(parent_window_candidate.appearance_manager, 'current_theme'): break
            if hasattr(parent_window_candidate, 'appearance_manager') and \
               hasattr(parent_window_candidate.appearance_manager, 'current_theme') and \
               parent_window_candidate.appearance_manager.current_theme == "dark":
                text_color = "#888888"
            else: text_color = "gray"

        self.setStyleSheet(f"font-style: {font_style}; color: {text_color};")
        self.setText(current_display_text)


    def _get_key_info_for_internal_format(self, qt_key, is_keypad, event_text) -> Dict[str, Any]:
        internal_str = self._qt_key_to_internal_format_str(qt_key, is_keypad, event_text)
        display_str = self._qt_key_to_display_str(qt_key, is_keypad)
        return {'qt_key': qt_key, 'is_keypad': is_keypad, 'event_text': event_text,
                'internal_format_str': internal_str, 'display_str': display_str}

    def _qt_key_to_internal_format_str(self, qt_key, is_keypad, event_text) -> str:
        if is_keypad:
            if Qt.Key_0 <= qt_key <= Qt.Key_9: return f"num_{qt_key - Qt.Key_0}"
            if qt_key == Qt.Key_Period or qt_key == Qt.Key_Comma: return "num_decimal"
            if qt_key == Qt.Key_Asterisk: return "num_multiply" # <--- Для Numpad *
            if qt_key == Qt.Key_Plus: return "num_add"
            if qt_key == Qt.Key_Minus: return "num_subtract"
            if qt_key == Qt.Key_Slash: return "num_divide"
        qt_to_internal_map = {
            Qt.Key_Tab: "tab", Qt.Key_Return: "enter", Qt.Key_Enter: "enter", 
            Qt.Key_Escape: "esc", Qt.Key_Space: "space", Qt.Key_Backspace: "backspace", 
            Qt.Key_Delete: "delete", Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", 
            Qt.Key_Right: "right", Qt.Key_Home: "home", Qt.Key_End: "end", 
            Qt.Key_PageUp: "page_up", Qt.Key_PageDown: "page_down", Qt.Key_Insert: "insert",
            Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3", Qt.Key_F4: "f4", Qt.Key_F5: "f5",
            Qt.Key_F6: "f6", Qt.Key_F7: "f7", Qt.Key_F8: "f8", Qt.Key_F9: "f9", Qt.Key_F10: "f10",
            Qt.Key_F11: "f11", Qt.Key_F12: "f12", 
            Qt.Key_Slash: "/", Qt.Key_Asterisk: "*", # <--- Для основной *
            Qt.Key_Minus: "-", Qt.Key_Plus: "+", Qt.Key_Period: ".", Qt.Key_Comma: ","}
        if qt_key in qt_to_internal_map: return qt_to_internal_map[qt_key]
        if Qt.Key_0 <= qt_key <= Qt.Key_9: return str(qt_key - Qt.Key_0)
        if Qt.Key_A <= qt_key <= Qt.Key_Z: return chr(qt_key).lower()
        if event_text and len(event_text) == 1 and not event_text.isspace() and not event_text.isalnum(): return event_text.lower()
        portable_text = QKeySequence(qt_key).toString(QKeySequence.PortableText).lower()
        if portable_text and not any(mod in portable_text for mod in ["ctrl", "alt", "shift", "meta", "tab", "windows"]):
            if portable_text == "del": return "delete"
            if portable_text == "ins": return "insert"
            if portable_text == "pgup": return "page_up" 
            if portable_text == "pgdn": return "page_down"
            return portable_text
        logging.warning(f"[HCL] Не удалось преобразовать Qt ключ {qt_key} (text: '{event_text}') во внутренний формат строки.")
        return ""

    def _qt_key_to_display_str(self, qt_key, is_keypad) -> str:
        if is_keypad:
            if Qt.Key_0 <= qt_key <= Qt.Key_9: return f"Num {qt_key - Qt.Key_0}"
            if qt_key == Qt.Key_Period or qt_key == Qt.Key_Comma: return "Num ."
            if qt_key == Qt.Key_Asterisk: return "Num *" # <--- Для Numpad *
            if qt_key == Qt.Key_Plus: return "Num +"
            if qt_key == Qt.Key_Minus: return "Num -"
            if qt_key == Qt.Key_Slash: return "Num /"
        qt_to_display_map = {
            Qt.Key_Tab: "Tab", Qt.Key_Return: "Enter", Qt.Key_Enter: "Enter", 
            Qt.Key_Escape: "Esc", Qt.Key_Space: "Space", Qt.Key_Backspace: "Backspace", 
            Qt.Key_Delete: "Delete", Qt.Key_Up: "Up", Qt.Key_Down: "Down", 
            Qt.Key_Left: "Left", Qt.Key_Right: "Right", Qt.Key_Home: "Home", 
            Qt.Key_End: "End", Qt.Key_PageUp: "PageUp", Qt.Key_PageDown: "PageDown",
            Qt.Key_Insert: "Insert", Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", 
            Qt.Key_F4: "F4", Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", 
            Qt.Key_F8: "F8", Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
        }
        if qt_key in qt_to_display_map: return qt_to_display_map[qt_key]
        native_text = QKeySequence(qt_key).toString(QKeySequence.NativeText)
        if native_text: 
            cleaned_native_text = native_text.replace("Ctrl+", "").replace("Alt+", "").replace("Shift+", "").replace("Meta+", "")
            # Для символов типа '*', '/', '+' и т.д. NativeText может вернуть просто символ
            if cleaned_native_text: return cleaned_native_text
        if Qt.Key_A <= qt_key <= Qt.Key_Z: return chr(qt_key)
        if Qt.Key_0 <= qt_key <= Qt.Key_9: return str(qt_key - Qt.Key_0)
        # Для основной клавиатуры * / + - . ,
        if qt_key == Qt.Key_Asterisk: return "*"
        if qt_key == Qt.Key_Slash: return "/"
        if qt_key == Qt.Key_Plus: return "+"
        if qt_key == Qt.Key_Minus: return "-"
        if qt_key == Qt.Key_Comma: return ","
        if qt_key == Qt.Key_Period: return "."
        logging.warning(f"[HCL] Не удалось получить строку отображения для Qt ключа {qt_key}.")
        return "?"

    def _generate_internal_format_string(self) -> str:
        final_parts = []
        # Модификаторы добавляются в определенном порядке для консистентности
        ordered_mods_for_string = ["ctrl", "alt", "shift", "win", "tab"]
        
        for mod_internal in ordered_mods_for_string:
            if mod_internal in self._pressed_modifier_parts:
                # Особая обработка для Tab: если он является основной клавишей,
                # он не должен дублироваться как модификатор.
                if mod_internal == "tab" and \
                   self._main_key_capture_info and \
                   self._main_key_capture_info.get('internal_format_str') == "tab":
                    continue 
                final_parts.append(mod_internal)
        
        main_key_internal_str = ""
        if self._main_key_capture_info and self._main_key_capture_info.get('internal_format_str'):
            main_key_internal_str = self._main_key_capture_info['internal_format_str']

        # Добавляем основную клавишу, если она есть и еще не была добавлена (актуально для Tab)
        if main_key_internal_str and main_key_internal_str not in final_parts:
            final_parts.append(main_key_internal_str)
        
        result_str = "+".join(filter(None, final_parts))
        logging.debug(f"[HCL._generate_internal_format_string] Generated: '{result_str}' from ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")
        return result_str
