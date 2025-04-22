# File: left_panel.py
# File: left_panel.py
from PySide6.QtWidgets import QFrame, QScrollArea, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from core.horizontal_list import HorizontalList

def create_left_panel(window):
    """Создает левую панель."""
    left_panel = LeftPanel(window)
    return left_panel.scroll_area, left_panel.result_frame, left_panel.result_label, left_panel.update_scrollregion


class LeftPanel:
    def __init__(self, parent: QWidget):
        self.parent = parent
        self.left_frame = None
        self.scroll_area = None
        self.result_frame = None
        self.heroes_list = None
        self.result_label = None
        self.setup_ui()

    def setup_ui(self):
        self._create_layout()
        self._create_widgets()        
        self._setup_widgets()
        self._setup_layout()

    def _create_widgets(self):
        """Создает виджеты: QFrame, QScrollArea, QLabel."""
        self.left_frame = QFrame(self.parent)
        self.scroll_area = QScrollArea(self.left_frame)
        self.result_frame = QFrame()
        self.heroes_list = HorizontalList(self.heroes_layout)
        self.result_label = QLabel("Выберите героев")

    def _setup_widgets(self):
        """Настраивает виджеты."""
        self.left_frame.setObjectName("left_frame_container")
        self.scroll_area.setObjectName("left_scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.result_frame.setObjectName("result_frame")
        self.result_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidget(self.result_frame)
        self.result_label.setObjectName("result_label")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("color: gray; padding: 10px;")
        self.result_label.hide()
        self.heroes_list.setObjectName("left_heroes_list")

    def _create_layout(self):
        """Создает layout."""
        self.layout = QVBoxLayout(self.left_frame)
        self.heroes_layout = QHBoxLayout()
        self.result_layout = QVBoxLayout(self.result_frame)

    def _setup_layout(self):
        """Настраивает layout."""
        self.layout.setObjectName("left_frame_layout")
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.scroll_area, )
        self.result_layout.setObjectName("result_layout")
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.result_layout.setContentsMargins(2, 2, 2, 2)
        self.result_layout.setSpacing(1)
        self.result_frame.setLayout(self.result_layout)
        self.result_layout.addWidget(self.result_label)
        self.result_layout.addLayout(self.heroes_layout)
    def update_scrollregion(self):
        """Обновляет геометрию ScrollArea."""
        self.scroll_area.updateGeometry()

    def get_widgets(self):
        return self.scroll_area, self.result_frame, self.result_label, self.update_scrollregion