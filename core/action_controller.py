# File: core/action_controller.py
import logging
import time
# ИЗМЕНЕНО: QAbstractItemView импортируется из QtWidgets
from PySide6.QtCore import Slot, QMetaObject, Qt # Добавлен QMetaObject, Qt
from PySide6.QtWidgets import QAbstractItemView, QMessageBox, QApplication
from PySide6.QtCore import QPoint
from core import utils # для capture_screen_area
import cv2 # для imwrite
import os # для path.join
from core import utils_gui # для copy_to_clipboard
from info.translations import get_text
# HERO_NAME_ROLE теперь будет доступен через self.mw.right_panel_instance.HERO_NAME_ROLE
# или нужно импортировать его из right_panel, если right_panel_instance может быть None в момент вызова
from core.right_panel import HERO_NAME_ROLE


class ActionController:
    def __init__(self, main_window):
        self.mw = main_window
        logging.info("ActionController initialized.")

    @Slot(str)
    def handle_move_cursor(self, direction):
        # ИЗМЕНЕНО: Логирование на DEBUG
        logging.debug(f"ActionController: handle_move_cursor received direction: {direction}")

        # ROO DEBUG: Дополнительные логи для диагностики проблемы TAB+стрелки
        mw_has_tab_manager = hasattr(self.mw, 'tab_mode_manager')
        logging.debug(f"ROO DEBUG: MainWindow has tab_mode_manager attr: {mw_has_tab_manager}")
        if not mw_has_tab_manager:
            tab_manager = None
        else:
            tab_manager = getattr(self.mw, 'tab_mode_manager')
            logging.debug(f"ROO DEBUG: tab_mode_manager is None: {tab_manager is None}")
            if tab_manager is not None:
                logging.debug(f"ROO DEBUG: tab_manager type: {type(tab_manager)}")
                logging.debug(f"ROO DEBUG: tab_mode_manager._is_active: {getattr(tab_manager, '_is_active', 'NO _is_active attr')}")
                logging.debug(f"ROO DEBUG: hotkey_manager_global.tab_pressed: {getattr(getattr(self.mw, 'hotkey_manager_global', None), 'tab_pressed', 'NO hotkey_manager_global or tab_pressed')}")

        # Проверяем, активен ли режим таба
        is_tab_mode_active = getattr(self.mw, 'tab_mode_manager', None) and self.mw.tab_mode_manager.is_active()
        logging.debug(f"ROO DEBUG: is_tab_mode_active = {is_tab_mode_active}")

        if is_tab_mode_active:
            # ROO DEBUG: Добавлено логирование для проверки _tray_window
            logging.debug("ROO DEBUG: Tab mode active - checking tab_mode_manager._tray_window")
            tab_mgr = getattr(self.mw, 'tab_mode_manager', None)
            if tab_mgr:
                tray_window_exists = hasattr(tab_mgr, '_tray_window')
                logging.debug(f"ROO DEBUG: tab_mode_manager has _tray_window attr: {tray_window_exists}")
                if tray_window_exists:
                    tray_obj = getattr(tab_mgr, '_tray_window', None)
                    logging.debug(f"ROO DEBUG: _tray_window is None: {tray_obj is None}")
                    if tray_obj:
                        logging.debug(f"ROO DEBUG: _tray_window type: {type(tray_obj)}")
                        logging.debug(f"ROO DEBUG: _tray_window.isVisible(): {tray_obj.isVisible()}")
                        logging.debug(f"ROO DEBUG: _tray_window.pos(): {tray_obj.pos()}")

            # ROO DEBUG: Добавлено логирование для проверки self.mw.tray_window
            mw_tray_exists = hasattr(self.mw, 'tray_window')
            logging.debug(f"ROO DEBUG: MainWindow has tray_window attr: {mw_tray_exists}")
            if mw_tray_exists:
                mw_tray_obj = getattr(self.mw, 'tray_window', None)
                logging.debug(f"ROO DEBUG: mw.tray_window is None: {mw_tray_obj is None}")
                if mw_tray_obj:
                    logging.debug("ROO DEBUG: mw.tray_window exists and not None")

            # В режиме таба перемещаем TrayWindow по экрану
            logging.debug("ActionController: Tab mode active - moving TrayWindow")
            self._move_window_in_tab_mode(direction)
            return

        # Обычная логика для режима не-таба
        list_widget = self.mw.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mw.mode == 'min':
            logging.debug(f"Move cursor ignored (list widget: {list_widget is not None}, visible: {list_widget.isVisible() if list_widget else 'N/A'}, mode: {self.mw.mode})")
            return
        count = list_widget.count()
        if count == 0:
            self.mw.hotkey_cursor_index = -1
            if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
                self.mw.ui_updater.update_hotkey_highlight(old_index=self.mw.hotkey_cursor_index)
            return
        
        old_index = self.mw.hotkey_cursor_index
        num_columns = max(1, self.mw._calculate_columns())
        
        if self.mw.hotkey_cursor_index < 0:
            new_index = 0
        else:
            current_row = self.mw.hotkey_cursor_index // num_columns
            current_col = self.mw.hotkey_cursor_index % num_columns
            new_index = self.mw.hotkey_cursor_index

            if direction == 'left':
                if current_col > 0: new_index -= 1
                elif current_row > 0: new_index = (current_row - 1) * num_columns + (num_columns - 1); new_index = min(new_index, count - 1)
                else: new_index = count - 1
            elif direction == 'right':
                if current_col < num_columns - 1 and self.mw.hotkey_cursor_index < count - 1: new_index += 1
                elif self.mw.hotkey_cursor_index < count - 1: new_index = (current_row + 1) * num_columns
                else: new_index = 0
                new_index = min(new_index, count - 1)
            elif direction == 'up':
                new_index -= num_columns
                if new_index < 0:
                    last_row_index = (count - 1) // num_columns
                    potential_index = last_row_index * num_columns + current_col
                    new_index = min(potential_index, count - 1)
            elif direction == 'down':
                new_index += num_columns
                if new_index >= count:
                    potential_index = current_col
                    new_index = min(potential_index, count - 1) 
                    if new_index < 0 and count > 0 : 
                        new_index = 0
                    elif new_index >= count and count > 0 :
                         new_index = 0

            if count > 0 : 
                new_index = max(0, min(count - 1, new_index))
            else:
                new_index = -1

        if count == 0:
            self.mw.hotkey_cursor_index = -1
        elif old_index != new_index:
            self.mw.hotkey_cursor_index = new_index
            if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
                self.mw.ui_updater.update_hotkey_highlight(old_index=old_index)
                logging.debug(f"Cursor moved to index {new_index}")
        elif 0 <= self.mw.hotkey_cursor_index < count:
            current_item = list_widget.item(self.mw.hotkey_cursor_index)
            if current_item:
                list_widget.scrollToItem(current_item, QAbstractItemView.ScrollHint.EnsureVisible)

    def _move_window_in_tab_mode(self, direction):
        """Перемещает TrayWindow на 10 пикселей в указанном направлении."""
        logging.debug(f"ActionController: _move_window_in_tab_mode called with direction: {direction}")

        # Проверим, есть ли tab_mode_manager и _tray_window
        if not hasattr(self.mw, 'tab_mode_manager') or self.mw.tab_mode_manager is None:
            logging.debug("ActionController: tab_mode_manager not found or None - returning")
            return

        tray_window_obj = self.mw.tab_mode_manager._tray_window
        if tray_window_obj is None:
            logging.debug("ActionController: tab_mode_manager._tray_window is None - returning")
            return

        if not tray_window_obj.isVisible():
            logging.debug("ActionController: TrayWindow not visible - returning")
            return

        pos = tray_window_obj.pos()
        original_x, original_y = pos.x(), pos.y()
        logging.debug(f"ActionController: original pos = ({original_x}, {original_y})")

        # Вычисляем новую позицию
        x, y = original_x, original_y
        if direction == 'left':
            x -= 50
        elif direction == 'right':
            x += 50
        elif direction == 'up':
            y -= 50
        elif direction == 'down':
            y += 50
        else:
            logging.debug(f"ActionController: unknown direction: {direction}")
            return

        tray_window_obj.move(x, y)
        logging.debug(f"ActionController: Moved TrayWindow to ({x}, {y})")


    @Slot()
    def handle_toggle_selection(self):
        # ИЗМЕНЕНО: Логирование на DEBUG
        logging.debug("ActionController: handle_toggle_selection triggered")

        # Проверяем, активен ли таб режим
        is_tab_mode_active = getattr(self.mw, 'tab_mode_manager', None) and self.mw.tab_mode_manager.is_active()

        if is_tab_mode_active:
            # В таб режиме выбираем героя в TrayWindow
            logging.debug("ActionController: Tab mode active - selecting current hero in TrayWindow")
            tray_window = self.mw.tab_mode_manager._tray_window
            if tray_window and hasattr(tray_window, 'select_current_hero'):
                tray_window.select_current_hero()
                logging.debug("ActionController: Selected current hero in TrayWindow")
            else:
                logging.debug("ActionController: TrayWindow does not have select_current_hero method")
            return

        # Обычная логика для режима не-таба
        list_widget = self.mw.right_list_widget
        if not list_widget or not list_widget.isVisible() or self.mw.mode == 'min' or \
           self.mw.hotkey_cursor_index < 0 or not self.mw.right_panel_instance:
            logging.warning(f"Toggle selection ignored (list/visibility/mode/index/panel_instance issues)")
            return

        if 0 <= self.mw.hotkey_cursor_index < list_widget.count():
            item = list_widget.item(self.mw.hotkey_cursor_index)
            if item:
                try:
                    is_selected = item.isSelected(); new_state = not is_selected
                    hero_name_data = item.data(HERO_NAME_ROLE)
                    logging.debug(f"Toggling selection for item {self.mw.hotkey_cursor_index} ('{hero_name_data}'). State: {is_selected} -> {new_state}")
                    item.setSelected(new_state)
                except RuntimeError:
                    logging.warning(f"RuntimeError accessing item during toggle selection (index {self.mw.hotkey_cursor_index}). Might be deleting.")
                except Exception as e:
                    logging.error(f"Error toggling selection via hotkey: {e}", exc_info=True)
            else:
                logging.warning(f"Item at index {self.mw.hotkey_cursor_index} is None.")
        else:
            logging.warning(f"Invalid hotkey cursor index: {self.mw.hotkey_cursor_index}")

    @Slot()
    def handle_toggle_mode(self):
        # ИЗМЕНЕНО: Логирование на DEBUG
        logging.debug("ActionController: handle_toggle_mode triggered")
        debounce_time = 0.3
        current_time = time.time()
        
        # Используем QMetaObject.invokeMethod для вызова change_mode в основном потоке GUI
        # Это предотвратит проблемы, если handle_toggle_mode вызывается из другого потока (например, hotkey)
        def _do_toggle():
            logging.debug("ActionController: _do_toggle (for handle_toggle_mode) executing.")
            if hasattr(self.mw, '_last_mode_toggle_time'):
                if current_time - self.mw._last_mode_toggle_time < debounce_time:
                    logging.warning(f"Mode toggle ignored due to debounce ({current_time - self.mw._last_mode_toggle_time:.2f}s < {debounce_time}s)")
                    return
                self.mw._last_mode_toggle_time = current_time
                target_mode = "middle" if self.mw.mode == "min" else "min"
                if hasattr(self.mw, 'change_mode'): 
                    self.mw.change_mode(target_mode)
                else:
                    logging.error("ActionController: MainWindow has no 'change_mode' method.")
            else:
                # Инициализируем, если атрибута нет, и сразу выполняем
                self.mw._last_mode_toggle_time = current_time
                target_mode = "middle" if self.mw.mode == "min" else "min"
                if hasattr(self.mw, 'change_mode'):
                    self.mw.change_mode(target_mode)
                else:
                    logging.error("ActionController: MainWindow has no 'change_mode' method (on first call).")

        QMetaObject.invokeMethod(self.mw, "_do_toggle_mode_slot", Qt.ConnectionType.QueuedConnection)


    @Slot()
    def handle_clear_all(self):
        # ИЗМЕНЕНО: Логирование на DEBUG
        logging.debug("ActionController: handle_clear_all triggered")
        if hasattr(self.mw, 'logic'):
            self.mw.logic.clear_all()
            if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
                self.mw.ui_updater.update_ui_after_logic_change()
            if hasattr(self.mw, '_reset_hotkey_cursor_after_clear'):
                self.mw._reset_hotkey_cursor_after_clear()
        else:
            logging.error("ActionController: MainWindow has no 'logic' attribute.")


    @Slot()
    def handle_debug_capture(self):
        # ИЗМЕНЕНО: Логирование на DEBUG
        logging.debug("ActionController: handle_debug_capture triggered. Capturing screen area...")
        try: 
            screenshot = utils.capture_screen_area(utils.RECOGNITION_AREA)
            if screenshot is not None:
                filename = "debug_screenshot_test.png"
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                filepath = os.path.join(base_dir, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                cv2.imwrite(filepath, screenshot)
                logging.info(f"Debug Capture saved to: {filepath}") # Оставляем INFO, т.к. это действие пользователя
                if self.mw: QMessageBox.information(self.mw, "Debug Screenshot", f"Тестовый скриншот сохранен как:\n{filepath}")
            else:
                logging.warning("Failed to capture screenshot (capture_screen_area returned None).")
                if self.mw: QMessageBox.warning(self.mw, "Debug Screenshot", "Не удалось сделать тестовый скриншот.")
        except Exception as e:
            logging.error(f"Error during debug capture: {e}", exc_info=True)
            if self.mw: QMessageBox.critical(self.mw, "Debug Screenshot Error", f"Ошибка при сохранении скриншота:\n{e}")

    @Slot()
    def handle_copy_team(self):
        # ИЗМЕНЕНО: Логирование на DEBUG
        logging.debug("ActionController: handle_copy_team triggered.")
        if hasattr(self.mw, 'logic'):
            utils_gui.copy_to_clipboard(self.mw.logic)
        else:
            logging.error("ActionController: MainWindow has no 'logic' attribute.")
