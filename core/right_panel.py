# File: core/right_panel.py
from info import translations
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QLabel, QListWidget, QListWidgetItem,
    QListView, QPushButton, QVBoxLayout, QWidget
)
from database.heroes_bd import heroes
from images_load import is_invalid_pixmap, SIZES # Добавляем SIZES
from logic import TEAM_SIZE
import logging

HERO_NAME_ROLE = Qt.UserRole + 1
TARGET_COLUMN_COUNT = 5 # Желаемое количество столбцов

class RightPanel:
    """Класс для создания и управления правой панелью."""
    def __init__(self, window: QWidget, initial_mode="middle"):
        self.window = window
        if not hasattr(window, 'logic'): raise AttributeError("Объект 'window' должен иметь атрибут 'logic'.")
        self.logic = window.logic
        self.current_mode = initial_mode # Сохраняем текущий режим

        self.frame = QFrame(window); self.frame.setObjectName("right_frame"); self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget = QListWidget(); self.list_widget.setObjectName("right_list_widget")
        
        self.selected_heroes_label = QLabel(
            translations.get_text("selected_none", language=self.logic.DEFAULT_LANGUAGE, max_team_size=TEAM_SIZE))
        
        self.selected_heroes_label.setObjectName("selected_heroes_label"); self.selected_heroes_label.setWordWrap(True)
        self.copy_button = QPushButton(translations.get_text("copy_rating", language=self.logic.DEFAULT_LANGUAGE)); self.copy_button.setObjectName("copy_button")
        self.clear_button = QPushButton(translations.get_text("clear_all", language=self.logic.DEFAULT_LANGUAGE)); self.clear_button.setObjectName("clear_button")
        self.hero_items = {}

        self._setup_list_widget() # Передаем режим
        self._populate_list_widget()
        self._setup_layout()
        self._connect_signals()

    def _setup_list_widget(self):
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust) # Позволяет QListWidget управлять размером элементов
        self.list_widget.setMovement(QListView.Movement.Static)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setWordWrap(True) # Для текста под иконками, если он есть
        self.list_widget.setUniformItemSizes(True) # Для производительности, если все иконки одного размера

        # Получаем размеры иконок для текущего режима
        icon_width, icon_height = SIZES.get(self.current_mode, {}).get('right', (40, 40))
        self.list_widget.setIconSize(QSize(icon_width, icon_height))

        # Рассчитываем gridSize для достижения ~TARGET_COLUMN_COUNT столбцов
        # Это примерный расчет. Реальное количество столбцов также будет зависеть от ширины панели.
        # Мы устанавливаем item'ам фиксированный размер через gridSize, чтобы контролировать их ширину.
        # Предполагаем небольшой отступ (spacing_guess) между иконками
        spacing_guess = 4 if self.current_mode == "middle" else 10 # Примерные значения
        # Ширина элемента = ширина иконки + небольшой запас для текста/отступов
        item_width_for_calc = icon_width + 15 # Запас для текста под иконкой и внутренних отступов QListWidgetItem
        # Высота элемента = высота иконки + запас для текста
        item_height_for_calc = icon_height + (20 if self.current_mode == "max" else 10)

        self.list_widget.setGridSize(QSize(item_width_for_calc, item_height_for_calc))
        self.list_widget.setSpacing(spacing_guess)
        
        # self.list_widget.setFlow(QListView.Flow.LeftToRight) # Элементы располагаются слева направо
        # self.list_widget.setWrapping(True) # Включаем перенос строк

        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        viewport = self.list_widget.viewport()
        if viewport:
            logging.debug(f"[RightPanel] List widget configured for mode '{self.current_mode}'. IconSize: {icon_width}x{icon_height}, GridSize: {item_width_for_calc}x{item_height_for_calc}, Spacing: {spacing_guess}")
        else:
            logging.debug(f"[RightPanel] List widget configured for mode '{self.current_mode}'. Viewport is None.")


    def _populate_list_widget(self):
        self.hero_items.clear()
        right_images = getattr(self.window, 'right_images', {})
        if not right_images: logging.warning("[RightPanel] 'right_images' not found or empty in main window.")

        # Получаем размеры иконок для текущего режима (снова, т.к. populate может вызываться отдельно)
        icon_w, icon_h = SIZES.get(self.current_mode, {}).get('right', (40, 40))

        for hero in heroes:
            item = QListWidgetItem()
            # Текст под иконкой только для 'max' режима, как и было
            item_text = hero if self.current_mode == "max" else ""
            item.setText(item_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
            
            icon_pixmap : QPixmap | None = right_images.get(hero)
            if is_invalid_pixmap(icon_pixmap):
                logging.warning(f"[RightPanel] Invalid or missing icon for hero: '{hero}'. Setting placeholder.")
                # Можно создать плейсхолдер с текстом, если иконка не загрузилась
                # placeholder_pixmap = QPixmap(icon_w, icon_h)
                # placeholder_pixmap.fill(Qt.GlobalColor.lightGray)
                # painter = QPainter(placeholder_pixmap)
                # painter.drawText(placeholder_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, hero[:1])
                # painter.end()
                # item.setIcon(QIcon(placeholder_pixmap))
            else:
                item.setIcon(QIcon(icon_pixmap))
            
            # Устанавливаем размер элемента, чтобы он был предсказуем для расчета столбцов
            # Это может быть переопределено gridSize, но для ясности
            item.setSizeHint(QSize(icon_w + 10, icon_h + (20 if self.current_mode == "max" else 10) ))


            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setData(HERO_NAME_ROLE, hero)
            item.setToolTip(hero)
            self.list_widget.addItem(item)
            self.hero_items[hero] = item
        logging.debug(f"[RightPanel] List populated with {len(self.hero_items)} items for mode {self.current_mode}.")

    def _setup_layout(self):
        self.layout = QVBoxLayout(self.frame); self.layout.setObjectName("right_panel_layout")
        self.layout.setContentsMargins(5, 5, 5, 5); self.layout.setSpacing(5)
        self.layout.addWidget(self.list_widget, stretch=1); self.layout.addWidget(self.selected_heroes_label)
        self.layout.addWidget(self.copy_button); self.layout.addWidget(self.clear_button)

    def _connect_signals(self):
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
