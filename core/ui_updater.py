# File: core/ui_updater.py
import logging
import time
from PySide6.QtCore import QTimer, Qt, QMetaObject
from PySide6.QtWidgets import QFrame, QAbstractItemView, QLabel, QMessageBox
from PySide6.QtGui import QColor, QBrush

import display
import horizontal_list
from images_load import get_images_for_mode, SIZES
from mode_manager import PANEL_MIN_WIDTHS, MODE_DEFAULT_WINDOW_SIZES
from left_panel import create_left_panel
from right_panel import RightPanel, HERO_NAME_ROLE # Импортируем HERO_NAME_ROLE
import delegate
from horizontal_list import clear_layout as clear_layout_util
from core.lang.translations import get_text
from logic import TEAM_SIZE


class UiUpdater:
    def __init__(self, main_window):
        self.mw = main_window

    def update_interface_for_mode(self, new_mode=None):
        if new_mode is None: new_mode = self.mw.mode
        current_mode = new_mode
        t0 = time.time()
        logging.info(f"UiUpdater: Updating interface for mode '{current_mode}'")
        if not self.mw: logging.error("UiUpdater: MainWindow reference is None!"); return

        current_selection_ids = set(self.mw.logic.selected_heroes)
        
        widgets_to_delete = []
        if self.mw.left_panel_widget: widgets_to_delete.append(self.mw.left_panel_widget)
        if self.mw.right_panel_widget: widgets_to_delete.append(self.mw.right_panel_widget)
        
        if self.mw.inner_layout:
            for widget in widgets_to_delete:
                if widget: # Проверка, что виджет не None
                    self.mw.inner_layout.removeWidget(widget)
                    widget.setParent(None)
                    widget.deleteLater()
        
        self.mw.left_panel_widget = None; self.mw.canvas = None; self.mw.result_frame = None
        self.mw.result_label = None; self.mw.update_scrollregion = lambda: None
        self.mw.right_panel_widget = None; self.mw.right_frame = None
        self.mw.selected_heroes_label = None; self.mw.right_list_widget = None
        self.mw.hero_items.clear(); self.mw.right_panel_instance = None
        
        img_load_success = True
        try:
            self.mw.right_images, self.mw.left_images, self.mw.small_images, self.mw.horizontal_images = get_images_for_mode(current_mode)
        except Exception as e:
            logging.critical(f"Image loading error: {e}")
            QMessageBox.critical(self.mw, "Ошибка", f"Не удалось загрузить изображения: {e}")
            img_load_success = False
        if not img_load_success: return

        if self.mw.main_widget: # Убедимся, что main_widget существует
            self.mw.canvas, self.mw.result_frame, self.mw.result_label, self.mw.update_scrollregion = create_left_panel(self.mw.main_widget)
            parent_widget_lp = self.mw.canvas.parentWidget() if self.mw.canvas else None
            if isinstance(parent_widget_lp, QFrame):
                self.mw.left_panel_widget = parent_widget_lp
                self.mw.left_panel_widget.setObjectName("left_panel_container_frame")
            elif self.mw.canvas: # Если parent не QFrame, используем сам canvas
                self.mw.left_panel_widget = self.mw.canvas
            else: # Если canvas не создан
                logging.error("Left panel (canvas) could not be created.")
                return # Не можем продолжать без левой панели

            if self.mw.left_panel_widget:
                 self.mw.left_panel_widget.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('left', 0))
                 if self.mw.inner_layout: self.mw.inner_layout.addWidget(self.mw.left_panel_widget, stretch=1)
        else:
            logging.error("UiUpdater: main_widget is None, cannot create left panel.")
            return


        if current_mode != "min" and self.mw.main_widget:
            self.mw.right_panel_instance = RightPanel(self.mw, current_mode)
            if self.mw.right_panel_instance:
                self.mw.right_panel_widget = self.mw.right_panel_instance.frame
                self.mw.right_frame = self.mw.right_panel_instance.frame
                self.mw.selected_heroes_label = self.mw.right_panel_instance.selected_heroes_label
                self.mw.right_list_widget = self.mw.right_panel_instance.list_widget
                self.mw.hero_items = self.mw.right_panel_instance.hero_items
                if self.mw.right_list_widget:
                    delegate_instance = delegate.HotkeyFocusDelegate(self.mw)
                    self.mw.right_list_widget.setItemDelegate(delegate_instance)
                    # Отсоединяем старые сигналы перед подключением новых, если они есть
                    if hasattr(self.mw.right_list_widget, '_selection_signal_connected'):
                        try: self.mw.right_list_widget.itemSelectionChanged.disconnect(self.mw.handle_selection_changed)
                        except RuntimeError: pass
                    try: self.mw.right_list_widget.itemSelectionChanged.connect(self.mw.handle_selection_changed)
                    except TypeError: pass # Если сигнал уже подключен с тем же слотом
                    self.mw.right_list_widget._selection_signal_connected = True

                    if hasattr(self.mw.right_list_widget, '_context_menu_signal_connected'):
                        try: self.mw.right_list_widget.customContextMenuRequested.disconnect(self.mw.show_priority_context_menu)
                        except RuntimeError: pass
                    try: self.mw.right_list_widget.customContextMenuRequested.connect(self.mw.show_priority_context_menu)
                    except TypeError: pass
                    self.mw.right_list_widget._context_menu_signal_connected = True

                if self.mw.right_panel_widget and self.mw.inner_layout:
                    self.mw.right_panel_widget.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('right', 0))
                    self.mw.inner_layout.addWidget(self.mw.right_panel_widget, stretch=1)
                    if self.mw.left_panel_widget: self.mw.inner_layout.setStretchFactor(self.mw.left_panel_widget, 2)
                    self.mw.inner_layout.setStretchFactor(self.mw.right_panel_widget, 1)
        
        # --- Настройка окна ---
        if self.mw.top_frame and self.mw.main_layout and self.mw.icons_scroll_area :
            top_h = self.mw.top_frame.sizeHint().height()
            horiz_size = SIZES.get(current_mode, {}).get('horizontal', (35,35)); h_icon_h = horiz_size[1]
            icons_h = h_icon_h + 12
            spacing = self.mw.main_layout.spacing()
            base_h = top_h + icons_h + spacing
            self.mw.icons_scroll_area.setFixedHeight(icons_h)
            self.mw.setMinimumHeight(0); self.mw.setMaximumHeight(16777215)
            is_min_mode = (current_mode == "min")
            current_topmost_state = self.mw._is_win_topmost

            target_flags = Qt.WindowType.Window
            if is_min_mode: target_flags |= Qt.WindowType.FramelessWindowHint
            if current_topmost_state: target_flags |= Qt.WindowType.WindowStaysOnTopHint
            
            if self.mw.windowFlags() != target_flags: # Меняем флаги только если они отличаются
                 self.mw.setWindowFlags(target_flags)
                 self.mw.show() # Важно после смены флагов

            self.mw._apply_mouse_invisible_mode()

            version_label_widget = self.mw.top_frame.findChild(QLabel, "version_label")
            close_button_ref = self.mw.close_button
            about_program_button_ref = self.mw.about_program_button
            rating_button_ref = self.mw.rating_button
            menu_button = self.mw.top_panel_instance.menu_button if self.mw.top_panel_instance else None

            # Управление видимостью элементов
            if menu_button: menu_button.setVisible(not is_min_mode and current_mode == "middle")
            if version_label_widget: version_label_widget.setVisible(not is_min_mode)
            if about_program_button_ref: about_program_button_ref.setVisible(not is_min_mode and current_mode == "max")
            if rating_button_ref: rating_button_ref.setVisible(not is_min_mode and current_mode == "max")
            if close_button_ref: close_button_ref.setVisible(is_min_mode)

            if is_min_mode:
                self.mw.setWindowTitle("")
                calculated_fixed_min_height = base_h + 5
                self.mw.setMinimumHeight(calculated_fixed_min_height); self.mw.setMaximumHeight(calculated_fixed_min_height)
                if self.mw.left_panel_widget: self.mw.left_panel_widget.hide()
                if self.mw.icons_scroll_area: self.mw.icons_scroll_area.show()
                if self.mw.enemies_widget: self.mw.enemies_widget.show()
                if self.mw.counters_widget: self.mw.counters_widget.show()
                if self.mw.icons_main_h_layout and self.mw.counters_widget and self.mw.enemies_widget:
                    self.mw.icons_main_h_layout.setStretchFactor(self.mw.counters_widget, 1)
                    self.mw.icons_main_h_layout.setStretchFactor(self.mw.enemies_widget, 0)
            else: # middle или max
                self.mw.setWindowTitle(f"{get_text('title', language=self.mw.logic.DEFAULT_LANGUAGE)} v{self.mw.app_version}")
                if self.mw.left_panel_widget: self.mw.left_panel_widget.show()
                if self.mw.icons_scroll_area: self.mw.icons_scroll_area.show()
                if self.mw.enemies_widget: self.mw.enemies_widget.hide() # Скрываем врагов для middle/max
                if self.mw.counters_widget: self.mw.counters_widget.show()
                if self.mw.icons_main_h_layout and self.mw.counters_widget and self.mw.enemies_widget:
                     self.mw.icons_main_h_layout.setStretchFactor(self.mw.counters_widget, 1)
                     self.mw.icons_main_h_layout.setStretchFactor(self.mw.enemies_widget, 0) # Хотя он и скрыт
                min_h_val = base_h + (200 if current_mode == "middle" else 300)
                self.mw.setMinimumHeight(min_h_val)
            
            self.mw.updateGeometry() # Обновить геометрию после всех изменений
            target_size = MODE_DEFAULT_WINDOW_SIZES.get(current_mode, {'width': 800, 'height': 600})
            target_w, target_h = target_size['width'], target_size['height']
            final_w = max(target_w, self.mw.minimumSizeHint().width())
            final_h = self.mw.minimumHeight() if current_mode == 'min' else max(target_h, self.mw.minimumHeight())
            self.mw.resize(final_w, final_h)
        
        self.update_ui_after_logic_change() # Обновить данные в UI
        if self.mw.right_list_widget: # Восстановить выделение после создания списка
             QTimer.singleShot(50, lambda: self.update_list_item_selection_states(force_update=True))

        logging.info(f"UiUpdater: Update interface for mode '{current_mode}' finished in {time.time() - t0:.4f} s")


    def update_ui_after_logic_change(self):
        logging.info("UiUpdater: Updating UI after logic change."); start_time = time.time()
        self._update_selected_label()
        self._update_counterpick_display()
        self._update_horizontal_lists()
        self.update_list_item_selection_states() # Должен быть вызван до _update_priority_labels
        self._update_priority_labels()
        end_time = time.time(); logging.info(f"UiUpdater: UI Update Finished in {end_time - start_time:.4f} sec.")

    def _update_selected_label(self):
        label_to_update = self.mw.selected_heroes_label
        if label_to_update and self.mw.right_panel_widget and self.mw.right_panel_widget.isVisible():
             # Не используем try-except здесь, предполагаем, что виджет существует, если проверка пройдена
             label_to_update.setText(self.mw.logic.get_selected_heroes_text())

    def _update_counterpick_display(self):
        if self.mw.mode == "min": return
        if not (self.mw.result_frame and self.mw.canvas and self.mw.left_images and self.mw.small_images):
            # Проверка на None перед использованием
            if not self.mw.result_frame: logging.warning("result_frame is None in _update_counterpick_display")
            if not self.mw.canvas: logging.warning("canvas is None in _update_counterpick_display")
            if not self.mw.left_images: logging.warning("left_images is None in _update_counterpick_display")
            if not self.mw.small_images: logging.warning("small_images is None in _update_counterpick_display")
            return

        display.generate_counterpick_display(self.mw.logic, self.mw.result_frame, self.mw.left_images, self.mw.small_images)
        if self.mw.update_scrollregion: # update_scrollregion может быть None
            QTimer.singleShot(0, self.mw.update_scrollregion)
        logging.debug("Counterpick display (left panel) updated.")


    def _update_horizontal_lists(self):
        # ... (без изменений, использует self.mw) ...
        logging.debug("UiUpdater: Updating horizontal lists...")
        if not (self.mw.counters_layout and self.mw.enemies_layout and self.mw.horizontal_info_label):
            logging.error("Horizontal list layouts or info label not initialized for UiUpdater.")
            return

        if self.mw.horizontal_info_label.parentWidget():
            parent_layout = self.mw.horizontal_info_label.parentWidget().layout()
            if parent_layout: parent_layout.removeWidget(self.mw.horizontal_info_label)
            self.mw.horizontal_info_label.setParent(None)
        self.mw.horizontal_info_label.hide()

        clear_layout_util(self.mw.counters_layout)
        clear_layout_util(self.mw.enemies_layout)

        if not self.mw.logic.selected_heroes:
            self.mw.horizontal_info_label.setText(get_text("select_enemies_for_recommendations", language=self.mw.logic.DEFAULT_LANGUAGE))
            self.mw.counters_layout.addWidget(self.mw.horizontal_info_label)
            self.mw.horizontal_info_label.show()
            self.mw.counters_layout.addStretch(1); self.mw.enemies_layout.addStretch(1)
        else:
            horizontal_list.update_horizontal_icon_list(self.mw, self.mw.counters_layout)
            if self.mw.mode == "min":
                horizontal_list.update_enemy_horizontal_list(self.mw, self.mw.enemies_layout)
            else: self.mw.enemies_layout.addStretch(1)
            counters_items_count = sum(1 for i in range(self.mw.counters_layout.count()) if self.mw.counters_layout.itemAt(i).widget())
            if counters_items_count == 0 :
                 self.mw.horizontal_info_label.setText(get_text("no_recommendations", language=self.mw.logic.DEFAULT_LANGUAGE))
                 self.mw.counters_layout.insertWidget(0, self.mw.horizontal_info_label); self.mw.horizontal_info_label.show()
                 if self.mw.counters_layout.count() == 0 or self.mw.counters_layout.itemAt(self.mw.counters_layout.count() - 1).spacerItem() is None:
                     self.mw.counters_layout.addStretch(1)
        if self.mw.icons_scroll_area and self.mw.icons_scroll_content:
            QTimer.singleShot(0, self.mw.icons_scroll_area.updateGeometry)
            QTimer.singleShot(10, self.mw.icons_scroll_content.adjustSize)


    def update_list_item_selection_states(self, force_update=False):
        # ... (логика остается, но использует self.mw для доступа к виджетам и состоянию) ...
        list_widget = self.mw.right_list_widget; hero_items_dict = self.mw.hero_items
        if not (list_widget and list_widget.isVisible() and hero_items_dict and list_widget.count() == len(hero_items_dict)):
            if not list_widget or not list_widget.isVisible() : logging.debug("UiUpdater: Skipping selection state update (no list or not visible)")
            else: logging.warning(f"UiUpdater: Selection state update skipped: mismatch or empty (list:{list_widget.count()} vs dict:{len(hero_items_dict)})")
            return
        
        self.mw.is_programmatically_updating_selection = True
        list_widget.blockSignals(True) # Блокируем сигналы
        current_logic_selection = set(self.mw.logic.selected_heroes)
        for hero, item in hero_items_dict.items():
            if item: # Проверка, что item не None
                is_currently_selected_in_widget = item.isSelected()
                should_be_selected_in_logic = (hero in current_logic_selection)
                if is_currently_selected_in_widget != should_be_selected_in_logic or force_update:
                    item.setSelected(should_be_selected_in_logic)
        self._update_selected_label() # Обновить текст после изменения выделения
        if list_widget.viewport(): # Проверка на None
             QMetaObject.invokeMethod(list_widget.viewport(), "update", Qt.ConnectionType.QueuedConnection)
        list_widget.blockSignals(False) # Разблокируем сигналы
        self.mw.is_programmatically_updating_selection = False


    def _update_priority_labels(self):
        # ... (логика остается, но использует self.mw) ...
        list_widget = self.mw.right_list_widget; hero_items_dict = self.mw.hero_items
        if not (list_widget and list_widget.isVisible() and hero_items_dict): return

        priority_color = QColor("lightcoral"); default_brush = QBrush(Qt.GlobalColor.transparent)
        focused_index = self.mw.hotkey_cursor_index
        for hero, item in hero_items_dict.items():
             if item: # Проверка на None
                 item_index = list_widget.row(item)
                 is_priority = hero in self.mw.logic.priority_heroes
                 is_hotkey_focused = (item_index == focused_index and self.mw.mode != 'min')
                 is_selected = item.isSelected()
                 target_brush = default_brush
                 if is_priority and not is_selected and not is_hotkey_focused:
                     target_brush = QBrush(priority_color)
                 if item.background() != target_brush:
                     item.setBackground(target_brush)

    def update_hotkey_highlight(self, old_index=None):
        # ... (логика остается, но использует self.mw) ...
        list_widget = self.mw.right_list_widget
        if not (list_widget and list_widget.isVisible() and self.mw.mode != 'min' and list_widget.count() > 0):
            return
        
        new_index = self.mw.hotkey_cursor_index
        needs_viewport_update = False
        
        # Снять выделение/тултип со старого элемента
        if old_index is not None and old_index != new_index and 0 <= old_index < list_widget.count():
            old_item = list_widget.item(old_index)
            if old_item:
                hero_name_old = old_item.data(HERO_NAME_ROLE) # Доступ к HERO_NAME_ROLE
                current_tooltip_old = old_item.toolTip()
                if hero_name_old and current_tooltip_old and current_tooltip_old.startswith(">>>"):
                    old_item.setToolTip(hero_name_old)
                needs_viewport_update = True
        
        # Установить выделение/тултип на новый элемент
        if 0 <= new_index < list_widget.count():
            new_item = list_widget.item(new_index)
            if new_item:
                hero_name_new = new_item.data(HERO_NAME_ROLE)
                focus_tooltip = f">>> {hero_name_new} <<<" if hero_name_new else ">>> <<<"
                if new_item.toolTip() != focus_tooltip:
                    new_item.setToolTip(focus_tooltip)
                list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
                needs_viewport_update = True
        
        if needs_viewport_update:
             self._update_priority_labels() # Обновить фон после изменения тултипов/фокуса
             if list_widget.viewport():
                 QMetaObject.invokeMethod(list_widget.viewport(), "update", Qt.ConnectionType.QueuedConnection)
