# File: core/ui_components/hotkey_capture_line_edit.py
import logging
from PySide6.QtWidgets import QLineEdit, QApplication, QDialog
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QKeySequence
from core.lang.translations import get_text


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
            if hasattr(parent_window_candidate, 'appearance_manager'): 
                break
        
        if hasattr(parent_window_candidate, 'appearance_manager') and parent_window_candidate.appearance_manager.current_theme == "dark":
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
        qt_app_mods_enum = QApplication.keyboardModifiers()
        
        logging.debug(f"[HCL.keyPress] START - Key: {QKeySequence(pressed_key_qt).toString()}, Text: '{event_text}', QtMods: {qt_app_mods_enum}")
        logging.debug(f"[HCL.keyPress] Before - ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")

        if pressed_key_qt == Qt.Key_Escape and not self._pressed_modifier_parts and not self._main_key_capture_info:
            event.accept()
            logging.info(f"[HCL.keyPress] Hotkey capture for '{self.action_id}' canceled by Escape.")
            self.capture_canceled.emit(self.action_id)
            self._reset_internal_capture_state()
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().reject()
            return

        if pressed_key_qt == Qt.Key_Tab:
            event.accept() 
            if "tab" not in self._pressed_modifier_parts:
                self._pressed_modifier_parts.append("tab")
            self._update_display_text_while_capturing()
            return 

        event.accept() 
        is_standard_modifier_key = pressed_key_qt in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta)

        if not is_standard_modifier_key and not self._main_key_capture_info: 
            self._main_key_capture_info = {
                'qt_key': pressed_key_qt,
                'is_keypad': bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier),
                'event_text': event_text,
                'pynput_str': self._qt_key_to_pynput_str(pressed_key_qt, 
                                                        bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier), 
                                                        event_text),
                'display_str': self._qt_key_to_display_str(pressed_key_qt, 
                                                           bool(event.modifiers() & Qt.KeyboardModifier.KeypadModifier))
            }
            logging.debug(f"[HCL.keyPress] Main key captured: {self._main_key_capture_info}")
        
        active_mods = set()
        if qt_app_mods_enum & Qt.KeyboardModifier.ControlModifier: active_mods.add("ctrl")
        if qt_app_mods_enum & Qt.KeyboardModifier.AltModifier: active_mods.add("alt")
        if qt_app_mods_enum & Qt.KeyboardModifier.ShiftModifier: active_mods.add("shift")
        if qt_app_mods_enum & Qt.KeyboardModifier.MetaModifier: active_mods.add("win")
        if "tab" in self._pressed_modifier_parts: 
             active_mods.add("tab")
        
        self._pressed_modifier_parts = [] 
        for mod_key_str in ["ctrl", "alt", "shift", "win", "tab"]: 
            if mod_key_str in active_mods:
                self._pressed_modifier_parts.append(mod_key_str)

        logging.debug(f"[HCL.keyPress] After - ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")
        self._update_display_text_while_capturing()


    def keyReleaseEvent(self, event: QEvent.KeyRelease):
        event.accept()
        if event.isAutoRepeat(): return

        released_key_qt = event.key()
        qt_mods_after_release_enum = QApplication.keyboardModifiers()

        logging.debug(f"[HCL.keyRelease] START - Released Key: {QKeySequence(released_key_qt).toString()}, QtMods: {qt_mods_after_release_enum}")
        logging.debug(f"[HCL.keyRelease] Before - ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")
        
        hotkey_completed_this_release = False

        if self._main_key_capture_info and released_key_qt == self._main_key_capture_info.get('qt_key') and released_key_qt != Qt.Key_Tab:
            final_hotkey_str = self._generate_pynput_compatible_string()
            logging.info(f"[HCL.keyRelease] Main key (not Tab) '{self._main_key_capture_info.get('display_str')}' released. Final: '{final_hotkey_str}'")
            self._emit_or_cancel(final_hotkey_str)
            hotkey_completed_this_release = True
        elif released_key_qt == Qt.Key_Tab:
            if (self._main_key_capture_info and self._main_key_capture_info.get('qt_key') == Qt.Key_Tab) or \
               ("tab" in self._pressed_modifier_parts and not self._main_key_capture_info):
                if not self._main_key_capture_info or self._main_key_capture_info.get('pynput_str') != 'tab':
                    self._main_key_capture_info = { 
                        'qt_key': Qt.Key_Tab, 'is_keypad': False, 'event_text': '',
                        'pynput_str': "tab", 'display_str': "Tab"
                    }
                if "tab" in self._pressed_modifier_parts: 
                     self._pressed_modifier_parts.remove("tab")
                
                final_hotkey_str = self._generate_pynput_compatible_string()
                logging.info(f"[HCL.keyRelease] Tab released as main/sole key. Final: '{final_hotkey_str}'")
                self._emit_or_cancel(final_hotkey_str)
                hotkey_completed_this_release = True
            elif "tab" in self._pressed_modifier_parts: 
                 self._pressed_modifier_parts.remove("tab")
                 logging.debug("[HCL.keyRelease] Tab released as modifier (main key still active or no main key yet).")
        
        current_active_mods_set = set()
        if qt_mods_after_release_enum & Qt.KeyboardModifier.ControlModifier: current_active_mods_set.add("ctrl")
        if qt_mods_after_release_enum & Qt.KeyboardModifier.AltModifier: current_active_mods_set.add("alt")
        if qt_mods_after_release_enum & Qt.KeyboardModifier.ShiftModifier: current_active_mods_set.add("shift")
        if qt_mods_after_release_enum & Qt.KeyboardModifier.MetaModifier: current_active_mods_set.add("win")
        
        new_pressed_modifier_parts = []
        for mod_key_str in ["ctrl", "alt", "shift", "win"]: 
            if mod_key_str in current_active_mods_set:
                new_pressed_modifier_parts.append(mod_key_str)
        if "tab" in self._pressed_modifier_parts: 
             if released_key_qt != Qt.Key_Tab: 
                  if "tab" not in new_pressed_modifier_parts: new_pressed_modifier_parts.append("tab") 
        self._pressed_modifier_parts = new_pressed_modifier_parts


        if not hotkey_completed_this_release:
            if not self._main_key_capture_info and not self._pressed_modifier_parts and qt_mods_after_release_enum == Qt.KeyboardModifier.NoModifier:
                logging.debug("[HCL.keyRelease] No active main key or modifiers left. Resetting state.")
                self._reset_internal_capture_state()
            else:
                logging.debug(f"[HCL.keyRelease] Hotkey not completed. Updating display. ModParts: {self._pressed_modifier_parts}, MainKey: {self._main_key_capture_info}")
                self._update_display_text_while_capturing()
        else:
            logging.debug(f"[HCL.keyRelease] Hotkey completed. State will be reset by _emit_or_cancel.")


    def _emit_or_cancel(self, hotkey_str):
        logging.debug(f"[HCL._emit_or_cancel] Attempting to emit/cancel for hotkey_str: '{hotkey_str}', action: {self.action_id}")
        valid_hotkey = False
        if hotkey_str:
            stripped_hotkey = hotkey_str.strip()
            if stripped_hotkey and stripped_hotkey != "+" and not stripped_hotkey.endswith("+") and not stripped_hotkey.startswith("+"):
                valid_hotkey = True

        if valid_hotkey:
            logging.info(f"[HCL._emit_or_cancel] VALID Hotkey captured for {self.action_id}: '{hotkey_str}'. Emitting signal.")
            self.hotkey_captured.emit(self.action_id, hotkey_str)
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().accept()
        else:
            logging.warning(f"[HCL._emit_or_cancel] INVALID Hotkey capture for '{self.action_id}' (string: '{hotkey_str}'). Canceling input.")
            self.capture_canceled.emit(self.action_id)
            if self.parent() and isinstance(self.parent(), QDialog): self.parent().reject()
        self._reset_internal_capture_state()

    def _update_display_text_while_capturing(self):
        ordered_display_mods = []
        standard_mods = ["ctrl", "alt", "shift", "win"]
        has_tab_mod = "tab" in self._pressed_modifier_parts
        
        for mod_key in standard_mods:
            if mod_key in self._pressed_modifier_parts:
                ordered_display_mods.append(mod_key.capitalize())
        
        if has_tab_mod and self._main_key_capture_info and self._main_key_capture_info.get('pynput_str') != 'tab': 
            ordered_display_mods.append("Tab")
        
        display_parts = ordered_display_mods
        is_complete_combo = False

        if self._main_key_capture_info and self._main_key_capture_info.get('display_str'):
            main_key_display = self._main_key_capture_info['display_str']
            if main_key_display == "Tab" and "Tab" in display_parts: 
                 pass 
            else:
                 display_parts.append(main_key_display)
            is_complete_combo = True
        elif "tab" in self._pressed_modifier_parts and not self._main_key_capture_info : 
            if not any(mod.lower() == "tab" for mod in display_parts): 
                display_parts.append("Tab")
            if len(display_parts) == 1 and display_parts[0] == "Tab":
                 is_complete_combo = True


        current_display_text = "+".join(filter(None, display_parts))

        if not current_display_text:
            self._reset_field_to_prompt()
            return

        text_color = "inherit" 
        font_style = "normal"

        if not is_complete_combo and current_display_text:
            current_display_text += " + ..."
            font_style = "italic"
            parent_window_candidate = self
            while parent_window_candidate.parent() is not None:
                parent_window_candidate = parent_window_candidate.parent()
                if hasattr(parent_window_candidate, 'appearance_manager'):
                    break
            
            if hasattr(parent_window_candidate, 'appearance_manager') and parent_window_candidate.appearance_manager.current_theme == "dark":
                text_color = "#888888"
            else: 
                text_color = "gray"

        self.setStyleSheet(f"font-style: {font_style}; color: {text_color};")
        self.setText(current_display_text)

    def _qt_key_to_pynput_str(self, qt_key, is_keypad, event_text) -> str:
        if is_keypad:
            if Qt.Key_0 <= qt_key <= Qt.Key_9: return f"num_{qt_key - Qt.Key_0}"
            # Явно проверяем Qt.Key_Comma для Numpad Decimal
            if qt_key == Qt.Key_Period or qt_key == Qt.Key_Comma: return "num_decimal" 
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
            Qt.Key_Slash: "/", Qt.Key_Asterisk: "*", Qt.Key_Minus: "-", Qt.Key_Plus: "+", 
            Qt.Key_Period: ".", # Основная точка
            Qt.Key_Comma: ","   # Основная запятая
        }
        if qt_key in qt_to_pynput_map: return qt_to_pynput_map[qt_key]

        if Qt.Key_0 <= qt_key <= Qt.Key_9: return str(qt_key - Qt.Key_0)
        if Qt.Key_A <= qt_key <= Qt.Key_Z: return chr(qt_key).lower()
        
        if event_text and len(event_text) == 1 and not event_text.isspace() and not event_text.isalnum():
            return event_text.lower() 
            
        portable_text = QKeySequence(qt_key).toString(QKeySequence.PortableText).lower()
        if portable_text and not any(mod in portable_text for mod in ["ctrl", "alt", "shift", "meta", "tab"]):
            return portable_text
        return ""

    def _qt_key_to_display_str(self, qt_key, is_keypad) -> str:
        if is_keypad:
            if Qt.Key_0 <= qt_key <= Qt.Key_9: return f"Num {qt_key - Qt.Key_0}"
            # Явно проверяем Qt.Key_Comma для Numpad Decimal
            if qt_key == Qt.Key_Period or qt_key == Qt.Key_Comma: return "Num Del" # Или "Num ." по вашему усмотрению
            if qt_key == Qt.Key_Asterisk: return "Num *"
            if qt_key == Qt.Key_Plus: return "Num +"
            if qt_key == Qt.Key_Minus: return "Num -"
            if qt_key == Qt.Key_Slash: return "Num /"
        
        if qt_key == Qt.Key_Tab: return "Tab" 

        native_text = QKeySequence(qt_key).toString(QKeySequence.NativeText)
        if native_text: 
            cleaned_native_text = native_text.replace("Ctrl+", "").replace("Alt+", "").replace("Shift+", "").replace("Meta+", "")
            if cleaned_native_text: return cleaned_native_text
        
        if Qt.Key_A <= qt_key <= Qt.Key_Z: return chr(qt_key)
        if Qt.Key_0 <= qt_key <= Qt.Key_9: return str(qt_key - Qt.Key_0)
        # Если это Qt.Key_Comma, но не is_keypad, то это обычная запятая
        if qt_key == Qt.Key_Comma: return ","
        if qt_key == Qt.Key_Period: return "."
        return "?"


    def _generate_pynput_compatible_string(self) -> str:
        final_parts = []
        standard_mods = ["ctrl", "alt", "shift", "win"]
        has_tab_mod = "tab" in self._pressed_modifier_parts
        
        for mod_part in standard_mods:
            if mod_part in self._pressed_modifier_parts:
                final_parts.append(mod_part)
        
        main_key_pynput_str = ""
        if self._main_key_capture_info and self._main_key_capture_info.get('pynput_str'):
            main_key_pynput_str = self._main_key_capture_info['pynput_str']

        if main_key_pynput_str == "tab":
            if "tab" not in final_parts: 
                 final_parts.append("tab")
        else: 
            if has_tab_mod and "tab" not in final_parts: 
                final_parts.append("tab")
            if main_key_pynput_str and main_key_pynput_str not in final_parts:
                final_parts.append(main_key_pynput_str)
        
        seen = set()
        unique_final_parts = [x for x in final_parts if not (x in seen or seen.add(x))]
        result_str = "+".join(unique_final_parts)
        logging.debug(f"[HCL._generate_pynput_compatible_string] Generated: '{result_str}' from parts: {final_parts} (unique: {unique_final_parts})")
        return result_str
