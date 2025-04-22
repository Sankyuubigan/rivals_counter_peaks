# File: gui.py
print("[LOG] core/gui.py started")

import time
import threading
import sys # Добавлен импорт

print(f"[LOG] Пытаюсь импортировать PySide6.QtWidgets")
from PySide6.QtWidgets import (QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QFrame,
                               QLabel, QPushButton, QApplication, QListWidget, QListWidgetItem, QMenu,
                               QAbstractItemView, QStyle, QComboBox, QScrollArea, QMessageBox) # Добавлен QMessageBox

print(f"[LOG] Пытаюсь импортировать PySide6.QtCore")
from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QPoint, QModelIndex, QEvent, QThread, QObject

print(f"[LOG] Пытаюсь импортировать PySide6.QtGui")
from PySide6.QtGui import QColor, QPalette, QIcon, QBrush, QMouseEvent

from top_panel import create_top_panel
from right_panel import create_right_panel, HERO_NAME_ROLE

from left_panel import create_left_panel
from utils_gui import copy_to_clipboard
# from build import version # Версия теперь берется из logic или os.environ
from logic import CounterpickLogic, TEAM_SIZE
from images_load import get_images_for_mode, SIZES, load_hero_templates
from translations import get_text, set_language, DEFAULT_LANGUAGE, TRANSLATIONS, SUPPORTED_LANGUAGES
from mode_manager import change_mode, update_interface_for_mode
from core.mode import ModeManager
from core.ui_update import UiUpdateManager
from horizontal_list import update_horizontal_icon_list
from core.hotkeys import HotkeyManager # Добавлен импорт HotkeyManager
from heroes_bd import heroes
from core.utils_gui import calculate_columns
from typing import TYPE_CHECKING
from display import generate_counterpick_display, generate_minimal_icon_list
# <<< ДОБАВЛЕНО: Импорты для распознавания >>>
from utils import capture_screen_area, RECOGNITION_AREA, RECOGNITION_THRESHOLD
from core.win_api import WinApiManager
# <<< КОНЕЦ ДОБАВЛЕННОГО >>>

from recognition import RecognitionManager

# --- Класс MainWindow ---
class MainWindow(QMainWindow):
    recognize_heroes_signal = Signal()
    # <<< ------------------------------------ >>>
    # <<< ДОБАВЛЕНО: Сигнал для обновления UI после распознавания >>>
    recognition_complete_signal = Signal(list)
    # <<< -------------------------------------------------------- >>>

    if TYPE_CHECKING:
        from main import app_version
    def __init__(self, app_version):
        super().__init__()
        # Получаем версию из переменной окружения, установленной в build.py
        self.app_version = app_version
        self.logic = CounterpickLogic()
        # Передаем версию в logic
        self.logic.APP_VERSION = self.app_version #  

        #self.mode = "middle" # Начальный режим
        self.initial_pos = None # Начальная позиция окна
        self.mode_positions = {"max": None, "middle": None, "min": None} # Позиции для каждого режима
        self.copy_to_clipboard = lambda: copy_to_clipboard(self.logic)

        # Атрибуты UI (инициализируем как None)
        self.right_images, self.left_images, self.small_images, self.horizontal_images = {}, {}, {}, {}
        self.top_frame, self.author_button, self.rating_button = None, None, None
        self.main_widget, self.inner_layout, self.left_container = None, None, None
        self.icons_scroll_area = None
        self.icons_scroll_content = None
        self.icons_scroll_content_layout = None
        self.canvas, self.result_frame, self.result_label = None, None, None
        self.update_scrollregion = lambda: None # Placeholder
        self.right_frame, self.selected_heroes_label = None, None
        self.right_list_widget = None
        self.hero_items = {} # Словарь для хранения QListWidgetItem'ов
        self.is_programmatically_updating_selection = False # Флаг для предотвращения рекурсии

        # Атрибуты для горячих клавиш
        self.hotkey_manager = HotkeyManager(self) # Создание менеджера горячих клавиш
        self.hotkey_cursor_index = -1 # Индекс элемента под фокусом хоткея (-1 = нет фокуса)
        self._num_columns_cache = 1 # Кэш количества колонок в QListWidget      

        # Создание менеджера режимов
        self.mode_manager = ModeManager(self)

        # <<< ДОБАВЛЕНО: Атрибуты для распознавания >>>
        self.recognition_manager = RecognitionManager(self.logic)
        # <<< ------------------------------------ >>>

        # <<< ДОБАВЛЕНО: Атрибуты для win_api >>>
        if sys.platform == 'win32':
            self.win_api_manager = WinApiManager(self)

        #Создание менеджера обновлений UI
        self.ui_update_manager = UiUpdateManager(self)

        # <<< ------------------------------------ >>>

        # Атрибуты для перемещения окна без рамки
        self._mouse_pressed = False
        self._old_pos = None

        # <<< ДОБАВЛЕНО: Загрузка шаблонов при инициализации >>>
        self.hotkey_manager.start_keyboard_listener()

    # --- Перемещение окна без рамки ---
    def mousePressEvent(self, event: QMouseEvent):
        # Разрешаем перемещение только в min режиме и только если зажали top_frame
        if self.mode == "min" and self.top_frame and self.top_frame.underMouse():
            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_pressed = True
                self._old_pos = event.globalPosition().toPoint() # Запоминаем глобальную позицию
                event.accept() # Говорим, что обработали событие
                return # Выходим, чтобы не передавать дальше
        self._mouse_pressed = False # Сбрасываем флаг в остальных случаях
        super().mousePressEvent(event) # Вызываем стандартный обработчик

    def mouseMoveEvent(self, event: QMouseEvent):
        # Перемещаем окно, только если зажата кнопка в min режиме
        if self.mode == "min" and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint() # Обновляем позицию
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        # Сбрасываем флаги при отпускании левой кнопки
        if self.mode == "min" and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False
            self._old_pos = None
            event.accept()
            return
        super().mouseReleaseEvent(event)
    # ------------------------------------

    def _create_lists(self):
        """Создаёт списки для главного окна."""
        # Создание правой панели (со списком героев)
        self.right_list_widget = QListWidget()
        self.right_list_widget.setObjectName("right_list_widget")

    def _create_panels(self):
        """Создаёт панели для главного окна."""
        # Создаем левую панель с контрпиками
        self.result_frame = QFrame()
        self.result_frame.setObjectName("result_frame")
        self.result_frame.setMinimumWidth(150)


    def _create_ui_elements(self):
        self._create_panels()
        self._create_lists()
    def _update_topmost_button_visuals(topmost_button): #deleted self
        if topmost_button: update_func = getattr(topmost_button, '_update_visual_state', None);  callable(update_func) and update_func()

    def _create_layout(self):
        """Создает макеты (layouts) для главного окна."""
        # Создаем верхнюю панель
        (self.top_frame, self.author_button, self.rating_button, _) = create_top_panel(self, self.change_mode, self.logic, self.app_version) # self.mode_manager.change_mode
        self.main_layout.addWidget(self.top_frame)

        # Создаем панель для горизонтального списка иконок
        self.icons_scroll_area = QScrollArea(); self.icons_scroll_area.setObjectName("icons_scroll_area")
        self.icons_scroll_area.setWidgetResizable(True)
        self.icons_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.icons_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icons_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f0f0f0; }") # Стиль панели
        self.icons_scroll_content = QWidget(); self.icons_scroll_content.setObjectName("icons_scroll_content")
        self.icons_scroll_content_layout = QHBoxLayout(self.icons_scroll_content)
        self.icons_scroll_content_layout.setObjectName("icons_scroll_content_layout")
        self.icons_scroll_content_layout.setContentsMargins(5, 2, 5, 2); self.icons_scroll_content_layout.setSpacing(4); self.icons_scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.icons_scroll_area.setWidget(self.icons_scroll_content)

        # Расчет высоты панели иконок
        try:
            if not self.horizontal_images: # Загружаем, если еще не загружены
                 _, _, _, self.horizontal_images = get_images_for_mode(self.mode_manager.current_mode)
            h_icon_h = SIZES[self.mode_manager.current_mode]['horizontal'][1] if self.mode_manager.current_mode in SIZES and 'horizontal' in SIZES[self.mode_manager.current_mode] else 30
            icons_frame_height = h_icon_h + 12 # Добавляем отступы (5+5 + 2 для содержимого)
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки/расчета изображений в init_ui: {e}")
            icons_frame_height = 42  # Fallback
            self.horizontal_images = {} # Сбрасываем, если ошибка
        self.icons_scroll_area.setFixedHeight(icons_frame_height) # Устанавливаем фиксированную высоту
        self.main_layout.addWidget(self.icons_scroll_area) # Добавляем панель иконок под верхнюю панель

        # Основной виджет для левой и правой панелей
        self.main_widget = QWidget(); self.main_widget.setObjectName("main_widget")
        self.inner_layout = QHBoxLayout(self.main_widget); self.inner_layout.setObjectName("inner_layout")
        self.inner_layout.setContentsMargins(0, 0, 0, 0); self.inner_layout.setSpacing(0) # Без отступов и расстояний
        self.main_layout.addWidget(self.main_widget, stretch=1) # Этот виджет будет растягиваться


    def _setup_widgets(self):
        """Настраивает виджеты (стили, привязки)."""
        # Стилизация левой панели с контрпиками
        self.result_frame.setStyleSheet("QFrame { background-color: #e0e0e0; }")
        self.result_frame.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)

        # Стилизация правой панели
        self.right_list_widget.setStyleSheet("""
             QListWidget { background-color: #ffffff; }
             QListWidget::item { padding: 5px; }
             QListWidget::item:selected { background-color: #c0c0c0; }
        """)
        self.right_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    def init_ui(self):
        self.setWindowTitle(f"{get_text('title')} v{self.app_version}") # Используем версию из атрибута
        self.setGeometry(100, 100, 950, 350); self.setMinimumSize(400, 100)
        self.initial_pos = self.pos(); self.mode_positions["middle"] = self.pos() # Сохраняем начальную позицию для среднего режима

        central_widget = QWidget(self); self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget); self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        self._create_widgets()
        self._create_ui_elements()
        self._setup_widgets()
        self._create_layout()


        # Callback для смены языка (сохраняем в атрибуте)
        self.switch_language_callback = lambda lang: self.switch_language(lang)
        # Первоначальная настройка интерфейса под текущий режим

        update_interface_for_mode(self)

        # --- Подключение сигналов ---
        # --- Конец подключения сигналов ---

        # Установка начального фокуса хоткея, если нужно
        if self.right_list_widget and self.right_list_widget.count() > 0 and self.mode != 'min':
            self.hotkey_cursor_index = 0
            # Обновляем подсветку с небольшой задержкой, чтобы UI успел отрисоваться
            QTimer.singleShot(100, lambda: self._update_hotkey_highlight(None))    


        self.right_list_widget = QListWidget(); self.right_list_widget.setObjectName("right_list_widget")

    def _update_hotkey_highlight(self, old_index=None):
        """Обновляет подсветку (через делегата) и тултип элемента под фокусом хоткея."""
        # print(f"[LOG] _update_hotkey_highlight called: old={old_index}, new={self.hotkey_cursor_index}") # DEBUG LOG
        if not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode_manager.current_mode == 'min':
            # Если виджета нет или режим min, убедимся, что старый фокус снят
            if old_index is not None and self.right_list_widget and 0 <= old_index < self.right_list_widget.count():
                try:
                     old_item = self.right_list_widget.item(old_index)
                     if old_item:
                         hero_name = old_item.data(HERO_NAME_ROLE)
                         if hero_name and ">>>" in old_item.toolTip():
                             old_item.setToolTip(hero_name)
                             self.right_list_widget.viewport().update() # Запросить перерисовку для удаления рамки
                except Exception as e: print(f"[ERROR] processing old item index {old_index} on clear: {e}")
            return

        list_widget = self.right_list_widget; count = list_widget.count()
        if count == 0: return

        needs_viewport_update = False
        new_index = self.hotkey_cursor_index
        # Восстановление подсказки старого элемента (если он не новый фокус)
        if old_index is not None and old_index != new_index and 0 <= old_index < count: #if old_index is not None and old_index != new_index and 0 <= old_index < count:
            try:
                old_item = list_widget.item(old_index)
                if old_item:
                    hero_name = old_item.data(HERO_NAME_ROLE)
                    if hero_name and ">>>" in old_item.toolTip(): # Если была фокусная подсказка
                        old_item.setToolTip(hero_name) # Восстанавливаем базовую
                        needs_viewport_update = True
            except RuntimeError: pass # Виджет мог быть удален
            except Exception as e: print(f"[ERROR] processing old item index {old_index}: {e}")

        # Установка подсказки нового элемента
        if 0 <= new_index < count:
            try:
                new_item = list_widget.item(new_index)
                if new_item:
                    hero_name = new_item.data(HERO_NAME_ROLE)
                    focus_tooltip = f">>> {hero_name} <<<"
                    if hero_name and new_item.toolTip() != focus_tooltip:
                        new_item.setToolTip(focus_tooltip)
                        needs_viewport_update = True
                    # Прокрутка к элементу
                    list_widget.scrollToItem(new_item, QAbstractItemView.ScrollHint.EnsureVisible)
            except RuntimeError: pass # Виджет мог быть удален
            except Exception as e: print(f"[ERROR] processing new item index {new_index}: {e}")

        # Обновляем viewport, если изменился тултип или индекс
        
        if needs_viewport_update or old_index != new_index: #if needs_viewport_update or old_index != new_index:
             try:
                list_widget.viewport().update()
             except RuntimeError: pass  # Игнорируем, если виджет удален

    def closeEvent(self, event):
        """Перехватывает событие закрытия окна."""
        print("Close event triggered.")
        self.hotkey_manager.stop_keyboard_listener()
        super().closeEvent(event) # Вызываем стандартный обработчик закрытия
    # --- END HOTKEY METHODS ---



    # --- Existing Methods ---



    def update_selected_label(self):
        """Обновляет текст метки с количеством выбранных героев."""
        if self.selected_heroes_label:
             try: self.selected_heroes_label.setText(self.logic.get_selected_heroes_text())
             except RuntimeError: pass # Игнорируем ошибку, если виджет удален
             except Exception as e: print(f"[ERROR] updating selected label: {e}")

    def update_counterpick_display(self):
        """Обновляет левую панель (result_frame) с рейтингом или иконками контрпиков."""
        if not self.result_frame:
             # print("[WARN] No result_frame found in update_counterpick_display")
             return
        # Находим result_label безопасным способом
        result_label_found = self.findChild(QLabel, "result_label") # Ищем во всем окне

        try:
            layout = self.result_frame.layout()
            # Если layout еще не создан (маловероятно, т.к. создается в left_panel), создаем его
            if not layout:
                 layout = QVBoxLayout(self.result_frame); layout.setObjectName("result_layout")
                 layout.setAlignment(Qt.AlignmentFlag.AlignTop); layout.setContentsMargins(2,2,2,2); layout.setSpacing(1)
                 self.result_frame.setLayout(layout)

            # Не очищаем layout здесь, это делается внутри generate_* функций

            # Определяем, какие картинки нужны
            images_ok = bool(self.left_images)
            if self.mode != 'min': images_ok = images_ok and bool(self.small_images)
            if self.mode_manager.current_mode != 'min': images_ok = images_ok and bool(self.small_images)
            # Перезагружаем картинки, если их нет 
            if not images_ok:
                 try:
                     print("[INFO] Перезагрузка изображений для display...")
                     _, self.left_images, self.small_images, _ = get_images_for_mode(self.mode)
                 except Exception as e: print(f"[ERROR] reloading images for display: {e}"); return

            # Вызываем нужную функцию для генерации контента
            if self.mode_manager.current_mode == "min":
                generate_minimal_icon_list(self.logic, self.result_frame, self.left_images)
            else:
                generate_counterpick_display(self.logic, self.result_frame, self.left_images, self.small_images)

            # Обновление геометрии и прокрутки ScrollArea
            # layout.activate() # activate() может быть не нужен
            self.result_frame.adjustSize() # Подгоняем размер result_frame под контент
            if self.canvas: # self.canvas - это ScrollArea из left_panel
                self.canvas.updateGeometry() # Обновляем геометрию ScrollArea
                # Вызываем update_scrollregion после небольшой задержки
                QTimer.singleShot(10, self.update_scrollregion);
                # self.canvas.verticalScrollBar().setValue(0); # Прокрутка в начало не всегда желательна
                self.canvas.update() # Принудительная перерисовка ScrollArea

        except RuntimeError as e: print(f"[ERROR] RuntimeErr(upd_cnt): {e}")
        except Exception as e: print(f"[ERROR] General Err(upd_cnt): {e}")


  

    def handle_selection_changed(self):
        """Слот, вызываемый при изменении выделения в QListWidget."""
        # Игнорируем, если изменение вызвано программно (из update_list_item_selection_states)
        if self.is_programmatically_updating_selection: return
        if not self.right_list_widget: return

        print("[UI Event] Selection changed by user/hotkey.")
        list_widget = self.right_list_widget; current_ui_selection_names = set()
        # Собираем имена всех выделенных героев
        for item in list_widget.selectedItems():
            hero_name = item.data(HERO_NAME_ROLE);
            if hero_name: current_ui_selection_names.add(hero_name)

        # Обновляем логику только если реальный выбор отличается от того, что в logic
        if set(self.logic.selected_heroes) != current_ui_selection_names:
            self.logic.set_selection(current_ui_selection_names)
            self.ui_update_manager.update_ui_after_logic_change() # Полное обновление UI
        else:
             print("[UI Event] Selection unchanged in logic, skipping full UI update.")
             self.ui_update_manager.update_priority_labels()


    def show_priority_context_menu(self, pos):
        """Показывает контекстное меню для установки/снятия приоритета."""
        if not self.right_list_widget or not self.right_list_widget.isVisible(): return
        list_widget = self.right_list_widget
        # Получаем элемент под курсором
        item = list_widget.itemAt(pos)
        if not item: return
        hero_name = item.data(HERO_NAME_ROLE)
        if not hero_name: return

        # Получаем глобальные координаты для показа меню
        global_pos = list_widget.viewport().mapToGlobal(pos)

        menu = QMenu(self)
        is_priority = hero_name in self.logic.priority_heroes
        is_selected = item.isSelected()

        # Создаем действие в меню
        action_text = get_text('remove_priority', language=self.logic.DEFAULT_LANGUAGE) if is_priority else get_text('set_priority', language=self.logic.DEFAULT_LANGUAGE)
        priority_action = menu.addAction(action_text)
        # Действие доступно только если герой выбран
        priority_action.setEnabled(is_selected)

        # Показываем меню и обрабатываем выбор
        action = menu.exec(global_pos)
        if action == priority_action:
             # Проверяем еще раз, что герой выбран (на всякий случай)
             if hero_name in self.logic.selected_heroes:
                 self.logic.set_priority(hero_name)
                 self.ui_update_manager.update_ui_after_logic_change()
             else: print(f"Cannot change priority for '{hero_name}' as it's not selected.")

    def change_mode(self, mode):
        """Инициирует смену режима отображения."""
        self.mode_manager.change_mode(mode)




    # --- Остальные методы ---
    def restore_hero_selections(self):
        """Восстанавливает UI в соответствии с текущим состоянием logic."""
        # print("[UI Restore] Restoring hero selections and UI state.")
        # Эта функция теперь вызывается из update_interface_for_mode ПОСЛЕ создания панелей
        # Основная логика обновления UI теперь в update_ui_after_logic_change
        self.ui_update_manager.update_ui_after_logic_change()
        # Восстанавливаем подсветку фокуса хоткея, если он был установлен
        if self.hotkey_cursor_index != -1:
             # print("[UI Restore] Scheduling focus highlight update.")
             # Используем QTimer для вызова после завершения текущего цикла событий
             QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))


    def switch_language(self, lang):
        """Переключает язык интерфейса."""
        print(f"[LANG] Attempting to switch language to {lang}")
        current_lang = self.logic.DEFAULT_LANGUAGE # Получаем текущий язык из logic
        if current_lang != lang and lang in SUPPORTED_LANGUAGES:
            set_language(lang) # Устанавливаем новый язык в translations.py
            self.logic.DEFAULT_LANGUAGE = lang # Обновляем язык в logic
            self.update_language()
            self.ui_update_manager.update_ui_after_logic_change() # Пересчитываем и перерисовываем все зависимые части
            # Восстанавливаем подсветку фокуса хоткея
            if self.hotkey_cursor_index != -1:
                # print("[LANG] Scheduling focus highlight update after language switch.")
                QTimer.singleShot(50, lambda: self._update_hotkey_highlight(None))
        elif current_lang == lang:
            print(f"[LANG] Language already set to {lang}")
        else:
             print(f"[WARN] Unsupported language: {lang}")


    def update_language(self):
        """Обновляет тексты интерфейса и подсказки элементов списка."""
        print("[LANG] Updating UI language texts...")
        self.setWindowTitle(f"{get_text('title')} v{self.app_version}")

        if self.selected_heroes_label: self.update_selected_label()
        if self.author_button: self.author_button.setText(get_text('about_author'))
        if self.rating_button: self.rating_button.setText(get_text('hero_rating'))
        # Обновляем панели (они найдут свои элементы и обновят текст)
        if self.top_frame: self._update_top_panel_lang()
        if self.right_frame: self._update_right_panel_lang()
        # Обновление подсказок и текстов в QListWidget (если он существует и видим)
        if self.right_list_widget and self.right_list_widget.isVisible():
            self._update_list_widget_language()
            calculate_columns(self)
        # Обновление текста в result_label (если герои не выбраны)
        if self.result_label and not self.logic.selected_heroes:
             self.result_label.setText(get_text('no_heroes_selected', language=self.logic.DEFAULT_LANGUAGE))

    def _update_list_widget_language(self):
        """Обновляет тексты и тултипы элементов в QListWidget."""
        if not self.right_list_widget: return
        focused_hero_tooltip = None
        focused_item = None
        # Сохраняем текущую фокусную подсказку, если она есть
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
             try:
                 focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
                 if focused_item: focused_hero_tooltip = focused_item.toolTip()
             except RuntimeError: pass # Игнорируем, если виджет уже удален

        # Обновляем тексты и базовые подсказки
        for i in range(self.right_list_widget.count()):
             try:
                item = self.right_list_widget.item(i)
                if item:
                    hero_name = item.data(HERO_NAME_ROLE)
                    if hero_name:
                        # Обновляем текст элемента (имя в max, пусто в middle)
                        item_text = hero_name if self.mode == "max" else ""
                        if item.text() != item_text: item.setText(item_text) # self.mode_manager.current_mode
                        # Обновляем базовую подсказку
                        item.setToolTip(get_text(hero_name, default_text=hero_name, language=self.logic.DEFAULT_LANGUAGE))
             except RuntimeError: continue # Пропускаем, если виджет удален

        # Восстанавливаем фокусный тултип, если элемент тот же и тултип был фокусным
        current_focused_item = None
        if 0 <= self.hotkey_cursor_index < self.right_list_widget.count():
             try:
                current_focused_item = self.right_list_widget.item(self.hotkey_cursor_index)
             except RuntimeError: pass
        if focused_hero_tooltip and current_focused_item == focused_item and ">>>" in focused_hero_tooltip:
             # Восстанавливаем фокусную подсказку (>>> Имя <<<)
             hero_name = current_focused_item.data(HERO_NAME_ROLE)
             if hero_name:
                 focus_tooltip = f">>> {get_text(hero_name, default_text=hero_name, language=self.logic.DEFAULT_LANGUAGE)} <<<"
                 current_focused_item.setToolTip(focus_tooltip)


    def _update_top_panel_lang(self):
        """Обновляет язык элементов верхней панели."""
        if not self.top_frame: return
        print("[LANG] Updating top panel language...")
        try:
            # Находим элементы по имени объекта (предпочтительнее)
            lang_label = self.top_frame.findChild(QLabel, "language_label")
            mode_label = self.top_frame.findChild(QLabel, "mode_label")
            min_button = self.top_frame.findChild(QPushButton, "min_button")
            middle_button = self.top_frame.findChild(QPushButton, "middle_button")
            max_button = self.top_frame.findChild(QPushButton, "max_button")
            topmost_button = self.top_frame.findChild(QPushButton, "topmost_button")
            lang_combo = self.top_frame.findChild(QComboBox, "language_combo")
            version_label = self.top_frame.findChild(QLabel, "version_label") # Находим лейбл версии

            # Обновляем тексты найденных элементов
            if lang_label: lang_label.setText(get_text('language', language=self.logic.DEFAULT_LANGUAGE))
            if mode_label: mode_label.setText(get_text('mode', language=self.logic.DEFAULT_LANGUAGE))
            if min_button: min_button.setText(get_text('mode_min', language=self.logic.DEFAULT_LANGUAGE))
            if middle_button: middle_button.setText(get_text('mode_middle', language=self.logic.DEFAULT_LANGUAGE))
            if max_button: max_button.setText(get_text('mode_max', language=self.logic.DEFAULT_LANGUAGE))
            if topmost_button: MainWindow._update_topmost_button_visuals(topmost_button)
            if version_label: version_label.setText(f"v{self.app_version}")  # Обновляем текст версии
            if self.author_button: self.author_button.setText(get_text('about_author', language=self.logic.DEFAULT_LANGUAGE))
            if self.rating_button: self.rating_button.setText(get_text('hero_rating', language=self.logic.DEFAULT_LANGUAGE))

            # Обновление комбо-бокса языка
            if lang_combo:
                current_lang_code = self.logic.DEFAULT_LANGUAGE # Берем язык из logic
                lang_combo.blockSignals(True) # Блокируем сигналы
                # Находим индекс текущего языка по коду
                index_to_set = -1
                current_items = [lang_combo.itemText(i) for i in range(lang_combo.count())]
                expected_items = list(SUPPORTED_LANGUAGES.values())

                # Перезаполняем, если список отличается
                if current_items != expected_items:
                    lang_combo.clear()
                    lang_combo.addItems(expected_items)

                # Находим индекс для установки
                for index, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
                    if code == current_lang_code:
                        index_to_set = index
                        break
                # Устанавливаем текущий элемент по индексу
                if index_to_set != -1:
                    lang_combo.setCurrentIndex(index_to_set)
                lang_combo.blockSignals(False) # Разблокируем сигналы

        except Exception as e: print(f"[ERROR] updating top panel language: {e}")


    def _update_right_panel_lang(self):
         """Обновляет язык элементов правой панели."""
         if not self.right_frame: return
         print("[LANG] Updating right panel language...")
         try:
             # Находим кнопки по имени объекта
             copy_button = self.right_frame.findChild(QPushButton, "copy_button")
             clear_button = self.right_frame.findChild(QPushButton, "clear_button")
             # Обновляем текст кнопок
             if copy_button: copy_button.setText(get_text('copy_rating', language=self.logic.DEFAULT_LANGUAGE))
             if clear_button: clear_button.setText(get_text('clear_all', language=self.logic.DEFAULT_LANGUAGE))
             # Обновляем метку выбранных героев (она тоже на правой панели)
             self.update_selected_label()
         except Exception as e: print(f"[ERROR] updating right panel language: {e}")


# --- Глобальные функции ---
def create_gui():
    """Создает и возвращает экземпляр MainWindow."""
    return MainWindow()
