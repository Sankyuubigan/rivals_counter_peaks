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
        self.mw.mode_positions[self.mw.mode] = self.mw.pos()

        screen = QApplication.primaryScreen()
        if not screen:
            logging.error("TabModeManager: Не удалось получить главный экран.")
            return
        screen_geom = screen.availableGeometry()

        tab_window_width = int(screen_geom.width() * 0.4)
        tab_window_height = self._calculate_tab_mode_height()

        tab_x = (screen_geom.width() - tab_window_width) // 2
        tab_y = screen_geom.y()

        # КРИТИЧНЫЙ ИНСАЙТ: Установить геометрию ОНА НА НЕТРИБИВ от тяжелых UI обновлений
        tab_height = self._calculate_tab_mode_height()

        self.mw._is_win_topmost = True
        if hasattr(self.mw, 'flags_manager'):
            self.mw.flags_manager.apply_mouse_invisible_mode("enable_tab_mode")

        self.mw.setMinimumSize(tab_window_width, tab_height)
        self.mw.setMaximumSize(tab_window_width, tab_height)
        self.mw.setGeometry(tab_x, tab_y, tab_window_width, tab_height)
        logging.info("[TAB MODE] Window geometry set FIRST at: ({},{}), size=({},{})".format(tab_x, tab_y, tab_window_width, tab_height))

        # Моментально показать окно БЕЗ ожидания UI обновлений
        self.mw.show()
        # Убрал QApplication.processEvents() здесь - вызовем позже для смоотх переключения
        logging.info("[TAB MODE] Window shown IMMEDIATELY: {}".format(self.mw.geometry()))

        # Отложим UI обновления чтобы избежать мелькания
        QTimer.singleShot(50, self._start_ui_updates_async)  # Увеличил задержку
        QTimer.singleShot(150, self._finalize_and_process_events)  # Увеличил задержку

    def disable(self):
        """Выключает режим 'Таба' и восстанавливает предыдущее состояние."""
        logging.info("TabModeManager: disable() called.")
        if not self._is_active:
            logging.warning("TabModeManager: disable() called, but not active.")
            return

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

        # Принудительное обновление без processEvents чтобы избежать мелькания
        self.mw.update()
        # QApplication.processEvents() убран для предотвращения визуального мерцания

        logging.info("[TAB MODE] Tab mode activation completed")

    def _finalize_window_position(self):
        """Финализация позиции окна после первого рендеринга для устранения задержек"""
        # Этот метод может быть вызван из старого кода, но теперь основная логика в finalize_and_process_events
        if self.is_active():
            QApplication.processEvents()