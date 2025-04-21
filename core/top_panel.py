from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSlider,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QSpacerItem,
)
from PySide6.QtCore import Qt
from translations import get_text, SUPPORTED_LANGUAGES
from dialogs import show_author_info, show_hero_rating
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui import MainWindow  # Только для type hinting, избегаем циклического импорта
# <<< ------------------------------------------------- >>>


# <<< ИЗМЕНЕНИЕ: parent теперь типизирован как MainWindow >>>
def create_top_panel(parent: 'MainWindow', switch_mode_callback, logic, app_version):
# <<< ------------------------------------------------- >>>
    top_frame = QFrame(parent); top_frame.setObjectName("top_frame"); top_frame.setStyleSheet("background-color: lightgray;"); top_frame.setFixedHeight(40)
    panel = TopPanel(parent, switch_mode_callback, logic, app_version)
    return panel.top_frame, panel.author_button, panel.rating_button, switch_mode_callback


class TopPanel:
    def __init__(self, parent: 'MainWindow', switch_mode_callback, logic, app_version):
        self.parent = parent
        self.switch_mode_callback = switch_mode_callback
        self.app_version = app_version
        self.logic = logic
        self.top_frame = QFrame(parent)
        self.author_button = None
        self.rating_button = None
        self.setup_ui()

    def setup_ui(self):
        self._create_widgets()
        self._setup_widgets()
        self._create_layout()
        self._setup_layout()

    def _create_widgets(self):
        self.top_frame.setObjectName("top_frame")
        self.top_frame.setStyleSheet("background-color: lightgray;")
        self.top_frame.setFixedHeight(40)

        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setObjectName("transparency_slider")
        self.language_label = QLabel(get_text('language'))
        self.language_label.setObjectName("language_label")
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("language_combo")
        self.mode_label = QLabel(get_text('mode'))
        self.mode_label.setObjectName("mode_label")
        self.min_button = QPushButton(get_text('mode_min'))
        self.min_button.setObjectName("min_button")
        self.middle_button = QPushButton(get_text('mode_middle'))
        self.middle_button.setObjectName("middle_button")
        self.max_button = QPushButton(get_text('mode_max'))
        self.max_button.setObjectName("max_button")
        self.topmost_button = QPushButton()
        self.topmost_button.setObjectName("topmost_button")
        self.author_button = QPushButton(get_text('about_author'))
        self.author_button.setObjectName("author_button")
        self.rating_button = QPushButton(get_text('hero_rating'))
        self.rating_button.setObjectName("rating_button")
        self.version_label = QLabel(f"v{self.app_version}")
        self.version_label.setObjectName("version_label")
        self.close_button = QPushButton("X")
        self.close_button.setObjectName("close_button")

    def _setup_widgets(self):
        # Прозрачность
        self.transparency_slider.setRange(10, 100)
        self.transparency_slider.setValue(100)
        self.transparency_slider.setFixedWidth(100)
        self.transparency_slider.setStyleSheet(""" QSlider { height: 15px; } QSlider::groove:horizontal { border: 1px solid #999; height: 6px; background: #d3d3d3; margin: 0px; } QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; } QSlider::handle:horizontal:hover { background: #45a049; } """)
        self.transparency_slider.valueChanged.connect(lambda val: self.parent.setWindowOpacity(val / 100.0))

        # Язык
        self.language_label.setStyleSheet("font-size: 10pt;")
        self.language_combo.addItems(SUPPORTED_LANGUAGES.values())
        self.language_combo.setCurrentText(SUPPORTED_LANGUAGES[self.logic.DEFAULT_LANGUAGE])
        self.language_combo.setStyleSheet("font-size: 10pt;")
        self.language_combo.currentTextChanged.connect(lambda text: self.parent.switch_language_callback(list(SUPPORTED_LANGUAGES.keys())[list(SUPPORTED_LANGUAGES.values()).index(text)]))

        # Режим
        self.mode_label.setStyleSheet("font-size: 10pt;")
        self.min_button.setStyleSheet("font-size: 10pt; padding: 2px;")
        self.min_button.clicked.connect(lambda: self.switch_mode_callback("min"))
        self.middle_button.setStyleSheet("font-size: 10pt; padding: 2px;")
        self.middle_button.clicked.connect(lambda: self.switch_mode_callback("middle"))
        self.max_button.setStyleSheet("font-size: 10pt; padding: 2px;")
        self.max_button.clicked.connect(lambda: self.switch_mode_callback("max"))

        # Кнопка поверх окон
        def update_topmost_visual_state():
                is_topmost = self.parent._is_win_topmost
                self.topmost_button.setText(get_text('topmost_on', language=self.logic.DEFAULT_LANGUAGE) if is_topmost else get_text('topmost_off', language=self.logic.DEFAULT_LANGUAGE))
                bg_color = "#4CAF50" if is_topmost else "gray"
                border_color = "#388E3C" if is_topmost else "#666666"
                hover_bg_color = "#45a049" if is_topmost else "#757575"
                self.topmost_button.setStyleSheet(f"""
                QPushButton {{
                    font-size: 10pt; padding: 2px;
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    color: white;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg_color};
                }}
            """)
        setattr(self.topmost_button, '_update_visual_state', update_topmost_visual_state)
        self.topmost_button.clicked.connect(self.parent.toggle_topmost_winapi)
        self.parent.set_topmost_winapi(False)
        update_topmost_visual_state()

        self.author_button.setStyleSheet("font-size: 10pt; padding: 2px;")
        self.author_button.clicked.connect(lambda: show_author_info(self.parent, self.app_version))
        self.author_button.setVisible(False)
        self.rating_button.setStyleSheet("font-size: 10pt; padding: 2px;")
        self.rating_button.clicked.connect(lambda: show_hero_rating(self.parent, self.app_version))
        self.rating_button.setVisible(False)

        self.version_label.setStyleSheet("font-size: 9pt; color: grey; margin-left: 10px; margin-right: 5px;")

        self.close_button.setFixedSize(25, 25)
        self.close_button.setStyleSheet("QPushButton { font-size: 10pt; font-weight: bold; padding: 1px; color: black; background-color: #ff605c; border-radius: 5px; margin-left: 5px; } QPushButton:hover { background-color: #e04340; }")
        self.close_button.clicked.connect(self.parent.close)
        self.close_button.setVisible(False)

    def _create_layout(self):
        self.layout = QHBoxLayout(self.top_frame)

    def _setup_layout(self):
        self.layout.setContentsMargins(5, 2, 5, 2)
        self.layout.setSpacing(5)
        self.layout.addWidget(self.transparency_slider)
        self.layout.addWidget(self.language_label,)
        self.layout.addWidget(self.language_combo)
        self.layout.addWidget(self.mode_label)
        self.layout.addWidget(self.min_button)
        self.layout.addWidget(self.middle_button)
        self.layout.addWidget(self.max_button)
        self.layout.addWidget(self.topmost_button)
        self.layout.addStretch(1)
        self.layout.addWidget(self.rating_button)
        self.layout.addWidget(self.author_button)
        self.layout.addWidget(self.version_label)

        # Вставка close_button после растяжки
        self._insert_close_button()

    def _insert_close_button(self):
        stretch_index = -1
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if isinstance(item, QSpacerItem) and item.spacerItem().expandingDirections() & Qt.Orientation.Horizontal:
                stretch_index = i
                break
        if stretch_index != -1:
            self.layout.insertWidget(stretch_index + 1, self.close_button)
        else:
            self.layout.addWidget(self.close_button)