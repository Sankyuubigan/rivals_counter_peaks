# File: core/left_panel.py
from PySide6.QtWidgets import QFrame, QScrollArea, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

# <<< ИСПРАВЛЕНО: Используем абсолютные импорты >>>
# from core.horizontal_list import HorizontalList # Этот импорт здесь не нужен
# <<< ----------------------------------------- >>>

# <<< ИСПРАВЛЕНО: Функция create_left_panel теперь возвращает кортеж >>>
def create_left_panel(parent_widget: QWidget):
    """Создает левую панель и возвращает ее основные компоненты."""
    left_panel_instance = LeftPanel(parent_widget)
    return left_panel_instance.get_widgets() # Возвращаем результат get_widgets
# <<< ---------------------------------------------------------- >>>

class LeftPanel:
    def __init__(self, parent: QWidget):
        self.parent = parent
        # Инициализируем атрибуты до вызова setup_ui
        self.left_frame: QFrame | None = None
        self.scroll_area: QScrollArea | None = None
        self.result_frame: QFrame | None = None
        self.result_layout: QVBoxLayout | None = None
        self.result_label: QLabel | None = None
        # Запускаем настройку UI
        self.setup_ui()

    def setup_ui(self):
        self._create_widgets()
        self._create_layout()
        self._setup_widgets()
        self._setup_layout()

    def _create_widgets(self):
        """Создает виджеты: QFrame, QScrollArea, QLabel."""
        self.left_frame = QFrame(self.parent)
        self.scroll_area = QScrollArea(self.left_frame)
        self.result_frame = QFrame() # Родителя указывать не нужно
        self.result_label = QLabel("Выберите героев")

    def _setup_widgets(self):
        """Настраивает виджеты."""
        self.left_frame.setObjectName("left_frame_container")
        self.left_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setObjectName("left_scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.result_frame.setObjectName("result_frame")
        self.result_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidget(self.result_frame)
        self.result_label.setObjectName("result_label")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("color: gray; padding: 10px;")
        # self.result_label.hide() # Начальное состояние будет установлено в MainWindow

    def _create_layout(self):
        """Создает layout'ы."""
        self.layout = QVBoxLayout(self.left_frame)
        self.result_layout = QVBoxLayout(self.result_frame)

    def _setup_layout(self):
        """Настраивает финальную структуру layout'ов."""
        self.layout.setObjectName("left_frame_layout")
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.scroll_area)

        self.result_layout.setObjectName("result_layout")
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.result_layout.setContentsMargins(2, 2, 2, 2)
        self.result_layout.setSpacing(1)
        # Добавляем result_label в result_layout
        self.result_layout.addWidget(self.result_label)

    def update_scrollregion(self):
        """Обновляет геометрию ScrollArea."""
        if self.scroll_area:
             self.scroll_area.updateGeometry()

    def get_widgets(self):
        """Возвращает основные виджеты панели для использования в MainWindow."""
        return self.scroll_area, self.result_frame, self.result_label, self.update_scrollregion