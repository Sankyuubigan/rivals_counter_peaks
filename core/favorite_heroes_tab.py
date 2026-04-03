# File: core/favorite_heroes_tab.py
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
                               QPushButton, QLabel, QGridLayout, QApplication)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from core.database.heroes_bd import heroes
from core.image_manager import ImageManager
from core.app_settings_manager import AppSettingsManager
from info.translations import get_text
from images_load import is_invalid_pixmap


class FavoriteHeroesTab(QWidget):
    """Вкладка для выбора избранных героев."""

    def __init__(self, image_manager: ImageManager, settings_manager: AppSettingsManager, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        self.settings_manager = settings_manager
        self.parent_window = parent

        self._init_ui()
        self._load_favorites()
        self._restore_selection()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Описание ---
        desc_label = QLabel(get_text("favorite_heroes_description",
                                     default_text="Выберите героев, за которых вы могли бы или хотели бы отыграть"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 12px; margin: 5px;")
        main_layout.addWidget(desc_label)

        # --- Сетка героев ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setSpacing(5)

        scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(scroll_area, stretch=1)

        # --- Кнопки ---
        button_layout = QHBoxLayout()
        self.copy_button = QPushButton(get_text("favorite_heroes_copy_button", default_text="Копировать избранных"))
        self.copy_button.clicked.connect(self._copy_favorites_to_clipboard)

        self.clear_button = QPushButton(get_text("favorite_heroes_clear_button", default_text="Очистить избранных"))
        self.clear_button.clicked.connect(self._clear_favorites)

        button_layout.addStretch(1)
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)

        # --- Заполняем сетку ---
        self._populate_grid()

    def _populate_grid(self):
        """Заполняет сетку иконок героев."""
        # Очистка
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        right_images = self.image_manager.get_specific_images('middle', 'right')

        # Определяем тему
        current_theme = "light"
        if hasattr(self.parent_window, 'settings_manager'):
            current_theme = self.parent_window.settings_manager.get_theme()

        # Сколько колонок
        cols = 8
        row, col = 0, 0

        for hero in heroes:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(50, 60)
            btn.setToolTip(hero)

            pixmap = right_images.get(hero)
            if is_invalid_pixmap(pixmap):
                btn.setText(hero[:5])
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        border: 2px solid #999;
                        border-radius: 5px;
                        font-size: 8px;
                    }
                    QPushButton:checked {
                        background-color: #FFD700;
                        border: 3px solid #FF4500;
                    }
                """)
            else:
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(40, 40))
                bg_color = "#f0f0f0" if current_theme == "light" else "#2a2a2a"
                border_color = "#ccc" if current_theme == "light" else "#555"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_color};
                        border: 2px solid {border_color};
                        border-radius: 5px;
                    }}
                    QPushButton:checked {{
                        background-color: #FFD700;
                        border: 3px solid #FF4500;
                    }}
                """)

            btn.clicked.connect(lambda checked, h=hero: self._on_hero_toggled(h, checked))
            self.grid_layout.addWidget(btn, row, col)

            col += 1
            if col >= cols:
                col = 0
                row += 1

        self.grid_layout.setColumnStretch(cols, 1)

    def _load_favorites(self):
        """Загружает избранных героев из конфига."""
        self.favorites = set(self.settings_manager.get_favorite_heroes())

    def _restore_selection(self):
        """Восстанавливает выделение кнопок из загруженных favorites."""
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                hero = widget.toolTip()
                if hero in self.favorites:
                    widget.setChecked(True)

    def _on_hero_toggled(self, hero: str, checked: bool):
        """Обрабатывает переключение героя."""
        if checked:
            self.favorites.add(hero)
        else:
            self.favorites.discard(hero)
        # Сохраняем в конфиг
        self.settings_manager.set_favorite_heroes(list(self.favorites))
        logging.info(f"[FavoriteHeroes] Избранные: {self.favorites}")

    def _copy_favorites_to_clipboard(self):
        """Копирует список избранных героев в буфер обмена."""
        if not self.favorites:
            return
        text = ", ".join(sorted(self.favorites))
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        logging.info(f"[FavoriteHeroes] Избранные скопированы в буфер: {text}")

    def _clear_favorites(self):
        """Очищает список избранных."""
        self.favorites.clear()
        self.settings_manager.set_favorite_heroes([])
        # Снимаем все выделения
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton) and widget.isChecked():
                widget.setChecked(False)
        logging.info("[FavoriteHeroes] Избранные очищены")

    def update_theme(self):
        """Обновляет тему при смене темы."""
        self._populate_grid()
        # Восстанавливаем выделение
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                hero = widget.toolTip()
                if hero in self.favorites:
                    widget.setChecked(True)
