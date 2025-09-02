# File: core/ui_updater.py
import logging
import time
from PySide6.QtCore import QTimer, Qt, QMetaObject
from PySide6.QtWidgets import QFrame, QAbstractItemView, QLabel, QMessageBox, QApplication, QHBoxLayout
from PySide6.QtGui import QBrush, QColor

import display
import horizontal_list
from images_load import get_images_for_mode, SIZES
from mode_manager import PANEL_MIN_WIDTHS, MODE_DEFAULT_WINDOW_SIZES
from left_panel import create_left_panel
from right_panel import RightPanel, HERO_NAME_ROLE 
import delegate
from horizontal_list import clear_layout as clear_layout_util 
from info.translations import get_text
from logic import TEAM_SIZE


class UiUpdater:
    def __init__(self, main_window):
        self.mw = main_window
        # Флаги для предотвращения дублирующих обновлений UI
        self._last_updated_mode = None
        self._is_updating_ui = False
        self._last_uilogic_update_time = 0
        # Кэширование результатов последних обновлений
        self._cached_enemy_widgets = {}
        self._cached_counter_widgets = {}

    def update_interface_for_mode(self, new_mode=None):
        if new_mode is None: new_mode = self.mw.mode
        current_mode = new_mode
        t0 = time.perf_counter()
        logging.info(f"--> UiUpdater: update_interface_for_mode for mode '{current_mode}' START")
        if not self.mw:
            logging.error("UiUpdater: MainWindow reference is None!")
            return

        if hasattr(self.mw, 'flags_manager') and self.mw.flags_manager._is_applying_flags_operation:
            logging.warning(f"    UiUpdater: update_interface_for_mode skipped due to _is_applying_flags_operation flag. Mode: {current_mode}")
            return

        # ПРОВЕРКА ДЛЯ ПРЕДТВРАЩЕНИЯ НЕЖЕЛАТЕЛЬНОГО ПЕРЕСОЗДАНИЯ ВИДЖЕТОВ В ТАБ РЕЖИМЕ
        is_tab_mode = self.mw.tab_mode_manager.is_active() if self.mw.tab_mode_manager else False
        if is_tab_mode and hasattr(self, '_tab_widgets_already_created') and self._tab_widgets_already_created:
            logging.info("    UiUpdater: TAB MODE - Skipping widget recreation, only updating visibility")
            # В таб режиме просто обновляем видимость виджетов вместо их пересоздания
            self._update_tab_mode_ui_visibility(current_mode)
            logging.info(f"<-- UiUpdater: Update interface for tab mode '{current_mode}' finished (no recreation) in {(time.perf_counter() - t0)*1000:.2f} ms")
            return

        t_delete_start = time.perf_counter()
        widgets_to_delete = []
        if self.mw.left_panel_widget: widgets_to_delete.append(self.mw.left_panel_widget)
        if self.mw.right_panel_widget: widgets_to_delete.append(self.mw.right_panel_widget)
        
        if self.mw.inner_layout:
            for widget in widgets_to_delete:
                if widget and widget.parent() == self.mw.main_widget : 
                    logging.debug(f"    UiUpdater: Removing and deleting old panel widget: {widget.objectName() if hasattr(widget, 'objectName') else type(widget)}")
                    self.mw.inner_layout.removeWidget(widget)
                    widget.setParent(None) 
                    widget.deleteLater()
                elif widget: 
                    widget.deleteLater()
        
        if widgets_to_delete:
            # УБРАН processEvents() для предотвращения мелькания
            pass


        logging.debug(f"    UiUpdater: Deleting old panel widgets (and processEvents) took {(time.perf_counter() - t_delete_start)*1000:.2f} ms")
        
        self.mw.left_panel_widget = None; self.mw.canvas = None; self.mw.result_frame = None
        self.mw.result_label = None; self.mw.update_scrollregion_callback = lambda: None
        self.mw.right_panel_widget = None; self.mw.right_frame = None
        self.mw.selected_heroes_label = None; self.mw.right_list_widget = None
        # ПОЛНАЯ ОЧИСТКА hero_items для предотвращения дублирования иконок
        self.mw.hero_items.clear()
        logging.info(f"    UiUpdater: Cleared hero_items ({len(self.mw.hero_items)} items remaining)")
        self.mw.right_panel_instance = None

        # ПРИНУДИТЕЛЬНАЯ ОЧИСТКА КЭША ИЗОБРАЖЕНИЙ при смене режима
        import images_load
        images_load.loaded_images.clear()
        images_load.original_images.clear()
        images_load.CV2_HERO_TEMPLATES.clear()
        logging.info("    UiUpdater: Cleared all image caches (QPixmap and CV2)")
        
        t_img_load_start = time.perf_counter()
        img_load_success = True
        
        self.mw.right_images, self.mw.left_images, self.mw.small_images, self.mw.horizontal_images = get_images_for_mode(current_mode)
        if not self.mw.left_images and not self.mw.horizontal_images and current_mode != "min": 
            logging.critical(f"Image loading failed critically for mode {current_mode}. No images returned.")
            QMessageBox.critical(self.mw, "Ошибка", f"Не удалось загрузить основные изображения для режима {current_mode}.")
            img_load_success = False
            
        logging.debug(f"    UiUpdater: Image loading for mode '{current_mode}' took {(time.perf_counter() - t_img_load_start)*1000:.2f} ms. Success: {img_load_success}")
        if not img_load_success: 
            logging.error("<-- UiUpdater: update_interface_for_mode FINISHED (image load error)")
            return

        t_left_panel_start = time.perf_counter()
        if self.mw.main_widget: 
            created_left_widgets = create_left_panel(self.mw.main_widget)
            self.mw.canvas, self.mw.result_frame, self.mw.result_label, self.mw.update_scrollregion_callback = created_left_widgets
            
            parent_widget_lp = self.mw.canvas.parentWidget() if self.mw.canvas else None
            if isinstance(parent_widget_lp, QFrame) and parent_widget_lp.objectName() == "left_frame_container":
                 self.mw.left_panel_widget = parent_widget_lp
            elif self.mw.canvas : 
                 self.mw.left_panel_widget = self.mw.canvas
            else: 
                logging.error("    UiUpdater: Left panel (canvas) could not be created.")
                return 

            if self.mw.left_panel_widget:
                 self.mw.left_panel_widget.setObjectName("left_panel_container_frame") 
                 min_w_left = PANEL_MIN_WIDTHS.get(current_mode, {}).get('left', 200) 
                 self.mw.left_panel_widget.setMinimumWidth(min_w_left if current_mode != "min" else 0)
                 if self.mw.inner_layout: self.mw.inner_layout.addWidget(self.mw.left_panel_widget, stretch=2) 
        else:
            logging.error("    UiUpdater: main_widget is None, cannot create left panel.")
            return
        logging.debug(f"    UiUpdater: Left panel creation took {(time.perf_counter() - t_left_panel_start)*1000:.2f} ms")

        t_right_panel_start = time.perf_counter()
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
                    
                    if hasattr(self.mw, 'handle_selection_changed'):
                        try: self.mw.right_list_widget.itemSelectionChanged.disconnect(self.mw.handle_selection_changed)
                        except RuntimeError: pass 
                        self.mw.right_list_widget.itemSelectionChanged.connect(self.mw.handle_selection_changed)
                    
                    if hasattr(self.mw, 'show_priority_context_menu'):
                        try: self.mw.right_list_widget.customContextMenuRequested.disconnect(self.mw.show_priority_context_menu)
                        except RuntimeError: pass
                        self.mw.right_list_widget.customContextMenuRequested.connect(self.mw.show_priority_context_menu)

                if self.mw.right_panel_widget and self.mw.inner_layout:
                    min_w_right = PANEL_MIN_WIDTHS.get(current_mode, {}).get('right', 150)
                    self.mw.right_panel_widget.setMinimumWidth(min_w_right)
                    self.mw.inner_layout.addWidget(self.mw.right_panel_widget, stretch=1)
            else:
                logging.error("    UiUpdater: Не удалось создать RightPanel instance.")
        logging.debug(f"    UiUpdater: Right panel creation took {(time.perf_counter() - t_right_panel_start)*1000:.2f} ms")
        
        t_height_vis_start = time.perf_counter()
        is_min_mode = (current_mode == "min")
        is_tab_mode = self.mw.tab_mode_manager.is_active() if self.mw.tab_mode_manager else False

        if self.mw.top_panel_instance:
            tp = self.mw.top_panel_instance
            tp.mode_label.setVisible(True)
            tp.min_button.setVisible(True)
            tp.middle_button.setVisible(True)
            tp.max_button.setVisible(True)
            
            tp.version_label.setVisible(not is_min_mode and not is_tab_mode)
            tp.menu_button.setVisible(not is_min_mode and not is_tab_mode) 
            if hasattr(tp, 'close_button_min_mode') and tp.close_button_min_mode:
                 tp.close_button_min_mode.setVisible(is_min_mode and not is_tab_mode)
            tp.update_language() 

        if self.mw.left_panel_widget: self.mw.left_panel_widget.setVisible(not is_min_mode and not is_tab_mode)
        if self.mw.right_panel_widget: self.mw.right_panel_widget.setVisible(not is_min_mode and not is_tab_mode)
        if self.mw.icons_scroll_area: self.mw.icons_scroll_area.show()

        self.mw.tab_mode_manager._set_tab_mode_ui_visible(is_tab_mode)

        self.mw.setMinimumHeight(0); self.mw.setMaximumHeight(16777215) 
        
        top_h = self.mw.top_frame.sizeHint().height() if self.mw.top_frame and self.mw.top_frame.isVisible() else 0
        
        if is_tab_mode:
            icons_h = self.mw.tab_mode_manager._calculate_tab_mode_height()
        else:
            _, h_icon_h = SIZES.get(current_mode, {}).get('horizontal', (35,35)) 
            icons_h = h_icon_h + 12 
        
        if self.mw.icons_scroll_area:
            self.mw.icons_scroll_area.setFixedHeight(icons_h)
        
        if is_min_mode and not is_tab_mode:
            self.mw.setWindowTitle("") 
            spacing = self.mw.main_layout.spacing() if self.mw.main_layout else 0
            calculated_fixed_min_height = top_h + icons_h + (spacing if top_h > 0 and icons_h > 0 else 0) + 5 
            
            self.mw.setMinimumHeight(calculated_fixed_min_height)
            self.mw.setMaximumHeight(calculated_fixed_min_height)
            self.mw.resize(MODE_DEFAULT_WINDOW_SIZES['min']['width'], calculated_fixed_min_height) 
            logging.info(f"    UiUpdater: Min mode. Fixed height: {calculated_fixed_min_height}, Width: {MODE_DEFAULT_WINDOW_SIZES['min']['width']}")
        elif not is_tab_mode: 
            self.mw.setWindowTitle(f"{get_text('title')} v{self.mw.app_version}")
            min_h_val = top_h + icons_h + (200 if current_mode == "middle" else 300) 
            self.mw.setMinimumHeight(min_h_val) 
            
            target_size = MODE_DEFAULT_WINDOW_SIZES.get(current_mode, {'width': 800, 'height': 600})
            target_w, target_h = target_size['width'], target_size['height']
            final_w = max(target_w, self.mw.minimumSizeHint().width())
            final_h = max(target_h, self.mw.minimumHeight())
            self.mw.resize(final_w, final_h)
            logging.info(f"    UiUpdater: Mode '{current_mode}'. Resized to {final_w}x{final_h}")
            
        self.mw.updateGeometry() 
        logging.debug(f"    UiUpdater: Height/Visibility updates took {(time.perf_counter() - t_height_vis_start)*1000:.2f} ms")
        
        logging.info("[TAB MODE] Calling update_ui_after_logic_change")
        self.update_ui_after_logic_change()
        logging.info("[TAB MODE] Finished update_ui_after_logic_change")

        # Обновляем геометрию окна после изменений контента в таб режиме
        if self.mw.tab_mode_manager and self.mw.tab_mode_manager.is_active():
            self.mw.tab_mode_manager._adapt_window_to_content()

        logging.info("[TAB MODE] Window geometry after adaptation: position={}, size={}".format(
            self.mw.pos(), self.mw.size()))
        if self.mw.right_list_widget:
              self.update_list_item_selection_states(force_update=True)

        if hasattr(self.mw, 'flags_manager'):
            self.mw.flags_manager.apply_mouse_invisible_mode(f"ui_update_for_mode_{current_mode}")
        else:
            logging.error("UiUpdater: flags_manager not found in MainWindow.")

        # Устанавливаем флаг, что виджеты созданы для таб режима (чтобы избежать повторного создания)
        if is_tab_mode:
            self._tab_widgets_already_created = True

        logging.info(f"<-- UiUpdater: Update interface for mode '{current_mode}' finished in {(time.perf_counter() - t0)*1000:.2f} ms")


    def update_ui_after_logic_change(self, force_update=False):
        """Оптимизированный update_ui_after_logic_change с предотвращением дублирующих вызовов"""
        current_time = time.perf_counter()

        # Предотвращение слишком частых обновлений (менее 100ms между вызовами)
        if not force_update and (current_time - self._last_uilogic_update_time) < 0.1:
            logging.debug("    UiUpdater: update_ui_after_logic_change SKIPPED - too frequent call")
            return

        # Предотвращение рекурсивных вызовов
        if self._is_updating_ui:
            logging.debug("    UiUpdater: update_ui_after_logic_change SKIPPED - recursive call detected")
            return

        self._is_updating_ui = True
        self._last_uilogic_update_time = current_time

        t_start_logic_update = time.perf_counter()
        logging.info("    UiUpdater: update_ui_after_logic_change START")

        try:
            self._update_selected_label()
            self._update_counterpick_display()
            logging.info("    UiUpdater: Calling _update_horizontal_lists")
            self._update_horizontal_lists()
            logging.info("    UiUpdater: Finished _update_horizontal_lists")
            self.update_list_item_selection_states()
            self._update_priority_labels()
        finally:
            self._is_updating_ui = False

        finish_time = time.perf_counter() - t_start_logic_update
        logging.info(f"    UiUpdater: update_ui_after_logic_change FINISHED in {finish_time*1000:.2f} ms.")

    def _update_selected_label(self):
        label_to_update = self.mw.selected_heroes_label
        if label_to_update and self.mw.right_panel_widget and self.mw.right_panel_widget.isVisible():
             heroes_list_str = ", ".join(self.mw.logic.selected_heroes) if self.mw.logic.selected_heroes else get_text("none_selected_placeholder")
             label_text = get_text("selected_heroes_label_format",
                                   selected_text=get_text("selected_some"), 
                                   count=len(self.mw.logic.selected_heroes), 
                                   max_team_size=TEAM_SIZE, 
                                   heroes_list=heroes_list_str)
             if not self.mw.logic.selected_heroes:
                 label_text = get_text("selected_none", max_team_size=TEAM_SIZE)

             label_to_update.setText(label_text)


    def _update_counterpick_display(self):
        if self.mw.mode == "min": 
            logging.debug("    UiUpdater: Skipping _update_counterpick_display for min mode.")
            return
            
        if not (self.mw.result_frame and self.mw.canvas and self.mw.left_images and self.mw.small_images):
            logging.debug("    UiUpdater: Skipping _update_counterpick_display due to missing elements (result_frame, canvas, or images).")
            return

        display.generate_counterpick_display(self.mw.logic, self.mw.result_frame, self.mw.left_images, self.mw.small_images)
        if self.mw.update_scrollregion_callback:
            self.mw.update_scrollregion_callback()


    def _update_horizontal_lists(self):
        """Оптимизированный _update_horizontal_lists с кэшированием для таб режима"""
        is_tab_mode = self.mw.tab_mode_manager.is_active() if self.mw.tab_mode_manager else False

        if is_tab_mode:
            # Проверка наличия контейнеров
            if not (self.mw.tab_enemies_layout and self.mw.tab_counters_layout):
                return

            # КЭШИРОВАНИЕ: проверяем, не изменились ли данные с последнего обновления
            current_selection = list(self.mw.logic.selected_heroes) if self.mw.logic.selected_heroes else []
            cache_key = f"tab_{len(current_selection)}_{hash(str(current_selection))}"

            if hasattr(self, '_last_tab_update_cache') and self._last_tab_update_cache == cache_key:
                logging.debug("[TAB MODE] Skipping horizontal lists update - data unchanged")
                return

            # Добавляем логирование для отладки
            logging.info(f"[TAB MODE] Updating horizontal lists. Selected heroes: {current_selection}")

            # Очистка и обновление списков с логированием
            clear_layout_util(self.mw.tab_enemies_layout)
            clear_layout_util(self.mw.tab_counters_layout)
            logging.debug("[TAB MODE] Layouts cleared")

            # Вызываем обновление списков с логированием
            enemy_count = horizontal_list.update_enemy_horizontal_list(self.mw, self.mw.tab_enemies_layout)
            counter_count = horizontal_list.update_horizontal_icon_list(self.mw, self.mw.tab_counters_layout)

            # Сохраняем кэш для следующего вызова
            self._last_tab_update_cache = cache_key

            # Логируем результаты
            logging.info(f"[TAB MODE] Count from enemies update: {enemy_count}")
            logging.info(f"[TAB MODE] Count from counters update: {counter_count}")

            # Оптимизированная проверка видимости без детального логирования
            if self.mw.tab_enemies_layout.count() > 0:
                first_item = self.mw.tab_enemies_layout.itemAt(0)
                if first_item and first_item.widget():
                    widget = first_item.widget()
                    if not widget.isVisible():
                        widget.setVisible(True)

            if self.mw.tab_counters_layout.count() > 0:
                first_item = self.mw.tab_counters_layout.itemAt(0)
                if first_item and first_item.widget():
                    widget = first_item.widget()
                    if not widget.isVisible():
                        widget.setVisible(True)
                    if widget.parentWidget():
                        parent_visible = widget.parentWidget().isVisible()
                        if not parent_visible:
                            widget.parentWidget().setVisible(True)
                    else:
                        # Попробуем установить корректного родителя
                        widget.setParent(self.mw.tab_counters_container)
                        widget.setVisible(True)

            # Оптимизированные синхронные вызовы
            self._fix_scroll_area_size_hint()
            self._force_visual_update()

            # Принудительное исправление видимости виджетов (оптимизированное)
            self._fix_tab_widget_visibility()

            # Адаптируем размер окна под новое содержимое
            if self.mw.tab_mode_manager:
                self.mw.tab_mode_manager._adapt_window_to_content()
        else:
            if not (self.mw.counters_layout and self.mw.enemies_layout and self.mw.horizontal_info_label):
                logging.warning("UiUpdater: Пропуск обновления списков обычного режима (нет элементов).")
                return

            if self.mw.horizontal_info_label.parentWidget():
                parent_layout = self.mw.horizontal_info_label.parentWidget().layout()
                if parent_layout:
                    parent_layout.removeWidget(self.mw.horizontal_info_label)
                self.mw.horizontal_info_label.setParent(None)
            self.mw.horizontal_info_label.hide()

            clear_layout_util(self.mw.counters_layout)
            clear_layout_util(self.mw.enemies_layout)

            if not self.mw.logic.selected_heroes:
                self.mw.horizontal_info_label.setText(get_text("select_enemies_for_recommendations"))
                self.mw.counters_layout.addWidget(self.mw.horizontal_info_label)
                self.mw.horizontal_info_label.show()
                self.mw.counters_layout.addStretch(1)
                self.mw.enemies_layout.addStretch(1)
            else:
                horizontal_list.update_horizontal_icon_list(self.mw, self.mw.counters_layout)
                if self.mw.mode == "min":
                    horizontal_list.update_enemy_horizontal_list(self.mw, self.mw.enemies_layout)
                else:
                    self.mw.enemies_layout.addStretch(1)

                has_counters = any(self.mw.counters_layout.itemAt(i).widget() for i in range(self.mw.counters_layout.count()) if self.mw.counters_layout.itemAt(i).widget() is not None)
                if not has_counters:
                    self.mw.horizontal_info_label.setText(get_text("no_recommendations"))
                    self.mw.counters_layout.addWidget(self.mw.horizontal_info_label)
                    self.mw.horizontal_info_label.show()
                    self.mw.counters_layout.addStretch(1)

        if self.mw.icons_scroll_area and self.mw.icons_scroll_content:
            self.mw.icons_scroll_area.updateGeometry()
            self.mw.icons_scroll_content.adjustSize()

    def _log_sizes_after_update(self):
        """Функция для возможных будущих проверок размеров, сейчас silent."""
        pass


    def update_list_item_selection_states(self, force_update=False):
        list_widget = self.mw.right_list_widget; hero_items_dict = self.mw.hero_items
        if not (list_widget and list_widget.isVisible() and hero_items_dict and list_widget.count() == len(hero_items_dict)):
            return
        
        self.mw.is_programmatically_updating_selection = True
        list_widget.blockSignals(True) 
        current_logic_selection = set(self.mw.logic.selected_heroes)
        for hero, item in hero_items_dict.items():
            if item: 
                is_currently_selected_in_widget = item.isSelected()
                should_be_selected_in_logic = (hero in current_logic_selection)
                if is_currently_selected_in_widget != should_be_selected_in_logic or force_update:
                    item.setSelected(should_be_selected_in_logic)
        self._update_selected_label() 
        if list_widget.viewport(): 
             QMetaObject.invokeMethod(list_widget.viewport(), "update", Qt.ConnectionType.QueuedConnection)
        list_widget.blockSignals(False) 
        self.mw.is_programmatically_updating_selection = False


    def _update_priority_labels(self):
        list_widget = self.mw.right_list_widget; hero_items_dict = self.mw.hero_items
        if not (list_widget and list_widget.isVisible() and hero_items_dict): return

        current_theme = "light"
        if hasattr(self.mw, 'appearance_manager'): 
            current_theme = self.mw.appearance_manager.current_theme

        priority_bg_color_hex = "#ffdddd" 
        if current_theme == "dark":
            priority_bg_color_hex = "#603030" 
        
        priority_color = QColor(priority_bg_color_hex)
        default_brush = QBrush(Qt.GlobalColor.transparent) 
        
        focused_index = self.mw.hotkey_cursor_index
        for hero, item in hero_items_dict.items():
             if item: 
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
        list_widget = self.mw.right_list_widget
        if not (list_widget and list_widget.isVisible() and self.mw.mode != 'min' and list_widget.count() > 0):
            return
        
        new_index = self.mw.hotkey_cursor_index
        needs_viewport_update = False
        
        if old_index is not None and old_index != new_index and 0 <= old_index < list_widget.count():
            old_item = list_widget.item(old_index)
            if old_item:
                hero_name_old = old_item.data(HERO_NAME_ROLE) 
                current_tooltip_old = old_item.toolTip()
                if hero_name_old and current_tooltip_old and current_tooltip_old.startswith(">>>"):
                    old_item.setToolTip(hero_name_old)
                needs_viewport_update = True
        
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
              self._update_priority_labels()
              if list_widget.viewport():
                  QMetaObject.invokeMethod(list_widget.viewport(), "update", Qt.ConnectionType.QueuedConnection)

    def _force_visual_update(self):
        """Оптимизированное принудительное обновление визуального дисплея для таб-режима"""
        # УБРАНЫ избыточные update() и repaint() вызовы для отдельных виджетов
        # Оставлен только один финальный repaint() основного окна - достаточно эффективно
        if self.mw:
            self.mw.repaint()

    def _fix_scroll_area_size_hint(self):
        """Исправляет sizeHint ScrollArea после наполнения контентом в таб режиме."""
        if not self.mw.icons_scroll_area or not self.mw.icons_scroll_content:
            return

        try:
            # Упрощенная оптимизация scroll area - только необходимый расчет размеров
            if self.mw.tab_mode_manager and self.mw.tab_mode_manager.is_active():
                container_height = getattr(self.mw, 'container_height_for_tab_mode', 48)
                min_height = max(container_height * 2 + 6, self.mw.icons_scroll_area.minimumHeight())
                new_scroll_size_hint = self.mw.icons_scroll_area.sizeHint()
                min_width = max(new_scroll_size_hint.width(), self.mw.icons_scroll_area.minimumWidth())
                self.mw.icons_scroll_area.setMinimumSize(min_width, min_height)
            # updateGeometry() достаточно для пересчета размеров без избыточных операций
            self.mw.icons_scroll_area.updateGeometry()

        except Exception as e:
            logging.error(f"UiUpdater: Error in _fix_scroll_area_size_hint: {e}")

    def _fix_tab_widget_visibility(self):
        """
        Проверяет и исправляет видимость всех виджетов в таб режиме после полного рендеринга.
        Выполняется через QTimer чтобы дать Qt время завершить все layout updates.
        Добавлено детальное логирование для диагностики проблемы видимости.
        """
        if not (self.mw.tab_mode_manager and self.mw.tab_mode_manager.is_active()):
            return

        try:
            # Исправляем видимость контейнеров без лишнего логирования
            if self.mw.tab_counters_container and not self.mw.tab_counters_container.isVisible():
                self.mw.tab_counters_container.setVisible(True)
                self.mw.tab_counters_container.update()

            if self.mw.tab_enemies_container and not self.mw.tab_enemies_container.isVisible():
                self.mw.tab_enemies_container.setVisible(True)
                self.mw.tab_enemies_container.update()

            # Простой цикл исправления видимости виджетов без детального логирования
            def fix_layout_visibility(layout):
                if not layout:
                    return 0
                fixed_count = 0
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() and not item.widget().isVisible():
                        item.widget().setVisible(True)
                        item.widget().update()
                        fixed_count += 1
                return fixed_count

            counters_fixed = fix_layout_visibility(self.mw.tab_counters_layout)
            enemies_fixed = fix_layout_visibility(self.mw.tab_enemies_layout)

            if counters_fixed > 0 or enemies_fixed > 0:
                logging.info(f"SUMMARY: Fixed visibility for {counters_fixed} counter widgets and {enemies_fixed} enemy widgets")

            # Принудительное обновление scroll area
            if self.mw.icons_scroll_area:
                self.mw.icons_scroll_area.repaint()

        except Exception as e:
            logging.error(f"UiUpdater: Error in _fix_tab_widget_visibility: {e}")

        logging.info("UiUpdater: _fix_tab_widget_visibility completed")

    def _update_tab_mode_ui_visibility(self, current_mode):
        """Обновление только видимости виджетов для таб режима без их пересоздания"""
        logging.info(f"UiUpdater: Optimizing tab mode UI visibility for mode '{current_mode}'")

        # Устанавливаем видимость для таб режима
        is_min_mode = (current_mode == "min")
        is_tab_mode = self.mw.tab_mode_manager.is_active() if self.mw.tab_mode_manager else False

        # Обновляем видимость панелей в зависимости от режима
        if self.mw.left_panel_widget:
            self.mw.left_panel_widget.setVisible(not is_min_mode and not is_tab_mode)
        if self.mw.right_panel_widget:
            self.mw.right_panel_widget.setVisible(not is_min_mode and not is_tab_mode)

        # Устанавливаем видимость таб контейнеров
        if self.mw.tab_enemies_container:
            self.mw.tab_enemies_container.setVisible(is_tab_mode)
        if self.mw.tab_counters_container:
            self.mw.tab_counters_container.setVisible(is_tab_mode)

        # Устанавливаем видимость топ панели
        if self.mw.top_frame:
            self.mw.top_frame.setVisible(not is_tab_mode)

        # Обновляем скролл эрию для таб режима
        if self.mw.icons_scroll_area:
            self.mw.icons_scroll_area.show()

            if is_tab_mode:
                icons_h = self.mw.tab_mode_manager._calculate_tab_mode_height()
                self.mw.icons_scroll_area.setFixedHeight(icons_h)

        # Обновляем геометрию
        if self.mw. icons_scroll_area and self.mw. icons_scroll_content:
            self.mw.icons_scroll_area.updateGeometry()
            self.mw.icons_scroll_content.adjustSize()

        # Принудительное обновление визуального отображения
        if self.mw:
            self.mw.updateGeometry()
            self.mw.update()

        logging.info("UiUpdater: Tab mode UI visibility updated without widget recreation")