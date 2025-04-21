from PySide6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QListWidget, QComboBox, QScrollArea)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QResizeEvent
PANEL_MIN_WIDTHS = {
    'max': {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300}, 'min': {'left': 0, 'right': 0}
}
MODE_DEFAULT_WINDOW_SIZES = {
    'max': {'width': 1100, 'height': 800}, 'middle': {'width': 950, 'height': 600}, 'min': {'width': 600, 'height': 0}}


class Mode:
    def __init__(self, name, pos, size, none):
        self.name = name
        self.pos = pos
        self.size = size


class ModeManager:
    def __init__(self, main_window):
        self.current_mode = "middle"
        self.modes = {
            "min": Mode("min", None, None, None),
            "middle": Mode("middle", None, None, None),
            "max": Mode("max", None, None, None)}
        self.main_window = main_window
    def clear_layout_recursive(self, layout):
        if layout is None: return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self.clear_layout_recursive(sub_layout)  # Рекурсивно очищаем вложенный layout
                    sub_layout.deleteLater()
                else:
                    spacer = item.spacerItem()
                    if spacer is not None:
                        layout.removeItem(item)
        self.current_mode = "middle"

    def _validate_mode_name(self, mode_name: str) -> None:
        if mode_name not in self.modes:
            raise ValueError(f"Неизвестный режим: {mode_name}")
    
    def _get_mode_by_name(self, mode_name: str) -> Mode:
        return self._get_mode(mode_name)

    def _get_mode(self, mode_name: str) -> Mode:
        self._validate_mode_name(mode_name)
        return self.modes[mode_name]
        
    def _update_current_mode(self, mode_name):
        self.current_mode = mode_name
        
    def _set_window_geometry(self, window, mode_name):
        mode = self._get_mode_by_name(mode_name)
        if mode.pos is not None: window.move(mode.pos)

    def _change_mode(self, window, mode):
        """Инициирует смену режима отображения."""
        pass

    def change_mode(self, window, mode):
        self._change_mode(window, mode)
