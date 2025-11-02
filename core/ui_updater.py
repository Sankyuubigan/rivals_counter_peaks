# File: core/ui_updater.py
import logging
import time
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QColor, QBrush
# Импортируем `create_left_panel` из правильного модуля `left_panel`.
from core.left_panel import create_left_panel
from core.right_panel import RightPanel, HERO_NAME_ROLE
import core.delegate as delegate
from core.horizontal_list import clear_layout as clear_layout_util
from core.event_bus import event_bus
import core.display as display

class UiUpdater(QObject):
    # Правильно объявляем сигнал как атрибут класса
    ui_updated = Signal()
    
    def __init__(self, main_window):
        super().__init__()  # Важно вызвать конструктор QObject для поддержки сигналов
        self.mw = main_window
        self._is_updating_ui = False
        
    def update_interface_for_mode(self, new_mode=None):
        if new_mode is None: new_mode = self.mw.mode
        logging.info(f"UiUpdater: update_interface_for_mode for mode '{new_mode}'")
        if hasattr(self.mw, 'counter_pick_layout') and self.mw.counter_pick_layout:
            clear_layout_util(self.mw.counter_pick_layout)
        
        self.mw.hero_items.clear()
        images = self.mw.image_manager.get_images(new_mode)
        self.mw.right_images, self.mw.left_images, self.mw.small_images, self.mw.horizontal_images = images
        
        if hasattr(self.mw, 'counter_pick_tab'):
            # Вызываем `create_left_panel` из импортированного модуля.
            left_widgets = create_left_panel(self.mw.counter_pick_tab)
            # `create_left_panel` теперь возвращает 4 элемента, включая callback
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
            # ИСПРАВЛЕНИЕ: НЕ переустанавливаем делегат, так как RoleBorderDelegate уже установлен в RightPanel
            logging.info(f"[UI-Updater] Current delegate: {self.mw.right_list_widget.itemDelegate()}")
            logging.info(f"[UI-Updater] RoleBorderDelegate is preserved, not overriding with HotkeyFocusDelegate")

            # Используем существующий делегат для сигналов
            delegate_instance = self.mw.right_list_widget.itemDelegate()
            if hasattr(delegate_instance, 'mw'):
                delegate_instance.mw = self.mw  # Устанавливаем ссылку на главное окно если нужно
            self.mw.right_list_widget.itemSelectionChanged.connect(self.mw.action_controller.handle_selection_changed)
            self.mw.right_list_widget.customContextMenuRequested.connect(self.mw.action_controller.show_priority_context_menu)
        
        self.update_ui_after_logic_change()

    def update_ui_after_logic_change(self, force_update=False, start_time: float = None):
        if self._is_updating_ui and not force_update: return
        
        self._is_updating_ui = True
        try:
            if start_time:
                delta = time.time() - start_time
                logging.info(f"[TIME-LOG] {delta:.3f}s: UiUpdater started logic update.")

            # ИСПРАВЛЕНИЕ: Если враги не выбраны, используем тир-лист с учетом карты
            if not self.mw.logic.selected_heroes:
                counter_scores = self.mw.logic.calculate_tier_list_scores_with_map(self.mw.logic.selected_map)
                effective_team = []
            else:
                counter_scores = self.mw.logic.calculate_counter_scores()
                effective_team = self.mw.logic.effective_team
                
            self._update_counterpick_display(counter_scores, effective_team)
            self.update_list_item_selection_states()
            self._update_priority_labels()
            self._update_selected_heroes_label()
            
            payload = {
                "selected_heroes": list(self.mw.logic.selected_heroes),
                "counter_scores": counter_scores,
                "effective_team": effective_team,
                "start_time": start_time,
                "selected_map": self.mw.logic.selected_map
            }
            event_bus.emit("logic_updated", payload)
            
            self.ui_updated.emit()
        except Exception as e:
            logging.error(f"Error in update_ui_after_logic_change: {e}")
        finally:
            self._is_updating_ui = False

    def _update_counterpick_display(self, counter_scores, effective_team):
        if hasattr(self.mw, 'result_frame') and self.mw.result_frame:
            display.generate_counterpick_display(
                self.mw.logic, self.mw.result_frame, self.mw.left_images,
                self.mw.small_images, counter_scores, effective_team
            )

    def update_list_item_selection_states(self):
        if not hasattr(self.mw, 'right_list_widget'): return
        
        list_widget = self.mw.right_list_widget
        list_widget.blockSignals(True)
        current_logic_selection = set(self.mw.logic.selected_heroes)
        for hero, item in self.mw.hero_items.items():
            item.setSelected(hero in current_logic_selection)
        list_widget.blockSignals(False)

    def _update_priority_labels(self):
        if not hasattr(self.mw, 'hero_items'): return
        
        priority_color = QColor("#ffdddd") 
        default_brush = QBrush(Qt.GlobalColor.transparent)
        
        for hero, item in self.mw.hero_items.items():
            is_priority = hero in self.mw.logic.priority_heroes
            if not item.isSelected():
                item.setBackground(QBrush(priority_color) if is_priority else default_brush)
            else:
                item.setBackground(default_brush)

    def _update_selected_heroes_label(self):
        if hasattr(self.mw, 'right_panel_instance'):
            self.mw.right_panel_instance.update_language()

    def update_hotkey_highlight(self, old_index=None):
        if not hasattr(self.mw, 'right_list_widget'): return
        
        list_widget = self.mw.right_list_widget
        new_index = self.mw.hotkey_cursor_index
        if old_index is not None and 0 <= old_index < list_widget.count():
            item = list_widget.item(old_index)
            if item: item.setToolTip(item.data(HERO_NAME_ROLE))
        if 0 <= new_index < list_widget.count():
            item = list_widget.item(new_index)
            if item:
                item.setToolTip(f">>> {item.data(HERO_NAME_ROLE)} <<<")
                list_widget.scrollToItem(item)
        
        if list_widget.viewport():
            list_widget.viewport().update()