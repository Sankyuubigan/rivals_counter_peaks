import logging
from PyQt5.QtWidgets import QListWidgetItem
from core.mode import ModeManager
from core.hotkeys import HotkeyManager

class UiUpdateManager:
    def __init__(self, main_window, hotkey_manager: HotkeyManager, mode_manager: ModeManager):
        self.main_window = main_window
        self.hotkey_manager = hotkey_manager
        self.mode_manager = mode_manager

    def update_ui_after_logic_change(self):
        self._update_list_item_visuals()
        self.update_list_item_selection_states()
        self.update_priority_labels()

    def update_list_item_selection_states(self):
        logging.debug("Updating list item selection states")
        for index in range(self.main_window.hero_list.count()):
            item: QListWidgetItem = self.main_window.hero_list.item(index)
            hero_name = item.data(30)

            is_selected = hero_name in self.main_window._selected_heroes

            if is_selected:
                if item.background() != self.main_window.selected_brush:
                    item.setBackground(self.main_window.selected_brush)
            else:
                if item.background() != self.main_window.unselected_brush:
                    item.setBackground(self.main_window.unselected_brush)

    def update_priority_labels(self):
        logging.debug("Updating priority labels")

        for index in range(self.main_window.hero_list.count()):
            item: QListWidgetItem = self.main_window.hero_list.item(index)
            hero_name = item.data(30)

            if hero_name in self.main_window._selected_heroes_with_priority:
                if item.text().endswith(")"):
                    item.setText(item.text()[:-3] + " (" + str(self.main_window._selected_heroes_with_priority[hero_name]) + ")")
                else:
                    item.setText(item.text() + " (" + str(self.main_window._selected_heroes_with_priority[hero_name]) + ")")
            else:
                if item.text().endswith(")"):
                    item.setText(item.text()[:-3])

    def _update_mode_button_visuals(self):
        logging.debug("Updating mode button visuals")
        if self.mode_manager.current_mode == self.mode_manager.MIN_MODE:
            self.main_window.mode_button.setText("Min")
            self.main_window.mode_button.setStyleSheet("background-color: green;")
        elif self.mode_manager.current_mode == self.mode_manager.MIDDLE_MODE:
            self.main_window.mode_button.setText("Middle")
            self.main_window.mode_button.setStyleSheet("background-color: orange;")
        elif self.mode_manager.current_mode == self.mode_manager.MAX_MODE:
            self.main_window.mode_button.setText("Max")
            self.main_window.mode_button.setStyleSheet("background-color: red;")

    def _update_list_item_visuals(self):
        logging.debug("Updating list item visuals")

        self.main_window.hero_list.clear()

        for item_info in self.main_window._all_heroes:
            hero_name = item_info['name']
            is_valid = item_info['is_valid']

            list_item = QListWidgetItem(hero_name)

            list_item.setData(30, hero_name)

            if is_valid:
                list_item.setForeground(self.main_window.valid_hero_text_color)
            else:
                list_item.setForeground(self.main_window.invalid_hero_text_color)

            self.main_window.hero_list.addItem(list_item)

        self.update_list_item_selection_states()
        self.update_priority_labels()