# File: core/top_panel.py
from PySide6.QtWidgets import (
    QFrame, QLabel, QSlider, QComboBox, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt

from translations import get_text, SUPPORTED_LANGUAGES
from dialogs import show_author_info, show_hero_rating
# <<< ---------------------------------------------- >>>
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_window import MainWindow


class TopPanel:
    """Класс для создания и управления верхней панелью."""

    def __init__(self, parent: 'MainWindow', switch_mode_callback, logic, app_version):
        self.parent = parent
        self.switch_mode_callback = switch_mode_callback # Это метод MainWindow.change_mode
        self.logic = logic
        self.app_version = app_version

        self.top_frame = QFrame(parent)
        self.top_frame.setObjectName("top_frame")
        self.top_frame.setStyleSheet("QFrame#top_frame { background-color: lightgray; }")
        self.top_frame.setFixedHeight(40)

        self.author_button: QPushButton | None = None
        self.rating_button: QPushButton | None = None

        self._setup_ui()

    def _setup_ui(self):
        """Создает layout и виджеты для панели."""
        layout = QHBoxLayout(self.top_frame)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # Прозрачность
        self.transparency_slider = self._create_slider()
        layout.addWidget(self.transparency_slider)

        # Язык
        self.language_label = QLabel(get_text('language', language=self.logic.DEFAULT_LANGUAGE))
        self.language_label.setObjectName("language_label")
        self.language_label.setStyleSheet("font-size: 10pt;")
        self.language_combo = self._create_language_combo()
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)

        # Режим
        self.mode_label = QLabel(get_text('mode', language=self.logic.DEFAULT_LANGUAGE))
        self.mode_label.setObjectName("mode_label")
        self.mode_label.setStyleSheet("font-size: 10pt;")
        self.min_button = self._create_mode_button('mode_min', "min")
        self.middle_button = self._create_mode_button('mode_middle', "middle")
        self.max_button = self._create_mode_button('mode_max', "max")
        layout.addWidget(self.mode_label)
        layout.addWidget(self.min_button)
        layout.addWidget(self.middle_button)
        layout.addWidget(self.max_button)

        # Поверх окон
        self.topmost_button = self._create_topmost_button()
        layout.addWidget(self.topmost_button)

        # Растяжка
        layout.addStretch(1)

        # Кнопки Об авторе / Рейтинг
        self.rating_button = self._create_info_button('hero_rating', lambda: show_hero_rating(self.parent, self.app_version))
        self.author_button = self._create_info_button('about_author', lambda: show_author_info(self.parent, self.app_version))
        layout.addWidget(self.rating_button)
        layout.addWidget(self.author_button)

        # Версия
        self.version_label = QLabel(f"v{self.app_version}")
        self.version_label.setObjectName("version_label")
        self.version_label.setStyleSheet("font-size: 9pt; color: grey; margin-left: 10px; margin-right: 5px;")
        layout.addWidget(self.version_label)

        # Кнопка Закрыть
        self.close_button = self._create_close_button()
        self._insert_widget_after_stretch(layout, self.close_button)

    # Методы _create_slider, _create_language_combo, _create_mode_button, _create_topmost_button,
    # _create_info_button, _create_close_button, _insert_widget_after_stretch
    # остаются без изменений, но метод update_language добавлен ниже для полноты

    def update_language(self):
        """Обновляет тексты элементов на панели."""
        current_lang = self.logic.DEFAULT_LANGUAGE
        self.language_label.setText(get_text('language', language=current_lang))
        self.mode_label.setText(get_text('mode', language=current_lang))
        self.min_button.setText(get_text('mode_min', language=current_lang))
        self.middle_button.setText(get_text('mode_middle', language=current_lang))
        self.max_button.setText(get_text('mode_max', language=current_lang))

        # Обновляем текст кнопки topmost
        update_func = getattr(self.topmost_button, '_update_visual_state', None)
        if update_func: update_func()

        if self.author_button: self.author_button.setText(get_text('about_author', language=current_lang))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating', language=current_lang))

        # Обновляем комбо-бокс языка
        current_text = SUPPORTED_LANGUAGES.get(current_lang, "N/A")
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentText(current_text)
        self.language_combo.blockSignals(False)

    # --- Копируем код вспомогательных методов создания виджетов ---
    def _create_slider(self) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("transparency_slider")
        slider.setRange(10, 100); slider.setValue(100); slider.setFixedWidth(100)
        slider.setStyleSheet("""
            QSlider { height: 15px; }
            QSlider::groove:horizontal { border: 1px solid #999; height: 6px; background: #d3d3d3; margin: 0px; border-radius: 3px;}
            QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
            QSlider::handle:horizontal:hover { background: #45a049; }
        """)
        slider.valueChanged.connect(lambda val: self.parent.setWindowOpacity(val / 100.0))
        return slider

    def _create_language_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("language_combo")
        combo.addItems(SUPPORTED_LANGUAGES.values())
        combo.setCurrentText(SUPPORTED_LANGUAGES[self.logic.DEFAULT_LANGUAGE])
        combo.setStyleSheet("font-size: 10pt;")
        combo.currentTextChanged.connect(
            lambda text: self.parent.switch_language(
                list(SUPPORTED_LANGUAGES.keys())[list(SUPPORTED_LANGUAGES.values()).index(text)]
            )
        )
        return combo

    def _create_mode_button(self, text_key: str, mode_name: str) -> QPushButton:
        button = QPushButton(get_text(text_key, language=self.logic.DEFAULT_LANGUAGE))
        button.setObjectName(f"{mode_name}_mode_button")
        button.setStyleSheet("font-size: 10pt; padding: 2px;")
        button.clicked.connect(lambda: self.switch_mode_callback(mode_name))
        return button

    def _create_topmost_button(self) -> QPushButton:
        button = QPushButton()
        button.setObjectName("topmost_button")
        def update_visual_state():
            is_topmost = self.parent._is_win_topmost
            button.setText(get_text('topmost_on' if is_topmost else 'topmost_off', language=self.logic.DEFAULT_LANGUAGE))
            bg_color = "#4CAF50" if is_topmost else "gray"; border_color = "#388E3C" if is_topmost else "#666666"
            hover_bg_color = "#45a049" if is_topmost else "#757575"
            button.setStyleSheet(f"""
                QPushButton {{ font-size: 10pt; padding: 2px; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 4px; color: white; min-width: 80px; }}
                QPushButton:hover {{ background-color: {hover_bg_color}; }}
            """)
        setattr(button, '_update_visual_state', update_visual_state)
        button.clicked.connect(self.parent.toggle_topmost_winapi)
        update_visual_state()
        return button

    def _create_info_button(self, text_key: str, callback) -> QPushButton:
        button = QPushButton(get_text(text_key, language=self.logic.DEFAULT_LANGUAGE))
        button.setObjectName(f"{text_key}_button")
        button.setStyleSheet("font-size: 10pt; padding: 2px;")
        button.clicked.connect(callback)
        button.setVisible(False)
        return button

    def _create_close_button(self) -> QPushButton:
        button = QPushButton("X")
        button.setObjectName("close_button")
        button.setFixedSize(25, 25)
        button.setStyleSheet("""
            QPushButton { font-size: 10pt; font-weight: bold; padding: 1px; color: black; background-color: #ff605c; border-radius: 5px; margin-left: 5px; border: 1px solid #E04340; }
            QPushButton:hover { background-color: #e04340; }
            QPushButton:pressed { background-color: #c0302c; }
        """)
        button.clicked.connect(self.parent.close)
        button.setVisible(False)
        return button

    def _insert_widget_after_stretch(self, layout: QHBoxLayout, widget: QWidget):
        stretch_index = -1
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if isinstance(item, QSpacerItem) and item.spacerItem().expandingDirections() & Qt.Orientation.Horizontal:
                stretch_index = i
                break
        if stretch_index != -1: layout.insertWidget(stretch_index + 1, widget)
        else: layout.addWidget(widget)
