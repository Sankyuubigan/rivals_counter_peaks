# File: core/tab_mode_manager.py
import logging
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QTimer

from mode_manager import MODE_DEFAULT_WINDOW_SIZES
from images_load import SIZES

if TYPE_CHECKING:
    from main_window import MainWindow

class TabModeManager:
    """Управляет входом, выходом и состоянием режима 'Таба'."""
    def __init__(self, main_window: 'MainWindow'):
        self.mw = main_window
        self._is_active = False
        self._geometry_before_tab: QRect | None = None

    def is_active(self) -> bool:
        """Возвращает, активен ли в данный момент режим 'Таба'."""
        return self._is_active

    def enable(self):
        """Включает режим 'Таба'."""
        logging.info("TabModeManager: enable() called.")
        if self._is_active:
            logging.warning("TabModeManager: enable() called, but already active.")
            return

        self._is_active = True
        self._geometry_before_tab = self.mw.geometry()

        screen = QApplication.primaryScreen()
        if not screen:
            logging.error("TabModeManager: Не удалось получить главный экран.")
            return
        screen_geom = screen.availableGeometry()

        # Проверяем сохраненную геометрию и используем её, если она существует
        saved_geometry = None
        if hasattr(self.mw, 'app_settings_manager') and self.mw.app_settings_manager:
            try:
                saved_geometry = self.mw.app_settings_manager.get_tab_window_geometry()
                logging.info(f"[TAB MODE] Loaded saved tab geometry: {saved_geometry}")
            except Exception as e:
                logging.warning(f"[TAB MODE] Failed to load saved geometry: {e}")
                saved_geometry = None

        tab_window_width = int(screen_geom.width() * 0.4)
        tab_window_height = self._calculate_tab_mode_height()

        # Используем сохраненную позицию или рассчитываем новую
        if saved_geometry and saved_geometry.get('x') is not None and saved_geometry.get('y') is not None:
            tab_x = saved_geometry['x']
            tab_y = saved_geometry['y']
            tab_window_width = saved_geometry.get('width', tab_window_width)  # Используем сохраненную ширину, если есть
            tab_window_height = saved_geometry.get('height', tab_window_height)  # Используем сохраненную высоту, если есть
            logging.info(f"[TAB MODE] Using saved position: ({tab_x},{tab_y}), size=({tab_window_width},{tab_window_height})")
        else:
            tab_x = (screen_geom.width() - tab_window_width) // 2
            tab_y = screen_geom.y()
            logging.info("[TAB MODE] Using default centered position")

        # Устанавливаем флаги окна перед показом для уменьшения мелькания
        self.mw._is_win_topmost = True
        if hasattr(self.mw, 'flags_manager'):
            self.mw.flags_manager.apply_mouse_invisible_mode("enable_tab_mode")

        # Устанавливаем геометрию и показываем окно для гладкого перехода
        self.mw.setGeometry(tab_x, tab_y, tab_window_width, tab_window_height)
        self.mw.show()
        logging.info("[TAB MODE] Window geometry set and shown: ({},{}), size=({},{})".format(tab_x, tab_y, tab_window_width, tab_window_height))

        # Откладываем тяжёлые UI обновления для минимизации мелькания
        QTimer.singleShot(100, self._start_ui_updates_async)
        QTimer.singleShot(200, self._finalize_and_process_events)

    def disable(self):
        """Выключает режим 'Таба' и восстанавливает предыдущее состояние."""
        logging.info("TabModeManager: disable() called.")
        if not self._is_active:
            logging.warning("TabModeManager: disable() called, but not active.")
            return

        # Сохраняем текущую геометрию окна таб-режима в настройки перед выходом
        if hasattr(self.mw, 'app_settings_manager') and self.mw.app_settings_manager:
            try:
                current_geometry = self.mw.geometry()
                geometry_dict = {
                    'x': current_geometry.x(),
                    'y': current_geometry.y(),
                    'width': current_geometry.width(),
                    'height': current_geometry.height()
                }
                self.mw.app_settings_manager.set_tab_window_geometry(geometry_dict)
                logging.info(f"[TAB MODE] Saved tab geometry: {geometry_dict}")
            except Exception as e:
                logging.warning(f"[TAB MODE] Failed to save tab geometry: {e}")

        self._is_active = False
        self.mw._is_win_topmost = False

        self.mw.setMinimumSize(300, 70)
        self.mw.setMaximumSize(16777215, 16777215)

        self._set_tab_mode_ui_visible(False)

        previous_mode = self.mw.mode_manager.current_mode if hasattr(self.mw, 'mode_manager') else "middle"

        self.mw.change_mode(previous_mode)

        if self._geometry_before_tab and self._geometry_before_tab.isValid():
            self.mw.setGeometry(self._geometry_before_tab)

        self.mw.show()

    def _set_tab_mode_ui_visible(self, tab_mode_active: bool):
        """Управляет видимостью контейнеров для разных режимов."""
        logging.info(f"TabModeManager: _set_tab_mode_ui_visible(tab_mode_active={tab_mode_active})")

        if self.mw.normal_mode_container:
            self.mw.normal_mode_container.setVisible(not tab_mode_active)

        if self.mw.tab_enemies_container:
            self.mw.tab_enemies_container.setVisible(tab_mode_active)
            self.mw.tab_enemies_container.repaint()  # FIX: Force repaint для корректного визуального обновления

        if self.mw.tab_counters_container:
            self.mw.tab_counters_container.setVisible(tab_mode_active)
            self.mw.tab_counters_container.repaint()  # FIX: Force repaint для корректного визуального обновления

        if self.mw.left_panel_widget:
            self.mw.left_panel_widget.setVisible(not tab_mode_active)

        if self.mw.right_panel_widget:
            self.mw.right_panel_widget.setVisible(not tab_mode_active)

        if self.mw.top_frame:
            self.mw.top_frame.setVisible(not tab_mode_active)

    def _calculate_tab_mode_height(self) -> int:
        """Рассчитывает высоту окна для таб-режима на основе высоты контейнеров."""
        container_height = getattr(self.mw, 'container_height_for_tab_mode', 48) # Default to 48 if not set

        if self.mw.icons_main_layout:
            margins = self.mw.icons_main_layout.contentsMargins()
            spacing = self.mw.icons_main_layout.spacing()
            # Height is two containers + spacing between them + top/bottom margins
            total_height = (container_height * 2) + spacing + margins.top() + margins.bottom()
        else:
            # Fallback calculation
            total_height = (container_height * 2) + 10

        return max(70, total_height)

    def _start_ui_updates_async(self):
        """Запуск тяжелых UI обновлений асинхронно после позиционирования окна"""
        if not self.is_active():
            return

        logging.info("[TAB MODE] Starting UI updates asynchronously")

        # Сначала просто сделать контейнеры видимыми (быстро)
        self._set_tab_mode_ui_visible(True)
        logging.info("[TAB MODE] UI visibility set")

        # Затем запустить тяжелое обновление интерфейса
        if hasattr(self.mw, 'ui_updater') and self.mw.ui_updater:
            logging.info("[TAB MODE] Starting heavy UI update process")
            self.mw.ui_updater.update_interface_for_mode()
            logging.info("[TAB MODE] UI updates completed")

    def _finalize_and_process_events(self):
        """Финализация и обработка всех отложенных событий"""
        if not self.is_active():
            return

        current_pos = self.mw.pos()
        current_size = self.mw.size()
        logging.info(f"[TAB MODE] Final position and size: pos={current_pos}, size={current_size}")

        # Автоматически адаптируем размер окна под содержимое после UI обновлений
        self._adapt_window_to_content()

        # Принудительное обновление без processEvents чтобы избежать визуального мерцания
        self.mw.update()
        # QApplication.processEvents() убран для предотвращения визуального мерцания

        logging.info("[TAB MODE] Tab mode activation completed")

    def _adapt_window_to_content(self):
        """Адаптирует размер окна под текущее содержимое контейнеров в таб режиме"""
        if not self.is_active():
            return

        try:
            content_height = 0

            # Рассчитываем новую высоту на основе текущего содержимого контейнеров
            if self.mw.tab_enemies_container and self.mw.tab_enemies_container.isVisible():
                enemies_size_hint = self.mw.tab_enemies_container.sizeHint()
                content_height += enemies_size_hint.height()

            if self.mw.tab_counters_container and self.mw.tab_counters_container.isVisible():
                counters_size_hint = self.mw.tab_counters_container.sizeHint()
                content_height += counters_size_hint.height()

            # Добавляем отступы и границы
            if self.mw.icons_main_layout:
                margins = self.mw.icons_main_layout.contentsMargins()
                spacing = self.mw.icons_main_layout.spacing()
                content_height += margins.top() + margins.bottom() + spacing

            # Минимальная и максимальная высота
            new_height = max(100, content_height)

            # Получаем информацию об экране для фиксации ширины на 40%
            screen = QApplication.primaryScreen()
            if screen:
                screen_geom = screen.availableGeometry()
                new_width = int(screen_geom.width() * 0.4)
                new_x = max(0, self.mw.geometry().x())  # сохраняем текущую позицию по X, но не меньше 0
                if new_x + new_width > screen_geom.width():
                    new_x = screen_geom.width() - new_width
            else:
                new_width = 1000  # fallback
                new_x = self.mw.geometry().x()

            current_geom = self.mw.geometry()

            # Устанавливаем новый размер с фиксированной шириной 40%, но адаптированной высотой
            self.mw.setGeometry(new_x, current_geom.y(), new_width, new_height)
            logging.info(f"[TAB MODE] Window adapted: pos=({new_x}, {current_geom.y()}), size=({new_width}, {new_height}) - fixed width 40%, adaptive height")

        except Exception as e:
            logging.warning(f"[TAB MODE] Error adapting window to content: {e}")

    def _finalize_window_position(self):
        """Финализация позиции окна после первого рендеринга для устранения задержек"""
        # Этот метод может быть вызван из старого кода, но теперь основная логика в finalize_and_process_events
        if self.is_active():
            QApplication.processEvents()