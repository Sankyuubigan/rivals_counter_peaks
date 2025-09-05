# File: core/tier_list_tab.py
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QFrame, QPushButton, 
                               QHBoxLayout, QLabel, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from core.logic import CounterpickLogic
from core.image_manager import ImageManager
from info.translations import get_text
from images_load import is_invalid_pixmap
class TierListTab(QWidget):
    """Вкладка для отображения тир-листа (меты) героев."""
    def __init__(self, logic: CounterpickLogic, image_manager: ImageManager, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.image_manager = image_manager
        self.parent_window = parent
        
        self._init_ui()
        self._populate_tier_list()
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Панель с кнопкой обновления
        top_panel = QFrame()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 5, 0, 5)
        
        refresh_button = QPushButton(get_text("tier_list_refresh_button", default_text="Обновить"))
        refresh_button.clicked.connect(self._populate_tier_list)
        
        top_layout.addStretch(1)
        top_layout.addWidget(refresh_button)
        
        main_layout.addWidget(top_panel)
        
        # Область прокрутки для списка
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.result_frame = QFrame()
        self.result_layout = QVBoxLayout(self.result_frame)
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.result_layout.setContentsMargins(2, 2, 2, 2)
        self.result_layout.setSpacing(1)
        
        scroll_area.setWidget(self.result_frame)
        main_layout.addWidget(scroll_area)
    def _populate_tier_list(self):
        """Запрашивает данные и заполняет список героев."""
        # Очистка старого списка
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Получение данных
        scores = self.logic.calculate_tier_list_scores()
        if not scores:
            self.result_layout.addWidget(QLabel(get_text("tier_list_no_data", default_text="Не удалось рассчитать тир-лист.")))
            return
            
        # ИСПРАВЛЕНИЕ: Сортируем словарь по значениям (очкам) - item[1]
        sorted_heroes = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        
        left_images = self.image_manager.get_specific_images('middle', 'left')
        
        # Определение цветов темы
        current_theme = "light"
        if hasattr(self.parent_window, 'settings_manager'):
            current_theme = self.parent_window.settings_manager.get_theme()
        
        text_color = QColor("black") if current_theme == "light" else QColor("#e0e0e0")
        
        # Заполнение списка
        for hero, score in sorted_heroes:
            hero_frame = QFrame()
            hero_layout = QHBoxLayout(hero_frame)
            hero_layout.setContentsMargins(4, 1, 4, 1)
            hero_layout.setSpacing(5)
            pixmap = left_images.get(hero)
            if is_invalid_pixmap(pixmap):
                logging.warning(f"[TierList] Invalid pixmap for hero: {hero}")
                continue
            img_label = QLabel()
            img_label.setPixmap(pixmap)
            
            score_text = f"<b>{score:.2f}</b>"
            text_label = QLabel(f"{hero}: {score_text}")
            text_label.setStyleSheet(f"color: {text_color.name()};")
            
            hero_layout.addWidget(img_label)
            hero_layout.addWidget(text_label)
            hero_layout.addStretch(1)
            
            self.result_layout.addWidget(hero_frame)
        
        self.result_layout.addStretch(1)