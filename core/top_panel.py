# File: top_panel.py
from PySide6.QtWidgets import QFrame, QLabel, QSlider, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt
from translations import get_text, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from dialogs import show_author_info, show_hero_rating
from build import version

def create_top_panel(parent, switch_mode_callback, logic):
    top_frame = QFrame(parent); top_frame.setObjectName("top_frame"); top_frame.setStyleSheet("background-color: lightgray;"); top_frame.setFixedHeight(40)
    layout = QHBoxLayout(top_frame); layout.setContentsMargins(5, 2, 5, 2); layout.setSpacing(5)

    # Прозрачность
    transparency_slider = QSlider(Qt.Orientation.Horizontal); transparency_slider.setRange(10, 100); transparency_slider.setValue(100); transparency_slider.setFixedWidth(100)
    transparency_slider.setStyleSheet(""" QSlider { height: 15px; } QSlider::groove:horizontal { border: 1px solid #999; height: 6px; background: #d3d3d3; margin: 0px; } QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; } QSlider::handle:horizontal:hover { background: #45a049; } """)
    transparency_slider.valueChanged.connect(lambda val: parent.setWindowOpacity(val / 100.0)); layout.addWidget(transparency_slider)

    # Язык
    language_label = QLabel(get_text('language')); language_label.setObjectName("language_label"); language_label.setStyleSheet("font-size: 10pt;")
    language_combo = QComboBox(); language_combo.setObjectName("language_combo"); language_combo.addItems(SUPPORTED_LANGUAGES.values()); language_combo.setCurrentText(SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE]); language_combo.setStyleSheet("font-size: 10pt;")
    language_combo.currentTextChanged.connect(lambda text: parent.switch_language_callback(list(SUPPORTED_LANGUAGES.keys())[list(SUPPORTED_LANGUAGES.values()).index(text)]))
    layout.addWidget(language_label); layout.addWidget(language_combo)

    # Режим
    mode_label = QLabel(get_text('mode')); mode_label.setStyleSheet("font-size: 10pt;")
    min_button = QPushButton(get_text('mode_min')); min_button.setStyleSheet("font-size: 10pt; padding: 2px;"); min_button.clicked.connect(lambda: switch_mode_callback("min"))
    middle_button = QPushButton(get_text('mode_middle')); middle_button.setStyleSheet("font-size: 10pt; padding: 2px;"); middle_button.clicked.connect(lambda: switch_mode_callback("middle"))
    max_button = QPushButton(get_text('mode_max')); max_button.setStyleSheet("font-size: 10pt; padding: 2px;"); max_button.clicked.connect(lambda: switch_mode_callback("max"))
    layout.addWidget(mode_label); layout.addWidget(min_button); layout.addWidget(middle_button); layout.addWidget(max_button)

    # Поверх окон
    topmost_button = QPushButton(); topmost_button.setObjectName("topmost_button")
    def update_topmost_state():
        is_topmost = bool(parent.windowFlags() & Qt.WindowStaysOnTopHint); topmost_button.setText(get_text('topmost_on') if is_topmost else get_text('topmost_off'))
        bg_color = "#4CAF50" if is_topmost else "gray"; border_color = "#388E3C" if is_topmost else "#666666"
        topmost_button.setStyleSheet(f""" font-size: 10pt; padding: 2px; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 4px; """)
    topmost_button.clicked.connect(lambda: [parent.setWindowFlag(Qt.WindowStaysOnTopHint, not bool(parent.windowFlags() & Qt.WindowStaysOnTopHint)), parent.show(), update_topmost_state()])
    update_topmost_state(); layout.addWidget(topmost_button)

    # Растяжка перед правыми элементами
    layout.addStretch(1)

    # Кнопки Об авторе / Рейтинг
    author_button = QPushButton(get_text('about_author')); author_button.setStyleSheet("font-size: 10pt; padding: 2px;"); author_button.clicked.connect(lambda: show_author_info(parent)); author_button.setVisible(False)
    rating_button = QPushButton(get_text('hero_rating')); rating_button.setStyleSheet("font-size: 10pt; padding: 2px;"); rating_button.clicked.connect(lambda: show_hero_rating(parent)); rating_button.setVisible(False)
    layout.addWidget(rating_button)
    layout.addWidget(author_button)

    # Версия
    version_label = QLabel(f"v{version}"); version_label.setObjectName("version_label"); version_label.setStyleSheet("font-size: 9pt; color: grey; margin-left: 10px; margin-right: 5px;")
    layout.addWidget(version_label)

    # Кнопка Закрыть
    close_button = QPushButton("X"); close_button.setObjectName("close_button"); close_button.setFixedSize(25, 25)
    close_button.setStyleSheet("font-size: 10pt; font-weight: bold; padding: 1px; color: black; background-color: #ff605c; border-radius: 5px; margin-left: 5px;")
    close_button.clicked.connect(parent.close); close_button.setVisible(False)
    layout.addWidget(close_button)

    return top_frame, author_button, rating_button, switch_mode_callback