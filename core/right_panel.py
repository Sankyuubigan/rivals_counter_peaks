# File: core/right_panel.py
from core.lang import translations
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QLabel, QListWidget, QListWidgetItem,
    QListView, QPushButton, QVBoxLayout, QWidget
)
from database.heroes_bd import heroes
from images_load import is_invalid_pixmap
from logic import TEAM_SIZE
import logging

HERO_NAME_ROLE = Qt.UserRole + 1

class RightPanel:
    """Класс для создания и управления правой панелью."""
    def __init__(self, window: QWidget, initial_mode="middle"):
        self.window = window
        if not hasattr(window, 'logic'): raise AttributeError("Объект 'window' должен иметь атрибут 'logic'.")
        self.logic = window.logic
        self.initial_mode = initial_mode

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

    def _setup_list_widget(self):
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_widget.setMovement(QListView.Movement.Static)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setWordWrap(True)
        self.list_widget.setUniformItemSizes(True)
        if self.initial_mode == "max": icon_size = QSize(60, 60); grid_size = QSize(85, 95); self.list_widget.setSpacing(10)
        else: icon_size = QSize(40, 40); grid_size = QSize(icon_size.width() + 15, icon_size.height() + 10); self.list_widget.setSpacing(4)
        self.list_widget.setIconSize(icon_size); self.list_widget.setGridSize(grid_size)
        
        # Основные стили для QListWidget и его элементов теперь в QSS файлах.
        # Можно оставить здесь специфичные настройки, если они не перекрываются QSS.
        # self.list_widget.setStyleSheet("""...""") # Удалено, так как будет в QSS

        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        viewport = self.list_widget.viewport()
        if viewport:
            logging.debug(f"[RightPanel] List widget configured for mode '{self.initial_mode}'. ListWidget objectName: '{self.list_widget.objectName()}', Viewport objectName: '{viewport.objectName() if viewport else 'N/A'}'")
        else:
            logging.debug(f"[RightPanel] List widget configured for mode '{self.initial_mode}'. ListWidget objectName: '{self.list_widget.objectName()}', Viewport is None.")


    def _populate_list_widget(self):
        self.hero_items.clear()
        right_images = getattr(self.window, 'right_images', {})
        if not right_images: logging.warning("[RightPanel] 'right_images' not found or empty in main window.")

        for hero in heroes:
            item = QListWidgetItem(); item_text = hero if self.initial_mode == "max" else ""
            item.setText(item_text); item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
            icon_pixmap : QPixmap | None = right_images.get(hero)
            if is_invalid_pixmap(icon_pixmap): logging.warning(f"[RightPanel] Invalid or missing icon for hero: '{hero}'. Setting placeholder.")
            else: item.setIcon(QIcon(icon_pixmap))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setData(HERO_NAME_ROLE, hero); item.setToolTip(hero)
            self.list_widget.addItem(item); self.hero_items[hero] = item
        logging.debug(f"[RightPanel] List populated with {len(self.hero_items)} items.")

    def _setup_layout(self):
        self.layout = QVBoxLayout(self.frame); self.layout.setObjectName("right_panel_layout")
        self.layout.setContentsMargins(5, 5, 5, 5); self.layout.setSpacing(5)
        self.layout.addWidget(self.list_widget, stretch=1); self.layout.addWidget(self.selected_heroes_label)
        self.layout.addWidget(self.copy_button); self.layout.addWidget(self.clear_button)

    def _connect_signals(self):
        # Соединяем сигналы с методами MainWindow, а не ActionController напрямую отсюда
        # ActionController будет подключен к сигналам MainWindow
        if hasattr(self.window, 'action_controller') and self.window.action_controller:
            if hasattr(self.window.action_controller, 'handle_copy_team'):
                 self.copy_button.clicked.connect(self.window.action_controller.handle_copy_team)
            if hasattr(self.window.action_controller, 'handle_clear_all'):
                 self.clear_button.clicked.connect(self.window.action_controller.handle_clear_all)
        else:
            logging.error("[RightPanel] ActionController not found in parent window for connecting button signals.")


    def update_language(self):
        self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
        self.copy_button.setText(translations.get_text('copy_rating', language=self.logic.DEFAULT_LANGUAGE))
        self.clear_button.setText(translations.get_text('clear_all', language=self.logic.DEFAULT_LANGUAGE))