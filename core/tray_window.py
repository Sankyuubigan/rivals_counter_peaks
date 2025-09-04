import logging
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QHBoxLayout, QScrollArea, QSizePolicy, QProgressBar
from PySide6.QtCore import QRect, Qt, Signal
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
        # Прогресс бар для распознавания
        self.recognition_progress_bar: QProgressBar | None = None

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

        tab_window_width = self._calculate_tab_mode_width()
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

    def _calculate_tab_mode_width(self) -> int:
        """Рассчитывает ширину окна для таб-режима на основе количества контрпиков."""
        try:
            if self.main_window and hasattr(self.main_window, 'logic') and self.main_window.logic.selected_heroes:
                counter_scores = self.main_window.logic.calculate_counter_scores()
                counter_heroes_count = len([h for h in counter_scores if counter_scores.get(h, 0) >= 1.0])
                icon_width = 40  # approximate icon width
                spacing = 4   # spacing between icons
                margins = 20  # total margins (approximate)
                calculated_width = max(800, icon_width * min(counter_heroes_count, 25) + (min(counter_heroes_count, 25) - 1) * spacing + margins)
                optimal_width = min(calculated_width, 1200)  # max 1200px
                logging.debug(f"[TrayWindow] Calculated adaptive width: {optimal_width} (counters: {counter_heroes_count})")
                return optimal_width
        except Exception as e:
            logging.warning(f"[TrayWindow] Failed to calculate dynamic width: {e}")

        # Fallback to default 40%
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.availableGeometry()
            return int(screen_geom.width() * 0.4)
        return 1000

    def _calculate_tab_mode_height(self) -> int:
        """Рассчитывает высоту окна для таб-режима на основе реального контента контейнеров."""
        # Высота прогресс бара
        progress_bar_height = 8 if self.recognition_progress_bar else 0

        # Рассчитываем высоту на основе реального содержимого
        containers_height = 0
        spacing_between_containers = 10  # spacing между контейнерами
        margins_top_bottom = 5 * 2  # margins (5,5,5,5) top + bottom = 10
        progress_spacing = 5  # spacing для progress бара

        # Фиксированная высота контейнеров вместо sizeHint()
        container_fixed_height = 48  # на основе icon_height + 8 как в main_window.py

        # Получаем высоту tab_enemies_layout - используем фиксированную
        if hasattr(self.main_window, 'tab_enemies_layout') and self.main_window.tab_enemies_layout:
            containers_height += container_fixed_height
            logging.debug(f"[TrayWindow] Using fixed height {container_fixed_height} for enemies layout")

        # Получаем высоту tab_counters_layout - используем фиксированную
        if hasattr(self.main_window, 'tab_counters_layout') and self.main_window.tab_counters_layout:
            containers_height += container_fixed_height
            logging.debug(f"[TrayWindow] Using fixed height {container_fixed_height} for counters layout")

        # Добавляем spacing между layout'ами, если оба существуют
        if (hasattr(self.main_window, 'tab_enemies_layout') and self.main_window.tab_enemies_layout and
            hasattr(self.main_window, 'tab_counters_layout') and self.main_window.tab_counters_layout):
            containers_height += spacing_between_containers

        # Добавляем прогресс бар (только если layout enemies существует) с spacing
        if hasattr(self.main_window, 'tab_enemies_layout') and self.main_window.tab_enemies_layout:
            containers_height += progress_spacing + progress_bar_height

        # Добавляем margins
        total_height = containers_height + margins_top_bottom

        # Минимальная высота увеличена
        min_height = 70

        final_height = max(min_height, total_height)
        logging.debug(f"TrayWindow: Final height calculations: containers_h={containers_height}, margins={margins_top_bottom}, total_calc={final_height}")
        logging.debug(f"[TrayWindow] Calculated adaptive height: {final_height} (fixed containers: {container_fixed_height}, spacing: {spacing_between_containers}, progress: {progress_spacing + progress_bar_height})")
        return final_height

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

        # Добавляем enemies layout напрямую в scroll area
        if hasattr(self.main_window, 'tab_enemies_layout') and self.main_window.tab_enemies_layout:
            # Создаем новый виджет и устанавливаем layout
            enemies_widget = QWidget()
            enemies_widget.setLayout(self.main_window.tab_enemies_layout)
            enemies_scroll.setWidget(enemies_widget)
            layout.addWidget(enemies_scroll)

        # Создаем scroll area для counters с horizontal scroll
        counters_scroll = QScrollArea()
        counters_scroll.setWidgetResizable(True)
        counters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        counters_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Добавляем counters layout напрямую в scroll area
        if hasattr(self.main_window, 'tab_counters_layout') and self.main_window.tab_counters_layout:
            # Создаем новый виджет и устанавливаем layout
            counters_widget = QWidget()
            counters_widget.setLayout(self.main_window.tab_counters_layout)
            counters_scroll.setWidget(counters_widget)
            layout.addWidget(counters_scroll)

        # Создаем прогресс бар для распознавания
        self.recognition_progress_bar = QProgressBar()
        self.recognition_progress_bar.setFixedHeight(8)
        self.recognition_progress_bar.setRange(0, 100)
        self.recognition_progress_bar.setValue(0)
        self.recognition_progress_bar.setVisible(False)
        self.recognition_progress_bar.setTextVisible(False)

        # Добавляем прогресс бар после counters_scroll
        layout.addWidget(self.recognition_progress_bar)

    def _setup_window_properties(self):
        """Настраивает свойства окна."""
        self.setWindowTitle("Rivals Counter Peaks - TAB Mode")
        self.setMinimumSize(800, 70)  # Минимальная площадь увеличена
        self.setMaximumSize(1200, 16777215)  # Ограничение максимальной ширины до 1200px

        # Настраиваем флаги окна для overlay поведения
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)

    def _get_all_hero_widgets(self):
        """Получить все виджеты героев из обоих layout'ов."""
        hero_widgets = []

        # Добавляем виджеты врагов
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_enemies_layout'):
            enemies_layout = self.main_window.tab_enemies_layout
            if enemies_layout:
                for i in range(enemies_layout.count()):
                    item = enemies_layout.itemAt(i)
                    if item and item.widget():
                        hero_widgets.append(item.widget())

        # Добавляем виджеты контрпиков
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_counters_layout'):
            counters_layout = self.main_window.tab_counters_layout
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
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_enemies_layout'):
                enemies_layout = self.main_window.tab_enemies_layout
                enemies_count = enemies_layout.count() if enemies_layout else 0

                if self.cursor_index < enemies_count and direction == 'down':
                    # Переход к контрпикам
                    new_index = enemies_count
                elif self.cursor_index >= enemies_count and direction == 'up':
                    # Переход к врагам
                    new_index = 0
        elif direction == 'down':
            # Аналогично как для up
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_enemies_layout'):
                enemies_layout = self.main_window.tab_enemies_layout
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

        # Рассчитываем counter_scores и effective_team для правильной работы обновления списков
        counter_scores = None
        effective_team = None
        if self.main_window.logic.selected_heroes:
            counter_scores = self.main_window.logic.calculate_counter_scores()
            effective_team = self.main_window.logic.calculate_effective_team(counter_scores)
            logging.info("ROO DEBUG: TrayWindow._update_content calculated counter_scores and effective_team")

        # Обновляем горизонтальные списки в таб-режиме с параметрами
        logging.info("ROO DEBUG: TrayWindow calling ui_updater._update_horizontal_lists() with arguments")
        self.main_window.ui_updater._update_horizontal_lists(counter_scores, effective_team)
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

        # Адаптируем высоту окна под содержимое, если не слишком маленький resize
        if self._initialized and event.size().width() > 800:  # Избегаем рекурсии в маленьких размерах
            self._adapt_window_height_to_content()

    def _adapt_window_height_to_content(self):
        """Адаптирует высоту окна под текущее содержимое контейнеров."""
        try:
            current_height = self.height()
            optimal_height = self._calculate_tab_mode_height()

            # Не изменяем высоту, если разница слишком маленькая (для избежания мигания)
            height_difference = abs(current_height - optimal_height)
            if height_difference > 5:  # Минимальный порог изменения
                new_width = self.width()
                self.resize(new_width, optimal_height)
                logging.debug(f"[TrayWindow] Adjusted height from {current_height} to {optimal_height}")

        except Exception as e:
            logging.warning(f"[TrayWindow] Failed to adapt height to content: {e}")

    def start_recognition_progress(self):
        """Запустить прогресс бар распознавания"""
        if self.recognition_progress_bar:
            self.recognition_progress_bar.setRange(0, 0)  # Неопределенный прогресс
            self.recognition_progress_bar.setVisible(True)
            logging.info("[TrayWindow] Recognition progress started")
            logging.info("ROO DEBUG: Progress bar signal start_recognition_progress activated")

    def stop_recognition_progress(self):
        """Остановить прогресс бар распознавания"""
        if self.recognition_progress_bar:
            self.recognition_progress_bar.setRange(0, 100)
            self.recognition_progress_bar.setValue(100)
            # Скрыть через небольшую задержку для визуального эффекта
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, lambda: self.recognition_progress_bar.setVisible(False))
            logging.info("[TrayWindow] Recognition progress stopped")
            logging.info("ROO DEBUG: Progress bar signal stop_recognition_progress activated")