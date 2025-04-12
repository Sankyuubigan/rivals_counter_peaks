# File: gui.py
from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame,
                               QLabel, QPushButton, QApplication, QListWidget, QListWidgetItem, QMenu)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from top_panel import create_top_panel
from right_panel import create_right_panel, HERO_NAME_ROLE
from left_panel import create_left_panel
from utils_gui import copy_to_clipboard
from build import version
from logic import CounterpickLogic, TEAM_SIZE
from images_load import get_images_for_mode
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
        # self._previous_selection = set() # Больше не нужно хранить здесь

        # Атрибуты UI
        self.right_images = {}
        self.left_images = {}
        self.small_images = {}
        self.horizontal_images = {}
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
        self.is_programmatically_updating_selection = False # Флаг для предотвращения рекурсии

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{version}")
        self.setGeometry(100, 100, 950, 300)
        self.setMinimumSize(400, 100) # Устанавливаем разумный минимум
        # self.setMaximumSize(2000, 2000) # Максимум пока уберем
        self.initial_pos = self.pos()
        self.mode_positions["middle"] = self.pos()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0) # Убираем расстояние между top, icons, main

        # 1. Верхняя панель
        (self.top_frame, self.author_button, self.rating_button,
         self.switch_mode_cb) = create_top_panel(self, self.change_mode, self.logic)
        self.main_layout.addWidget(self.top_frame)

        # 2. Горизонтальный список иконок (под верхней панелью)
        self.icons_frame = QFrame(self)
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(5, 2, 5, 2)
        self.icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) # Выравнивание по центру верт.
        self.icons_frame.setFixedHeight(30)
        self.icons_frame.setStyleSheet("background-color: #f0f0f0;")
        self.main_layout.addWidget(self.icons_frame)

        # 3. Основной виджет с левой/правой панелями
        self.main_widget = QWidget()
        self.inner_layout = QHBoxLayout(self.main_widget)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        # Добавляем main_widget в main_layout и даем ему растягиваться
        self.main_layout.addWidget(self.main_widget, stretch=1)

        # --- Загрузка изображений ---
        try:
            self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(self.mode)
        except Exception as e:
            print(f"Критическая ошибка загрузки изображений: {e}")
            self.close(); return

        # --- Создание левой и правой панелей ВНУТРИ main_widget ---
        # Левая панель
        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.left_container)
        left_layout.addWidget(self.canvas, stretch=1)
        self.inner_layout.addWidget(self.left_container, stretch=2) # Добавляем в inner_layout

        # Правая панель
        self.right_frame, self.selected_heroes_label = create_right_panel(self, self.mode)
        self.inner_layout.addWidget(self.right_frame, stretch=1) # Добавляем в inner_layout
        # -------------------------------------------

        self.switch_language_callback = lambda lang: self.switch_language(lang)
        self.update_language()

        update_interface_for_mode(self) # Применяем начальный режим

    # --- МЕТОДЫ ОБНОВЛЕНИЯ UI ---

    def update_list_item_selection_states(self):
        """Обновляет состояние ВЫДЕЛЕНИЯ элементов списка в соответствии с logic.selected_heroes."""
        # print("Обновление состояния selection items...")
        if not self.hero_items or not self.right_list_widget:
            # print("Словарь hero_items или right_list_widget не инициализирован.")
            return

        try:
             # Блокируем сигналы ТОЛЬКО на время изменения выделения в цикле
             self.is_programmatically_updating_selection = True
             self.right_list_widget.blockSignals(True)
             # print("Сигналы списка заблокированы.")

             current_logic_selection = set(self.logic.selected_heroes)
             updated_count = 0
             for hero, item in self.hero_items.items():
                 if item is None: continue
                 try:
                     target_selected = hero in current_logic_selection
                     if item.isSelected() != target_selected:
                         item.setSelected(target_selected)
                         updated_count += 1
                 except RuntimeError as e:
                     print(f"  [!] Ошибка Runtime при обновлении selection для {hero}: {e}")

             # print(f"Обновлено состояний выделения: {updated_count}")

        finally:
            try:
                self.right_list_widget.blockSignals(False)
                self.is_programmatically_updating_selection = False
                # print("Сигналы списка разблокированы.")
            except RuntimeError:
                 print("[!] Ошибка разблокировки сигналов списка.")


    def update_priority_labels(self):
        """Обновляет ВИЗУАЛЬНОЕ отображение приоритета (фон)."""
        # print("Обновление отображения приоритета...")
        if not self.hero_items: return
        priority_color = QColor("lightcoral")
        default_brush = QBrush(Qt.GlobalColor.transparent)
        for hero, item in self.hero_items.items():
             if item is None: continue
             try:
                  is_priority = hero in self.logic.priority_heroes
                  current_bg_brush = item.background()
                  target_brush = QBrush(priority_color) if is_priority else default_brush
                  if current_bg_brush != target_brush:
                      item.setBackground(target_brush)
             except RuntimeError as e: pass # Игнорируем ошибки для удаленных элементов

    def update_selected_label(self):
        if self.selected_heroes_label and isinstance(self.selected_heroes_label, QLabel):
            try:
                current_text = self.logic.get_selected_heroes_text()
                self.selected_heroes_label.setText(current_text)
            except RuntimeError as e: pass

    def update_counterpick_display(self):
        # print("--- Начало update_counterpick_display ---")
        if not self.result_frame or not self.result_label: return
        try:
             layout = self.result_frame.layout()
             if layout is None: return
        except RuntimeError as e: return

        # Очистка result_frame
        while layout.count():
             item = layout.takeAt(0)
             widget = item.widget()
             if widget and widget != self.result_label: widget.deleteLater()
             elif item.layout(): # Рекурсивно чистим вложенные layout'ы
                 while item.layout().count():
                      sub_item = item.layout().takeAt(0)
                      if sub_item.widget(): sub_item.widget().deleteLater()
             # Удаляем пустые пространства или сам layout item
             elif item.spacerItem() or not widget: layout.removeItem(item)


        try:
            if not self.logic.selected_heroes:
                self.result_label.setText(get_text('no_heroes_selected'))
                self.result_label.show() # Показываем метку, если нет выбранных
                # Добавляем метку в layout, если ее там нет
                if layout.indexOf(self.result_label) == -1:
                     layout.addWidget(self.result_label)
                layout.addStretch(1) # Добавляем растяжение под меткой
            else:
                self.result_label.hide() # Скрываем метку при отображении результатов
                # Убираем метку из layout, если она там была
                if layout.indexOf(self.result_label) != -1:
                    layout.removeWidget(self.result_label)

                if not self.left_images or (self.mode != 'min' and not self.small_images):
                    print("[!] Перезагрузка изображений для display...")
                    try:
                        _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
                    except Exception as e: print(f"[!] Ошибка: {e}"); return

                # Генерация контента
                if self.mode == "min":
                    generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
                else:
                    generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)

            # Обновление геометрии и прокрутки
            layout.activate()
            self.result_frame.adjustSize()
            if self.canvas:
                self.canvas.updateGeometry()
                if self.update_scrollregion: self.update_scrollregion()
                self.canvas.verticalScrollBar().setValue(0)
                self.canvas.update()

        except RuntimeError as e: print(f"[!] Ошибка Runtime в update_counterpick_display: {e}")
        except Exception as e: print(f"[!] Ошибка в update_counterpick_display: {e}")
        # print("--- Конец update_counterpick_display ---")


    def update_ui_after_logic_change(self):
        """ОСНОВНОЙ МЕТОД ОБНОВЛЕНИЯ UI после изменения логики."""
        # print("===== Запуск полного обновления UI =====")
        self.update_selected_label()              # 1. Текст "Выбрано: ..."
        self.update_counterpick_display()         # 2. Левая панель (рейтинг)
        update_horizontal_icon_list(self)         # 3. Горизонтальный список
        self.update_list_item_selection_states()  # 4. Выделение в списке героев
        self.update_priority_labels()             # 5. Визуал приоритета (фон)
        # print("===== Полное обновление UI завершено =====")

    # --- Обработчик сигнала itemSelectionChanged ---
    def handle_selection_changed(self):
        """
        Обрабатывает изменение выделения. Передает новое состояние в logic.set_selection.
        """
        if self.is_programmatically_updating_selection: return
        if not self.right_list_widget: return

        print("--- Сработал handle_selection_changed ---")
        current_selected_items = self.right_list_widget.selectedItems()
        # Получаем МНОЖЕСТВО имен героев, которые ВЫДЕЛЕНЫ в UI сейчас
        current_ui_selection_names = {item.data(HERO_NAME_ROLE) for item in current_selected_items if item.data(HERO_NAME_ROLE)}

        print(f"Current UI Selection: {current_ui_selection_names}")
        # print(f"Current Logic Selection (before): {self.logic.selected_heroes}")

        # Вызываем метод логики, передавая ему желаемое состояние
        self.logic.set_selection(current_ui_selection_names)

        # После изменения логики, запускаем полное обновление UI
        # Это синхронизирует UI (включая label и выделение) с новым состоянием логики
        print("Вызов update_ui_after_logic_change после set_selection...")
        self.update_ui_after_logic_change()

        print("--- Завершение handle_selection_changed ---")


    # --- Контекстное меню для приоритета ---
    def show_priority_context_menu(self, pos):
         if not self.right_list_widget: return
         global_pos = self.right_list_widget.viewport().mapToGlobal(pos)
         item = self.right_list_widget.itemAt(pos)
         if not item: return
         hero_name = item.data(HERO_NAME_ROLE)
         if not hero_name or not item.isSelected(): return # Только для выделенных

         menu = QMenu(self)
         is_priority = hero_name in self.logic.priority_heroes
         remove_p_text = get_text('remove_priority', 'Снять приоритет')
         set_p_text = get_text('set_priority', 'Назначить приоритет')
         action_text = remove_p_text if is_priority else set_p_text
         priority_action = menu.addAction(action_text)

         action = menu.exec(global_pos)
         if action == priority_action:
              print(f"Действие приоритета для {hero_name} выбрано.")
              self.logic.set_priority(hero_name) # Убираем коллбэк
              self.update_ui_after_logic_change() # Обновляем UI после изменения логики


    def change_mode(self, mode):
        print(f"Смена режима на: {mode}")
        change_mode(self, mode)

    def restore_hero_selections(self):
        # Этот метод, по сути, просто триггер для полного обновления UI
        print("Восстановление состояния UI (вызов полного обновления)...")
        self.update_ui_after_logic_change()
        print("Восстановление состояния UI завершено.")

    def switch_language(self, lang):
        print(f"Переключение языка на: {lang}")
        set_language(lang)
        self.update_language()
        self.update_ui_after_logic_change() # Полное обновление UI

    def update_language(self):
        # print("Обновление текстов интерфейса...")
        self.setWindowTitle(f"{get_text('title')} v{version}")
        if self.selected_heroes_label: self.update_selected_label()
        if self.result_label and not self.logic.selected_heroes:
             self.result_label.setText(get_text('no_heroes_selected'))
        if self.author_button: self.author_button.setText(get_text('about_author'))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating'))
        # Обновление текстов в top_frame
        if self.top_frame: self._update_top_panel_lang()
        # Обновление текстов в right_frame
        if self.right_frame: self._update_right_panel_lang()
        # Обновление подсказок и т.д. (вызывается из switch_language через update_ui)
        # print("Тексты интерфейса обновлены.")

    def _update_top_panel_lang(self):
        """Обновляет тексты в верхней панели."""
        labels = self.top_frame.findChildren(QLabel)
        lang_key, mode_key = 'language', 'mode'
        for label in labels:
            current_text = label.property("original_text_key") # Проверяем, есть ли ключ
            if current_text == lang_key: label.setText(get_text(lang_key))
            elif current_text == mode_key: label.setText(get_text(mode_key))
            else: # Если ключа нет, пытаемся угадать по текущему тексту
                 possible_lang = [get_text(lang_key, lang=l) for l in SUPPORTED_LANGUAGES]
                 possible_mode = [get_text(mode_key, lang=l) for l in SUPPORTED_LANGUAGES]
                 if label.text() in possible_lang:
                     label.setText(get_text(lang_key)); label.setProperty("original_text_key", lang_key)
                 elif label.text() in possible_mode:
                     label.setText(get_text(mode_key)); label.setProperty("original_text_key", mode_key)

        buttons = self.top_frame.findChildren(QPushButton)
        key_map = {
            'mode_min': [get_text('mode_min', lang=l) for l in SUPPORTED_LANGUAGES],
            'mode_middle': [get_text('mode_middle', lang=l) for l in SUPPORTED_LANGUAGES],
            'mode_max': [get_text('mode_max', lang=l) for l in SUPPORTED_LANGUAGES],
            'topmost_on': [get_text('topmost_on', lang=l) for l in SUPPORTED_LANGUAGES],
            'topmost_off': [get_text('topmost_off', lang=l) for l in SUPPORTED_LANGUAGES],
            'about_author': [get_text('about_author', lang=l) for l in SUPPORTED_LANGUAGES],
            'hero_rating': [get_text('hero_rating', lang=l) for l in SUPPORTED_LANGUAGES],
        }
        for button in buttons:
             found_key = None
             for key, texts in key_map.items():
                 if button.text() in texts:
                     found_key = key
                     break
             if found_key: button.setText(get_text(found_key))

    def _update_right_panel_lang(self):
        """Обновляет тексты в правой панели."""
        buttons = self.right_frame.findChildren(QPushButton)
        key_map = {
             'copy_rating': [get_text('copy_rating', lang=l) for l in SUPPORTED_LANGUAGES],
             'clear_all': [get_text('clear_all', lang=l) for l in SUPPORTED_LANGUAGES],
        }
        for button in buttons:
             found_key = None
             for key, texts in key_map.items():
                 if button.text() in texts:
                     found_key = key
                     break
             if found_key: button.setText(get_text(found_key))


# --- Глобальные функции ---
def create_gui():
    return MainWindow()