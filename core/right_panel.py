# File: core/right_panel.py
# Импортируем get_text напрямую
from core.translations import get_text
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
    QWidget, # Добавлен QWidget
    QMenu # Добавлен QMenu
)

# Импортируем делегат
from delegate import HotkeyFocusDelegate # Используем относительный импорт

# Импортируем список героев из корня проекта
# Добавляем '..' для выхода из 'core'
from heroes_bd import heroes

# Используется для передачи имени героя
HERO_NAME_ROLE = Qt.UserRole + 1

# Функция create_right_panel теперь не нужна, используем класс напрямую
# def create_right_panel(window, initial_mode="middle"):
#     right_panel = RightPanel(window, initial_mode)
#     return right_panel.frame

class RightPanel:
    """
    Класс для создания и управления правой панелью.
    """
    # Добавляем type hinting для window (ожидаем объект с атрибутами logic, right_images и методами)
    def __init__(self, window: QWidget, initial_mode="middle"):
        """
        Инициализация правой панели.
        """
        self.window = window
        # Добавляем проверку наличия атрибута logic
        if not hasattr(window, 'logic'):
            raise AttributeError("Объект 'window' должен иметь атрибут 'logic'.")
        self.logic = window.logic
        self.initial_mode = initial_mode

        # --- Создание виджетов ---
        self.frame = QFrame(window) # Родитель - главное окно
        self.frame.setObjectName("right_frame")
        self.frame.setFrameShape(QFrame.Shape.NoFrame) # Убираем рамку у QFrame

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("right_list_widget")

        # Используем get_text напрямую, передавая язык из logic
        self.selected_heroes_label = QLabel(get_text("selected", language=self.logic.DEFAULT_LANGUAGE))
        self.selected_heroes_label.setObjectName("selected_heroes_label")
        self.selected_heroes_label.setWordWrap(True)

        self.copy_button = QPushButton(get_text("copy_rating", language=self.logic.DEFAULT_LANGUAGE))
        self.copy_button.setObjectName("copy_button")

        self.clear_button = QPushButton(get_text("clear_all", language=self.logic.DEFAULT_LANGUAGE))
        self.clear_button.setObjectName("clear_button")

        # Словарь для хранения QListWidgetItem
        self.hero_items = {}

        # --- Настройка виджетов и Layout ---
        self._setup_list_widget()
        self._populate_list_widget()
        self._setup_layout()
        self._connect_signals()

        # Сохраняем ссылки в главном окне (если нужно)
        # Эти атрибуты должны быть объявлены в MainWindow.__init__
        if hasattr(window, 'right_list_widget'):
            window.right_list_widget = self.list_widget
        if hasattr(window, 'selected_heroes_label'):
            window.selected_heroes_label = self.selected_heroes_label
        if hasattr(window, 'hero_items'):
            window.hero_items = self.hero_items # Обновляем словарь в MainWindow

    def _setup_list_widget(self):
        """Настраивает QListWidget."""
        delegate = HotkeyFocusDelegate(self.window) # Делегат для рамки фокуса
        self.list_widget.setItemDelegate(delegate)
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_widget.setMovement(QListView.Movement.Static)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setWordWrap(True)
        self.list_widget.setUniformItemSizes(True) # Оптимизация

        # Размеры и отступы
        if self.initial_mode == "max":
            icon_size = QSize(60, 60); grid_size = QSize(85, 95); self.list_widget.setSpacing(10)
        else: # middle
            icon_size = QSize(40, 40)
            grid_size = QSize(icon_size.width() + 15, icon_size.height() + 10) # Примерный расчет
            self.list_widget.setSpacing(4)
        self.list_widget.setIconSize(icon_size)
        self.list_widget.setGridSize(grid_size)

        # Стили
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: white; border: 1px solid #d3d3d3; border-radius: 3px;
                outline: 0; padding: 2px;
            }
            QListWidget::item {
                padding: 2px; margin: 1px; color: black; border-radius: 4px;
                border: 1px solid transparent; background-color: transparent;
                text-align: center;
            }
            QListWidget::item:selected { background-color: #3399ff; color: white; border: 1px solid #2d8ae5; }
            QListWidget::item:!selected:hover { background-color: #e0f7ff; border: 1px solid #cceeff; }
            QListWidget::item:focus { border: 1px solid transparent; outline: 0; }
        """)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _populate_list_widget(self):
        """Заполняет QListWidget элементами героев."""
        self.hero_items.clear() # Очищаем перед заполнением
        # Проверяем наличие атрибута right_images в window
        right_images = getattr(self.window, 'right_images', {})

        for hero in heroes:
            item = QListWidgetItem()
            item_text = hero if self.initial_mode == "max" else ""
            item.setText(item_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)

            icon_pixmap = right_images.get(hero) # Используем get для безопасного доступа
            if icon_pixmap and not icon_pixmap.isNull():
                item.setIcon(QIcon(icon_pixmap))
            # else: print(f"[WARN] No right image for {hero}")

            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setData(HERO_NAME_ROLE, hero)
            item.setToolTip(hero)

            if hero in self.logic.selected_heroes:
                item.setSelected(True)

            self.list_widget.addItem(item)
            self.hero_items[hero] = item

    def _setup_layout(self):
        """Создает и настраивает QVBoxLayout для панели."""
        self.layout = QVBoxLayout(self.frame)
        self.layout.setObjectName("right_panel_layout")
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        # Добавляем виджеты в layout
        self.layout.addWidget(self.list_widget, stretch=1) # Список растягивается
        self.layout.addWidget(self.selected_heroes_label)
        self.layout.addWidget(self.copy_button)
        self.layout.addWidget(self.clear_button)

    def _connect_signals(self):
        """Подключает сигналы виджетов к слотам главного окна."""
        # Проверяем наличие методов перед подключением
        if hasattr(self.window, 'handle_selection_changed'):
             self.list_widget.itemSelectionChanged.connect(self.window.handle_selection_changed)
        if hasattr(self.window, 'show_priority_context_menu'):
             self.list_widget.customContextMenuRequested.connect(self.window.show_priority_context_menu)
        if hasattr(self.window, 'copy_to_clipboard'):
             self.copy_button.clicked.connect(self.window.copy_to_clipboard)
        if hasattr(self.window, '_handle_clear_all'): # Подключаем к внутреннему слоту MainWindow
             self.clear_button.clicked.connect(self.window._handle_clear_all)

    def update_language(self):
        """Обновляет тексты на панели."""
        self.selected_heroes_label.setText(self.logic.get_selected_heroes_text()) # Обновляем текст метки
        self.copy_button.setText(get_text('copy_rating', language=self.logic.DEFAULT_LANGUAGE))
        self.clear_button.setText(get_text('clear_all', language=self.logic.DEFAULT_LANGUAGE))
        # Подсказки для QListWidget обновляются в MainWindow.update_language
