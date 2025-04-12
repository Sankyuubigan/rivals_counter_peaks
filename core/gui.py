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
from translations import get_text, set_language, DEFAULT_LANGUAGE, TRANSLATIONS, SUPPORTED_LANGUAGES # Добавил SUPPORTED_LANGUAGES
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
        self._previous_selection = set()

        # Атрибуты UI
        self.right_images = {}
        self.left_images = {}
        self.small_images = {}
        self.horizontal_images = {}
        self.top_frame = None
        self.author_button = None
        self.rating_button = None
        self.main_widget = None        # Контейнер для left_container и right_frame
        self.inner_layout = None       # QHBoxLayout внутри main_widget
        self.left_container = None     # Контейнер для canvas в левой части
        self.icons_frame = None        # Горизонтальный фрейм с иконками <--- Перемещен
        self.icons_layout = None       # Layout внутри icons_frame <--- Перемещен
        self.canvas = None             # QScrollArea в левой части
        self.result_frame = None       # QFrame внутри canvas
        self.result_label = None       # QLabel внутри result_frame
        self.update_scrollregion = lambda: None
        self.right_frame = None        # Правая панель (содержит list_widget)
        self.selected_heroes_label = None
        self.right_list_widget = None  # Сам QListWidget
        self.hero_items = {}           # {hero_name: QListWidgetItem}
        self.is_programmatically_updating_selection = False

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{version}")
        self.setGeometry(100, 100, 950, 300) # Немного увеличил высоту по умолчанию
        self.setMaximumSize(2000, 2000)
        self.initial_pos = self.pos()
        self.mode_positions["middle"] = self.pos()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        # Основной ВЕРТИКАЛЬНЫЙ layout окна
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0) # Без отступов между top, icons, main

        # 1. Верхняя панель (top_frame)
        (self.top_frame, self.author_button, self.rating_button,
         self.switch_mode_cb) = create_top_panel(self, self.change_mode, self.logic)
        self.main_layout.addWidget(self.top_frame)

        # 2. Горизонтальный список иконок (icons_frame) - ВСЕГДА ВИДИМ
        self.icons_frame = QFrame(self) # Был в left_container, теперь напрямую в окне
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(5, 2, 5, 2)
        self.icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.icons_frame.setFixedHeight(30) # Фиксированная высота
        # self.icons_frame.setVisible(True) # По умолчанию видим
        self.icons_frame.setStyleSheet("background-color: #f0f0f0;") # Легкий фон для отделения
        self.main_layout.addWidget(self.icons_frame) # Добавляем в ВЕРТИКАЛЬНЫЙ layout

        # 3. Основной виджет с разделением на лево/право (main_widget)
        self.main_widget = QWidget()
        self.inner_layout = QHBoxLayout(self.main_widget) # Горизонтальное разделение
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        self.main_layout.addWidget(self.main_widget, stretch=1) # Растягиваем эту часть

        # --- Загрузка изображений ---
        try:
            # Загружаем изображения для текущего режима (понадобятся для панелей)
            self.right_images, self.left_images, self.small_images, self.horizontal_images = get_images_for_mode(self.mode)
        except Exception as e:
            print(f"Критическая ошибка загрузки изображений: {e}")
            self.close()
            return

        # --- Создание левой и правой панелей ---
        # Левая панель (контейнер + скролл)
        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        # icons_frame больше не здесь
        self.canvas, self.result_frame, self.result_label, self.update_scrollregion = create_left_panel(self.left_container)
        left_layout.addWidget(self.canvas, stretch=1)

        # Правая панель (создается через функцию)
        self.right_frame, self.selected_heroes_label = create_right_panel(self, self.mode)

        # Добавляем левую и правую панель в ИХ горизонтальный layout (inner_layout)
        self.inner_layout.addWidget(self.left_container, stretch=2)
        self.inner_layout.addWidget(self.right_frame, stretch=1)
        # -------------------------------------------

        self.switch_language_callback = lambda lang: self.switch_language(lang)
        self.update_language() # Обновляем тексты сразу

        update_interface_for_mode(self) # Применяем начальный режим (вызовет restore)

    # --- МЕТОДЫ ОБНОВЛЕНИЯ UI ---

    def update_list_item_selection_states(self):
        """Обновляет состояние ВЫДЕЛЕНИЯ элементов списка в соответствии с logic.selected_heroes."""
        print("Обновление состояния selection items...")
        if not self.hero_items or not self.right_list_widget:
            print("Словарь hero_items или right_list_widget не инициализирован.")
            return

        try:
             self.is_programmatically_updating_selection = True
             self.right_list_widget.blockSignals(True)
             # print("Сигналы списка заблокированы.")
        except RuntimeError:
             print("[!] Ошибка блокировки сигналов списка.")
             self.is_programmatically_updating_selection = False
             return

        updated_count = 0
        try:
            current_logic_selection = set(self.logic.selected_heroes)
            for hero, item in self.hero_items.items():
                if item is None: continue
                try:
                    target_selected = hero in current_logic_selection
                    if item.isSelected() != target_selected:
                        item.setSelected(target_selected)
                        updated_count += 1
                except RuntimeError as e:
                    print(f"  [!] Ошибка Runtime при обновлении selection для {hero}: {e}")

            # Обновляем внутреннее состояние для handle_selection_changed
            self._previous_selection = current_logic_selection

        finally:
            try:
                self.right_list_widget.blockSignals(False)
                self.is_programmatically_updating_selection = False
                # print(f"Сигналы списка разблокированы. Обновлено состояний выделения: {updated_count}")
            except RuntimeError:
                 print("[!] Ошибка разблокировки сигналов списка.")


    def update_priority_labels(self):
        """Обновляет ВИЗУАЛЬНОЕ отображение приоритета (фон)."""
        # print("Обновление отображения приоритета...")
        if not self.hero_items: return

        updated_count = 0
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
                      updated_count +=1
             except RuntimeError as e:
                  print(f"  [!] Ошибка Runtime при обновлении фона приоритета для {hero}: {e}")
        # print(f"Обновлено фонов приоритета: {updated_count}")

    def update_selected_label(self):
        if self.selected_heroes_label and isinstance(self.selected_heroes_label, QLabel):
            try:
                current_text = self.logic.get_selected_heroes_text()
                self.selected_heroes_label.setText(current_text)
            except RuntimeError as e:
                 print(f"  [!] Ошибка Runtime при обновлении selected_heroes_label: {e}")

    def update_counterpick_display(self):
        # ... (код без изменений) ...
        print("--- Начало update_counterpick_display ---")
        if not self.result_frame or not self.result_label:
            print("[!] Ошибка: result_frame или result_label не инициализированы.")
            return
        try:
             layout = self.result_frame.layout()
             if layout is None:
                  print("[!] Ошибка: layout у result_frame отсутствует.")
                  return
        except RuntimeError as e:
             print(f"[!] Ошибка Runtime при проверке result_frame/result_label: {e}")
             return

        # Очистка result_frame
        deleted_count = 0
        items_to_remove = []
        for i in range(layout.count()):
             item = layout.itemAt(i)
             if item:
                 widget = item.widget()
                 # Не удаляем self.result_label, если он там есть
                 if widget and widget != self.result_label:
                      items_to_remove.append(widget) # Сохраняем сам виджет для удаления
                 elif not widget and item.spacerItem(): # Удаляем распорки тоже
                      items_to_remove.append(item) # Сохраняем QSpacerItem


        for item_or_widget in reversed(items_to_remove):
            try:
                if isinstance(item_or_widget, QWidget):
                    layout.removeWidget(item_or_widget)
                    item_or_widget.deleteLater()
                else: # Предполагаем, что это QSpacerItem
                    layout.removeItem(item_or_widget)
                deleted_count += 1
            except RuntimeError as e: pass

        try:
            if not self.logic.selected_heroes:
                self.result_label.setVisible(True)
                self.result_label.setText(get_text('no_heroes_selected'))
            else:
                if not self.left_images or (self.mode != 'min' and not self.small_images):
                     print("[!] Предупреждение: Изображения не загружены в self.")
                     try:
                        _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
                        print("Изображения перезагружены.")
                     except Exception as e:
                        print(f"[!] Ошибка загрузки изображений: {e}")
                        return

                # Генерация контента
                if self.mode == "min":
                    self.result_label.setVisible(False) # В мин. режиме метка не нужна
                    generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
                else:
                    self.result_label.setVisible(False) # Скрываем метку и при генерации детального списка
                    # self.result_label.setText("") # Очищаем на всякий случай
                    generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)

            # Обновление геометрии и прокрутки
            layout.activate()
            self.result_frame.adjustSize()
            if self.canvas:
                self.canvas.updateGeometry()
                if self.update_scrollregion: self.update_scrollregion()
                self.canvas.verticalScrollBar().setValue(0) # Прокрутка вверх при обновлении
                self.canvas.update()

        except RuntimeError as e:
             print(f"[!] КРИТИЧЕСКАЯ ОШИБКА Runtime при обновлении панели контрпиков: {e}")
        except Exception as e:
             print(f"[!] Неожиданная ошибка при обновлении панели контрпиков: {e}")
        # print("--- Конец update_counterpick_display ---")


    def update_ui_after_logic_change(self):
        """ОСНОВНОЙ МЕТОД ОБНОВЛЕНИЯ UI после изменения логики."""
        print("===== Запуск полного обновления UI =====")
        self.update_selected_label()              # 1. Текст "Выбрано: ..."
        self.update_counterpick_display()         # 2. Левая панель (рейтинг)
        update_horizontal_icon_list(self)         # 3. Горизонтальный список
        self.update_list_item_selection_states()  # 4. Выделение в списке героев
        self.update_priority_labels()             # 5. Визуал приоритета (фон)
        print("===== Полное обновление UI завершено =====")

    # --- Обработчик сигнала itemSelectionChanged ---
    def handle_selection_changed(self):
        """
        Обрабатывает изменение выделения. Определяет, какой герой был добавлен/удален
        и вызывает logic.toggle_hero. Логика лимита и замены - внутри toggle_hero.
        """
        if self.is_programmatically_updating_selection:
            # print("Изменение выделения проигнорировано (программное)")
            return

        if not self.right_list_widget: return

        print("--- Сработал handle_selection_changed ---")
        current_selected_items = self.right_list_widget.selectedItems()
        current_selection_names = {item.data(HERO_NAME_ROLE) for item in current_selected_items if item.data(HERO_NAME_ROLE)}
        previous_selection_names = self._previous_selection # Используем сохраненное состояние

        print(f"UI Selection: {current_selection_names}")
        print(f"Previous (Logic): {previous_selection_names}")

        # Находим изменения относительно СОХРАНЕННОГО состояния
        added = current_selection_names - previous_selection_names
        removed = previous_selection_names - current_selection_names
        print(f"Added in UI: {added}")
        print(f"Removed in UI: {removed}")

        # Вызываем toggle_hero для каждого изменения
        # Порядок важен, если происходит замена (сначала удаление старого неявно произойдет в toggle при добавлении нового)
        callback_needed = False
        for hero_name in removed:
            if hero_name in self.logic.selected_heroes: # Если он действительно был выбран в логике
                print(f" -> UI deselect: {hero_name}. Calling toggle_hero.")
                self.logic.toggle_hero(hero_name, None) # Вызываем БЕЗ коллбэка
                callback_needed = True

        for hero_name in added:
             # Не проверяем лимит здесь, toggle_hero сам разберется
             print(f" -> UI select: {hero_name}. Calling toggle_hero.")
             self.logic.toggle_hero(hero_name, None) # Вызываем БЕЗ коллбэка
             callback_needed = True

        # Если были какие-либо изменения, вызываем ПОЛНОЕ обновление UI ОДИН раз
        if callback_needed:
            print("Изменения обработаны, вызываем update_ui_after_logic_change...")
            self.update_ui_after_logic_change()
        else:
            # Если изменений не было (например, клик на уже выбранный элемент без Ctrl),
            # нужно синхронизировать _previous_selection с текущим состоянием UI на всякий случай
            self._previous_selection = current_selection_names
            print("Изменений в логике не было.")

        print("--- Завершение handle_selection_changed ---")


    # --- Контекстное меню для приоритета ---
    def show_priority_context_menu(self, pos):
         if not self.right_list_widget: return
         global_pos = self.right_list_widget.viewport().mapToGlobal(pos)
         item = self.right_list_widget.itemAt(pos)
         if not item: return

         hero_name = item.data(HERO_NAME_ROLE)
         if not hero_name: return
         # Меню показываем только для ВЫДЕЛЕННЫХ
         if not item.isSelected(): return

         menu = QMenu(self)
         is_priority = hero_name in self.logic.priority_heroes
         # Добавляем переводы для действий меню
         remove_p_text = get_text('remove_priority', 'Снять приоритет')
         set_p_text = get_text('set_priority', 'Назначить приоритет')
         action_text = remove_p_text if is_priority else set_p_text
         priority_action = menu.addAction(action_text)

         action = menu.exec(global_pos)

         if action == priority_action:
              print(f"Действие приоритета для {hero_name} выбрано.")
              self.logic.set_priority(hero_name, self.update_ui_after_logic_change)


    def change_mode(self, mode):
        print(f"Смена режима на: {mode}")
        change_mode(self, mode)

    def restore_hero_selections(self):
        print("Восстановление состояния UI...")
        self.update_ui_after_logic_change()
        print("Восстановление состояния UI завершено.")

    def switch_language(self, lang):
        print(f"Переключение языка на: {lang}")
        set_language(lang)
        self.update_language()
        self.update_ui_after_logic_change()

    def update_language(self):
        print("Обновление текстов интерфейса...")
        self.setWindowTitle(f"{get_text('title')} v{version}")

        # Обновление метки "Выбрано"
        if self.selected_heroes_label and isinstance(self.selected_heroes_label, QLabel):
             try:
                  self.update_selected_label() # Пересчитает текст с учетом языка и кол-ва
             except RuntimeError as e: pass

        # Обновление метки "Выберите героев"
        if self.result_label and isinstance(self.result_label, QLabel) and not self.logic.selected_heroes:
             try:
                  self.result_label.setText(get_text('no_heroes_selected'))
             except RuntimeError as e: pass

        # Кнопки в top_frame
        if self.author_button: self.author_button.setText(get_text('about_author'))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating'))

        if self.top_frame:
            # Метки языка и режима
            labels = self.top_frame.findChildren(QLabel)
            lang_key, mode_key = 'language', 'mode' # Ищем по ключам
            for label in labels:
                 # Безопаснее проверять по objectName, если он задан,
                 # но пока будем сравнивать с переводом ключей
                 if label.text() in [get_text(lang_key, lang) for lang in SUPPORTED_LANGUAGES]:
                      label.setText(get_text(lang_key))
                 elif label.text() in [get_text(mode_key, lang) for lang in SUPPORTED_LANGUAGES]:
                      label.setText(get_text(mode_key))

            # Кнопки режимов и "Поверх окон"
            buttons = self.top_frame.findChildren(QPushButton)
            mode_min_key, mode_mid_key, mode_max_key = 'mode_min', 'mode_middle', 'mode_max'
            top_on_key, top_off_key = 'topmost_on', 'topmost_off'

            possible_min_texts = [get_text(mode_min_key, lang) for lang in SUPPORTED_LANGUAGES]
            possible_mid_texts = [get_text(mode_mid_key, lang) for lang in SUPPORTED_LANGUAGES]
            possible_max_texts = [get_text(mode_max_key, lang) for lang in SUPPORTED_LANGUAGES]
            possible_top_on_texts = [get_text(top_on_key, lang) for lang in SUPPORTED_LANGUAGES]
            possible_top_off_texts = [get_text(top_off_key, lang) for lang in SUPPORTED_LANGUAGES]

            for button in buttons:
                 current_text = button.text()
                 if current_text in possible_min_texts: button.setText(get_text(mode_min_key))
                 elif current_text in possible_mid_texts: button.setText(get_text(mode_mid_key))
                 elif current_text in possible_max_texts: button.setText(get_text(mode_max_key))
                 elif current_text in possible_top_on_texts: button.setText(get_text(top_on_key))
                 elif current_text in possible_top_off_texts: button.setText(get_text(top_off_key))
                 # Кнопки автора и рейтинга уже обновлены выше

        # Кнопки в right_frame
        if self.right_frame:
             buttons_right = self.right_frame.findChildren(QPushButton)
             copy_key, clear_key = 'copy_rating', 'clear_all'
             possible_copy_texts = [get_text(copy_key, lang) for lang in SUPPORTED_LANGUAGES]
             possible_clear_texts = [get_text(clear_key, lang) for lang in SUPPORTED_LANGUAGES]
             for button in buttons_right:
                  current_text = button.text()
                  if current_text in possible_copy_texts: button.setText(get_text(copy_key))
                  elif current_text in possible_clear_texts: button.setText(get_text(clear_key))

        # Обновляем всплывающие подсказки и другие тексты, если они есть и зависят от языка
        # Например, в display.py для tooltips маленьких иконок
        self.update_counterpick_display() # Перегенерируем левую панель для обновления tooltips

        print("Тексты интерфейса обновлены.")


# --- Глобальные функции ---
def create_gui():
    return MainWindow()