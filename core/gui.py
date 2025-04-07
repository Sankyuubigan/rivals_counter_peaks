from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from top_panel import create_top_panel
from right_panel import create_right_panel
from left_panel import create_left_panel
from utils_gui import update_language, switch_language, copy_to_clipboard
from build import version
from logic import CounterpickLogic
from images_load import load_images, get_images_for_mode
from translations import get_text
from heroes_bd import heroes, hero_roles


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logic = CounterpickLogic()
        self.mode = "middle"  # Изменяем начальный режим на "middle"
        self.buttons = {}
        self.initial_pos = None
        self.mode_positions = {"max": None, "middle": None, "min": None}
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
            self, self.logic, self.buttons, copy_to_clipboard, self.result_frame, self.result_label,
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

        self.update_interface_for_mode(self.mode)
        self.switch_language_callback = lambda lang: switch_language(
            self, lang, self.logic, self.result_label, self.selected_heroes_label, self.author_button,
            self.rating_button, self.top_frame, lambda: self.update_counters_wrapper()
        )
        update_language(self, self.result_label, self.selected_heroes_label, self.logic, self.author_button,
                        self.rating_button, self.top_frame)

        self.restore_hero_selections()
        self.update_counters_wrapper()

    def update_horizontal_icon_list(self):
        print("Вызов update_horizontal_icon_list")
        while self.icons_layout.count():
            item = self.icons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Рассчитываем рейтинг контрпиков
        counter_scores = self.logic.calculate_counter_scores()
        self.logic.calculate_effective_team(counter_scores)

        # Фильтруем героев: оставляем только тех, у кого рейтинг > 0
        filtered_heroes = [(hero, score) for hero, score in counter_scores.items() if score > 0]
        # Сортируем по убыванию рейтинга
        filtered_heroes.sort(key=lambda x: x[1], reverse=True)
        print(f"Отфильтрованные герои с рейтингом > 0: {filtered_heroes}")

        if not filtered_heroes:
            print("Нет героев с рейтингом > 0, пропускаем обновление горизонтального списка.")
            return

        print(f"Обновление горизонтального списка с selected_heroes: {self.logic.selected_heroes}")
        print(f"Размер horizontal_images: {len(self.horizontal_images)}")
        for hero, score in filtered_heroes:
            if hero in self.horizontal_images and self.horizontal_images[hero]:
                img_label = QLabel()
                img_label.setPixmap(self.horizontal_images[hero])
                img_label.setFixedSize(25, 25)  # Фиксированный размер для предотвращения сжатия
                if hero in self.logic.selected_heroes:
                    img_label.setStyleSheet("border: 2px solid yellow;")
                if hero in self.logic.effective_team:
                    img_label.setStyleSheet("border: 2px solid lightblue;")
                self.icons_layout.addWidget(img_label)
                print(f"Добавлен герой {hero} с рейтингом {score} в горизонтальный список")

        self.icons_frame.update()
        self.left_container.update()
        self.main_widget.update()
        print(f"Видимость icons_frame: {self.icons_frame.isVisible()}")
        print("Завершено обновление горизонтального списка")

    def update_interface_for_mode(self, mode):
        if self.mode in self.mode_positions:
            self.mode_positions[self.mode] = self.pos()

        # Очищаем словарь buttons перед удалением виджетов
        self.buttons.clear()

        # Загружаем изображения для нового режима
        self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(mode)

        # Удаляем старые виджеты из inner_layout
        while self.inner_layout.count():
            item = self.inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Пересоздаём icons_frame и его layout
        self.icons_frame = QFrame(self.main_widget)
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(0, 5, 0, 5)
        self.icons_layout.setAlignment(Qt.AlignLeft)

        # Пересоздаём левые и правые панели
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(
            self.main_widget)
        self.right_frame, self.selected_heroes_label, self.update_counters_wrapper, self.update_selected_label_wrapper = create_right_panel(
            self, self.logic, self.buttons, copy_to_clipboard, self.result_frame, self.result_label,
            self.canvas, self.update_scrollregion, mode
        )

        # Пересоздаём left_container
        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.icons_frame)
        left_layout.addWidget(self.canvas, stretch=1)

        # Настраиваем интерфейс в зависимости от режима
        if mode == "max":
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.resize(1700, 1000)
            self.left_container.setMinimumWidth(600)
            self.left_container.setMaximumWidth(600)
            self.inner_layout.addWidget(self.left_container)
            self.inner_layout.addWidget(self.right_frame, stretch=1)
            self.canvas.setVisible(True)
            self.icons_frame.setVisible(True)
            self.left_container.setVisible(True)
            self.right_frame.setVisible(True)
            for i, hero in enumerate(heroes):
                btn = self.buttons[hero]
                icon = self.right_images.get(hero)
                if icon is not None and not icon.isNull():
                    btn.icon_label.setPixmap(icon)
                else:
                    print(f"Предупреждение: Нет валидной иконки для {hero} в режиме 'max'")
                btn.setVisible(True)
            self.author_button.setVisible(True)
            self.rating_button.setVisible(True)
        elif mode == "middle":
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.resize(880, 460)
            self.left_container.setMinimumWidth(0)
            self.left_container.setMaximumWidth(16777215)
            self.inner_layout.addWidget(self.left_container, stretch=2)
            self.inner_layout.addWidget(self.right_frame, stretch=1)
            self.canvas.setVisible(True)
            self.icons_frame.setVisible(True)
            self.left_container.setVisible(True)
            self.right_frame.setVisible(True)
            for i, hero in enumerate(heroes):
                btn = self.buttons[hero]
                icon = self.right_images.get(hero)
                if icon is not None and not icon.isNull():
                    btn.icon_label.setPixmap(icon)
                else:
                    print(f"Предупреждение: Нет валидной иконки для {hero} в режиме 'middle'")
                btn.text_label.setText("")
                btn.setVisible(True)
            self.author_button.setVisible(False)
            self.rating_button.setVisible(False)
        elif mode == "min":
            self.left_container.setMinimumWidth(0)
            self.left_container.setMaximumWidth(16777215)
            self.inner_layout.addWidget(self.left_container, stretch=1)
            self.author_button.setVisible(False)
            self.rating_button.setVisible(False)
            self.right_frame.setVisible(False)

            top_frame_height = 40
            icon_height = 35
            margin = 10
            new_height = top_frame_height + icon_height + margin
            self.setFixedHeight(new_height)
            self.resize(600, new_height)
            self.icons_frame.setVisible(True)

        self.update_counters_wrapper()
        self.update_horizontal_icon_list()

        if self.mode_positions[mode] is not None:
            self.move(self.mode_positions[mode])
        else:
            self.mode_positions[mode] = self.pos()

        self.restore_hero_selections()

    def change_mode(self, mode):
        self.mode = mode
        self.update_interface_for_mode(mode)

    def restore_hero_selections(self):
        for hero in self.logic.selected_heroes:
            if hero in self.buttons:
                self.buttons[hero].setStyleSheet("background-color: lightblue; border: none;")
        for hero in self.logic.priority_heroes:
            if hero in self.buttons:
                self.logic.set_priority(
                    hero, self.buttons[hero], self.buttons[hero].parent(),
                    lambda: self.update_counters_wrapper()
                )
        self.update_counters_wrapper()
        self.update_selected_label_wrapper()
        self.update_horizontal_icon_list()


def create_gui():
    return MainWindow()