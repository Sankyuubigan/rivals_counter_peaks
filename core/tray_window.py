import logging
from typing import TYPE_CHECKING, Dict, List, Tuple
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QProgressBar, 
                               QScrollArea, QFrame)
from PySide6.QtCore import Qt, Slot, QRect, QSize, QTimer, QObject
from PySide6.QtGui import QMoveEvent, QResizeEvent, QColor
from core.event_bus import event_bus
from core.horizontal_list import IconWithRatingWidget, is_invalid_pixmap
from info.translations import get_text
from core.image_manager import SIZES

if TYPE_CHECKING:
    from main_window_refactored import MainWindowRefactored
    from PySide6.QtGui import QPixmap

class TrayWindow(QMainWindow):
    """Оптимизированное окно для таб-режима, которое переиспользует виджеты."""
    def __init__(self, main_window: 'MainWindowRefactored'):
        super().__init__()
        self.main_window = main_window
        self.logic = main_window.logic 
        self.image_manager = main_window.image_manager
        self._initialized = False
        self._restored_geometry = False
        self.enemy_widgets: Dict[str, IconWithRatingWidget] = {}
        self.counter_widgets: Dict[str, IconWithRatingWidget] = {}
        self._last_enemy_count = 0
        self._last_counter_count = 0
        self._pending_update = False
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_update)
        self._setup_window_properties()
        self._create_ui()
        self._connect_signals()
        logging.info("[TrayWindow] Инициализация завершена.")

    def _setup_window_properties(self):
        self.setWindowTitle("Rivals Counter Peaks - TAB Mode")
        # Уменьшаем высоту окна и делаем его более компактным
        self.setMinimumSize(400, 100)
        self.setMaximumHeight(120)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        # Устанавливаем атрибуты для быстрого отображения
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        # Отключаем тени для ускорения отрисовки
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)

    def _create_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
        # Устанавливаем фон для центрального виджета
        central_widget.setStyleSheet("""
            #central_widget {
                background-color: rgba(40, 40, 40, 200);
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 5px;
            }
        """)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)  # УБИРАЕМ ОТСТУПЫ МЕЖДУ СЛОЯМИ
        
        # Верхний слой для врагов - теперь с выравниванием вправо
        self.enemies_layout = QHBoxLayout()
        self.enemies_layout.setContentsMargins(0,0,0,0)
        self.enemies_layout.setSpacing(2)  # Уменьшаем отступы между иконками
        self.enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight)  # Выравниваем врагов вправо
        # Устанавливаем фиксированную высоту для слоя врагов, чтобы он не занимал место когда пуст
        self.enemies_container = QWidget()
        self.enemies_container.setLayout(self.enemies_layout)
        self.enemies_container.setFixedHeight(30)
        self.enemies_container.setStyleSheet("background: transparent;")
        
        # Нижний слой для контрпиков с прокруткой
        self.counters_scroll_area = QScrollArea()
        self.counters_scroll_area.setWidgetResizable(True)
        self.counters_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Убираем полосу прокрутки
        self.counters_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.counters_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # Устанавливаем такой же фон как у центрального виджета
        self.counters_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: rgba(40, 40, 40, 200);
                border: none;
            }
        """)
        # Уменьшаем высоту области контрпиков
        self.counters_scroll_area.setFixedHeight(50) 
        scroll_content_widget = QWidget()
        scroll_content_widget.setObjectName("scroll_content")
        # Устанавливаем фон для области прокрутки
        scroll_content_widget.setStyleSheet("""
            #scroll_content {
                background-color: rgba(40, 40, 40, 200);
                border: none;
            }
        """)
        self.counters_layout = QHBoxLayout(scroll_content_widget)
        self.counters_layout.setContentsMargins(0,0,0,0)
        self.counters_layout.setSpacing(2)  # Уменьшаем отступы между иконками
        self.counters_scroll_area.setWidget(scroll_content_widget)
        
        # Добавляем слои в основной layout
        layout.addWidget(self.enemies_container)
        layout.addWidget(self.counters_scroll_area)
        
        # Возвращаем прогрессбар
        self.recognition_progress_bar = QProgressBar()
        self.recognition_progress_bar.setFixedHeight(5)
        self.recognition_progress_bar.setRange(0, 0)
        self.recognition_progress_bar.setTextVisible(False)
        self.recognition_progress_bar.setVisible(False)
        layout.addWidget(self.recognition_progress_bar)

    def _connect_signals(self):
        event_bus.subscribe("logic_updated", self._schedule_update)
        if hasattr(self.main_window, 'recognition_manager'):
            self.main_window.recognition_manager.recognition_started.connect(self.start_recognition_progress)
            self.main_window.recognition_manager.recognition_stopped.connect(self.stop_recognition_progress)
            logging.info("[TrayWindow] Connected to recognition_manager signals")
        else:
            logging.error("[TrayWindow] recognition_manager not found in main_window!")

    def _schedule_update(self, data: dict):
        """Планирует отложенное обновление контента для предотвращения лагов."""
        if not self._initialized:
            logging.warning("[TrayWindow] _schedule_update called before window is initialized/shown. Skipping.")
            return
        if not isinstance(data, dict):
            logging.error(f"[TrayWindow] Invalid payload received for content update (not a dict): {data}")
            return
            
        # Сохраняем данные для отложенного обновления
        self._pending_data = data
        self._pending_update = True
        
        # Запускаем таймер для отложенного обновления (50мс задержка для большей отзывчивости)
        self._update_timer.start(50)

    def _process_pending_update(self):
        """Обрабатывает отложенное обновление контента."""
        if not self._pending_update or not hasattr(self, '_pending_data'):
            return
            
        self._pending_update = False
        data = self._pending_data
        
        selected_heroes = data.get("selected_heroes", [])
        counter_scores = data.get("counter_scores", {})
        effective_team = data.get("effective_team", [])
        
        # Проверяем, нужно ли вообще обновлять врагов
        if len(selected_heroes) != self._last_enemy_count:
            self._update_heroes_layout(selected_heroes)
            self._last_enemy_count = len(selected_heroes)
        
        # Проверяем, нужно ли обновлять контрпики
        heroes_to_display = [h for h, s in counter_scores.items() if s >= 1.0 or h in effective_team]
        if len(heroes_to_display) != self._last_counter_count:
            self._update_counters_layout(heroes_to_display)
            self._last_counter_count = len(heroes_to_display)
        
        # Управляем видимостью контейнеров в зависимости от наличия данных
        if not selected_heroes:
            self.enemies_container.hide()
        else:
            self.enemies_container.show()
            
        if not heroes_to_display:
            self.counters_scroll_area.hide()
        else:
            self.counters_scroll_area.show()

    def _update_heroes_layout(self, selected_heroes: List[str]):
        """Оптимизированное обновление слоя врагов."""
        horizontal_images = self.image_manager.get_specific_images('min', 'horizontal')
        
        # Очищаем только если количество виджетов не совпадает
        if self.enemies_layout.count() != len(selected_heroes) + 1:  # +1 для stretch
            self._clear_layout(self.enemies_layout)
            # Добавляем stretch слева, чтобы враги были справа
            self.enemies_layout.addStretch(1)
            
            # Добавляем врагов в правильном порядке (слева направо)
            for hero_name in selected_heroes:
                pixmap = horizontal_images.get(hero_name)
                if is_invalid_pixmap(pixmap):
                    logging.warning(f"Skipping enemy hero '{hero_name}' due to missing pixmap.")
                    continue
                    
                if hero_name not in self.enemy_widgets:
                    widget = IconWithRatingWidget(pixmap, 0, False, True, hero_name, parent=self)
                    widget.setFixedSize(pixmap.size().width() + 6, pixmap.size().height() + 6)  # Уменьшаем отступы
                    self.enemy_widgets[hero_name] = widget
                
                widget = self.enemy_widgets[hero_name]
                widget.setVisible(True)
                # Просто добавляем виджет в layout, выравнивание справа уже установлено
                self.enemies_layout.addWidget(widget)

    def _update_counters_layout(self, heroes_to_display: List[str]):
        """Оптимизированное обновление слоя контрпиков."""
        horizontal_images = self.image_manager.get_specific_images('min', 'horizontal')
        
        # Очищаем только если количество виджетов не совпадает
        if self.counters_layout.count() != len(heroes_to_display) + 1:  # +1 для stretch
            self._clear_layout(self.counters_layout)
            
            # Добавляем контрпики в порядке убывания рейтинга
            for hero_name in heroes_to_display:
                pixmap = horizontal_images.get(hero_name)
                if is_invalid_pixmap(pixmap):
                    logging.warning(f"Skipping counter hero '{hero_name}' due to missing pixmap.")
                    continue
                    
                if hero_name not in self.counter_widgets:
                    widget = IconWithRatingWidget(pixmap, 0, False, False, hero_name, parent=self)
                    widget.setFixedSize(pixmap.size().width() + 6, pixmap.size().height() + 6)  # Уменьшаем отступы
                    self.counter_widgets[hero_name] = widget
                
                widget = self.counter_widgets[hero_name]
                widget.setVisible(True)
                self.counters_layout.addWidget(widget)
            
            self.counters_layout.addStretch(1)

    def _clear_layout(self, layout: QHBoxLayout):
        """Оптимизированная очистка слоя без удаления виджетов."""
        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                widget.setVisible(False)  # Просто скрываем вместо удаления

    def show_tray(self):
        """Оптимизированный показ окна с минимальными операциями."""
        if not self._restored_geometry:
            self._restore_geometry()
            self._restored_geometry = True
            
        if not self.isVisible():
            # Устанавливаем флаги для быстрого отображения
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
            # Отключаем анимации для ускорения
            self.setAttribute(Qt.WA_Disabled, True)
            self.show()
            # Включаем обратно после отображения
            self.setAttribute(Qt.WA_Disabled, False)
            # Активируем окно после отображения
            self.raise_()
            self.activateWindow()
            
        self._initialized = True

    def hide_tray(self):
        """Оптимизированное скрытие окна."""
        if self.isVisible():
            self.hide()

    def _save_geometry(self):
        if not self.isVisible() or not self._initialized:
            return
        geo = self.geometry()
        settings_data = {"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()}
        self.main_window.settings_manager.set_tab_window_geometry(settings_data)

    def _restore_geometry(self):
        settings_data = self.main_window.settings_manager.get_tab_window_geometry()
        if all(k in settings_data for k in ["x", "y", "width", "height"]):
            # Ограничиваем высоту восстанавливаемого окна
            height = min(settings_data["height"], 120)
            self.setGeometry(QRect(settings_data["x"], settings_data["y"], settings_data["width"], height))
            logging.info(f"Tray geometry restored: {settings_data}")

    def moveEvent(self, event: QMoveEvent):
        # Отложенное сохранение геометрии для предотвращения лагов
        QTimer.singleShot(100, self._save_geometry)
        super().moveEvent(event)

    def resizeEvent(self, event: QResizeEvent):
        # Отложенное сохранение геометрии для предотвращения лагов
        QTimer.singleShot(100, self._save_geometry)
        super().resizeEvent(event)

    @Slot()
    def start_recognition_progress(self):
        """Показывает прогрессбар во время распознавания."""
        if self.recognition_progress_bar:
            self.recognition_progress_bar.setVisible(True)

    @Slot()
    def stop_recognition_progress(self):
        """Скрывает прогрессбар после завершения распознавания."""
        if self.recognition_progress_bar:
            self.recognition_progress_bar.setVisible(False)

    def closeEvent(self, event):
        self.hide_tray()
        event.ignore()