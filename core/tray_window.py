import logging
import os
import time
from typing import TYPE_CHECKING, Dict, List, Tuple
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QProgressBar,
                                QScrollArea, QFrame, QLabel)
from PySide6.QtCore import Qt, Slot, QRect, QSize, QTimer, QObject
from PySide6.QtGui import QMoveEvent, QResizeEvent, QColor, QPixmap
from core.event_bus import event_bus
from core.horizontal_list import IconWithRatingWidget, is_invalid_pixmap
from info.translations import get_text
from core.image_manager import SIZES

# Цвета рамок для ролей героев
ROLE_COLORS = {
    "Duelist": QColor("#FF4500"),    # Ярко-оранжевый цвет для дуэлистов
    "Vanguard": QColor("#0066CC"),   # Ярко-синий цвет для авангарда
    "Strategist": QColor("#00AA00")  # Ярко-зеленый цвет для стратегов
}

if TYPE_CHECKING:
    from main_window_refactored import MainWindowRefactored

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
        self._last_enemy_list: List[str] = []
        self._last_counter_list: List[str] = []
        self._pending_update = False
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_update)

        self.map_images: Dict[str, QPixmap] = {}
        self._load_map_images()

        self._setup_window_properties()
        self._create_ui()
        self._connect_signals()
        logging.info("[TrayWindow] Инициализация завершена.")

    def get_hero_role(self, hero_name: str) -> str:
        """
        Получает роль героя из данных ролей.

        Args:
            hero_name (str): Название героя

        Returns:
            str: Роль героя (Duelist, Vanguard, Strategist) или пустая строка если роль не найдена
        """
        from core.database.heroes_bd import ROLES_DATA
        for role, heroes_in_role in ROLES_DATA.items():
            if hero_name in heroes_in_role:
                return role
        return ""

    def _setup_window_properties(self):
        self.setWindowTitle("Rivals Counter Peaks - TAB Mode")
        self.setMinimumSize(400, 100)
        self.setMaximumHeight(120)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)

    def _load_map_images(self):
        """Загружает и кэширует изображения карт."""
        try:
            from core.utils import resource_path
            maps_dir = resource_path("resources/maps")
            if not os.path.isdir(maps_dir): return

            for map_name in self.logic.available_maps:
                filename = f"{map_name}.png"
                filepath = os.path.join(maps_dir, filename)
                if os.path.exists(filepath):
                    pixmap = QPixmap(filepath)
                    if not pixmap.isNull():
                        self.map_images[map_name] = pixmap.scaled(64, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                else:
                    logging.warning(f"Изображение карты не найдено: {filepath}")
        except Exception as e:
            logging.error(f"Ошибка при загрузке изображений карт: {e}")

    def _create_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
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
        layout.setSpacing(0)

        # Верхний контейнер для карты и врагов
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)

        # Виджет для отображения карты
        self.map_display_widget = QWidget()
        map_display_layout = QVBoxLayout(self.map_display_widget)
        map_display_layout.setContentsMargins(0, 0, 0, 0)
        self.map_image_label = QLabel()
        self.map_name_label = QLabel()
        self.map_name_label.setAlignment(Qt.AlignCenter)
        self.map_name_label.setStyleSheet("color: white; font-size: 9px; font-weight: bold;")
        map_display_layout.addWidget(self.map_image_label)
        map_display_layout.addWidget(self.map_name_label)
        self.map_display_widget.setVisible(False) # Скрыт по умолчанию

        # Контейнер для врагов
        self.enemies_container = QWidget()
        self.enemies_layout = QHBoxLayout(self.enemies_container)
        self.enemies_layout.setContentsMargins(0,0,0,0)
        self.enemies_layout.setSpacing(2)
        
        top_layout.addWidget(self.map_display_widget)
        top_layout.addWidget(self.enemies_container, 1) # Занимает оставшееся место

        self.counters_scroll_area = QScrollArea()
        self.counters_scroll_area.setWidgetResizable(True)
        self.counters_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.counters_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.counters_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.counters_scroll_area.setStyleSheet("background: transparent; border: none;")
        self.counters_scroll_area.setFixedHeight(50) 
        
        scroll_content_widget = QWidget()
        self.counters_layout = QHBoxLayout(scroll_content_widget)
        self.counters_layout.setContentsMargins(0,0,0,0)
        self.counters_layout.setSpacing(2)
        self.counters_scroll_area.setWidget(scroll_content_widget)
        
        layout.addWidget(top_container)
        layout.addWidget(self.counters_scroll_area)
        
        self.recognition_progress_bar = QProgressBar()
        self.recognition_progress_bar.setFixedHeight(5)
        self.recognition_progress_bar.setRange(0, 0)
        self.recognition_progress_bar.setTextVisible(False)
        self.recognition_progress_bar.setVisible(False)
        self.recognition_progress_bar.setStyleSheet("QProgressBar { border-radius: 2px; } QProgressBar::chunk { background-color: #0078d7; border-radius: 2px; }")
        layout.addWidget(self.recognition_progress_bar)

    def _connect_signals(self):
        event_bus.subscribe("logic_updated", self._schedule_update)
        if hasattr(self.main_window, 'recognition_manager'):
            self.main_window.recognition_manager.recognition_started.connect(self.start_recognition_progress)
            self.main_window.recognition_manager.recognition_stopped.connect(self.stop_recognition_progress)
        else:
            logging.error("[TrayWindow] recognition_manager not found in main_window!")

    def _schedule_update(self, data: dict):
        if not self._initialized: return
        if not isinstance(data, dict): return
            
        self._pending_data = data
        self._pending_update = True
        self._update_timer.start(50)

    def _update_map_display(self, selected_map: str = None):
        """Обновляет отображение карты в трее.

        Args:
            selected_map: Название выбранной карты или None если карта не выбрана
        """
        if selected_map and selected_map in self.map_images:
            # Показываем выбранную карту
            self.map_image_label.setPixmap(self.map_images[selected_map])
            self.map_name_label.setText(selected_map)
            self.map_display_widget.setVisible(True)
        else:
            # Показываем индикатор невыбранной карты
            # Создаем пустой pixmap для индикатора
            empty_pixmap = QPixmap(64, 36)
            empty_pixmap.fill(QColor(60, 60, 60, 150))  # Полупрозрачный серый фон

            self.map_image_label.setPixmap(empty_pixmap)
            self.map_name_label.setText(get_text("map_not_selected", "Карта не выбрана"))
            self.map_display_widget.setVisible(True)

    def _process_pending_update(self):
        if not self._pending_update or not hasattr(self, '_pending_data'): return
            
        self._pending_update = False
        data = self._pending_data
        start_time = data.get("start_time")
        
        if start_time:
            delta = time.time() - start_time
            logging.info(f"[TIME-LOG] {delta:.3f}s: TrayWindow received logic_updated event.")

        selected_heroes = sorted(data.get("selected_heroes", []))
        counter_scores = data.get("counter_scores", {})
        effective_team = data.get("effective_team", [])
        selected_map = data.get("selected_map")
        
        # Обновление информации о карте
        self._update_map_display(selected_map)
        
        # ИСПРАВЛЕНИЕ: Возвращена правильная сортировка по очкам (второй элемент кортежа)
        sorted_counters = sorted(counter_scores.items(), key=lambda item: item[1], reverse=True)
        heroes_to_display = [h for h, s in sorted_counters if s > 0 or h in effective_team]

        if selected_heroes != self._last_enemy_list:
            self._update_layout(self.enemies_layout, self.enemy_widgets, selected_heroes, is_enemy=True)
            self._last_enemy_list = selected_heroes

        if heroes_to_display != self._last_counter_list:
            self._update_layout(self.counters_layout, self.counter_widgets, heroes_to_display, is_enemy=False, scores=counter_scores, effective=effective_team)
            self._last_counter_list = heroes_to_display
            
        self.enemies_container.setVisible(bool(selected_heroes))
        self.counters_scroll_area.setVisible(bool(heroes_to_display))

        if start_time:
            delta_end = time.time() - start_time
            logging.info(f"[TIME-LOG] {delta_end:.3f}s: TOTAL time from hotkey to tray UI update complete.")

    def _update_layout(self, layout: QHBoxLayout, widget_cache: Dict, hero_list: List[str], is_enemy: bool, scores: Dict = None, effective: List = None):
        for widget in widget_cache.values():
            widget.setVisible(False)
        
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        if is_enemy: layout.addStretch(1)
        
        images = self.image_manager.get_specific_images('min', 'horizontal')
        
        for hero_name in hero_list:
            widget = widget_cache.get(hero_name)
            if not widget:
                pixmap = images.get(hero_name)
                if is_invalid_pixmap(pixmap): continue

                rating = scores.get(hero_name, 0) if scores else 0
                is_effective = hero_name in (effective or [])
                tooltip = f"{hero_name}: {rating:.1f}" if not is_enemy else hero_name
                widget = IconWithRatingWidget(pixmap, rating, is_effective, is_enemy, tooltip, parent=self.centralWidget())
                widget.setFixedSize(pixmap.size().width() + 4, pixmap.size().height() + 4)

                # Получаем роль героя и устанавливаем рамку
                hero_role = self.get_hero_role(hero_name)
                if hero_role:
                    border_color = ROLE_COLORS.get(hero_role)
                    if border_color:
                        widget.set_border(border_color, 3)  # Устанавливаем рамку толщиной 3px

                widget_cache[hero_name] = widget

            widget.setVisible(True)
            layout.addWidget(widget)
            
        if not is_enemy: layout.addStretch(1)

    def show_tray(self):
        if not self._restored_geometry:
            self._restore_geometry()
            self._restored_geometry = True
            
        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()
            
        self._initialized = True

    def hide_tray(self):
        if self.isVisible():
            self._save_geometry()
            self.hide()

    def _save_geometry(self):
        if not self.isVisible() or not self._initialized: return
        geo = self.geometry()
        settings_data = {"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()}
        self.main_window.settings_manager.set_tab_window_geometry(settings_data)

    def _restore_geometry(self):
        settings_data = self.main_window.settings_manager.get_tab_window_geometry()
        if all(k in settings_data for k in ["x", "y", "width", "height"]):
            height = min(settings_data["height"], 120)
            self.setGeometry(QRect(settings_data["x"], settings_data["y"], settings_data["width"], height))

    def moveEvent(self, event: QMoveEvent):
        QTimer.singleShot(250, self._save_geometry)
        super().moveEvent(event)

    def resizeEvent(self, event: QResizeEvent):
        QTimer.singleShot(250, self._save_geometry)
        super().resizeEvent(event)

    @Slot()
    def start_recognition_progress(self):
        if self.recognition_progress_bar: self.recognition_progress_bar.setVisible(True)

    @Slot()
    def stop_recognition_progress(self):
        if self.recognition_progress_bar: self.recognition_progress_bar.setVisible(False)

    def closeEvent(self, event):
        self.hide_tray()
        event.ignore()