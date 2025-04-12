# File: mode_manager.py
from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget
from PySide6.QtCore import Qt, QSize
from right_panel import create_right_panel
from left_panel import create_left_panel
from images_load import get_images_for_mode, TOP_HORIZONTAL_ICON_SIZE
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes

# --- МИНИМАЛЬНАЯ ШИРИНА ПАНЕЛЕЙ ДЛЯ РАЗНЫХ РЕЖИМОВ ---
# Здесь вы регулируете МИНИМАЛЬНУЮ ширину левой и правой части
PANEL_MIN_WIDTHS = {
    'max':    {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300},
    'min':    {'left': 0,   'right': 0}  # В min режиме правая панель не создается
}
# ----------------------------------------------------

# --- ПРЕДПОЧТИТЕЛЬНЫЕ РАЗМЕРЫ ОКНА ДЛЯ КАЖДОГО РЕЖИМА ---
# Здесь вы можете задать ЖЕЛАЕМЫЕ ширину и высоту окна при переключении на режим.
# Пользователь сможет изменить размер окна после переключения (кроме высоты в 'min').
# ВНИМАНИЕ: Значение 'height' для 'min' будет ИГНОРИРОВАТЬСЯ,
#           т.к. высота в этом режиме рассчитывается автоматически.
MODE_DEFAULT_WINDOW_SIZES = {
    'max':    {'width': 1100, 'height': 800},
    'middle': {'width': 950,  'height': 600},
    'min':    {'width': 600,  'height': 0} # Укажите желаемую ширину для min режима
}
# -------------------------------------------------------


def change_mode(window, mode):
    """Инициирует смену режима отображения."""
    print(f"--- Попытка смены режима на: {mode} ---")
    if window.mode == mode:
        print("Режим уже установлен.")
        return

    if window.mode in window.mode_positions and window.isVisible():
        window.mode_positions[window.mode] = window.pos()

    window.mode = mode
    update_interface_for_mode(window)

def update_interface_for_mode(window):
    """Перестраивает интерфейс для нового режима."""
    print(f"--- Начало перестроения UI для режима: {window.mode} ---")

    # --- Очистка только left/right панелей внутри main_widget ---
    # print("Очистка старого UI (left/right)...")
    if window.inner_layout:
        while window.inner_layout.count():
            item = window.inner_layout.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()
    else:
        if window.main_widget: window.inner_layout = QHBoxLayout(window.main_widget); window.inner_layout.setContentsMargins(0,0,0,0); window.inner_layout.setSpacing(0)
        else: print("[!] Ошибка: main_widget не найден."); return

    # Сброс ссылок
    window.left_container=None; window.canvas=None; window.result_frame=None; window.result_label=None
    window.right_frame=None; window.selected_heroes_label=None; window.right_list_widget=None; window.hero_items.clear()

    # --- Загрузка ресурсов ---
    try:
        # print(f"Загрузка изображений для режима: {window.mode}")
        window.right_images, window.left_images, window.small_images, window.horizontal_images = get_images_for_mode(window.mode)
    except Exception as e: print(f"Критическая ошибка загрузки изображений: {e}"); return

    # --- Пересоздание левой панели ---
    window.left_container = QWidget()
    left_layout = QVBoxLayout(window.left_container); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(0)
    window.canvas, window.result_frame, window.result_label, window.update_scrollregion = create_left_panel(window.left_container)
    left_layout.addWidget(window.canvas, stretch=1)
    window.left_container.setMinimumWidth(PANEL_MIN_WIDTHS[window.mode]['left']) # <--- Установка мин. ширины ЛЕВОЙ панели
    # print("Левая панель пересоздана.")

    # --- Пересоздание/Скрытие правой панели ---
    if window.mode != "min":
        window.right_frame, window.selected_heroes_label = create_right_panel(window, window.mode)
        window.right_frame.setMinimumWidth(PANEL_MIN_WIDTHS[window.mode]['right']) # <--- Установка мин. ширины ПРАВОЙ панели
        # print(f"Правая панель пересоздана для режима {window.mode}.")
    else:
        window.right_frame = None
        # print("Правая панель не создается (режим min).")

    # --- Сборка UI (добавление панелей в inner_layout) ---
    window.inner_layout.addWidget(window.left_container, stretch=2 if window.mode != 'min' else 1)
    if window.right_frame:
        window.inner_layout.addWidget(window.right_frame, stretch=1)
        window.right_frame.setVisible(True)
        window.left_container.setVisible(True)
        window.main_widget.setVisible(True)
    elif window.mode == 'min':
         window.left_container.setVisible(True) # Левая панель видима в min режиме (для minimal_icon_list)
         window.main_widget.setVisible(True)

    # --- Настройка видимости и размеров ОКНА/ПАНЕЛЕЙ ---
    # print(f"Настройка видимости и размеров для режима '{window.mode}'...")
    top_h = window.top_frame.sizeHint().height() if window.top_frame else 40
    icons_h = TOP_HORIZONTAL_ICON_SIZE.height() + window.icons_layout.contentsMargins().top() + window.icons_layout.contentsMargins().bottom() + 4
    window.icons_frame.setFixedHeight(icons_h)

    spacing = window.main_layout.spacing() if window.main_layout.spacing() >= 0 else 0
    base_h = top_h + icons_h + spacing

    # Сбрасываем ограничения по высоте
    window.setMinimumHeight(0)
    window.setMaximumHeight(16777215)

    calculated_fixed_min_height = 0 # Для хранения расчетной высоты min режима

    if window.mode == "max":
        window.main_widget.show()
        calculated_fixed_min_height = base_h + 300 # Минимальная высота для контента
        window.setMinimumHeight(calculated_fixed_min_height)
        if window.author_button: window.author_button.setVisible(True)
        if window.rating_button: window.rating_button.setVisible(True)
    elif window.mode == "middle":
        window.main_widget.show()
        calculated_fixed_min_height = base_h + 200 # Минимальная высота для контента
        window.setMinimumHeight(calculated_fixed_min_height)
        if window.author_button: window.author_button.setVisible(False)
        if window.rating_button: window.rating_button.setVisible(False)
    elif window.mode == "min":
        window.main_widget.hide() # Скрываем left/right панели
        calculated_fixed_min_height = base_h + 5 # Фиксированная высота = top + icons + запас
        window.setMinimumHeight(calculated_fixed_min_height)
        window.setMaximumHeight(calculated_fixed_min_height) # ФИКСИРУЕМ высоту
        print(f"Установлена ФИКСИРОВАННАЯ высота для min режима: {calculated_fixed_min_height}")
        if window.author_button: window.author_button.setVisible(False)
        if window.rating_button: window.rating_button.setVisible(False)

    # --- Финальное обновление Layout'ов и Геометрии (ПЕРЕД RESIZE) ---
    window.update_language()
    window.left_container.layout().activate()
    if window.right_frame: window.right_frame.layout().activate()
    window.inner_layout.activate()
    window.main_layout.activate()
    window.updateGeometry() # Важно обновить геометрию перед resize

    # --- Установка РАЗМЕРА ОКНА из словаря ---
    target_size = MODE_DEFAULT_WINDOW_SIZES.get(window.mode, {'width': 800, 'height': 600}) # Размер по умолчанию, если режим не найден
    target_w = target_size['width']
    target_h = target_size['height']

    if window.mode == 'min':
        # Для min режима используем РАССЧИТАННУЮ высоту и ширину из словаря
        print(f"Установка размера окна для 'min': {target_w}x{calculated_fixed_min_height}")
        window.resize(target_w, calculated_fixed_min_height)
    else:
        # Для других режимов используем ширину и высоту из словаря
        # Убедимся, что размер не меньше минимально допустимого
        min_w = window.minimumSizeHint().width() # Минимально возможная ширина
        actual_min_h = window.minimumHeight()    # Рассчитанная минимальная высота
        final_w = max(target_w, min_w)
        final_h = max(target_h, actual_min_h)
        print(f"Установка размера окна для '{window.mode}': {final_w}x{final_h} (Target: {target_w}x{target_h}, Min: {min_w}x{actual_min_h})")
        window.resize(final_w, final_h)
    # ----------------------------------------------

    # Восстанавливаем состояние UI
    window.restore_hero_selections()

    # Перемещаем окно
    if window.isVisible():
        target_pos = window.mode_positions.get(window.mode)
        if target_pos: window.move(target_pos)

    print(f"--- Перестроение UI для режима '{window.mode}' завершено ---")