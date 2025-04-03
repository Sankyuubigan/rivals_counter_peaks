from PySide6.QtWidgets import QFrame, QLabel, QSlider, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt
from translations import get_text, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from dialogs import show_author_info, show_hero_rating

def create_top_panel(parent, switch_mode_callback, logic):
    top_frame = QFrame(parent)
    top_frame.setStyleSheet("background-color: lightgray;")
    top_frame.setFixedHeight(40)  # Уменьшаем высоту панели
    layout = QHBoxLayout(top_frame)
    layout.setContentsMargins(5, 2, 5, 2)  # Уменьшаем отступы

    # Прозрачность (без рамки и текста)
    transparency_slider = QSlider(Qt.Horizontal)
    transparency_slider.setRange(10, 100)
    transparency_slider.setValue(100)
    transparency_slider.setFixedWidth(100)  # Уменьшаем ширину
    transparency_slider.setStyleSheet("""
        QSlider {
            height: 15px;  /* Увеличиваем высоту ползунка */
        }
        QSlider::groove:horizontal {
            border: 1px solid #999999;
            height: 6px;  /* Высота дорожки */
            background: #d3d3d3;  /* Светло-серый фон дорожки */
            margin: 0px;
        }
        QSlider::handle:horizontal {
            background: #4CAF50;  /* Зеленый цвет ползунка */
            border: 1px solid #388E3C;
            width: 12px;  /* Ширина ползунка */
            height: 12px;  /* Высота ползунка */
            margin: -4px 0;  /* Центрируем ползунок */
            border-radius: 6px;  /* Закругляем углы */
        }
        QSlider::handle:horizontal:hover {
            background: #45a049;  /* Цвет при наведении */
        }
    """)
    transparency_slider.valueChanged.connect(lambda val: parent.setWindowOpacity(val / 100.0))
    layout.addWidget(transparency_slider)

    # Язык
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

    # Режимы
    mode_frame = QFrame(top_frame)
    mode_layout = QHBoxLayout(mode_frame)  # Горизонтальный layout
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

    # Всегда поверх
    topmost_frame = QFrame(top_frame)
    topmost_layout = QHBoxLayout(topmost_frame)
    topmost_button = QPushButton("Поверх: Вкл")

    def update_topmost_style():
        if topmost_button.text() == "Поверх: Вкл":
            topmost_button.setStyleSheet("""
                font-size: 10pt;
                padding: 2px;
                background-color: lightgreen;
                border: 1px solid #388E3C;
                border-radius: 4px;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);  /* Добавляем тень для объемности */
            """)
        else:
            topmost_button.setStyleSheet("""
                font-size: 10pt;
                padding: 2px;
                background-color: lightcoral;
                border: 1px solid #D32F2F;
                border-radius: 4px;
                box-shadow: inset 2px 2px 5px rgba(0, 0, 0, 0.3);  /* Внутренняя тень для эффекта нажатия */
            """)

    topmost_button.clicked.connect(lambda: [
        parent.setWindowFlag(Qt.WindowStaysOnTopHint, topmost_button.text() == "Поверх: Вкл"),
        topmost_button.setText("Поверх: Выкл" if topmost_button.text() == "Поверх: Вкл" else "Поверх: Вкл"),
        update_topmost_style(),
        parent.show()
    ])
    update_topmost_style()  # Устанавливаем начальный стиль
    topmost_layout.addWidget(topmost_button)
    layout.addWidget(topmost_frame)

    # Кнопки "Об авторе" и "Рейтинг героев" (только в max)
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