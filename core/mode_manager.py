# File: core/mode_manager.py
import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QScrollArea)
from PySide6.QtCore import Qt, QTimer # Добавлен QTimer


# --- Константы ---
PANEL_MIN_WIDTHS = {
    'max': {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300},
    'min': {'left': 0, 'right': 0}
}
MODE_DEFAULT_WINDOW_SIZES = {
    'max': {'width': 1100, 'height': 800},
    'middle': {'width': 950, 'height': 600},
    'min': {'width': 600, 'height': 0}
}
# --- ---

class ModeManager:
    """Управляет текущим режимом окна и его позициями."""
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_mode = "middle"
        self.mode_positions = {
            "min": None,
            "middle": main_window.pos() if main_window.isVisible() else None,
            "max": None
        }

    def change_mode(self, new_mode_name: str):
        """Устанавливает новый режим и сохраняет позицию старого."""
        if new_mode_name not in self.mode_positions:
            print(f"[ERROR] Попытка установить неизвестный режим: {new_mode_name}")
            return
        if self.current_mode == new_mode_name:
            print(f"Режим уже установлен: {new_mode_name}")
            return

        print(f"[MODE] Сохранение позиции для режима '{self.current_mode}'...")
        if self.main_window.isVisible():
             current_pos = self.main_window.pos()
             self.mode_positions[self.current_mode] = current_pos
             print(f"[MODE] Позиция для '{self.current_mode}' сохранена: {current_pos}")

        print(f"[MODE] Установка нового режима: {new_mode_name}")
        self.current_mode = new_mode_name
        self.main_window.mode = new_mode_name

    def clear_layout_recursive(self, layout):
        """Рекурсивно очищает layout."""
        if layout is None: return
        while layout.count():
            item = layout.takeAt(0)
            if item is None: continue
            widget = item.widget()
            if widget is not None: widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self.clear_layout_recursive(sub_layout)
                    layout.removeItem(item)
                else:
                    spacer = item.spacerItem()
                    if spacer is not None: layout.removeItem(item)


# <<< ИЗМЕНЕНО: Функция change_mode теперь вызывает метод MainWindow >>>
def change_mode(window, mode_name):
    """Инициирует смену режима отображения через метод MainWindow."""
    # Проверяем, есть ли у окна метод change_mode (добавлен в MainWindow)
    if hasattr(window, 'change_mode') and callable(window.change_mode):
         window.change_mode(mode_name)
    else:
         print(f"[ERROR] У объекта 'window' нет метода 'change_mode'!")
# <<< -------------------------------------------------------- >>>


# <<< ИЗМЕНЕНО: Функция update_interface_for_mode теперь метод MainWindow >>>
# Оставляем здесь только константы и класс ModeManager
# def update_interface_for_mode(window):
#    # ... (весь код функции перенесен в MainWindow._update_interface_for_mode)
# <<< --------------------------------------------------------------- >>>