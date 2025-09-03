import logging
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QHBoxLayout, QScrollArea, QSizePolicy
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QCloseEvent

from core.mode_manager import MODE_DEFAULT_WINDOW_SIZES
from images_load import SIZES

if TYPE_CHECKING:
    from main_window import MainWindow

class TrayWindow(QMainWindow):
    """Отдельное окно для таб-режима с контейнерами врагов и контрпиков."""

    def __init__(self, main_window: 'MainWindow'):
        super().__init__()
        self.main_window = main_window
        self._initialized = False
        self._last_geometry: QRect | None = None
        # Добавляем поддержку выделения для перехода по героям
        self.cursor_index = -1  # Индекс выделенного героя
        self.last_highlighted_item = None  # Последний выделенный виджет

        self._setup_geometry()
        self._create_ui()
        self._setup_window_properties()

    def _setup_geometry(self):
        """Устанавливает геометрию окна на основе сохраненных настроек."""
        if not self.main_window or not hasattr(self.main_window, 'app_settings_manager'):
            return

        screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_geom = screen.availableGeometry()

        # Проверяем сохраненную геометрию
        saved_geometry = None
        try:
            saved_geometry = self.main_window.app_settings_manager.get_tab_window_geometry()
        except Exception as e:
            logging.warning(f"[TrayWindow] Failed to load saved geometry: {e}")

        tab_window_width = int(screen_geom.width() * 0.4)
        tab_window_height = self._calculate_tab_mode_height()

        # Используем сохраненную позицию или рассчитываем новую
        if saved_geometry and saved_geometry.get('x') is not None and saved_geometry.get('y') is not None:
            tab_x = saved_geometry['x']
            tab_y = saved_geometry['y']
            tab_window_width = saved_geometry.get('width', tab_window_width)
            tab_window_height = saved_geometry.get('height', tab_window_height)
        else:
            tab_x = (screen_geom.width() - tab_window_width) // 2
            tab_y = screen_geom.y()

        self.setGeometry(tab_x, tab_y, tab_window_width, tab_window_height)

    def _calculate_tab_mode_height(self) -> int:
        """Рассчитывает высоту окна для таб-режима на основе высоты контейнеров."""
        container_height = getattr(self.main_window, 'container_height_for_tab_mode', 48)

        if hasattr(self.main_window, 'icons_main_layout') and self.main_window.icons_main_layout:
            margins = self.main_window.icons_main_layout.contentsMargins()
            spacing = self.main_window.icons_main_layout.spacing()
            # Height is two containers + spacing between them + top/bottom margins
            total_height = (container_height * 2) + spacing + margins.top() + margins.bottom()
        else:
            total_height = (container_height * 2) + 10

        return max(70, total_height)

    def _create_ui(self):
        """Создает UI для tray window."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Создаем scroll area для enemies с horizontal scroll
        enemies_scroll = QScrollArea()
        enemies_scroll.setWidgetResizable(True)
        enemies_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        enemies_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        enemies_scroll.setMinimumHeight(65)
        enemies_scroll.setMaximumHeight(65)

        # Добавляем таб-контейнер enemies в scroll area
        if hasattr(self.main_window, 'tab_enemies_container') and self.main_window.tab_enemies_container:
            self.main_window.tab_enemies_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.main_window.tab_enemies_container.setMinimumHeight(60)
            self.main_window.tab_enemies_container.setMaximumHeight(60)
            enemies_scroll.setWidget(self.main_window.tab_enemies_container)
            layout.addWidget(enemies_scroll)

        # Создаем scroll area для counters с horizontal scroll
        counters_scroll = QScrollArea()
        counters_scroll.setWidgetResizable(True)
        counters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        counters_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        counters_scroll.setMinimumHeight(65)
        counters_scroll.setMaximumHeight(65)

        # Добавляем таб-контейнер counters в scroll area
        if hasattr(self.main_window, 'tab_counters_container') and self.main_window.tab_counters_container:
            self.main_window.tab_counters_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.main_window.tab_counters_container.setMinimumHeight(60)
            self.main_window.tab_counters_container.setMaximumHeight(60)
            counters_scroll.setWidget(self.main_window.tab_counters_container)
            layout.addWidget(counters_scroll)

    def _setup_window_properties(self):
        """Настраивает свойства окна."""
        self.setWindowTitle("Rivals Counter Peaks - TAB Mode")
        self.setMinimumSize(800, 70)
        self.setMaximumSize(16777215, 16777215)

        # Настраиваем флаги окна для overlay поведения
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)

    def _get_all_hero_widgets(self):
        """Получить все виджеты героев из обоих контейнеров."""
        hero_widgets = []

        # Добавляем виджеты врагов
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_enemies_container'):
            enemies_layout = self.main_window.tab_enemies_container.layout()
            if enemies_layout:
                for i in range(enemies_layout.count()):
                    item = enemies_layout.itemAt(i)
                    if item and item.widget():
                        hero_widgets.append(item.widget())

        # Добавляем виджеты контрпиков
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_counters_container'):
            counters_layout = self.main_window.tab_counters_container.layout()
            if counters_layout:
                for i in range(counters_layout.count()):
                    item = counters_layout.itemAt(i)
                    if item and item.widget():
                        hero_widgets.append(item.widget())

        return hero_widgets

    def _clear_highlight(self):
        """Сбросить выделение предыдущего героя."""
        logging.debug(f"[TrayWindow] _clear_highlight called - last_highlighted_item: {type(self.last_highlighted_item).__name__ if self.last_highlighted_item else None}")

        if self.last_highlighted_item and hasattr(self.last_highlighted_item, 'set_border'):
            # Сбросить рамку к исходному
            logging.debug(f"[TrayWindow] Clearing highlight by setting border to empty for {self.last_highlighted_item.hero_name if hasattr(self.last_highlighted_item, 'hero_name') else 'unknown'}")
            self.last_highlighted_item.set_border("", 0)
        elif self.last_highlighted_item and hasattr(self.last_highlighted_item, 'setStyleSheet'):
            # Fallback for QLabel
            logging.debug(f"[TrayWindow] Clearing highlight via setStyleSheet")
            self.last_highlighted_item.setStyleSheet("")
        self.last_highlighted_item = None

    def _highlight_hero_at_index(self, index):
        """Выделить героя по индексу."""
        logging.debug(f"[TrayWindow] _highlight_hero_at_index called for index {index}")
        self._clear_highlight()

        hero_widgets = self._get_all_hero_widgets()
        logging.debug(f"[TrayWindow] Available hero widgets: {len(hero_widgets)}")

        if 0 <= index < len(hero_widgets):
            widget = hero_widgets[index]
            logging.debug(f"[TrayWindow] Highlighting widget at index {index}: type={type(widget).__name__}, has_set_border={hasattr(widget, 'set_border')}")

            if widget and hasattr(widget, 'set_border'):
                # Добавить рамку для выделения с помощью set_border
                logging.debug(f"[TrayWindow] Setting GREEN border #00FF00 for highlighting")
                widget.set_border("#00FF00", 2)
                self.last_highlighted_item = widget
                self.cursor_index = index
                return True
            elif widget and hasattr(widget, 'setStyleSheet'):
                # Fallback for QLabel, use setStyleSheet
                logging.debug(f"[TrayWindow] Using setStyleSheet fallback for green highlighting")
                widget.setStyleSheet("border: 2px solid #00FF00; border-radius: 5px;")
                self.last_highlighted_item = widget
                self.cursor_index = index
                return True
            else:
                logging.warning(f"[TrayWindow] Widget at index {index} has no border setting method")

        logging.debug(f"[TrayWindow] Could not highlight widget at index {index}")
        return False

    def move_cursor(self, direction):
        """Переместить курсор в указанном направлении."""
        hero_widgets = self._get_all_hero_widgets()
        max_index = len(hero_widgets) - 1

        if max_index < 0:
            return  # Нет героев для переключения

        if self.cursor_index < 0:
            # Первый вызов - выделяем первого героя
            self._highlight_hero_at_index(0)
            return

        new_index = self.cursor_index

        if direction == 'right':
            new_index += 1
            if new_index > max_index:
                new_index = 0
        elif direction == 'left':
            new_index -= 1
            if new_index < 0:
                new_index = max_index
        elif direction == 'up':
            # Для up/down можно переключать между врагами и контрпиками
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_enemies_container'):
                enemies_layout = self.main_window.tab_enemies_container.layout()
                enemies_count = enemies_layout.count() if enemies_layout else 0

                if self.cursor_index < enemies_count and direction == 'down':
                    # Переход к контрпикам
                    new_index = enemies_count
                elif self.cursor_index >= enemies_count and direction == 'up':
                    # Переход к врагам
                    new_index = 0
        elif direction == 'down':
            # Аналогично как для up
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_enemies_container'):
                enemies_layout = self.main_window.tab_enemies_container.layout()
                enemies_count = enemies_layout.count() if enemies_layout else 0

                if self.cursor_index >= enemies_count and direction == 'down':
                    new_index = 0
                elif self.cursor_index < enemies_count and direction == 'up':
                    new_index = enemies_count

        if new_index != self.cursor_index:
            self._highlight_hero_at_index(new_index)

    def select_current_hero(self):
        """Выбрать текущего выделенного героя."""
        if self.cursor_index < 0 or not self.last_highlighted_item:
            logging.debug("TrayWindow: No hero selected - cursor not set")
            return

        # Получить имя героя из tooltip или другого атрибута
        hero_widgets = self._get_all_hero_widgets()
        if 0 <= self.cursor_index < len(hero_widgets):
            widget = hero_widgets[self.cursor_index]
            hero_name = self._get_hero_name_from_widget(widget)

            if hero_name:
                logging.info(f"TrayWindow: Selected hero '{hero_name}' at index {self.cursor_index}")
                # TODO: Передать выбор в логику main_window
                self._notify_hero_selected(hero_name)
            else:
                logging.warning("TrayWindow: Could not get hero name from widget")

    def _get_hero_name_from_widget(self, widget):
        """Получить имя героя из виджета."""
        if hasattr(widget, 'toolTip'):
            tooltip = widget.toolTip()
            if tooltip and '\n' in tooltip:
                # Tooltip обычно содержит "Hero Name\nRating: ..."
                hero_name = tooltip.split('\n')[0].strip()
                return hero_name

        # Альтернативно, проверить атрибут hero_name
        if hasattr(widget, 'hero_name'):
            return widget.hero_name

        return None

    def _notify_hero_selected(self, hero_name):
        """Уведомить main_window о выборе героя."""
        if hasattr(self, 'main_window') and self.main_window:
            # Используем EventBus или сигнал для передачи выбора
            if hasattr(self.main_window, 'logic'):
                self.main_window.logic.toggle_hero_selection(hero_name)
                logging.debug(f"TrayWindow: Toggled selection for '{hero_name}'")

                # Обновить UI
                if hasattr(self.main_window, 'ui_updater'):
                    self.main_window.ui_updater.update_ui_after_logic_change()

    def show_tray(self):
        """Показывает tray окно и обновляет содержимое."""
        logging.info("[TrayWindow] Showing tray window")

        # Гарантируем, что tab_mode активен, чтобы использовать корректные контейнеры
        if hasattr(self.main_window, 'tab_mode_manager') and self.main_window.tab_mode_manager and not self.main_window.tab_mode_manager.is_active():
            logging.info("ROO DEBUG: TrayWindow.show_tray - tab_mode not active, calling enable()")
            self.main_window.tab_mode_manager.enable()

        # Обновляем содержимое перед показом
        self._update_content()

        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()

        self._initialized = True

    def hide_tray(self):
        """Скрывает tray окно и сохраняет геометрию."""
        logging.info("[TrayWindow] Hiding tray window")

        # Сохраняем текущую геометрию
        self._save_geometry()

        self.hide()

    def _update_content(self):
        """Обновляет содержимое контейнеров."""
        logging.info("ROO DEBUG: TrayWindow._update_content called")
        if not self.main_window or not hasattr(self.main_window, 'ui_updater'):
            logging.warning("ROO DEBUG: TrayWindow._update_content - no main_window or ui_updater")
            return

        if hasattr(self, '_skip_content_update') and self._skip_content_update:
            logging.debug("ROO DEBUG: TrayWindow._update_content skipped due to skip flag")
            return

        # Проверяем активен ли таб-режим
        is_tab_active = hasattr(self.main_window, 'tab_mode_manager') and self.main_window.tab_mode_manager and self.main_window.tab_mode_manager.is_active()
        logging.info(f"ROO DEBUG: TrayWindow._update_content - tab_mode_manager.is_active() = {is_tab_active}")

        # РЕШЕНИЕ: Убрать блокировку обновления в таб-режиме, так как обновление должно происходить
        if is_tab_active:
            logging.info("ROO DEBUG: TrayWindow._update_content proceeding even though tab mode is active")

        # Обновляем горизонтальные списки в таб-режиме
        logging.info("ROO DEBUG: TrayWindow calling ui_updater._update_horizontal_lists()")
        self.main_window.ui_updater._update_horizontal_lists()
        logging.info("ROO DEBUG: TrayWindow._update_content completed")

    def _save_geometry(self):
        """Сохраняет текущую геометрию окна."""
        if not self.main_window or not hasattr(self.main_window, 'app_settings_manager'):
            return

        try:
            current_geometry = self.geometry()
            geometry_dict = {
                'x': current_geometry.x(),
                'y': current_geometry.y(),
                'width': current_geometry.width(),
                'height': current_geometry.height()
            }
            self.main_window.app_settings_manager.set_tab_window_geometry(geometry_dict)
            logging.info(f"[TrayWindow] Saved geometry: {geometry_dict}")
        except Exception as e:
            logging.warning(f"[TrayWindow] Failed to save geometry: {e}")

    def closeEvent(self, event: QCloseEvent):
        """Обработка закрытия окна."""
        logging.info("[TrayWindow] Close event received")

        # Сохраняем геометрию перед закрытием
        self._save_geometry()

        # Не блокируем закрытие, позволяем стандартное поведение
        super().closeEvent(event)

    def moveEvent(self, event):
        """Обработка перемещения окна для сохранения позиции."""
        super().moveEvent(event)

        # Обновляем сохраненную геометрию при перемещении
        if self._initialized:
            self._last_geometry = self.geometry()
            self._save_geometry()

    def resizeEvent(self, event):
        """Обработка изменения размера окна."""
        super().resizeEvent(event)

        # Обновляем сохраненную геометрию при изменении размера
        if self._initialized:
            self._last_geometry = self.geometry()
            self._save_geometry()

        # Адаптируем содержимое под новый размер
        if hasattr(self.main_window, 'tab_mode_manager') and self.main_window.tab_mode_manager:
            self.main_window.tab_mode_manager._adapt_window_to_content()