import logging

from PySide6.QtWidgets import QListWidgetItem

from core.mode import ModeManager
from core.win_api import WinApiManager


class UiUpdateManager:
    def __init__(
        self,
        main_window,
        win_api_manager: WinApiManager,
        mode_manager: ModeManager,
    ):
        self.main_window = main_window
        self.win_api_manager = win_api_manager
        self.mode_manager = mode_manager

    def _update_lists(self):
        self.main_window.left_panel.update_ui()
        self.main_window.right_panel.update_ui()
        self._update_list_item_visuals()  # Обновляем список героев
        self.update_list_item_selection_states()  # Обновляем выделение
        self.update_priority_labels()  # Обновляем приоритеты

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

    def _update_mode_text(self):
        logging.debug("Updating mode button visuals")
        if self.mode_manager.current_mode == "min":
            self.main_window.mode_button.setText("Min")
            self.main_window.mode_button.setStyleSheet("background-color: green;")
        elif self.mode_manager.current_mode == "middle":
            self.main_window.mode_button.setText("Middle")
            self.main_window.mode_button.setStyleSheet("background-color: orange;")
        elif self.mode_manager.current_mode == "max":
            self.main_window.mode_button.setText("Max")
            self.main_window.mode_button.setStyleSheet("background-color: red;")

    def _update_mode_button_visuals(self):
        logging.debug("Updating mode button visuals")
        if self.mode_manager.current_mode == "min":
            self.main_window.mode_button.setText("Min")
            self.main_window.mode_button.setStyleSheet("background-color: green;")
        elif self.mode_manager.current_mode == "middle":
            self.main_window.mode_button.setText("Middle")
            self.main_window.mode_button.setStyleSheet("background-color: orange;")
        elif self.mode_manager.current_mode == "max":
            self.main_window.mode_button.setText("Max")
            self.main_window.mode_button.setStyleSheet("background-color: red;")

    def _update_list_item_visuals(self):
        logging.debug("Updating list item visuals")  # Debug Log

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

    def _update_topmost_text(self):
        logging.debug("Updating topmost text")
        if self.win_api_manager.is_win_topmost:
            self.main_window.topmost_label.setText("Topmost: ON")
        else:
            self.main_window.topmost_label.setText("Topmost: OFF")

    def _update_recognition_text(self):
        logging.debug("Updating recognition text")
        if self.main_window.recognition_state:
            self.main_window.recognition_label.setText("Recognition: ON")
        else:
            self.main_window.recognition_label.setText("Recognition: OFF")

    def _update_heroes_count_text(self):
        logging.debug("Updating heroes count text")
        self.main_window.heroes_count_label.setText(
            f"Heroes count: {self.main_window.hero_list.count()}"
        )

    def update_ui(self):
        self._update_lists()
        self._update_mode_text()
        self._update_topmost_text()
        self._update_recognition_text()
        self._update_heroes_count_text()

    def update_ui_after_logic_change(self):
        self._update_lists()