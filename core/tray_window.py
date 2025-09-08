import logging
import time
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
        self._last_enemy_list: List[str] = []
        self._last_counter_list: List[str] = []
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
        self.setMinimumSize(400, 100)
        self.setMaximumHeight(120)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)

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
        
        self.enemies_container = QWidget()
        self.enemies_layout = QHBoxLayout(self.enemies_container)
        self.enemies_layout.setContentsMargins(0,0,0,0)
        self.enemies_layout.setSpacing(2)
        self.enemies_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.enemies_container.setFixedHeight(35)
        
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
        
        layout.addWidget(self.enemies_container)
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
        
        sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
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