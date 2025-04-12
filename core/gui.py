# File: gui.py
from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame,
                               QLabel, QPushButton, QApplication, QListWidget, QListWidgetItem, QMenu)
from PySide6.QtCore import Qt, QSize # Добавил QSize
from PySide6.QtGui import QColor, QBrush
from top_panel import create_top_panel
from right_panel import create_right_panel, HERO_NAME_ROLE
from left_panel import create_left_panel
from utils_gui import copy_to_clipboard
from build import version
from logic import CounterpickLogic, TEAM_SIZE
# Импортируем константу размера иконок
from images_load import get_images_for_mode, TOP_HORIZONTAL_ICON_SIZE
from translations import get_text, set_language, DEFAULT_LANGUAGE, TRANSLATIONS, SUPPORTED_LANGUAGES
from mode_manager import change_mode, update_interface_for_mode
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes
from display import generate_counterpick_display, generate_minimal_icon_list

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logic = CounterpickLogic()
        self.mode = "middle"
        self.initial_pos = None
        self.mode_positions = {"max": None, "middle": None, "min": None}
        self.copy_to_clipboard = lambda: copy_to_clipboard(self.logic)

        # Атрибуты UI
        self.right_images = {}
        self.left_images = {}
        self.small_images = {}
        self.horizontal_images = {}
        # Сохраняем размер иконок горизонтального списка
        self.top_horizontal_icon_size = TOP_HORIZONTAL_ICON_SIZE

        self.top_frame = None
        self.author_button = None
        self.rating_button = None
        self.main_widget = None
        self.inner_layout = None
        self.left_container = None
        self.icons_frame = None
        self.icons_layout = None
        self.canvas = None
        self.result_frame = None
        self.result_label = None
        self.update_scrollregion = lambda: None
        self.right_frame = None
        self.selected_heroes_label = None
        self.right_list_widget = None
        self.hero_items = {}
        self.is_programmatically_updating_selection = False

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{version}")
        self.setGeometry(100, 100, 950, 350) # Увеличил нач. высоту
        self.setMinimumSize(400, 100)
        self.initial_pos = self.pos()
        self.mode_positions["middle"] = self.pos()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Верхняя панель
        (self.top_frame, self.author_button, self.rating_button,
         self.switch_mode_cb) = create_top_panel(self, self.change_mode, self.logic)
        self.main_layout.addWidget(self.top_frame)

        # 2. Горизонтальный список иконок
        self.icons_frame = QFrame(self)
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(5, 2, 5, 2)
        self.icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Устанавливаем высоту фрейма на основе размера иконок + отступы
        icons_frame_height = self.top_horizontal_icon_size.height() + 4 + 4 # Иконка + верх/низ отступы/padding
        self.icons_frame.setFixedHeight(icons_frame_height)
        self.icons_frame.setStyleSheet("background-color: #f0f0f0;")
        self.main_layout.addWidget(self.icons_frame)

        # 3. Основной виджет с левой/правой панелями
        self.main_widget = QWidget()
        self.inner_layout = QHBoxLayout(self.main_widget)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1)

        # --- Загрузка изображений ---
        try:
            self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(self.mode)
        except Exception as e: print(f"Критическая ошибка загрузки изображений: {e}"); self.close(); return

        # --- Создание левой и правой панелей ВНУТРИ main_widget ---
        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(0)
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.left_container)
        left_layout.addWidget(self.canvas, stretch=1)
        self.inner_layout.addWidget(self.left_container, stretch=2)

        self.right_frame, self.selected_heroes_label = create_right_panel(self, self.mode)
        self.inner_layout.addWidget(self.right_frame, stretch=1)
        # -------------------------------------------

        self.switch_language_callback = lambda lang: self.switch_language(lang)
        self.update_language()
        update_interface_for_mode(self) # Применяем начальный режим

    # --- МЕТОДЫ ОБНОВЛЕНИЯ UI (без изменений в этой секции) ---
    def update_list_item_selection_states(self):
        if not self.hero_items or not self.right_list_widget: return
        try:
             self.is_programmatically_updating_selection = True
             self.right_list_widget.blockSignals(True)
             current_logic_selection = set(self.logic.selected_heroes)
             for hero, item in self.hero_items.items():
                 if item is None: continue
                 try: item.setSelected(hero in current_logic_selection)
                 except RuntimeError: pass # Игнор ошибок для удаленных
        finally:
            try: self.right_list_widget.blockSignals(False)
            except RuntimeError: pass
            self.is_programmatically_updating_selection = False

    def update_priority_labels(self):
        if not self.hero_items: return
        priority_color = QColor("lightcoral"); default_brush = QBrush(Qt.GlobalColor.transparent)
        for hero, item in self.hero_items.items():
             if item is None: continue
             try:
                  target_brush = QBrush(priority_color) if hero in self.logic.priority_heroes else default_brush
                  if item.background() != target_brush: item.setBackground(target_brush)
             except RuntimeError: pass

    def update_selected_label(self):
        if self.selected_heroes_label:
             try: self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass

    def update_counterpick_display(self):
        if not self.result_frame or not self.result_label: return
        try: layout = self.result_frame.layout(); assert layout is not None
        except (RuntimeError, AssertionError): return

        while layout.count():
             item = layout.takeAt(0); widget = item.widget()
             if widget and widget != self.result_label: widget.deleteLater()
             elif item.layout():
                 while item.layout().count(): sub_item = item.layout().takeAt(0); widget = sub_item.widget(); widget.deleteLater()
             elif item.spacerItem() or not widget: layout.removeItem(item)

        try:
            if not self.logic.selected_heroes:
                self.result_label.setText(get_text('no_heroes_selected')); self.result_label.show()
                if layout.indexOf(self.result_label) == -1: layout.addWidget(self.result_label)
                layout.addStretch(1)
            else:
                self.result_label.hide()
                if layout.indexOf(self.result_label) != -1: layout.removeWidget(self.result_label)
                if not self.left_images or (self.mode != 'min' and not self.small_images):
                     _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
                if self.mode == "min": generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
                else: generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)

            layout.activate(); self.result_frame.adjustSize()
            if self.canvas: self.canvas.updateGeometry(); self.update_scrollregion(); self.canvas.verticalScrollBar().setValue(0); self.canvas.update()
        except RuntimeError as e: print(f"Err(upd_cnt): {e}")
        except Exception as e: print(f"Err(upd_cnt_g): {e}")

    def update_ui_after_logic_change(self):
        self.update_selected_label()
        self.update_counterpick_display()
        update_horizontal_icon_list(self)
        self.update_list_item_selection_states()
        self.update_priority_labels()

    # --- Обработчик сигнала itemSelectionChanged ---
    def handle_selection_changed(self):
        if self.is_programmatically_updating_selection: return
        if not self.right_list_widget: return
        # print("--- Сработал handle_selection_changed ---")
        current_ui_selection_names = {item.data(HERO_NAME_ROLE) for item in self.right_list_widget.selectedItems() if item.data(HERO_NAME_ROLE)}
        # print(f"Current UI Selection: {current_ui_selection_names}")
        self.logic.set_selection(current_ui_selection_names)
        # print("Вызов update_ui_after_logic_change после set_selection...")
        self.update_ui_after_logic_change()
        # print("--- Завершение handle_selection_changed ---")

    # --- Контекстное меню для приоритета ---
    def show_priority_context_menu(self, pos):
         if not self.right_list_widget: return
         global_pos = self.right_list_widget.viewport().mapToGlobal(pos)
         item = self.right_list_widget.itemAt(pos)
         if not item: return
         hero_name = item.data(HERO_NAME_ROLE)
         if not hero_name or not item.isSelected(): return
         menu = QMenu(self)
         action_text = get_text('remove_priority') if hero_name in self.logic.priority_heroes else get_text('set_priority')
         priority_action = menu.addAction(action_text)
         action = menu.exec(global_pos)
         if action == priority_action:
              # print(f"Действие приоритета для {hero_name} выбрано.")
              self.logic.set_priority(hero_name)
              self.update_ui_after_logic_change()

    # --- Методы смены режима, восстановления, языка ---
    def change_mode(self, mode):
        # print(f"Смена режима на: {mode}")
        change_mode(self, mode)

    def restore_hero_selections(self):
        # print("Восстановление состояния UI (вызов полного обновления)...")
        self.update_ui_after_logic_change()
        # print("Восстановление состояния UI завершено.")

    def switch_language(self, lang):
        # print(f"Переключение языка на: {lang}")
        set_language(lang)
        self.update_language()
        self.update_ui_after_logic_change()

    def update_language(self):
        # print("Обновление текстов интерфейса...")
        self.setWindowTitle(f"{get_text('title')} v{version}")
        if self.selected_heroes_label: self.update_selected_label()
        if self.result_label and not self.logic.selected_heroes: self.result_label.setText(get_text('no_heroes_selected'))
        if self.author_button: self.author_button.setText(get_text('about_author'))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating'))
        if self.top_frame: self._update_top_panel_lang()
        if self.right_frame: self._update_right_panel_lang()

    def _update_top_panel_lang(self):
        key_map_label = {'language': 'language', 'mode': 'mode'}
        for label in self.top_frame.findChildren(QLabel):
            original_key = label.property("original_text_key")
            if original_key in key_map_label: label.setText(get_text(original_key))
            else: # Fallback by text matching
                possible_lang = [get_text('language', lang=l) for l in SUPPORTED_LANGUAGES]
                possible_mode = [get_text('mode', lang=l) for l in SUPPORTED_LANGUAGES]
                if label.text() in possible_lang: label.setText(get_text('language')); label.setProperty("original_text_key", 'language')
                elif label.text() in possible_mode: label.setText(get_text('mode')); label.setProperty("original_text_key", 'mode')

        key_map_button = {'mode_min': 'mode_min', 'mode_middle': 'mode_middle', 'mode_max': 'mode_max', 'topmost_on': 'topmost_on', 'topmost_off': 'topmost_off', 'about_author': 'about_author', 'hero_rating': 'hero_rating'}
        for button in self.top_frame.findChildren(QPushButton):
            found_key = None; current_text = button.text()
            for key, base_key in key_map_button.items():
                 if current_text in [get_text(base_key, lang=l) for l in SUPPORTED_LANGUAGES]: found_key = base_key; break
            if found_key:
                # Special handling for topmost button state
                if found_key == 'topmost_on' or found_key == 'topmost_off':
                    is_topmost = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
                    button.setText(get_text('topmost_on') if is_topmost else get_text('topmost_off'))
                else:
                     button.setText(get_text(found_key))


    def _update_right_panel_lang(self):
        key_map_button = {'copy_rating': 'copy_rating', 'clear_all': 'clear_all'}
        for button in self.right_frame.findChildren(QPushButton):
            found_key = None; current_text = button.text()
            for key, base_key in key_map_button.items():
                 if current_text in [get_text(base_key, lang=l) for l in SUPPORTED_LANGUAGES]: found_key = base_key; break
            if found_key: button.setText(get_text(found_key))


# --- Глобальные функции ---
def create_gui():
    return MainWindow()