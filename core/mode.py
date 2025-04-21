from PySide6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QListWidget, QComboBox, QScrollArea)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap

from left_panel import create_left_panel
from right_panel import create_right_panel
from images_load import get_images_for_mode, SIZES
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes
from translations import get_text

# from build import version # Версия теперь берется из MainWindow
import time
import gc  # Для сборки мусора


# --- Вспомогательная функция для очистки layout ---\ndef clear_layout_recursive(layout):
    if layout is None: return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            # print(f"Deleting widget: {widget.objectName()} ({type(widget).__name__})")
            widget.deleteLater()
        else:
            sub_layout = item.layout()
            if sub_layout is not None:
                # print(f"Clearing sub-layout: {sub_layout.objectName()} ({type(sub_layout).__name__})")
                clear_layout_recursive(sub_layout) # Рекурсивно очищаем вложенный layout
                # Удаляем сам объект QLayout
                sub_layout.deleteLater()
            else:
                spacer = item.spacerItem()
                if spacer is not None:
                    # print("Removing spacer")
                    layout.removeItem(item) # Удаляем spacer item


PANEL_MIN_WIDTHS = {
    'max': {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300},
    'min': {'left': 0, 'right': 0}  # Левая панель видима, но мин. ширина не важна
}
MODE_DEFAULT_WINDOW_SIZES = {
    'max': {'width': 1100, 'height': 800},
    'middle': {'width': 950, 'height': 600},
    'min': {'width': 600, 'height': 0}  # Высота будет переопределена в update_interface_for_mode
}


class ModeManager:
    def __init__(self, main_window):
        self.current_mode = "middle"
        self.modes = {
            "min": Mode("min", None, None),
            "middle": Mode("middle", None, None),
            "max": Mode("max", None, None),
        }
        self.main_window = main_window

    def _validate_mode_name(self, mode_name: str) -> None:
        if mode_name not in self.modes:
            raise ValueError(f"Неизвестный режим: {mode_name}")

    def _get_mode(self, mode_name: str) -> Mode:
        self._validate_mode_name(mode_name)
        return self.modes[mode_name]

    def _get_mode_by_name(self, mode_name: str) -> Mode:
        return self._get_mode(mode_name)

    def _update_current_mode(self, mode_name):
        self.current_mode = mode_name

    def _set_window_geometry(self, window, mode_name):
        mode = self._get_mode_by_name(mode_name)
        if mode.pos is not None:
            window.move(mode.pos)

    def change_mode(self, window, mode):
        self._change_mode(window, mode)

class Mode:
    """Data model for different modes."""


    def __init__(self, name, pos, size):
        self.name = name
        self.pos = pos
        self.size = size