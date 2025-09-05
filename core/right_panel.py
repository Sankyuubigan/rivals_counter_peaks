# File: core/right_panel.py
from info import translations
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QLabel, QListWidget, QListWidgetItem,
    QListView, QPushButton, QVBoxLayout, QWidget
)
# ИСПРАВЛЕНО: Исправлен путь импорта
from core.database.heroes_bd import heroes
from core.images_load import is_invalid_pixmap, SIZES
# ИСПРАВЛЕНО: Удален импорт logic, так как он используется через self.window.logic
from core import images_load
import logging

# ИСПРАВЛЕНО: Добавлена константа TEAM_SIZE
TEAM_SIZE = 6

HERO_NAME_ROLE = Qt.UserRole + 1
TARGET_COLUMN_COUNT = 5
class RightPanel:
    """Класс для создания и управления правой панелью."""
    def __init__(self, window: QWidget, initial_mode="middle"):
        self.window = window
        if not hasattr(window, 'logic'): raise AttributeError("Объект 'window' должен иметь атрибут 'logic'.")
        self.logic = window.logic
        self.current_mode = initial_mode
        self.frame = QFrame(window); self.frame.setObjectName("right_frame"); self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget = QListWidget(); self.list_widget.setObjectName("right_list_widget")
        
        self.selected_heroes_label = QLabel(
            translations.get_text("selected_none", language=self.logic.DEFAULT_LANGUAGE, max_team_size=TEAM_SIZE))
        
        self.selected_heroes_label.setObjectName("selected_heroes_label"); self.selected_heroes_label.setWordWrap(True)
        self.copy_button = QPushButton(translations.get_text("copy_rating", language=self.logic.DEFAULT_LANGUAGE)); self.copy_button.setObjectName("copy_button")
        self.clear_button = QPushButton(translations.get_text("clear_all", language=self.logic.DEFAULT_LANGUAGE)); self.clear_button.setObjectName("clear_button")
        self.hero_items = {}
        self._setup_list_widget()
        self._populate_list_widget()
        self._setup_layout()
        self._connect_signals()
        self._apply_selected_stylesheet()
    def _setup_list_widget(self):
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_widget.setMovement(QListView.Movement.Static)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setWordWrap(True)
        self.list_widget.setUniformItemSizes(True)
        icon_width, icon_height = SIZES.get(self.current_mode, {}).get('right', (40, 40))
        self.list_widget.setIconSize(QSize(icon_width, icon_height))
        item_width = icon_width + 15
        item_height = icon_height + 10
        self.list_widget.setGridSize(QSize(item_width, item_height))
        self.list_widget.setSpacing(4)
        
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    def _populate_list_widget(self):
        self.hero_items.clear()
        self.list_widget.clear()
        logging.info(f"[RightPanel] Cleared list widget for mode {self.current_mode}")
        right_images = getattr(self.window, 'right_images', {})
        if not right_images:
            logging.error(f"[RightPanel] 'right_images' not found for mode {self.current_mode}.")
            return
        for hero in heroes:
            item = QListWidgetItem()
            item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
            pixmap = right_images.get(hero)
            if is_invalid_pixmap(pixmap):
                logging.warning(f"[RightPanel] Invalid icon for hero: '{hero}'")
                continue
            
            item.setIcon(QIcon(pixmap))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setData(HERO_NAME_ROLE, hero)
            item.setToolTip(hero)
            self.list_widget.addItem(item)
            self.hero_items[hero] = item
        logging.info(f"[RightPanel] List populated with {len(self.hero_items)} items.")
    def _setup_layout(self):
        self.layout = QVBoxLayout(self.frame); self.layout.setObjectName("right_panel_layout")
        self.layout.setContentsMargins(5, 5, 5, 5); self.layout.setSpacing(5)
        self.layout.addWidget(self.list_widget, stretch=1); self.layout.addWidget(self.selected_heroes_label)
        self.layout.addWidget(self.copy_button); self.layout.addWidget(self.clear_button)
    def _connect_signals(self):
        if hasattr(self.window, 'action_controller'):
            self.copy_button.clicked.connect(self.window.action_controller.handle_copy_team)
            self.clear_button.clicked.connect(self.window.action_controller.handle_clear_all)
    def update_language(self):
        self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
        self.copy_button.setText(translations.get_text('copy_rating', language=self.logic.DEFAULT_LANGUAGE))
        self.clear_button.setText(translations.get_text('clear_all', language=self.logic.DEFAULT_LANGUAGE))
    def _apply_selected_stylesheet(self):
        # ИСПРАВЛЕНИЕ: Удалено неподдерживаемое свойство `box-shadow`.
        stylesheet = """
        QListWidget::item:selected {
            background-color: #FFD700;
            border: 4px solid #FF4500;
            color: white;
        }
        """
        self.list_widget.setStyleSheet(stylesheet)