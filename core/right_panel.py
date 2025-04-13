# File: right_panel.py
from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QListWidget, QListWidgetItem, QVBoxLayout,
                               QListView, QAbstractItemView, QMenu)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from heroes_bd import heroes
from translations import get_text
# Импортируем делегат
from delegate import HotkeyFocusDelegate

# Константа для хранения имени героя в данных элемента
HERO_NAME_ROLE = Qt.UserRole + 1

# Принимаем 'window' для доступа к logic и right_images
def create_right_panel(window, initial_mode="middle"):
    """
    Создает правую панель с QListWidget.
    Использует делегат ТОЛЬКО для отрисовки рамки фокуса.
    """
    logic = window.logic

    right_frame = QFrame(window)
    layout = QVBoxLayout(right_frame)
    layout.setContentsMargins(5, 5, 5, 5)

    list_widget = QListWidget()
    window.right_list_widget = list_widget # Сохраняем ссылку в окне

    # --- Создание и установка делегата ---
    delegate = HotkeyFocusDelegate(window)
    list_widget.setItemDelegate(delegate)
    # ------------------------------------

    # --- Настройка QListWidget ---
    list_widget.setViewMode(QListView.ViewMode.IconMode)
    list_widget.setResizeMode(QListView.ResizeMode.Adjust)
    list_widget.setMovement(QListView.Movement.Static)
    list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    list_widget.setWordWrap(True)

    # --- Размеры иконок и сетки ---
    if initial_mode == "max":
        icon_size = QSize(60, 60); grid_size = QSize(85, 95); list_widget.setSpacing(10)
    else: # middle
        icon_size = QSize(35, 35); grid_size = QSize(55, 50); list_widget.setSpacing(5)
    list_widget.setIconSize(icon_size); list_widget.setGridSize(grid_size)

    # --- Стили для ListWidget ---
    # Убираем правила для [hotkeyFocus="true"]
    list_widget.setStyleSheet("""
        QListWidget {
            background-color: white;
            border: 1px solid #d3d3d3;
            outline: 0;
        }
        QListWidget::item {
            padding: 2px;
            margin: 1px;
            color: black;
            border-radius: 3px;
            border: 1px solid transparent;
            background-color: transparent;
        }
        QListWidget::item:selected {
            background-color: #3399ff;
            color: white;
            border: 1px solid #2d8ae5;
        }
        QListWidget::item:!selected:hover {
            background-color: #e0f7ff;
            border: 1px solid #cceeff;
        }
    """)
    list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    selected_heroes_label = QLabel(get_text('selected'))
    selected_heroes_label.setWordWrap(True)

    # --- Создание QListWidgetItem ---
    hero_items = {}
    window.hero_items = hero_items

    for i, hero in enumerate(heroes):
        item = QListWidgetItem()
        item_text = hero if initial_mode == "max" else ""
        item.setText(item_text)
        if initial_mode == "max": item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        else: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_pixmap = window.right_images.get(hero)
        if icon_pixmap and not icon_pixmap.isNull(): item.setIcon(QIcon(icon_pixmap))
        else: print(f"Предупреждение: Нет иконки для {hero}")

        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        item.setData(HERO_NAME_ROLE, hero) # Имя героя
        # Больше не устанавливаем свойство hotkeyFocus здесь
        item.setToolTip(hero) # Базовая подсказка

        if hero in logic.selected_heroes: item.setSelected(True)

        list_widget.addItem(item)
        hero_items[hero] = item

    # --- Подключаем сигналы ---
    list_widget.itemSelectionChanged.connect(window.handle_selection_changed)
    list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    list_widget.customContextMenuRequested.connect(window.show_priority_context_menu)

    layout.addWidget(list_widget, stretch=1)
    layout.addWidget(selected_heroes_label)

    copy_button = QPushButton(get_text('copy_rating'))
    copy_button.clicked.connect(window.copy_to_clipboard)
    layout.addWidget(copy_button)

    clear_button = QPushButton(get_text('clear_all'))
    clear_button.clicked.connect(lambda: (logic.clear_all(), window.update_ui_after_logic_change()))
    layout.addWidget(clear_button)

    return right_frame, selected_heroes_label