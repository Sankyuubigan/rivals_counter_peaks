# File: core/top_panel.py
from PySide6.QtWidgets import (
    QFrame, QLabel, QSlider, QComboBox, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt
# <<< ИСПРАВЛЕНО: Используем абсолютные импорты >>>
import translations
import dialogs
# <<< ----------------------------------------- >>>
from translations import get_text, SUPPORTED_LANGUAGES # Импортируем отдельно для удобства
from dialogs import show_author_info, show_hero_rating
from typing import TYPE_CHECKING
import logging # <<< Добавлено для логирования

if TYPE_CHECKING:
    # Используем TYPE_CHECKING для избежания циклического импорта
    from main_window import MainWindow


class TopPanel:
    """Класс для создания и управления верхней панелью."""

    def __init__(self, parent: 'MainWindow', switch_mode_callback, logic, app_version):
        self.parent = parent
        self.switch_mode_callback = switch_mode_callback
        self.logic = logic
        self.app_version = app_version # Сохраняем версию

        self.top_frame = QFrame(parent)
        self.top_frame.setObjectName("top_frame")
        self.top_frame.setStyleSheet("QFrame#top_frame { background-color: lightgray; }")
        self.top_frame.setFixedHeight(40) # Фиксированная высота

        # Инициализируем атрибуты виджетов как None
        self.transparency_slider: QSlider | None = None
        self.language_label: QLabel | None = None
        self.language_combo: QComboBox | None = None
        self.mode_label: QLabel | None = None
        self.min_button: QPushButton | None = None
        self.middle_button: QPushButton | None = None
        self.max_button: QPushButton | None = None
        self.topmost_button: QPushButton | None = None
        self.rating_button: QPushButton | None = None
        self.author_button: QPushButton | None = None
        self.version_label: QLabel | None = None # <<< Добавлено
        self.close_button: QPushButton | None = None

        self._setup_ui()

    def _setup_ui(self):
        """Создает layout и виджеты для панели."""
        layout = QHBoxLayout(self.top_frame)
        layout.setContentsMargins(5, 2, 5, 2) # Отступы
        layout.setSpacing(5) # Расстояние между элементами

        # --- Слайдер прозрачности ---
        self.transparency_slider = self._create_slider()
        layout.addWidget(self.transparency_slider)

        # --- Выбор языка ---
        self.language_label = QLabel(get_text('language', language=self.logic.DEFAULT_LANGUAGE))
        self.language_label.setObjectName("language_label")
        self.language_label.setStyleSheet("font-size: 10pt;")
        self.language_combo = self._create_language_combo()
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)

        # --- Выбор режима ---
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

        # --- Кнопка "Поверх окон" ---
        self.topmost_button = self._create_topmost_button()
        layout.addWidget(self.topmost_button)

        # --- Растягивающийся промежуток ---
        layout.addStretch(1) # Занимает все доступное пространство

        # --- Кнопки "Об авторе" / "Рейтинг" ---
        self.rating_button = self._create_info_button('hero_rating', lambda: show_hero_rating(self.parent, self.app_version))
        self.author_button = self._create_info_button('about_author', lambda: show_author_info(self.parent, self.app_version))
        layout.addWidget(self.rating_button) # Добавляются после растяжки
        layout.addWidget(self.author_button)

        # --- Отображение версии ---
        # <<< ИЗМЕНЕНО: Создаем QLabel для версии >>>
        self.version_label = QLabel(f"v{self.app_version}")
        self.version_label.setObjectName("version_label")
        self.version_label.setStyleSheet("font-size: 9pt; color: grey; margin-left: 10px; margin-right: 5px;")
        layout.addWidget(self.version_label) # Добавляем в layout
        # <<< -------------------------------- >>>

        # --- Кнопка Закрыть (для минимального режима) ---
        self.close_button = self._create_close_button()
        # Добавляем кнопку закрытия после всех остальных элементов справа
        layout.addWidget(self.close_button)
        # Старый метод вставки после растяжки не нужен, т.к. версия и кнопка закрытия теперь тоже справа

    # --- Методы создания виджетов ---
    def _create_slider(self) -> QSlider:
        """Создает и настраивает слайдер прозрачности."""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("transparency_slider")
        slider.setRange(10, 100) # От 10% до 100%
        slider.setValue(100) # Начальное значение - непрозрачный
        slider.setFixedWidth(100) # Фиксированная ширина
        slider.setStyleSheet("""
            QSlider { height: 15px; }
            QSlider::groove:horizontal { border: 1px solid #999; height: 6px; background: #d3d3d3; margin: 0px; border-radius: 3px;}
            QSlider::handle:horizontal { background: #4CAF50; border: 1px solid #388E3C; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
            QSlider::handle:horizontal:hover { background: #45a049; }
        """)
        # Подключаем сигнал к изменению прозрачности родительского окна
        slider.valueChanged.connect(lambda val: self.parent.setWindowOpacity(val / 100.0))
        return slider

    def _create_language_combo(self) -> QComboBox:
        """Создает и настраивает выпадающий список языков."""
        combo = QComboBox()
        combo.setObjectName("language_combo")
        # Заполняем значениями из словаря языков
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
             combo.addItem(lang_name, lang_code) # Добавляем имя и код языка

        # Устанавливаем текущий язык
        current_lang_code = self.logic.DEFAULT_LANGUAGE
        index_to_select = combo.findData(current_lang_code)
        if index_to_select != -1:
             combo.setCurrentIndex(index_to_select)

        combo.setStyleSheet("font-size: 10pt;")
        # Подключаем сигнал к смене языка в родительском окне
        combo.currentIndexChanged.connect(
            lambda index: self.parent.switch_language(combo.itemData(index)) # Получаем код языка из данных элемента
        )
        return combo

    def _create_mode_button(self, text_key: str, mode_name: str) -> QPushButton:
        """Создает кнопку для переключения режима."""
        button = QPushButton(get_text(text_key, language=self.logic.DEFAULT_LANGUAGE))
        button.setObjectName(f"{mode_name}_mode_button")
        button.setStyleSheet("font-size: 10pt; padding: 2px;")
        # Подключаем к функции смены режима родительского окна
        button.clicked.connect(lambda: self.switch_mode_callback(mode_name))
        return button

    def _create_topmost_button(self) -> QPushButton:
        """Создает кнопку для переключения режима "Поверх окон"."""
        button = QPushButton()
        button.setObjectName("topmost_button")

        # Внутренняя функция для обновления вида кнопки (текст и стиль)
        def update_visual_state():
            if not button: return # Защита, если кнопка уже удалена
            is_topmost = self.parent._is_win_topmost # Получаем состояние из родителя
            # Устанавливаем текст
            button.setText(get_text('topmost_on' if is_topmost else 'topmost_off', language=self.logic.DEFAULT_LANGUAGE))
            # Устанавливаем стиль в зависимости от состояния
            bg_color = "#4CAF50" if is_topmost else "gray"
            border_color = "#388E3C" if is_topmost else "#666666"
            hover_bg_color = "#45a049" if is_topmost else "#757575"
            button.setStyleSheet(f"""
                QPushButton {{
                    font-size: 10pt; padding: 2px;
                    background-color: {bg_color}; border: 1px solid {border_color};
                    border-radius: 4px; color: white; min-width: 80px;
                }}
                QPushButton:hover {{ background-color: {hover_bg_color}; }}
            """)
        # Сохраняем ссылку на эту функцию внутри кнопки для вызова извне
        setattr(button, '_update_visual_state', update_visual_state)
        # Подключаем клик к переключению topmost в родительском окне
        button.clicked.connect(self.parent.toggle_topmost_winapi)
        # Обновляем начальное состояние
        update_visual_state()
        return button

    def _create_info_button(self, text_key: str, callback) -> QPushButton:
        """Создает кнопку для показа информационных диалогов ("Об авторе", "Рейтинг")."""
        button = QPushButton(get_text(text_key, language=self.logic.DEFAULT_LANGUAGE))
        button.setObjectName(f"{text_key}_button")
        button.setStyleSheet("font-size: 10pt; padding: 2px;")
        button.clicked.connect(callback) # Подключаем к переданной функции
        button.setVisible(False) # По умолчанию скрыты (показываются в max режиме)
        return button

    def _create_close_button(self) -> QPushButton:
        """Создает кастомную кнопку 'X' для закрытия окна (используется в min режиме)."""
        button = QPushButton("X")
        button.setObjectName("close_button")
        button.setFixedSize(25, 25) # Маленькая квадратная кнопка
        button.setStyleSheet("""
            QPushButton {
                font-size: 10pt; font-weight: bold; padding: 1px;
                color: black; background-color: #ff605c; /* Красный цвет */
                border-radius: 5px; margin-left: 5px;
                border: 1px solid #E04340;
            }
            QPushButton:hover { background-color: #e04340; }
            QPushButton:pressed { background-color: #c0302c; }
        """)
        # Подключаем к слоту close родительского окна
        button.clicked.connect(self.parent.close)
        button.setVisible(False) # По умолчанию скрыта
        return button

    def _insert_widget_after_stretch(self, layout: QHBoxLayout, widget: QWidget):
        """Вспомогательный метод для вставки виджета после растяжки (больше не используется)."""
        stretch_index = -1
        for i in range(layout.count()):
            item = layout.itemAt(i)
            # Ищем QSpacerItem с горизонтальной растяжкой
            if isinstance(item, QSpacerItem) and item.spacerItem().expandingDirections() & Qt.Orientation.Horizontal:
                stretch_index = i
                break
        if stretch_index != -1:
             # Вставляем после найденной растяжки
             layout.insertWidget(stretch_index + 1, widget)
        else:
             # Если растяжки нет, просто добавляем в конец
             layout.addWidget(widget)


    def update_language(self):
        """Обновляет тексты элементов на панели на текущий язык."""
        current_lang = self.logic.DEFAULT_LANGUAGE

        if self.language_label: self.language_label.setText(get_text('language', language=current_lang))
        if self.mode_label: self.mode_label.setText(get_text('mode', language=current_lang))
        if self.min_button: self.min_button.setText(get_text('mode_min', language=current_lang))
        if self.middle_button: self.middle_button.setText(get_text('mode_middle', language=current_lang))
        if self.max_button: self.max_button.setText(get_text('mode_max', language=current_lang))

        # Обновляем текст кнопки topmost через ее внутреннюю функцию
        if self.topmost_button:
            update_func = getattr(self.topmost_button, '_update_visual_state', None)
            if update_func and callable(update_func): # Добавлена проверка callable
                 try:
                     update_func()
                 except Exception as e:
                      logging.error(f"Error calling _update_visual_state for topmost button: {e}")
            elif not update_func:
                 logging.warning("'_update_visual_state' function not found on topmost_button.")


        if self.author_button: self.author_button.setText(get_text('about_author', language=current_lang))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating', language=current_lang))

        # <<< ИЗМЕНЕНО: Обновляем текст метки версии >>>
        if self.version_label:
             self.version_label.setText(f"v{self.app_version}")
        # <<< ---------------------------------- >>>


        # Обновляем текст выбранного элемента в комбо-боксе языка
        if self.language_combo:
            current_code = self.logic.DEFAULT_LANGUAGE
            index_to_select = self.language_combo.findData(current_code)
            if index_to_select != -1:
                 # Блокируем сигналы, чтобы не вызвать switch_language снова
                 self.language_combo.blockSignals(True)
                 self.language_combo.setCurrentIndex(index_to_select)
                 self.language_combo.blockSignals(False)