# File: right_panel.py
from PySide6.QtCore import QSize, Qt

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QListView,
    QPushButton,
    QVBoxLayout,
)

from core.translations import get_text

# Импортируем делегат
from delegate import HotkeyFocusDelegate

# Используется для передачи имени героя
HERO_NAME_ROLE = Qt.UserRole + 1

# Принимаем 'window' для доступа к logic и right_images
def create_right_panel(window, initial_mode="middle"):
    """
    Создает правую панель с QListWidget.
    Использует делегат ТОЛЬКО для отрисовки рамки фокуса.
    Множественный выбор должен работать.
    """
    right_panel = RightPanel(window, initial_mode)
    return right_panel.frame, right_panel.selected_heroes_label


class RightPanel:
    """
    Класс для создания и управления правой панелью.
    """

    def __init__(self, window, initial_mode="middle"):
        """
        Инициализация правой панели.
        """
        self.window = window
        self.logic = window.logic
        self.initial_mode = initial_mode
        self.frame = QFrame(window)
        self.frame.setObjectName("right_frame")
        self.selected_heroes_label = QLabel(get_text("selected"))
        self.setup_ui()

    def setup_ui(self):
        """
        Настройка пользовательского интерфейса.
        """
        self._create_widgets()
        self._setup_widgets()
        self._create_layout()
        self._setup_layout()

    def _create_widgets(self):
        """
        Создание виджетов.
        """
        from heroes_bd import heroes
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.layout = QVBoxLayout(self.frame)
        self.list_widget = QListWidget()
        self.selected_heroes_label.setWordWrap(True)
        self.selected_heroes_label.setObjectName("selected_heroes_label")
        self.window.right_list_widget = self.list_widget
        self.list_widget.setObjectName("right_list_widget")
        self.copy_button = QPushButton(self.logic.get_text("copy_rating"))
        self.copy_button.setObjectName("copy_button"); self.copy_button.setText(self.window.get_text("copy_rating"))
        self.clear_button = QPushButton(self.window.get_text("clear_all"))
        self.clear_button.setObjectName("clear_button")
        self.hero_items = {}
        self.window.hero_items = self.hero_items
        for hero in heroes:
            item = QListWidgetItem()
            item_text = hero if self.initial_mode == "max" else ""
            item.setText(item_text)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter
            )
            icon_pixmap = self.window.right_images.get(hero)
            if icon_pixmap and not icon_pixmap.isNull():
                item.setIcon(QIcon(icon_pixmap))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setData(self.HERO_NAME_ROLE, hero)
            item.setToolTip(hero)
            if hero in self.logic.selected_heroes:
                item.setSelected(True)
            self.list_widget.addItem(item)
            self.hero_items[hero] = item

    def _setup_widgets(self):
        """
        Настройка виджетов.
        """
        # --- Настройка QListWidget ---
        # Делегат отвечает за отрисовку рамки фокуса хоткея
        delegate = HotkeyFocusDelegate(self.window)
        self.list_widget.setItemDelegate(delegate)
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)  # Иконки сеткой
        self.list_widget.setResizeMode(
           QListView.ResizeMode.Adjust
        )  # Автоподстройка колонок
        self.list_widget.setMovement(QListView.Movement.Static)
        self.list_widget.setSelectionMode(            
            QAbstractItemView.SelectionMode.MultiSelection
        )  # Множественный выбор
        self.list_widget.setWordWrap(True)  # Перенос текста под иконкой (для max режима)
        self.list_widget.setUniformItemSizes(True)  # Оптимизация, если все элементы одного размера
    # -------------------------------------------------------

        self.list_widget.setStyleSheet("""
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
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)# Убираем фокус самого виджета
        self.list_widget.itemSelectionChanged.connect(
            self.window.handle_selection_changed
        )
        self.list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.list_widget.customContextMenuRequested.connect(
            self.window.show_priority_context_menu
        )
        if self.initial_mode == "max":
            icon_size = QSize(60, 60); grid_size = QSize(85, 95); self.list_widget.setSpacing(10)
        else:
            icon_size = QSize(40, 40)
            grid_size = QSize(icon_size.width() + 15, icon_size.height() + 10)
            self.list_widget.setSpacing(4)
        self.list_widget.setIconSize(icon_size); self.list_widget.setGridSize(grid_size)
        self.copy_button.clicked.connect(self.window.copy_to_clipboard)
        self.clear_button.clicked.connect(self.window._handle_clear_all)

    def _create_layout(self):
        """
        Создание компоновки.
        """
        self.layout.setObjectName("right_panel_layout")
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

    def _setup_layout(self):
        """
        Настройка компоновки.
        """
        self.layout.addWidget(self.list_widget, stretch=1)
        self.layout.addWidget(self.selected_heroes_label)
        self.layout.addWidget(self.copy_button)
        self.layout.addWidget(self.clear_button)