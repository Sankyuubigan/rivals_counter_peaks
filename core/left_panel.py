from PySide6.QtWidgets import QFrame, QScrollArea, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

def create_left_panel(parent):
    left_frame = QFrame(parent)
    layout = QVBoxLayout(left_frame)
    layout.setContentsMargins(0, 0, 0, 0)

    scroll_area = QScrollArea(left_frame)
    scroll_area.setWidgetResizable(True)
    layout.addWidget(scroll_area)

    result_frame = QFrame()
    scroll_area.setWidget(result_frame)
    result_layout = QVBoxLayout(result_frame)
    result_layout.setAlignment(Qt.AlignTop)

    result_label = QLabel("Выберите героев")
    result_layout.addWidget(result_label)

    def update_scrollregion():
        scroll_area.update()

    return scroll_area, result_frame, result_label, update_scrollregion