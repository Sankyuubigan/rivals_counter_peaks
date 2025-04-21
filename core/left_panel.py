# File: left_panel.py
from PySide6.QtWidgets import QFrame, QScrollArea, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

def create_left_panel(parent):
    """Создает левую панель (ScrollArea + ResultFrame + ResultLabel)."""
    left_frame = QFrame(parent)
    left_frame.setObjectName("left_frame_container") # Имя для контейнера левой панели
    layout = QVBoxLayout(left_frame)
    layout.setObjectName("left_frame_layout")
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0) # Убираем расстояние между ScrollArea и другими элементами (если будут)

    scroll_area = QScrollArea(left_frame)
    scroll_area.setObjectName("left_scroll_area")
    scroll_area.setWidgetResizable(True)
    # Убираем рамку у ScrollArea
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    layout.addWidget(scroll_area)

    # Frame внутри ScrollArea, где будут отображаться результаты
    result_frame = QFrame()
    result_frame.setObjectName("result_frame")
    # Убираем рамку у result_frame, стилизуем через display.py
    result_frame.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setWidget(result_frame)

    # Layout для result_frame (создается здесь, но заполняется в display.py)
    result_layout = QVBoxLayout(result_frame)
    result_layout.setObjectName("result_layout")
    result_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Элементы добавляются сверху вниз
    result_layout.setContentsMargins(2, 2, 2, 2) # Небольшие отступы внутри
    result_layout.setSpacing(1) # Минимальное расстояние между элементами
    result_frame.setLayout(result_layout) # Устанавливаем layout для frame

    # Метка, которая показывается, когда герои не выбраны
    # Она создается здесь, но добавляется/скрывается в display.py
    result_label = QLabel("Выберите героев") # Начальный текст
    result_label.setObjectName("result_label") # Имя объекта для поиска
    result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    result_label.setStyleSheet("color: gray; padding: 10px;") # Стиль для метки
    result_label.hide() # Скрываем по умолчанию
    result_layout.addWidget(result_label) # Добавляем в layout, чтобы ее можно было найти

    def update_scrollregion():
        """Обновляет геометрию ScrollArea."""
        # print("[DEBUG] update_scrollregion called")
        scroll_area.updateGeometry()
        # Можно добавить прокрутку вверх, если нужно
        # scroll_area.verticalScrollBar().setValue(0)

    # Возвращаем ScrollArea (холст), Frame для результатов, Метку и функцию обновления
    return scroll_area, result_frame, result_label, update_scrollregion