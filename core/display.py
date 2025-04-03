from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters
from translations import get_text

def generate_counterpick_display(self, result_frame, result_label, left_images, small_images):
    for widget in result_frame.findChildren(QFrame):
        widget.deleteLater()

    if not self.selected_heroes:
        self.current_result_text = ""
        result_label.setText(get_text('no_heroes_selected'))
        return

    counter_scores = self.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    self.current_result_text = f"{get_text('counterpick_rating')}\n"

    effective_team = self.calculate_effective_team(counter_scores)

    for counter, score in sorted_counters:
        if counter in left_images and left_images[counter]:
            counter_frame = QFrame(result_frame)
            counter_layout = QHBoxLayout(counter_frame)
            bg_color = QColor("lightblue") if counter in effective_team else result_frame.palette().window().color()
            counter_frame.setStyleSheet(f"background-color: {bg_color.name()};")
            counter_layout.setContentsMargins(2, 1, 2, 1)
            counter_layout.setAlignment(Qt.AlignLeft)  # Выравнивание влево

            img_label = QLabel()
            img_label.setPixmap(left_images[counter])
            counter_layout.addWidget(img_label)

            text_label = QLabel(f"{counter}: {score:.1f} {get_text('points')}")
            counter_layout.addWidget(text_label)

            counter_for_heroes = [hero for hero in self.selected_heroes if counter in heroes_counters.get(hero, [])]
            for hero in counter_for_heroes:
                if hero in small_images and small_images[hero]:
                    small_img_label = QLabel()
                    small_img_label.setPixmap(small_images[hero])
                    small_img_label.setStyleSheet("border: 2px solid green;")
                    counter_layout.addWidget(small_img_label)

            countered_by_heroes = [hero for hero in self.selected_heroes if hero in heroes_counters.get(counter, [])]
            for hero in countered_by_heroes:
                if hero in small_images and small_images[hero]:
                    small_img_label = QLabel()
                    small_img_label.setPixmap(small_images[hero])
                    small_img_label.setStyleSheet("border: 2px solid red;")
                    counter_layout.addWidget(small_img_label)

            result_frame.layout().addWidget(counter_frame)
            self.current_result_text += f"{counter}: {score:.1f} {get_text('points')}\n"

def generate_minimal_display(self, result_frame, result_label, left_images):
    for widget in result_frame.findChildren(QFrame):
        widget.deleteLater()

    if not self.selected_heroes:
        self.current_result_text = ""
        result_label.setText(get_text('no_heroes_selected'))
        return

    counter_scores = self.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    filtered_counters = [(hero, score) for hero, score in sorted_counters if score > 0][:5]

    if not filtered_counters:
        result_label.setText(get_text('no_counters_found'))
        return

    icons_frame = QFrame(result_frame)
    icons_layout = QHBoxLayout(icons_frame)
    icons_layout.setContentsMargins(0, 5, 0, 5)

    effective_team = self.calculate_effective_team(counter_scores)

    for counter, score in filtered_counters:
        if counter in left_images and left_images[counter]:
            img_label = QLabel()
            img_label.setPixmap(left_images[counter])
            if counter in effective_team:
                img_label.setStyleSheet("border: 2px solid lightblue;")
            icons_layout.addWidget(img_label)

    result_frame.layout().addWidget(icons_frame)
    self.current_result_text = ", ".join([f"{hero}: {score:.1f}" for hero, score in filtered_counters])

def generate_minimal_icon_list(self, result_frame, result_label, left_images):
    for widget in result_frame.findChildren(QFrame):
        widget.deleteLater()

    if not self.selected_heroes:
        self.current_result_text = ""
        result_label.setText(get_text('no_heroes_selected'))
        return

    counter_scores = self.calculate_counter_scores()
    sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
    filtered_counters = [(hero, score) for hero, score in sorted_counters if score > 0]

    if not filtered_counters:
        result_label.setText(get_text('no_counters_found'))
        return

    icons_frame = QFrame(result_frame)
    icons_layout = QHBoxLayout(icons_frame)
    icons_layout.setContentsMargins(0, 5, 0, 5)
    icons_layout.setAlignment(Qt.AlignLeft)  # Выравнивание влево

    effective_team = self.calculate_effective_team(counter_scores)

    for counter, score in filtered_counters:
        if counter in left_images and left_images[counter]:
            img_label = QLabel()
            img_label.setPixmap(left_images[counter])
            if counter in effective_team:
                img_label.setStyleSheet("border: 2px solid lightblue;")
            elif counter in self.selected_heroes:
                img_label.setStyleSheet("border: 2px solid yellow;")  # Выделение выбранных героев
            icons_layout.addWidget(img_label)

    result_frame.layout().addWidget(icons_frame)
    self.current_result_text = ", ".join([f"{hero}: {score:.1f}" for hero, score in filtered_counters])