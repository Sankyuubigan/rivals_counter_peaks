from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame
from PySide6.QtCore import Qt
from top_panel import create_top_panel
from right_panel import create_right_panel
from left_panel import create_left_panel
from utils_gui import update_language, switch_language, copy_to_clipboard
from build import version
from logic import CounterpickLogic
from images_load import load_images
from translations import get_text
from mode_manager import change_mode, update_interface_for_mode
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logic = CounterpickLogic()
        self.mode = "middle"
        self.buttons = {}
        self.initial_pos = None
        self.mode_positions = {"max": None, "middle": None, "min": None}
        self.copy_to_clipboard = copy_to_clipboard
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{version}")
        self.setGeometry(100, 100, 950, 270)
        self.setMaximumSize(2000, 2000)
        self.initial_pos = self.pos()
        self.mode_positions["middle"] = self.pos()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.top_frame, self.author_button, self.rating_button, self.switch_mode = create_top_panel(
            self, self.change_mode, self.logic
        )
        self.main_layout.addWidget(self.top_frame)

        self.main_widget = QWidget()
        self.inner_layout = QHBoxLayout(self.main_widget)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)

        self.icons_frame = QFrame(self.main_widget)
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(0, 5, 0, 5)
        self.icons_layout.setAlignment(Qt.AlignLeft)

        try:
            self.right_images, self.left_images, self.small_images, self.horizontal_images = load_images()
        except Exception as e:
            print(f"Ошибка загрузки изображений: {e}")
            self.close()
            return

        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(
            self.main_widget)
        self.right_frame, self.selected_heroes_label, self.update_counters_wrapper, self.update_selected_label_wrapper = create_right_panel(
            self, self.logic, self.buttons, self.copy_to_clipboard, self.result_frame, self.result_label,
            self.canvas, self.update_scrollregion, self.mode
        )

        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.icons_frame)
        left_layout.addWidget(self.canvas, stretch=1)

        self.inner_layout.addWidget(self.left_container, stretch=2)
        if self.mode != "min":
            self.inner_layout.addWidget(self.right_frame, stretch=1)

        self.main_layout.addWidget(self.main_widget)

        update_interface_for_mode(self)
        self.switch_language_callback = lambda lang: switch_language(
            self, lang, self.logic, self.result_label, self.selected_heroes_label, self.author_button,
            self.rating_button, self.top_frame, lambda: self.update_counters_wrapper()
        )
        update_language(self, self.result_label, self.selected_heroes_label, self.logic, self.author_button,
                        self.rating_button, self.top_frame)

        self.restore_hero_selections()
        self.update_counters_wrapper()
        self.update_result_label_text()
        update_horizontal_icon_list(self)

    def update_result_label_text(self):
        print("Вызов update_result_label_text")
        if not hasattr(self, 'result_label') or self.result_label is None:
            print("result_label не существует, пропускаем обновление текста")
            return
        try:
            if self.logic.selected_heroes:
                if hasattr(self.result_label, 'isVisible') and self.result_label.isVisible():
                    self.result_label.setText("")
            else:
                if hasattr(self.result_label, 'isVisible') and self.result_label.isVisible():
                    self.result_label.setText(get_text('no_heroes_selected'))
        except RuntimeError as e:
            print(f"Ошибка при обновлении result_label: {e}")

    def change_mode(self, mode):
        change_mode(self, mode)

    def restore_hero_selections(self):
        for hero in self.logic.selected_heroes:
            if hero in self.buttons:
                self.buttons[hero].update_style(selected=True)
        for hero in self.logic.priority_heroes:
            if hero in self.buttons:
                self.logic.set_priority(
                    hero, self.buttons[hero], self.buttons[hero].parent(),
                    lambda: self.update_counters_wrapper()
                )
        self.update_counters_wrapper()
        self.update_selected_label_wrapper()
        self.update_result_label_text()
        update_horizontal_icon_list(self)

def create_gui():
    return MainWindow()