# File: core/right_panel.py
from info import translations
from PySide6.QtWidgets import QAbstractItemView, QFrame, QLabel, QListWidget, QListWidgetItem, QListView, QPushButton, QVBoxLayout, QWidget, QComboBox, QHBoxLayout
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
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

class RightPanel(QWidget):
    """Класс для создания и управления правой панелью."""
    def __init__(self, window: QWidget, initial_mode="middle"):
        self.window = window
        if not hasattr(window, 'logic'): raise AttributeError("Объект 'window' должен иметь атрибут 'logic'.")
        self.logic = window.logic
        self.current_mode = initial_mode
        
        # Инициализация виджетов
        self.frame = QFrame(window)
        self.frame.setObjectName("right_frame")
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("right_list_widget")
        
        self.selected_heroes_label = QLabel(
            translations.get_text("selected_none", language=self.logic.DEFAULT_LANGUAGE, max_team_size=TEAM_SIZE))
        self.selected_heroes_label.setObjectName("selected_heroes_label")
        self.selected_heroes_label.setWordWrap(True)
        
        self.copy_button = QPushButton(translations.get_text("copy_rating", language=self.logic.DEFAULT_LANGUAGE))
        self.copy_button.setObjectName("copy_button")
        
        self.clear_button = QPushButton(translations.get_text("clear_all", language=self.logic.DEFAULT_LANGUAGE))
        self.clear_button.setObjectName("clear_button")
        
        # Новый виджет для выбора карты
        self.map_combo_box = QComboBox()
        self.map_combo_box.setObjectName("map_combo_box")
        self.map_combo_box.setToolTip(translations.get_text("select_map_tooltip", default_text="Выбрать карту для бонуса к рейтингу"))
        
        self.hero_items = {}
        self._setup_list_widget()
        self._populate_map_combo_box()
        self._populate_list_widget()
        self._setup_layout()
        self._connect_signals()
        self._apply_selected_stylesheet()
        
    def _populate_map_combo_box(self):
        """Заполняет выпадающий список картами."""
        self.map_combo_box.clear()
        # Добавляем опцию "Без карты"
        self.map_combo_box.addItem(translations.get_text("no_map_option", default_text="Без карты"), None)
        
        # Получаем список карт из логики
        available_maps = self.logic.available_maps
        for map_name in available_maps:
            self.map_combo_box.addItem(map_name, map_name)
        
        # Устанавливаем текущую выбранную карту
        self._update_map_selection()

    def _update_map_selection(self):
        """Обновляет выбранную опцию в QComboBox на основе self.logic.selected_map."""
        if self.logic.selected_map:
            index = self.map_combo_box.findData(self.logic.selected_map)
            if index >= 0:
                self.map_combo_box.setCurrentIndex(index)
                return
        # Если карта не выбрана или не найдена, выбираем "Без карты"
        self.map_combo_box.setCurrentIndex(0)

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
        self.layout = QVBoxLayout(self.frame)
        self.layout.setObjectName("right_panel_layout")
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # Добавляем виджет выбора карты
        self.layout.addWidget(self.map_combo_box)
        
        self.layout.addWidget(self.list_widget, stretch=1)
        self.layout.addWidget(self.selected_heroes_label)
        
        # Создаем горизонтальный layout для кнопок
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.clear_button)
        self.layout.addLayout(button_layout)

    def _connect_signals(self):
        if hasattr(self.window, 'action_controller'):
            self.copy_button.clicked.connect(self.window.action_controller.handle_copy_team)
            self.clear_button.clicked.connect(self.window.action_controller.handle_clear_all)
        
        # Подключаем сигнал изменения выбора карты
        self.map_combo_box.currentTextChanged.connect(self._on_map_changed)

    def _on_map_changed(self, map_name: str):
        """Слот, вызываемый при изменении карты в выпадающем списке."""
        selected_map_data = self.map_combo_box.currentData()
        if selected_map_data != self.logic.selected_map:
            self.logic.set_map_by_name(selected_map_data)
            # Запускаем полное обновление UI, так как изменились рейтинги
            if hasattr(self.window, 'ui_updater') and self.window.ui_updater:
                self.window.ui_updater.update_ui_after_logic_change()

    def update_language(self):
        self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
        self.copy_button.setText(translations.get_text('copy_rating', language=self.logic.DEFAULT_LANGUAGE))
        self.clear_button.setText(translations.get_text('clear_all', language=self.logic.DEFAULT_LANGUAGE))
        # Обновляем подсказку для комбобокса
        self.map_combo_box.setToolTip(translations.get_text("select_map_tooltip", default_text="Выбрать карту для бонуса к рейтингу"))
        # Обновляем элементы комбобокса
        self.map_combo_box.setItemText(0, translations.get_text("no_map_option", default_text="Без карты"))
        for i in range(1, self.map_combo_box.count()):
            self.map_combo_box.setItemText(i, self.map_combo_box.itemData(i))
        self._update_map_selection()

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