# File: core/mode_manager.py
import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QScrollArea)
from PySide6.QtCore import Qt

# Импорты из проекта
from left_panel import LeftPanel # Используем класс LeftPanel
from right_panel import RightPanel # Используем класс RightPanel
from images_load import get_images_for_mode, SIZES
from translations import get_text

# --- Константы ---
PANEL_MIN_WIDTHS = {
    'max': {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300},
    'min': {'left': 0, 'right': 0} # Левая панель не имеет мин. ширины, правая скрыта
}
MODE_DEFAULT_WINDOW_SIZES = {
    'max': {'width': 1100, 'height': 800},
    'middle': {'width': 950, 'height': 600},
    'min': {'width': 600, 'height': 0} # Высота будет рассчитана
}
# --- ---

class ModeManager:
    """Управляет текущим режимом окна и его позициями."""
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_mode = "middle" # Начальный режим
        # Словарь для хранения позиций окна для каждого режима
        self.mode_positions = {
            "min": None,
            "middle": main_window.pos() if main_window.isVisible() else None, # Сохраняем начальную позицию для middle
            "max": None
        }

    def change_mode(self, new_mode_name: str):
        """Устанавливает новый режим и сохраняет позицию старого."""
        if new_mode_name not in self.mode_positions:
            print(f"[ERROR] Попытка установить неизвестный режим: {new_mode_name}")
            return

        if self.current_mode == new_mode_name:
            print(f"Режим уже установлен: {new_mode_name}")
            return

        print(f"[MODE] Сохранение позиции для режима '{self.current_mode}'...")
        # Сохраняем текущую позицию окна для старого режима
        if self.main_window.isVisible():
             current_pos = self.main_window.pos()
             self.mode_positions[self.current_mode] = current_pos
             print(f"[MODE] Позиция для '{self.current_mode}' сохранена: {current_pos}")

        print(f"[MODE] Установка нового режима: {new_mode_name}")
        self.current_mode = new_mode_name
        # Обновляем атрибут mode в главном окне
        self.main_window.mode = new_mode_name
        # Позиция для нового режима будет восстановлена в update_interface_for_mode

    def clear_layout_recursive(self, layout):
        """Рекурсивно очищает layout от виджетов и вложенных layout'ов."""
        if layout is None: return
        while layout.count():
            item = layout.takeAt(0)
            if item is None: continue
            widget = item.widget()
            if widget is not None:
                # print(f"  Deleting widget: {widget.objectName()} ({type(widget).__name__})")
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    # print(f"  Clearing sub-layout: {sub_layout.objectName()} ({type(sub_layout).__name__})")
                    self.clear_layout_recursive(sub_layout)
                    layout.removeItem(item) # Удаляем QLayoutItem, содержащий sub_layout
                else:
                    spacer = item.spacerItem()
                    if spacer is not None:
                        # print("  Removing spacer item")
                        layout.removeItem(item) # Удаляем QSpacerItem


def change_mode(window, mode_name):
    """Инициирует смену режима отображения."""
    print(f"--- Попытка смены режима на: {mode_name} ---")
    # Проверяем, нужно ли вообще менять режим
    if window.mode == mode_name:
         print(f"Режим '{mode_name}' уже установлен.")
         return

    # --- Подготовка к смене режима ---
    start_time = time.time()
    # 1. Сохраняем позицию текущего окна
    if window.mode in window.mode_positions and window.isVisible():
        window.mode_positions[window.mode] = window.pos()
        print(f"Позиция для режима '{window.mode}' сохранена: {window.mode_positions[window.mode]}")

    # 2. Сбрасываем фокус хоткея перед перестройкой UI
    old_cursor_index = window.hotkey_cursor_index
    window.hotkey_cursor_index = -1
    # Проверяем наличие list_widget перед вызовом _update_hotkey_highlight
    if window.right_list_widget and window.right_list_widget.isVisible() and old_cursor_index >= 0:
        window._update_hotkey_highlight(old_cursor_index) # Снимаем подсветку

    # 3. Устанавливаем новый режим в менеджере и в окне
    window.mode_manager.change_mode(mode_name) # Обновляем режим в менеджере (и в window.mode)

    # --- Перестройка интерфейса ---
    update_interface_for_mode(window)

    # --- Завершение смены режима ---
    # 4. Восстанавливаем позицию окна для нового режима
    target_pos = window.mode_positions.get(window.mode)
    if target_pos and window.isVisible():
        print(f"Восстановление позиции для режима '{window.mode}': {target_pos}")
        window.move(target_pos)

    # 5. Восстанавливаем фокус хоткея после небольшой задержки
    QTimer.singleShot(150, window._reset_hotkey_cursor_after_mode_change)

    end_time = time.time()
    print(f"--- Смена режима на {mode_name} ЗАВЕРШЕНА (заняло: {end_time - start_time:.4f} сек) ---")


def update_interface_for_mode(window):
    """Перестраивает интерфейс для текущего режима (`window.mode`)."""
    t0 = time.time()
    current_mode = window.mode # Используем режим из window
    print(f"[TIMING] update_interface_for_mode: Start for mode '{current_mode}'")

    # --- 1. Очистка основного layout'а (inner_layout) ---
    t1 = time.time()
    if window.inner_layout:
        # print("Clearing inner_layout...")
        window.mode_manager.clear_layout_recursive(window.inner_layout)
    else:
        # Если inner_layout не существует, создаем его (это не должно происходить после init_ui)
        if window.main_widget:
             window.inner_layout = QHBoxLayout(window.main_widget)
             window.inner_layout.setObjectName("inner_layout")
             window.inner_layout.setContentsMargins(0,0,0,0); window.inner_layout.setSpacing(0)
        else: print("[!] КРИТИЧЕСКАЯ ОШИБКА: main_widget не найден."); return
    t2 = time.time(); # print(f"[TIMING] -> Clear inner_layout: {t2-t1:.4f} s")

    # --- 2. Сброс ссылок на виджеты панелей ---
    # Сбрасываем экземпляры панелей
    window.left_panel_instance = None
    window.right_panel_instance = None
    # Сбрасываем прямые ссылки на виджеты внутри панелей
    window.canvas = None; window.result_frame = None; window.result_label = None
    window.right_frame = None; window.selected_heroes_label = None; window.right_list_widget = None
    window.hero_items.clear()

    # --- 3. Загрузка/Получение изображений ---
    t1 = time.time()
    try:
        # print(f"Getting images for mode: {current_mode}")
        window.right_images, window.left_images, window.small_images, window.horizontal_images = get_images_for_mode(current_mode)
    except Exception as e: print(f"Критическая ошибка загрузки изображений для режима {current_mode}: {e}"); return
    t2 = time.time(); # print(f"[TIMING] -> Load/Get images: {t2-t1:.4f} s")

    # --- 4. Пересоздание левой панели ---
    t1 = time.time()
    # print("Creating left panel...")
    window.left_panel_instance = LeftPanel(window.main_widget) # Родитель - main_widget
    window.canvas, window.result_frame, window.result_label, window.update_scrollregion = window.left_panel_instance.get_widgets()
    # Устанавливаем минимальную ширину контейнера (QFrame) левой панели
    window.left_panel_instance.left_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('left', 0))
    # Добавляем контейнер левой панели в inner_layout
    window.inner_layout.addWidget(window.left_panel_instance.left_frame, stretch=1)
    t2 = time.time(); # print(f"[TIMING] -> Create left panel: {t2-t1:.4f} s")

    # --- 5. Пересоздание/Скрытие правой панели ---
    t1 = time.time()
    if current_mode != "min":
        # print("Creating right panel...")
        window.right_panel_instance = RightPanel(window, current_mode)
        # Получаем ссылки на виджеты из созданного экземпляра
        window.right_frame = window.right_panel_instance.frame
        window.selected_heroes_label = window.right_panel_instance.selected_heroes_label
        window.right_list_widget = window.right_panel_instance.list_widget
        window.hero_items = window.right_panel_instance.hero_items # Обновляем словарь ссылок
        # Устанавливаем минимальную ширину
        window.right_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(current_mode, {}).get('right', 0))
        # Добавляем QFrame правой панели в inner_layout
        window.inner_layout.addWidget(window.right_frame, stretch=1)
        # Устанавливаем растяжение панелей
        window.inner_layout.setStretch(0, 2) # Левая (индекс 0)
        window.inner_layout.setStretch(1, 1) # Правая (индекс 1)
    else:
        # print("Skipping right panel creation (min mode).")
        pass # Ссылки уже сброшены в None
    t2 = time.time(); # print(f"[TIMING] -> Create/Hide right panel: {t2-t1:.4f} s")

    # --- 6. Настройка окна и TopPanel ---
    t1 = time.time()
    # print("Configuring window and top panel...")
    # Расчет базовой высоты
    top_h = window.top_frame.sizeHint().height() if window.top_frame else 40
    # Проверяем наличие SIZES[current_mode] и 'horizontal' ключа
    horiz_size = SIZES.get(current_mode, {}).get('horizontal')
    h_icon_h = horiz_size[1] if horiz_size else 30 # Высота иконки из SIZES или 30 по умолчанию
    icons_h = h_icon_h + 12
    window.icons_scroll_area.setFixedHeight(icons_h)

    spacing = window.main_layout.spacing() if window.main_layout else 0
    base_h = top_h + icons_h + spacing

    # Сброс ограничений высоты
    window.setMinimumHeight(0); window.setMaximumHeight(16777215)

    is_min_mode = (current_mode == "min")
    current_flags = window.windowFlags()
    frameless_changed = False

    # Находим элементы в TopPanel
    lang_label = window.top_frame.findChild(QLabel, "language_label")
    lang_combo = window.top_frame.findChild(QComboBox, "language_combo")
    version_label = window.top_frame.findChild(QLabel, "version_label")
    close_button = window.top_frame.findChild(QPushButton, "close_button")

    if is_min_mode:
        # print("Setting up MIN mode UI...")
        if not (current_flags & Qt.WindowType.FramelessWindowHint):
            window.setWindowFlags(current_flags | Qt.WindowType.FramelessWindowHint)
            frameless_changed = True
        if lang_label: lang_label.hide()
        if lang_combo: lang_combo.hide()
        if version_label: version_label.hide()
        if window.author_button: window.author_button.hide()
        if window.rating_button: window.rating_button.hide()
        if close_button: close_button.show()
        window.setWindowTitle("")
        calculated_fixed_min_height = base_h + 5
        window.setMinimumHeight(calculated_fixed_min_height)
        window.setMaximumHeight(calculated_fixed_min_height)
        # Панели уже добавлены/не добавлены выше
    else:
        # print(f"Setting up {current_mode.upper()} mode UI...")
        if current_flags & Qt.WindowType.FramelessWindowHint:
            window.setWindowFlags(current_flags & ~Qt.WindowType.FramelessWindowHint)
            frameless_changed = True
        if lang_label: lang_label.show()
        if lang_combo: lang_combo.show()
        if version_label: version_label.show()
        if close_button: close_button.hide()
        window.setWindowTitle(f"{get_text('title', language=window.logic.DEFAULT_LANGUAGE)} v{window.app_version}")
        # Настройка минимальной высоты и кнопок автора/рейтинга
        if current_mode == "max":
            calculated_min_h = base_h + 300
            window.setMinimumHeight(calculated_min_h)
            if window.author_button: window.author_button.show()
            if window.rating_button: window.rating_button.show()
        else: # middle
            calculated_min_h = base_h + 200
            window.setMinimumHeight(calculated_min_h)
            if window.author_button: window.author_button.hide()
            if window.rating_button: window.rating_button.hide()

    # Применяем frameless/рамку
    if frameless_changed:
        print("[LOG] Frameless flag changed, calling window.show()")
        window.show()
    t2 = time.time(); # print(f"[TIMING] -> Setup window flags/visibility: {t2-t1:.4f} s")

    # --- 7. Обновление языка и геометрии ---
    t1 = time.time()
    # print("Updating language and geometry...")
    window.update_language() # Обновит тексты
    # Активируем layout'ы
    window.main_layout.activate()
    if window.inner_layout: window.inner_layout.activate() # Проверяем на None
    window.updateGeometry() # Пересчитываем геометрию
    t2 = time.time(); # print(f"[TIMING] -> Update language/layout/geometry: {t2-t1:.4f} s")

    # --- 8. Установка размера окна ---
    t1 = time.time()
    target_size = MODE_DEFAULT_WINDOW_SIZES.get(current_mode, {'width': 800, 'height': 600})
    target_w = target_size['width']; target_h = target_size['height']
    min_w = window.minimumSizeHint().width(); actual_min_h = window.minimumHeight()

    if current_mode == 'min':
        final_w = max(target_w, min_w)
        final_h = window.minimumHeight()
        window.resize(final_w, final_h)
    else:
        final_w = max(target_w, min_w)
        final_h = max(target_h, actual_min_h)
        window.resize(final_w, final_h)
    t2 = time.time(); # print(f"[TIMING] -> Resize window: {t2-t1:.4f} s")

    # --- 9. Восстановление состояния UI ---
    t1 = time.time()
    # print("Restoring UI state...")
    window.update_ui_after_logic_change()
    t2 = time.time(); # print(f"[TIMING] -> Restore UI state: {t2-t1:.4f} s")

    t_end = time.time()
    print(f"[TIMING] update_interface_for_mode: Finished (Total: {t_end - t0:.4f} s)")