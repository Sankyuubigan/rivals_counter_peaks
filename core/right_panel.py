# File: right_panel.py
from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QListWidget, QListWidgetItem, QVBoxLayout,
                               QScrollArea, QWidget, QListView, QAbstractItemView, QMenu)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from heroes_bd import heroes
from translations import get_text

# Константа для хранения имени героя в данных элемента
HERO_NAME_ROLE = Qt.UserRole + 1

def create_right_panel(window, initial_mode="middle"):
    """
    Создает правую панель с QListWidget для выбора героев.
    Отображает иконку над текстом (только в max режиме), использует стандартное выделение.
    """
    logic = window.logic

    right_frame = QFrame(window)
    layout = QVBoxLayout(right_frame)
    layout.setContentsMargins(5, 5, 5, 5)

    list_widget = QListWidget()
    window.right_list_widget = list_widget # Сохраняем ссылку

    # --- Настройка QListWidget ---
    list_widget.setViewMode(QListView.ViewMode.IconMode)
    list_widget.setResizeMode(QListView.ResizeMode.Adjust)
    list_widget.setMovement(QListView.Movement.Static)
    list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    list_widget.setWordWrap(True) # В max режиме может понадобиться

    # --- Размеры иконок и сетки ---
    if initial_mode == "max":
        icon_size = QSize(60, 60)
        grid_size = QSize(85, 95) # Ячейка больше иконки для текста
        list_widget.setSpacing(10)
    else: # middle (текста нет)
        icon_size = QSize(35, 35)
        # Уменьшаем высоту ячейки, т.к. нет текста
        grid_size = QSize(55, 50) # Ширина та же, высота меньше
        list_widget.setSpacing(5)

    list_widget.setIconSize(icon_size)
    list_widget.setGridSize(grid_size)

    # --- Стили для ListWidget ---
    list_widget.setStyleSheet("""
        QListWidget {
            background-color: white;
            border: 1px solid #d3d3d3;
            outline: 0;
        }
        QListWidget::item {
            padding: 2px;
            margin: 1px;
            border: 1px solid transparent;
            background-color: transparent;
            color: black;
        }
        /* Стиль для ВЫДЕЛЕННОГО элемента */
        QListWidget::item:selected {
            background-color: #3399ff; /* Синий фон */
            color: white;             /* Белый текст */
            border: 1px solid #2d8ae5;
            border-radius: 3px;
        }
        /* Стиль при наведении на НЕвыделенный */
        QListWidget::item:!selected:hover {
            background-color: #e0f7ff;
            border: 1px solid #cceeff;
            color: black; /* Убедимся, что текст остается черным */
        }
        /* Стиль при наведении на ВЫДЕЛЕННЫЙ (оставляем как selected, но можно добавить легкое изменение) */
        QListWidget::item:selected:hover {
            background-color: #2d8ae5; /* Чуть темнее синий */
            color: white;
            border: 1px solid #287acc;
            border-radius: 3px;
        }
    """)
    list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    selected_heroes_label = QLabel(get_text('selected'))
    selected_heroes_label.setWordWrap(True)

    # --- Создание QListWidgetItem ---
    print("Создание QListWidgetItems...")
    hero_items = {}
    window.hero_items = hero_items

    for i, hero in enumerate(heroes):
        item = QListWidgetItem()

        # --- Устанавливаем текст только для max режима ---
        if initial_mode == "max":
            item.setText(hero)
            item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        else:
            item.setText("") # Пустой текст для middle режима

        icon_pixmap = window.right_images.get(hero)
        if icon_pixmap and not icon_pixmap.isNull():
            item.setIcon(QIcon(icon_pixmap))
        else:
            print(f"Предупреждение: Нет иконки для {hero}")

        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        item.setData(HERO_NAME_ROLE, hero)

        if hero in logic.selected_heroes:
            item.setSelected(True)

        list_widget.addItem(item)
        hero_items[hero] = item

    # --- Подключаем сигнал изменения ВЫДЕЛЕНИЯ ---
    list_widget.itemSelectionChanged.connect(window.handle_selection_changed)

    # --- Контекстное меню ---
    list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    list_widget.customContextMenuRequested.connect(window.show_priority_context_menu)

    layout.addWidget(list_widget, stretch=1)
    layout.addWidget(selected_heroes_label)

    copy_button = QPushButton(get_text('copy_rating'))
    copy_button.clicked.connect(window.copy_to_clipboard)
    layout.addWidget(copy_button)

    clear_button = QPushButton(get_text('clear_all'))
    clear_button.clicked.connect(lambda: logic.clear_all(window.update_ui_after_logic_change))
    layout.addWidget(clear_button)

    print("Правая панель с QListWidget создана.")
    return right_frame, selected_heroes_label