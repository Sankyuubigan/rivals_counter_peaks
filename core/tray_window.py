import logging
from typing import TYPE_CHECKING, Dict, List, Tuple
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QProgressBar, 
                               QScrollArea, QFrame)
from PySide6.QtCore import Qt, Slot, QRect, QSize
from PySide6.QtGui import QCloseEvent, QMoveEvent, QResizeEvent
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
        self._setup_window_properties()
        self._create_ui()
        self._connect_signals()
        logging.info("[TrayWindow] Инициализация завершена.")
    def _setup_window_properties(self):
        self.setWindowTitle("Rivals Counter Peaks - TAB Mode")
        # ИСПРАВЛЕНИЕ: Уменьшаем высоту окна и делаем его более компактным
        self.setMinimumSize(400, 100)
        self.setMaximumHeight(120)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
    def _create_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Верхний слой для врагов
        self.enemies_layout = QHBoxLayout()
        self.enemies_layout.setContentsMargins(0,0,0,0)
        self.enemies_layout.setSpacing(4)
        
        # Нижний слой для контрпиков с прокруткой
        counters_scroll_area = QScrollArea()
        counters_scroll_area.setWidgetResizable(True)
        counters_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # ИСПРАВЛЕНИЕ: Убираем полосу прокрутки
        counters_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        counters_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # ИСПРАВЛЕНИЕ: Уменьшаем высоту области контрпиков
        counters_scroll_area.setFixedHeight(50) 
        scroll_content_widget = QWidget()
        self.counters_layout = QHBoxLayout(scroll_content_widget)
        self.counters_layout.setContentsMargins(0,0,0,0)
        self.counters_layout.setSpacing(4)
        counters_scroll_area.setWidget(scroll_content_widget)
        layout.addLayout(self.enemies_layout)
        layout.addWidget(counters_scroll_area)
        self.recognition_progress_bar = QProgressBar()
        self.recognition_progress_bar.setFixedHeight(5)
        self.recognition_progress_bar.setRange(0, 0)
        self.recognition_progress_bar.setTextVisible(False)
        self.recognition_progress_bar.setVisible(False)
        layout.addWidget(self.recognition_progress_bar)
    def _connect_signals(self):
        event_bus.subscribe("logic_updated", self._update_content)
        if hasattr(self.main_window, 'recognition_manager'):
            self.main_window.recognition_manager.recognition_started.connect(self.start_recognition_progress)
            self.main_window.recognition_manager.recognition_stopped.connect(self.stop_recognition_progress)
            # ИСПРАВЛЕНИЕ: Добавляем логирование для отслеживания подключения сигналов
            logging.info("[TrayWindow] Connected to recognition_manager signals")
        else:
            logging.error("[TrayWindow] recognition_manager not found in main_window!")
    @Slot(dict)
    def _update_content(self, data: dict):
        logging.info(f"[TrayWindow] Received 'logic_updated' event. Data type: {type(data)}.")
        if not self._initialized:
            logging.warning("[TrayWindow] _update_content called before window is initialized/shown. Skipping.")
            return
        if not isinstance(data, dict):
            logging.error(f"[TrayWindow] Invalid payload received for content update (not a dict): {data}")
            return
            
        logging.info(f"[TrayWindow] Обновление контента... Получено {len(data.get('selected_heroes', []))} врагов и {len(data.get('counter_scores', {}))} контрпиков.")
        
        horizontal_images = self.image_manager.get_specific_images('min', 'horizontal')
        selected_heroes = data.get("selected_heroes", [])
        counter_scores = data.get("counter_scores", {})
        effective_team = data.get("effective_team", [])
        
        self._update_hero_layout(self.enemies_layout, self.enemy_widgets, selected_heroes, is_enemy=True, image_dict=horizontal_images)
        
        heroes_to_display = [h for h, s in counter_scores.items() if s >= 1.0 or h in effective_team]
        sorted_counters = sorted(heroes_to_display, key=lambda h: counter_scores.get(h, -99), reverse=True)
        
        self._update_hero_layout(self.counters_layout, self.counter_widgets, sorted_counters, is_enemy=False, image_dict=horizontal_images, counter_scores=counter_scores, effective_team=effective_team)

    def _update_hero_layout(self, layout: QHBoxLayout, widget_dict: Dict[str, IconWithRatingWidget], hero_names: List[str], is_enemy: bool, image_dict: Dict[str, 'QPixmap'], **kwargs):
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().setVisible(False)
                item.widget().setParent(None)
        
        if is_enemy:
            layout.addStretch(1)
        for hero_name in hero_names:
            pixmap = image_dict.get(hero_name)
            # ИСПРАВЛЕНИЕ КРЭША: Пропускаем героя, если для него нет иконки
            if is_invalid_pixmap(pixmap):
                logging.warning(f"Skipping hero '{hero_name}' in tray window due to missing pixmap.")
                continue
            if hero_name in widget_dict:
                widget = widget_dict[hero_name]
            else:
                # ИСПРАВЛЕНИЕ: Создаем виджет с правильным размером иконки
                widget = IconWithRatingWidget(pixmap, 0, False, is_enemy, hero_name, parent=self)
                # Устанавливаем фиксированный размер для виджета, чтобы избежать растягивания
                widget.setFixedSize(pixmap.size().width() + 10, pixmap.size().height() + 10)
                widget_dict[hero_name] = widget
            
            if not is_enemy:
                rating = kwargs.get('counter_scores', {}).get(hero_name, 0.0)
                is_effective = hero_name in kwargs.get('effective_team', [])
                widget.rating_text = f"{rating:.0f}"
                widget.is_in_effective_team = is_effective
                widget.setToolTip(f"{hero_name}\nRating: {rating:.1f}")
            widget.setVisible(True)
            layout.addWidget(widget)
        if not is_enemy:
            layout.addStretch(1)
        heroes_to_remove = set(widget_dict.keys()) - set(hero_names)
        for hero_name in heroes_to_remove:
            widget = widget_dict.pop(hero_name)
            widget.deleteLater()
    def show_tray(self):
        if not self._restored_geometry:
            self._restore_geometry()
            self._restored_geometry = True
        if not self.isVisible():
            logging.info("[TrayWindow] Окно становится видимым.")
            self.show()
        self.raise_()
        self.activateWindow()
        self._initialized = True
    def hide_tray(self):
        logging.info("[TrayWindow] Окно скрывается.")
        self.hide()
    def _save_geometry(self):
        if not self.isVisible() or not self._initialized:
            return
        geo = self.geometry()
        settings_data = {"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()}
        self.main_window.settings_manager.set_tab_window_geometry(settings_data)
        logging.debug(f"Tray geometry saved: {settings_data}")
    def _restore_geometry(self):
        settings_data = self.main_window.settings_manager.get_tab_window_geometry()
        if all(k in settings_data for k in ["x", "y", "width", "height"]):
            # ИСПРАВЛЕНИЕ: Ограничиваем высоту восстанавливаемого окна
            height = min(settings_data["height"], 120)
            self.setGeometry(QRect(settings_data["x"], settings_data["y"], settings_data["width"], height))
            logging.info(f"Tray geometry restored: {settings_data}")
    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        self._save_geometry()
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._save_geometry()
    @Slot()
    def start_recognition_progress(self):
        logging.info("[TrayWindow] Recognition started - showing progress bar")
        if self.recognition_progress_bar:
            self.recognition_progress_bar.setVisible(True)
    @Slot()
    def stop_recognition_progress(self):
        logging.info("[TrayWindow] Recognition stopped - hiding progress bar")
        if self.recognition_progress_bar:
            self.recognition_progress_bar.setVisible(False)
    def closeEvent(self, event: QCloseEvent):
        self.hide_tray()
        event.ignore()