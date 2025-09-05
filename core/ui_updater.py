# File: core/ui_updater.py
import logging
import time
from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import QAbstractItemView, QFrame
from PySide6.QtGui import QColor, QBrush

import display
from core.image_manager import ImageManager
from left_panel import create_left_panel
from right_panel import RightPanel, HERO_NAME_ROLE
import delegate
from horizontal_list import clear_layout as clear_layout_util
from info.translations import get_text
from logic import TEAM_SIZE
from core.event_bus import event_bus

class UiUpdater:
    def __init__(self, main_window):
        self.mw = main_window
        self._is_updating_ui = False

    def update_interface_for_mode(self, new_mode=None):
        if new_mode is None: new_mode = self.mw.mode
        logging.info(f"--> UiUpdater: update_interface_for_mode for mode '{new_mode}'")

        # Очистка старых панелей
        if hasattr(self.mw, 'counter_pick_layout') and self.mw.counter_pick_layout:
            clear_layout_util(self.mw.counter_pick_layout)
        
        self.mw.left_panel_widget = None
        self.mw.right_panel_widget = None
        self.mw.hero_items.clear()

        # Загрузка изображений (теперь только для одного режима)
        images = self.mw.image_manager.get_images(new_mode)
        self.mw.right_images, self.mw.left_images, self.mw.small_images, self.mw.horizontal_images = images
        
        if hasattr(self.mw, 'counter_pick_tab'):
            # Создание левой панели
            left_widgets = create_left_panel(self.mw.counter_pick_tab)
            self.mw.canvas, self.mw.result_frame, self.mw.result_label, self.mw.update_scrollregion_callback = left_widgets
            self.mw.left_panel_widget = self.mw.canvas.parentWidget()
            self.mw.counter_pick_layout.addWidget(self.mw.left_panel_widget, stretch=2)

            # Создание правой панели
            self.mw.right_panel_instance = RightPanel(self.mw, new_mode)
            self.mw.right_panel_widget = self.mw.right_panel_instance.frame
            self.mw.right_list_widget = self.mw.right_panel_instance.list_widget
            self.mw.hero_items = self.mw.right_panel_instance.hero_items
            self.mw.counter_pick_layout.addWidget(self.mw.right_panel_widget, stretch=1)
            
            # Настройка делегата и сигналов
            delegate_instance = delegate.HotkeyFocusDelegate(self.mw)
            self.mw.right_list_widget.setItemDelegate(delegate_instance)
            self.mw.right_list_widget.itemSelectionChanged.connect(self.mw.action_controller.handle_selection_changed)
            self.mw.right_list_widget.customContextMenuRequested.connect(self.mw.action_controller.show_priority_context_menu)
        
        self.update_ui_after_logic_change()

    def update_ui_after_logic_change(self, force_update=False):
        if self._is_updating_ui and not force_update: return
        
        self._is_updating_ui = True
        try:
            logging.info("[UiUpdater] Starting UI update after logic change.")
            counter_scores = self.mw.logic.calculate_counter_scores() if self.mw.logic.selected_heroes else {}
            effective_team = self.mw.logic.calculate_effective_team(counter_scores) if counter_scores else []

            self._update_counterpick_display(counter_scores, effective_team)
            self.update_list_item_selection_states()
            self._update_priority_labels()
            self._update_selected_heroes_label() # Обновляем текстовую метку
            
            # Отправка события для TrayWindow
            payload = {
                "selected_heroes": list(self.mw.logic.selected_heroes),
                "counter_scores": counter_scores,
                "effective_team": effective_team
            }
            logging.info(f"[UiUpdater] Emitting 'logic_updated' with payload for {len(payload['selected_heroes'])} heroes.")
            event_bus.emit("logic_updated", payload)

        finally:
            self._is_updating_ui = False
            logging.info("[UiUpdater] Finished UI update after logic change.")


    def _update_counterpick_display(self, counter_scores, effective_team):
        if self.mw.result_frame:
            display.generate_counterpick_display(
                self.mw.logic, self.mw.result_frame, self.mw.left_images,
                self.mw.small_images, counter_scores, effective_team
            )

    def update_list_item_selection_states(self):
        if not (hasattr(self.mw, 'right_list_widget') and self.mw.right_list_widget): return
        
        list_widget = self.mw.right_list_widget
        list_widget.blockSignals(True)
        current_logic_selection = set(self.mw.logic.selected_heroes)
        logging.info(f"[UiUpdater] Updating right panel selection. Logic selection: {current_logic_selection}")
        updated_count = 0
        for hero, item in self.mw.hero_items.items():
            should_be_selected = hero in current_logic_selection
            if item.isSelected() != should_be_selected:
                item.setSelected(should_be_selected)
                updated_count += 1
        logging.info(f"[UiUpdater] Right panel selection states updated. {updated_count} items changed.")
        list_widget.blockSignals(False)

    def _update_priority_labels(self):
        if not (hasattr(self.mw, 'right_list_widget') and self.mw.right_list_widget): return
        
        list_widget = self.mw.right_list_widget
        priority_color = QColor("#ffdddd") 
        default_brush = QBrush(Qt.GlobalColor.transparent)
        
        for hero, item in self.mw.hero_items.items():
            is_priority = hero in self.mw.logic.priority_heroes
            item.setBackground(QBrush(priority_color) if is_priority and not item.isSelected() else default_brush)

    def _update_selected_heroes_label(self):
        """Обновляет текстовую метку с перечислением выбранных героев."""
        if hasattr(self.mw, 'right_panel_instance') and self.mw.right_panel_instance:
            label = getattr(self.mw.right_panel_instance, 'selected_heroes_label', None)
            if label:
                text = self.mw.logic.get_selected_heroes_text()
                label.setText(text)
                logging.info(f"[UiUpdater] Selected heroes label updated to: '{text}'")

    def update_hotkey_highlight(self, old_index=None):
        if not (hasattr(self.mw, 'right_list_widget') and self.mw.right_list_widget):
            return
        
        list_widget = self.mw.right_list_widget
        new_index = self.mw.hotkey_cursor_index

        if old_index is not None and 0 <= old_index < list_widget.count():
            list_widget.item(old_index).setToolTip(list_widget.item(old_index).data(HERO_NAME_ROLE))

        if 0 <= new_index < list_widget.count():
            item = list_widget.item(new_index)
            item.setToolTip(f">>> {item.data(HERO_NAME_ROLE)} <<<")
            list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
        
        if list_widget.viewport():
            list_widget.viewport().update()