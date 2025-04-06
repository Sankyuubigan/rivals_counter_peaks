from PySide6.QtWidgets import QFrame, QLabel, QSlider, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt
from translations import get_text, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from dialogs import show_author_info, show_hero_rating

def create_top_panel(parent, switch_mode_callback, logic):
    top_frame = QFrame(parent)
    top_frame.setStyleSheet("background-color: lightgray;")
    top_frame.setFixedHeight(40)
    layout = QHBoxLayout(top_frame)
    layout.setContentsMargins(5, 2, 5, 2)

    transparency_slider = QSlider(Qt.Horizontal)
    transparency_slider.setRange(10, 100)
    transparency_slider.setValue(100)
    transparency_slider.setFixedWidth(100)
    transparency_slider.setStyleSheet("""
        QSlider {
            height: 15px;
        }
        QSlider::groove:horizontal {
            border: 1px solid #999999;
            height: 6px;
            background: #d3d3d3;
            margin: 0px;
        }
        QSlider::handle:horizontal {
            background: #4CAF50;
            border: 1px solid #388E3C;
            width: 12px;
            height: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }
        QSlider::handle:horizontal:hover {
            background: #45a049;
        }
    """)
    transparency_slider.valueChanged.connect(lambda val: parent.setWindowOpacity(val / 100.0))
    layout.addWidget(transparency_slider)

    language_frame = QFrame(top_frame)
    language_layout = QHBoxLayout(language_frame)
    language_label = QLabel(get_text('language'))
    language_label.setStyleSheet("font-size: 10pt;")
    language_combo = QComboBox()
    language_combo.addItems(SUPPORTED_LANGUAGES.values())
    language_combo.setCurrentText(SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    language_combo.setStyleSheet("font-size: 10pt;")
    language_combo.currentTextChanged.connect(lambda text: parent.switch_language_callback(list(SUPPORTED_LANGUAGES.keys())[list(SUPPORTED_LANGUAGES.values()).index(text)]))
    language_layout.addWidget(language_label)
    language_layout.addWidget(language_combo)
    layout.addWidget(language_frame)

    mode_frame = QFrame(top_frame)
    mode_layout = QHBoxLayout(mode_frame)
    mode_label = QLabel("Режим:" if DEFAULT_LANGUAGE == 'ru_RU' else "Mode:")
    mode_label.setStyleSheet("font-size: 10pt;")
    min_button = QPushButton("Компактный")
    min_button.setStyleSheet("font-size: 10pt; padding: 2px;")
    min_button.clicked.connect(lambda: switch_mode_callback("min"))
    middle_button = QPushButton("Средний")
    middle_button.setStyleSheet("font-size: 10pt; padding: 2px;")
    middle_button.clicked.connect(lambda: switch_mode_callback("middle"))
    max_button = QPushButton("Большой")
    max_button.setStyleSheet("font-size: 10pt; padding: 2px;")
    max_button.clicked.connect(lambda: switch_mode_callback("max"))
    mode_layout.addWidget(mode_label)
    mode_layout.addWidget(min_button)
    mode_layout.addWidget(middle_button)
    mode_layout.addWidget(max_button)
    layout.addWidget(mode_frame)

    topmost_frame = QFrame(top_frame)
    topmost_layout = QHBoxLayout(topmost_frame)
    topmost_button = QPushButton()

    def update_topmost_state():
        is_topmost = bool(parent.windowFlags() & Qt.WindowStaysOnTopHint)
        topmost_button.setText("Поверх: Вкл" if is_topmost else "Поверх: Выкл")
        topmost_button.setStyleSheet("""
            font-size: 10pt;
            padding: 2px;
            background-color: %s;
            border: 1px solid %s;
            border-radius: 4px;
        """ % (
            "#4CAF50" if is_topmost else "gray",
            "#388E3C" if is_topmost else "#666666"
        ))

    topmost_button.clicked.connect(lambda: [
        parent.setWindowFlag(Qt.WindowStaysOnTopHint, not bool(parent.windowFlags() & Qt.WindowStaysOnTopHint)),
        parent.show(),
        update_topmost_state()
    ])
    update_topmost_state()  # Устанавливаем начальное состояние
    topmost_layout.addWidget(topmost_button)
    layout.addWidget(topmost_frame)

    author_button = QPushButton(get_text('about_author'))
    author_button.setStyleSheet("font-size: 10pt; padding: 2px;")
    author_button.clicked.connect(lambda: show_author_info(parent))
    author_button.setVisible(False)
    rating_button = QPushButton(get_text('hero_rating'))
    rating_button.setStyleSheet("font-size: 10pt; padding: 2px;")
    rating_button.clicked.connect(lambda: show_hero_rating(parent))
    rating_button.setVisible(False)
    layout.addStretch()
    layout.addWidget(rating_button)
    layout.addWidget(author_button)

    return top_frame, author_button, rating_button, switch_mode_callback