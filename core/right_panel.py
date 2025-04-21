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
    Множественный выбор должен работать.
    """
    logic = window.logic

    right_frame = QFrame(window)
    right_frame.setObjectName("right_frame") # Имя объекта
    # Убираем рамку у самого QFrame
    right_frame.setFrameShape(QFrame.Shape.NoFrame)
    layout = QVBoxLayout(right_frame)
    layout.setObjectName("right_panel_layout")
    layout.setContentsMargins(5, 5, 5, 5) # Отступы внутри панели
    layout.setSpacing(5) # Расстояние между элементами

    list_widget = QListWidget()
    window.right_list_widget = list_widget # Сохраняем ссылку в окне
    list_widget.setObjectName("right_list_widget") # Имя объекта


    # --- Создание и установка делегата ---
    # Делегат отвечает за отрисовку рамки фокуса хоткея
    delegate = HotkeyFocusDelegate(window)
    list_widget.setItemDelegate(delegate)
    # ------------------------------------

    # --- Настройка QListWidget ---
    list_widget.setViewMode(QListView.ViewMode.IconMode) # Иконки сеткой
    list_widget.setResizeMode(QListView.ResizeMode.Adjust) # Автоподстройка колонок
    list_widget.setMovement(QListView.Movement.Static) # Элементы неперемещаемые
    list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection) # Множественный выбор
    list_widget.setWordWrap(True) # Перенос текста под иконкой (для max режима)
    list_widget.setUniformItemSizes(True) # Оптимизация, если все элементы одного размера

    # --- Размеры иконок и сетки ---
    if initial_mode == "max":
        icon_size = QSize(60, 60); grid_size = QSize(85, 95); list_widget.setSpacing(10)
    else: # middle
        icon_size = QSize(40, 40)
        # grid_size должен быть чуть больше иконки + место для текста (если он есть)
        # Рассчитываем примерно: иконка + отступы + место под текст (если нужно)
        grid_width = icon_size.width() + 15 # Запас по ширине
        grid_height = icon_size.height() + 10 # Небольшой запас по высоте
        grid_size = QSize(grid_width, grid_height)
        list_widget.setSpacing(4) # Отступ между элементами сетки
    list_widget.setIconSize(icon_size); list_widget.setGridSize(grid_size)
    # -------------------------------------------------------

    # --- Стили для ListWidget ---
    list_widget.setStyleSheet("""
        QListWidget {
            background-color: white;
            border: 1px solid #d3d3d3; /* Рамка самого списка */
            border-radius: 3px;
            outline: 0; /* Убираем стандартную рамку фокуса Qt */
            padding: 2px; /* Небольшой отступ внутри списка */
        }
        QListWidget::item {
            /* Отступы вокруг элемента сетки */
            padding: 2px;
            margin: 1px;
            color: black; /* Цвет текста по умолчанию */
            border-radius: 4px; /* Скругление углов элемента */
            border: 1px solid transparent; /* Прозрачная рамка по умолчанию */
            background-color: transparent; /* Прозрачный фон по умолчанию */
            /* Выравнивание текста под иконкой по центру */
            text-align: center;
        }
        /* Стиль для выделенного элемента */
        QListWidget::item:selected {
            background-color: #3399ff; /* Цвет фона выделения */
            color: white; /* Цвет текста выделения */
            border: 1px solid #2d8ae5; /* Рамка выделения */
        }
        /* Стиль для элемента при наведении мыши (не выделенного) */
        QListWidget::item:!selected:hover {
            background-color: #e0f7ff; /* Светло-голубой фон */
            border: 1px solid #cceeff; /* Светло-голубая рамка */
        }
        /* Убираем рамку фокуса вокруг элемента при навигации клавиатурой Qt (делегат рисует свою) */
        QListWidget::item:focus {
             border: 1px solid transparent;
             outline: 0;
        }
    """)
    list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Убираем фокус самого виджета

    # Метка для отображения выбранных героев
    selected_heroes_label = QLabel(get_text('selected', language=logic.DEFAULT_LANGUAGE))
    selected_heroes_label.setWordWrap(True)
    selected_heroes_label.setObjectName("selected_heroes_label") # Имя объекта


    # --- Создание QListWidgetItem для каждого героя ---
    hero_items = {} # Очищаем словарь перед заполнением
    window.hero_items = hero_items # Сохраняем ссылку на словарь в главном окне

    for i, hero in enumerate(heroes):
        item = QListWidgetItem()
        # Текст элемента: имя героя в max режиме, пусто в middle
        item_text = hero if initial_mode == "max" else ""
        item.setText(item_text)
        # Выравнивание текста: под иконкой по центру
        item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)

        # Установка иконки
        icon_pixmap = window.right_images.get(hero)
        if icon_pixmap and not icon_pixmap.isNull():
            item.setIcon(QIcon(icon_pixmap))
        else:
            # print(f"Предупреждение: Нет иконки для {hero} в right_images")
            # Можно установить заглушку, но лучше убедиться, что изображения загружены
            pass

        # Флаги элемента: включен и выбираемый
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        # Сохраняем имя героя в пользовательских данных
        item.setData(HERO_NAME_ROLE, hero)
        # Устанавливаем подсказку с именем героя
        item.setToolTip(hero)

        # Устанавливаем начальное состояние выделения на основе логики
        if hero in logic.selected_heroes:
            item.setSelected(True)

        list_widget.addItem(item)
        hero_items[hero] = item # Сохраняем ссылку на элемент

    # --- Подключаем сигналы ---
    # Сигнал изменения выделения (срабатывает при клике или setSelected)
    list_widget.itemSelectionChanged.connect(window.handle_selection_changed)
    # Включаем пользовательское контекстное меню
    list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    # Подключаем сигнал для показа меню
    list_widget.customContextMenuRequested.connect(window.show_priority_context_menu)

    layout.addWidget(list_widget, stretch=1) # ListWidget занимает основное место
    layout.addWidget(selected_heroes_label)

    # Кнопки Копировать и Очистить
    copy_button = QPushButton(get_text('copy_rating', language=logic.DEFAULT_LANGUAGE))
    copy_button.setObjectName("copy_button") # Имя объекта
    copy_button.clicked.connect(window.copy_to_clipboard)
    layout.addWidget(copy_button)

    clear_button = QPushButton(get_text('clear_all', language=logic.DEFAULT_LANGUAGE))
    clear_button.setObjectName("clear_button") # Имя объекта
    # Вызываем _handle_clear_all для сброса фокуса хоткея и обновления UI
    clear_button.clicked.connect(window._handle_clear_all)
    layout.addWidget(clear_button)

    return right_frame, selected_heroes_label