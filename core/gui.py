from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from top_panel import create_top_panel
from right_panel import create_right_panel
from left_panel import create_left_panel
from utils_gui import update_language, switch_language, copy_to_clipboard
from build import version
from logic import CounterpickLogic
from images_load import load_images, get_images_for_mode
from translations import get_text
from heroes_bd import heroes

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logic = CounterpickLogic()
        self.mode = "middle"
        self.buttons = {}
        self.initial_pos = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{version}")
        self.setGeometry(100, 100, 950, 270)
        self.setMaximumSize(2000, 2000)
        self.initial_pos = self.pos()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.top_frame, self.author_button, self.rating_button, self.switch_mode = create_top_panel(
            self, self.change_mode, self.logic
        )
        main_layout.addWidget(self.top_frame)

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.main_widget, stretch=1)

        # Инициализируем левые и правые панели
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(
            self.main_widget)
        self.right_frame, self.selected_heroes_label, self.update_counters_wrapper, self.update_selected_label_wrapper = create_right_panel(
            self, self.logic, self.buttons, copy_to_clipboard, self.result_frame, self.result_label,
            self.canvas, self.update_scrollregion, self.mode
        )

        try:
            self.right_images, self.left_images, self.small_images = load_images()
        except Exception as e:
            print(f"Ошибка загрузки изображений: {e}")
            self.close()
            return

        self.main_layout.addWidget(self.canvas, stretch=1)
        if self.mode != "min":
            self.main_layout.addWidget(self.right_frame)

        self.update_interface_for_mode(self.mode)
        self.switch_language_callback = lambda lang: switch_language(
            self, lang, self.logic, self.result_label, self.selected_heroes_label, self.author_button,
            self.rating_button,
            self.top_frame, lambda: self.update_counters_wrapper(self.result_label, self.selected_heroes_label)
        )
        update_language(self, self.result_label, self.selected_heroes_label, self.logic, self.author_button,
                        self.rating_button, self.top_frame)

    def update_interface_for_mode(self, mode):
        self.right_images, self.left_images, self.small_images = get_images_for_mode(mode)
        for btn in self.buttons.values():
            btn.setVisible(False)

        # Очищаем main_layout
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Пересоздаем левые и правые панели
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(
            self.main_widget)
        self.right_frame, self.selected_heroes_label, self.update_counters_wrapper, self.update_selected_label_wrapper = create_right_panel(
            self, self.logic, self.buttons, copy_to_clipboard, self.result_frame, self.result_label,
            self.canvas, self.update_scrollregion, self.mode
        )

        if mode == "max":
            self.resize(1700, 1000)
            self.main_layout.addWidget(self.canvas, stretch=1)
            self.main_layout.addWidget(self.right_frame)  # Убираем stretch, чтобы ширина была гибкой
            self.canvas.setVisible(True)  # Убеждаемся, что левая панель видима
            self.right_frame.setVisible(True)  # Восстанавливаем видимость
            for i, hero in enumerate(heroes):
                btn = self.buttons[hero]
                icon = self.right_images.get(hero)
                if icon is not None and not icon.isNull():
                    btn.setIcon(icon)
                    btn.setIconSize(icon.size())  # Используем размер иконки
                else:
                    print(f"Предупреждение: Нет валидной иконки для {hero} в режиме 'max'")
                btn.setVisible(True)
                btn.setFixedSize(70, 70)  # Квадратные кнопки
                btn.setStyleSheet("""
                    QPushButton {
                        padding: 0;
                        margin: 0;
                        text-align: center;
                    }
                    QPushButton > QLabel {
                        font-size: 8pt;  /* Уменьшаем шрифт, чтобы текст помещался */
                    }
                """)  # Стили для текста
            self.author_button.setVisible(True)
            self.rating_button.setVisible(True)
        elif mode == "middle":
            self.resize(950, 270)
            self.main_layout.addWidget(self.canvas, stretch=1)
            self.main_layout.addWidget(self.right_frame)  # Убираем stretch, чтобы ширина была гибкой
            self.right_frame.setVisible(True)  # Восстанавливаем видимость
            for i, hero in enumerate(heroes):
                btn = self.buttons[hero]
                icon = self.right_images.get(hero)
                if icon is not None and not icon.isNull():
                    btn.setIcon(icon)
                    btn.setIconSize(icon.size())  # Используем размер иконки
                else:
                    print(f"Предупреждение: Нет валидной иконки для {hero} в режиме 'middle'")
                btn.setText("")  # Убираем текст в среднем режиме
                btn.setVisible(True)
                btn.setFixedSize(40, 40)  # Квадратные кнопки (высота = ширине)
                btn.setStyleSheet("QPushButton { padding: 0; margin: 0; }")  # Убираем отступы
            self.author_button.setVisible(False)
            self.rating_button.setVisible(False)
        elif mode == "min":
            self.main_layout.addWidget(self.canvas, stretch=1)
            self.logic.generate_minimal_icon_list(self.result_frame, self.result_label, self.left_images)
            self.update_counters_wrapper(self.result_label, self.selected_heroes_label)
            self.author_button.setVisible(False)
            self.rating_button.setVisible(False)
            self.right_frame.setVisible(False)  # Скрываем только в min

            # Рассчитываем высоту окна
            top_frame_height = 40  # Фиксированная высота верхней панели из top_panel.py
            icon_height = 35  # Новый размер иконок (из images_load.py)
            margin = 10  # Отступы (сверху и снизу)
            new_height = top_frame_height + icon_height + margin
            self.resize(600, new_height)  # Устанавливаем новую высоту
            self.adjustSize()  # Принудительно обновляем размер окна

        # Восстанавливаем выбор героев после обновления интерфейса
        self.restore_hero_selections()

    def change_mode(self, mode):
        self.mode = mode
        self.update_interface_for_mode(mode)
        # self.move(self.initial_pos)

    def restore_hero_selections(self):
        """Восстанавливаем выбор героев после смены режима."""
        for hero in self.logic.selected_heroes:
            if hero in self.buttons:
                self.buttons[hero].setStyleSheet("""
                    background-color: lightblue;
                    border: 2px solid yellow;  /* Добавляем желтую рамку для выделения */
                """)
        for hero in self.logic.priority_heroes:
            if hero in self.buttons:
                self.logic.set_priority(hero, self.buttons[hero], self.buttons[hero].parent(),
                                        lambda: self.update_counters_wrapper(self.result_label, self.selected_heroes_label))
        # Передаем self.result_label и self.selected_heroes_label
        self.update_counters_wrapper(self.result_label, self.selected_heroes_label)
        self.update_selected_label_wrapper(self.selected_heroes_label)

def create_gui():
    return MainWindow()