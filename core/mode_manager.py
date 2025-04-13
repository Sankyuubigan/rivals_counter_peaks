# File: mode_manager.py
from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QComboBox, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from right_panel import create_right_panel
from left_panel import create_left_panel
from images_load import get_images_for_mode, SIZES
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes
from translations import get_text
from build import version
import time # <<< Для измерения времени >>>

PANEL_MIN_WIDTHS = {
    'max':    {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300},
    'min':    {'left': 0,   'right': 0}
}
MODE_DEFAULT_WINDOW_SIZES = {
    'max':    {'width': 1100, 'height': 800},
    'middle': {'width': 950,  'height': 600},
    'min':    {'width': 600,  'height': 0}
}

def change_mode(window, mode):
    """Инициирует смену режима отображения."""
    print(f"--- Попытка смены режима на: {mode} ---")
    start_time = time.time() # <<< Время начала смены режима >>>
    if window.mode == mode: print("Режим уже установлен."); return
    if window.mode in window.mode_positions and window.isVisible(): window.mode_positions[window.mode] = window.pos()
    window.mode = mode
    update_interface_for_mode(window)
    end_time = time.time() # <<< Время конца смены режима >>>
    print(f"--- Смена режима на {mode} ЗАВЕРШЕНА (заняло: {end_time - start_time:.4f} сек) ---")

def update_interface_for_mode(window):
    """Перестраивает интерфейс для нового режима."""
    t0 = time.time() # Начало всей функции
    print(f"[TIMING] update_interface_for_mode: Start for mode '{window.mode}'")

    # Очистка inner_layout
    t1 = time.time()
    if window.inner_layout:
        while window.inner_layout.count(): item = window.inner_layout.takeAt(0); widget = item.widget();
        if widget: widget.deleteLater()
    else:
        if window.main_widget: window.inner_layout = QHBoxLayout(window.main_widget); window.inner_layout.setContentsMargins(0,0,0,0); window.inner_layout.setSpacing(0)
        else: print("[!] Ошибка: main_widget не найден."); return
    t2 = time.time(); print(f"[TIMING] -> Clear inner_layout: {t2-t1:.4f} s")

    # Сброс ссылок
    window.left_container=None; window.canvas=None; window.result_frame=None; window.result_label=None
    window.right_frame=None; window.selected_heroes_label=None; window.right_list_widget=None; window.hero_items.clear()

    # Загрузка ресурсов
    t1 = time.time()
    try:
        window.right_images, window.left_images, window.small_images, window.horizontal_images = get_images_for_mode(window.mode)
    except Exception as e: print(f"Критическая ошибка загрузки изображений: {e}"); return
    t2 = time.time(); print(f"[TIMING] -> Load images: {t2-t1:.4f} s")

    # Пересоздание левой панели
    t1 = time.time()
    window.left_container = QWidget(); left_layout = QVBoxLayout(window.left_container); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(0)
    window.canvas, window.result_frame, window.result_label, window.update_scrollregion = create_left_panel(window.left_container)
    left_layout.addWidget(window.canvas, stretch=1); window.left_container.setMinimumWidth(PANEL_MIN_WIDTHS.get(window.mode, {}).get('left', 0))
    window.inner_layout.addWidget(window.left_container, stretch=1)
    t2 = time.time(); print(f"[TIMING] -> Create left panel: {t2-t1:.4f} s")

    # Пересоздание/Скрытие правой панели
    t1 = time.time()
    if window.mode != "min":
        window.right_frame, window.selected_heroes_label = create_right_panel(window, window.mode)
        window.right_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(window.mode, {}).get('right', 0))
        window.inner_layout.addWidget(window.right_frame, stretch=1)
        window.inner_layout.setStretch(0, 2)
    else:
        window.right_frame = None
    t2 = time.time(); print(f"[TIMING] -> Create/Hide right panel: {t2-t1:.4f} s")

    # Настройка видимости и размеров ОКНА/ПАНЕЛЕЙ
    t1 = time.time()
    top_h = window.top_frame.sizeHint().height() if window.top_frame else 40
    h_icon_h = SIZES[window.mode]['horizontal'][1] if window.mode in SIZES and 'horizontal' in SIZES[window.mode] else 30
    icons_h = h_icon_h + 12
    window.icons_scroll_area.setFixedHeight(icons_h)

    spacing = window.main_layout.spacing() if window.main_layout.spacing() >= 0 else 0
    base_h = top_h + icons_h + spacing

    window.setMinimumHeight(0); window.setMaximumHeight(16777215)

    lang_label = window.top_frame.findChild(QLabel, "language_label")
    lang_combo = window.top_frame.findChild(QComboBox, "language_combo")
    version_label = window.top_frame.findChild(QLabel, "version_label")
    close_button = window.top_frame.findChild(QPushButton, "close_button")

    is_min_mode = (window.mode == "min")
    current_flags = window.windowFlags()

    # --- Управление видимостью и Frameless ---
    set_frameless = False
    if is_min_mode:
        if not (current_flags & Qt.WindowType.FramelessWindowHint): set_frameless = True; target_flags = current_flags | Qt.WindowType.FramelessWindowHint
        if lang_label: lang_label.hide();
        if lang_combo: lang_combo.hide();
        if version_label: version_label.hide();
        if window.author_button: window.author_button.hide();
        if window.rating_button: window.rating_button.hide();
        if close_button: close_button.show()
        window.setWindowTitle("")
        calculated_fixed_min_height = base_h + 5
        window.setMinimumHeight(calculated_fixed_min_height); window.setMaximumHeight(calculated_fixed_min_height)
        # Скрываем главный виджет с панелями
        if window.main_widget: window.main_widget.hide()
    else: # middle и max
        if current_flags & Qt.WindowType.FramelessWindowHint: set_frameless = True; target_flags = current_flags & ~Qt.WindowType.FramelessWindowHint
        if lang_label: lang_label.show();
        if lang_combo: lang_combo.show();
        if version_label: version_label.show();
        if close_button: close_button.hide()
        window.setWindowTitle(f"{get_text('title')} v{version}")
        # Показываем главный виджет и панели
        if window.main_widget: window.main_widget.show()
        if window.left_container: window.left_container.show()
        if window.right_frame: window.right_frame.show()
        # Настройка высоты и кнопок author/rating
        if window.mode == "max":
            calculated_min_h = base_h + 300; window.setMinimumHeight(calculated_min_h)
            if window.author_button: window.author_button.show();
            if window.rating_button: window.rating_button.show();
        else: # middle
            calculated_min_h = base_h + 200; window.setMinimumHeight(calculated_min_h)
            if window.author_button: window.author_button.hide();
            if window.rating_button: window.rating_button.hide();

    # Применяем флаг frameless только если он изменился
    if set_frameless:
        window.setWindowFlags(target_flags)
        window.show() # Обязательно после смены флагов
    t2 = time.time(); print(f"[TIMING] -> Setup visibility/frameless: {t2-t1:.4f} s")

    # Финальное обновление Layout'ов и Геометрии
    t1 = time.time()
    window.update_language() # Обновит тексты
    # Убираем activate(), они не должны быть нужны
    # if window.left_container and window.left_container.isVisible() and window.left_container.layout(): window.left_container.layout().activate()
    # if window.right_frame and window.right_frame.isVisible() and window.right_frame.layout(): window.right_frame.layout().activate()
    # if window.inner_layout: window.inner_layout.activate()
    # if window.main_layout: window.main_layout.activate()
    window.updateGeometry() # Достаточно для обновления геометрии
    t2 = time.time(); print(f"[TIMING] -> Update language/geometry: {t2-t1:.4f} s")

    # Установка РАЗМЕРА ОКНА из словаря
    t1 = time.time()
    target_size = MODE_DEFAULT_WINDOW_SIZES.get(window.mode, {'width': 800, 'height': 600})
    target_w = target_size['width']; target_h = target_size['height']
    if window.mode == 'min':
        final_h = window.minimumHeight()
        window.resize(target_w, final_h)
    else:
        min_w = window.minimumSizeHint().width(); actual_min_h = window.minimumHeight()
        final_w = max(target_w, min_w); final_h = max(target_h, actual_min_h)
        window.resize(final_w, final_h)
    t2 = time.time(); print(f"[TIMING] -> Resize window: {t2-t1:.4f} s")

    # Восстанавливаем состояние UI
    t1 = time.time()
    window.restore_hero_selections() # Это вызывает update_ui_after_logic_change -> update_counterpick_display и т.д.
    t2 = time.time(); print(f"[TIMING] -> Restore selections (triggers UI update): {t2-t1:.4f} s")

    # Перемещаем окно
    if window.isVisible():
        target_pos = window.mode_positions.get(window.mode)
        if target_pos: window.move(target_pos)

    t_end = time.time()
    print(f"[TIMING] update_interface_for_mode: Finished (Total: {t_end - t0:.4f} s)")