# File: top_panel.py
from PySide6.QtWidgets import (QFrame, QLabel, QSlider, QComboBox, QPushButton,
                               QHBoxLayout, QVBoxLayout, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt
from translations import get_text, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from dialogs import show_author_info, show_hero_rating
# from build import version # Версия берется из MainWindow/logic
# <<< ДОБАВЛЕНО: Проверка типа для parent (MainWindow) >>>
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gui import MainWindow # Только для type hinting, избегаем циклического импорта
# <<< ------------------------------------------------- >>>


# <<< ИЗМЕНЕНИЕ: parent теперь типизирован как MainWindow >>>
def create_top_panel(parent: 'MainWindow', switch_mode_callback, logic):
# <<< ------------------------------------------------- >>>
    top_frame = QFrame(parent); top_frame.setObjectName("top_frame"); top_frame.setStyleSheet("background-color: lightgray;"); top_frame.setFixedHeight(40)
    layout = QHBoxLayout(top_frame); layout.setContentsMargins(5, 2, 5, 2); layout.setSpacing(5)

    # Прозрачность
    transparency_slider = QSlider(Qt.Orientation.Horizontal); transparency_slider.setRange(10, 100); transparency_slider.setValue(100); transparency_slider.setFixedWidth(100)
    transparency_slider.setObjectName("transparency_slider")
    transparency_slider.setStyleSheet(""" QSlider { height: 15px; } QSlider::groove:horizontal { border: 1px solid #999; height: 6px; background: #d3d3d3; margin: 0px; } QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; } QSlider::handle:horizontal:hover { background: #45a049; } """)
    transparency_slider.valueChanged.connect(lambda val: parent.setWindowOpacity(val / 100.0)); layout.addWidget(transparency_slider)

    # Язык
    language_label = QLabel(get_text('language')); language_label.setObjectName("language_label"); language_label.setStyleSheet("font-size: 10pt;")
    language_combo = QComboBox(); language_combo.setObjectName("language_combo"); language_combo.addItems(SUPPORTED_LANGUAGES.values()); language_combo.setCurrentText(SUPPORTED_LANGUAGES[logic.DEFAULT_LANGUAGE]); language_combo.setStyleSheet("font-size: 10pt;")
    # Callback сохранен в parent.switch_language_callback
    language_combo.currentTextChanged.connect(lambda text: parent.switch_language_callback(list(SUPPORTED_LANGUAGES.keys())[list(SUPPORTED_LANGUAGES.values()).index(text)]))
    layout.addWidget(language_label); layout.addWidget(language_combo)

    # Режим
    mode_label = QLabel(get_text('mode')); mode_label.setObjectName("mode_label"); mode_label.setStyleSheet("font-size: 10pt;")
    min_button = QPushButton(get_text('mode_min')); min_button.setObjectName("min_button"); min_button.setStyleSheet("font-size: 10pt; padding: 2px;"); min_button.clicked.connect(lambda: switch_mode_callback("min"))
    middle_button = QPushButton(get_text('mode_middle')); middle_button.setObjectName("middle_button"); middle_button.setStyleSheet("font-size: 10pt; padding: 2px;"); middle_button.clicked.connect(lambda: switch_mode_callback("middle"))
    max_button = QPushButton(get_text('mode_max')); max_button.setObjectName("max_button"); max_button.setStyleSheet("font-size: 10pt; padding: 2px;"); max_button.clicked.connect(lambda: switch_mode_callback("max"))
    layout.addWidget(mode_label); layout.addWidget(min_button); layout.addWidget(middle_button); layout.addWidget(max_button)

    # Поверх окон
    topmost_button = QPushButton(); topmost_button.setObjectName("topmost_button")

    # Функция обновления вида кнопки (читает флаг из parent)
    def update_topmost_visual_state():
        is_topmost = parent._is_win_topmost # Читаем флаг из MainWindow
        topmost_button.setText(get_text('topmost_on', language=logic.DEFAULT_LANGUAGE) if is_topmost else get_text('topmost_off', language=logic.DEFAULT_LANGUAGE))
        bg_color = "#4CAF50" if is_topmost else "gray"; border_color = "#388E3C" if is_topmost else "#666666"
        hover_bg_color = "#45a049" if is_topmost else "#757575" # Цвет при наведении
        topmost_button.setStyleSheet(f"""
            QPushButton {{
                font-size: 10pt; padding: 2px;
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                color: white; /* Белый текст для лучшей читаемости */
                min-width: 80px; /* Минимальная ширина для текста */
            }}
            QPushButton:hover {{
                background-color: {hover_bg_color};
            }}
        """)

    # Сохраняем ссылку на функцию обновления в самой кнопке
    setattr(topmost_button, '_update_visual_state', update_topmost_visual_state)

    # Клик кнопки вызывает метод toggle_topmost_winapi из MainWindow
    topmost_button.clicked.connect(parent.toggle_topmost_winapi)

    # Устанавливаем начальное состояние API и обновляем вид кнопки при создании
    parent.set_topmost_winapi(False) # Начальное состояние: выключено
    update_topmost_visual_state() # Обновляем вид кнопки
    layout.addWidget(topmost_button)

    # --- Растяжка перед правыми элементами ---
    layout.addStretch(1)

    # --- Кнопки Об авторе / Рейтинг ---
    author_button = QPushButton(get_text('about_author')); author_button.setObjectName("author_button"); author_button.setStyleSheet("font-size: 10pt; padding: 2px;"); author_button.clicked.connect(lambda: show_author_info(parent)); author_button.setVisible(False) # Скрыта по умолчанию
    rating_button = QPushButton(get_text('hero_rating')); rating_button.setObjectName("rating_button"); rating_button.setStyleSheet("font-size: 10pt; padding: 2px;"); rating_button.clicked.connect(lambda: show_hero_rating(parent)); rating_button.setVisible(False) # Скрыта по умолчанию
    layout.addWidget(rating_button) # Добавляем в layout
    layout.addWidget(author_button) # Добавляем в layout

    # --- Версия (скрывается в min режиме) ---
    # Используем версию из parent.app_version (MainWindow)
    version_label = QLabel(f"v{parent.app_version}"); version_label.setObjectName("version_label"); version_label.setStyleSheet("font-size: 9pt; color: grey; margin-left: 10px; margin-right: 5px;")
    layout.addWidget(version_label)

    # --- Кнопка Закрыть (только для Frameless в min режиме) ---
    close_button = QPushButton("X"); close_button.setObjectName("close_button"); close_button.setFixedSize(25, 25)
    close_button.setStyleSheet("QPushButton { font-size: 10pt; font-weight: bold; padding: 1px; color: black; background-color: #ff605c; border-radius: 5px; margin-left: 5px; } QPushButton:hover { background-color: #e04340; }")
    close_button.clicked.connect(parent.close); close_button.setVisible(False) # Скрыта по умолчанию

    # Находим индекс растяжки, чтобы вставить кнопку справа
    stretch_index = -1
    for i in range(layout.count()):
        item = layout.itemAt(i)
        # Проверяем, что это QSpacerItem и он растягивается горизонтально
        if isinstance(item, QSpacerItem) and item.spacerItem().expandingDirections() & Qt.Orientation.Horizontal:
            stretch_index = i
            break
    # Вставляем кнопку закрытия ПОСЛЕ растяжки (справа)
    if stretch_index != -1:
        layout.insertWidget(stretch_index + 1, close_button)
    else: # Если растяжки нет (маловероятно), добавляем в конец
        layout.addWidget(close_button)


    return top_frame, author_button, rating_button, switch_mode_callback