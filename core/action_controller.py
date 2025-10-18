# File: core/action_controller.py
import logging
import time
from PySide6.QtCore import Slot, Qt, QPoint
from PySide6.QtWidgets import QAbstractItemView, QMessageBox, QApplication, QMenu
from core import utils
import cv2
import os
from core import utils_gui
from info.translations import get_text
from core.right_panel import HERO_NAME_ROLE


class ActionController:
    def __init__(self, main_window):
        self.mw = main_window
        logging.info("ActionController initialized.")

    @Slot()
    def handle_selection_changed(self):
        """Обрабатывает изменение выбора героев в QListWidget."""
        if getattr(self.mw, 'is_programmatically_updating_selection', False):
            return
            
        list_widget = getattr(self.mw, 'right_list_widget', None)
        if not list_widget:
            return
            
        selected_items = list_widget.selectedItems()
        current_ui_selection_names = set(item.data(HERO_NAME_ROLE) for item in selected_items if item and item.data(HERO_NAME_ROLE))

        if hasattr(self.mw.logic, 'selected_heroes') and set(self.mw.logic.selected_heroes) != current_ui_selection_names:
            self.mw.logic.set_selection(current_ui_selection_names)
            if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
                self.mw.ui_updater.update_ui_after_logic_change()

    @Slot(QPoint)
    def show_priority_context_menu(self, pos: QPoint):
        """Показывает контекстное меню для установки приоритета героя."""
        list_widget = getattr(self.mw, 'right_list_widget', None)
        if not list_widget or not list_widget.isVisible():
            return
        
        item = list_widget.itemAt(pos)
        if not item:
            return
            
        hero_name = item.data(HERO_NAME_ROLE)
        if not hero_name:
            return

        global_pos = list_widget.viewport().mapToGlobal(pos) if list_widget.viewport() else self.mw.mapToGlobal(pos)
        menu = QMenu(self.mw)
        is_priority = hero_name in self.mw.logic.priority_heroes
        is_selected = item.isSelected()
        action_text_key = 'remove_priority' if is_priority else 'set_priority'
        priority_action = menu.addAction(get_text(action_text_key))
        priority_action.setEnabled(is_selected)
        
        action = menu.exec(global_pos)
        
        if priority_action and action == priority_action:
            if hero_name in self.mw.logic.selected_heroes:
                self.mw.logic.set_priority(hero_name)
                if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
                    self.mw.ui_updater.update_ui_after_logic_change()

    @Slot(str)
    def handle_move_cursor(self, direction):
        logging.debug(f"ActionController: handle_move_cursor received direction: {direction}")

        is_tab_mode_active = getattr(self.mw, 'tab_mode_manager', None) and self.mw.tab_mode_manager.is_active()
        
        if is_tab_mode_active:
            self._move_window_in_tab_mode(direction)
            return

        list_widget = getattr(self.mw, 'right_list_widget', None)
        if not list_widget or not list_widget.isVisible():
            return
        
        count = list_widget.count()
        if count == 0:
            self.mw.hotkey_cursor_index = -1
            return
        
        old_index = self.mw.hotkey_cursor_index
        num_columns = max(1, self.mw.right_panel_instance._calculate_columns() if hasattr(self.mw, 'right_panel_instance') and self.mw.right_panel_instance else 5)
        
        if self.mw.hotkey_cursor_index < 0:
            new_index = 0
        else:
            current_row = self.mw.hotkey_cursor_index // num_columns
            current_col = self.mw.hotkey_cursor_index % num_columns
            new_index = self.mw.hotkey_cursor_index

            if direction == 'left':
                new_index = self.mw.hotkey_cursor_index - 1 if current_col > 0 else (current_row * num_columns) - 1
            elif direction == 'right':
                new_index = self.mw.hotkey_cursor_index + 1 if current_col < num_columns - 1 else (current_row + 1) * num_columns
            elif direction == 'up':
                new_index = self.mw.hotkey_cursor_index - num_columns
            elif direction == 'down':
                new_index = self.mw.hotkey_cursor_index + num_columns

            new_index = max(0, min(count - 1, new_index))

        if old_index != new_index:
            self.mw.hotkey_cursor_index = new_index
            if hasattr(self.mw, 'ui_updater'):
                self.mw.ui_updater.update_hotkey_highlight(old_index=old_index)

    def _move_window_in_tab_mode(self, direction):
        tray_window = getattr(getattr(self.mw, 'tab_mode_manager', None), '_tray_window', None)
        if not tray_window or not tray_window.isVisible():
            return

        pos = tray_window.pos()
        x, y = pos.x(), pos.y()
        step = 50
        if direction == 'left': x -= step
        elif direction == 'right': x += step
        elif direction == 'up': y -= step
        elif direction == 'down': y += step
        
        tray_window.move(x, y)
        logging.debug(f"Moved TrayWindow to ({x}, {y})")

    @Slot()
    def handle_toggle_selection(self):
        is_tab_mode_active = getattr(self.mw, 'tab_mode_manager', None) and self.mw.tab_mode_manager.is_active()

        if is_tab_mode_active:
            tray_window = getattr(getattr(self.mw, 'tab_mode_manager', None), '_tray_window', None)
            if tray_window and hasattr(tray_window, 'select_current_hero'):
                tray_window.select_current_hero()
            return

        list_widget = getattr(self.mw, 'right_list_widget', None)
        if not list_widget or self.mw.hotkey_cursor_index < 0:
            return

        item = list_widget.item(self.mw.hotkey_cursor_index)
        if item:
            item.setSelected(not item.isSelected())

    @Slot()
    def handle_clear_all(self):
        self.mw.logic.clear_all()
        if hasattr(self.mw, 'ui_updater'):
            self.mw.ui_updater.update_ui_after_logic_change()

    @Slot()
    def handle_debug_capture(self):
        try: 
            screenshot = utils.capture_screen_area(utils.RECOGNITION_AREA)
            if screenshot is not None:
                filename = "debug_screenshot.png"
                filepath = os.path.join(os.getcwd(), filename)
                cv2.imwrite(filepath, screenshot)
                QMessageBox.information(self.mw, "Debug Screenshot", f"Скриншот сохранен: {filepath}")
            else:
                QMessageBox.warning(self.mw, "Debug Screenshot", "Не удалось сделать скриншот.")
        except Exception as e:
            QMessageBox.critical(self.mw, "Debug Screenshot Error", f"Ошибка: {e}")

    @Slot()
    def handle_copy_team(self):
        utils_gui.copy_to_clipboard(self.mw.logic)

    @Slot()
    def handle_cycle_map(self):
        """Переключает на следующую карту и инициирует обновление UI."""
        logging.info("ActionController: Handling cycle map request.")
        self.mw.logic.cycle_next_map()
        # Полное обновление UI необходимо, так как все оценки героев изменятся
        if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
            self.mw.ui_updater.update_ui_after_logic_change()