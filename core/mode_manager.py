from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox, QPushButton)
from PySide6.QtCore import Qt
import time
import gc

from left_panel import create_left_panel
from right_panel import create_right_panel
from images_load import get_images_for_mode, SIZES
from translations import get_text
from .mode import Mode


PANEL_MIN_WIDTHS = {
    'max': {'left': 600, 'right': 480},
    'middle': {'left': 400, 'right': 300},
    'min': {'left': 0, 'right': 0}  # Левая панель видима, но мин. ширина не важна
}
MODE_DEFAULT_WINDOW_SIZES = {
    'max': {'width': 1100, 'height': 800}, 'middle': {'width': 950, 'height': 600},'min': {'width': 600, 'height': 0} # Высота будет переопределена в update_interface_for_mode
}

def update_interface_for_mode(window):
    """Перестраивает интерфейс для нового режима."""
    t0 = time.time()
    print(f"[TIMING] update_interface_for_mode: Start for mode '{window.mode_manager.current_mode}'")

    # --- 1. Очистка основного layout'а (inner_layout) ---
    t1 = time.time()
    if window.inner_layout:
        # print("Clearing inner_layout...")
        window.mode_manager.clear_layout_recursive(window.inner_layout)
    else: # Если inner_layout еще не создан
        if window.main_widget:
            window.inner_layout = QHBoxLayout(window.main_widget)
            window.inner_layout.setObjectName("inner_layout")
            window.inner_layout.setContentsMargins(0,0,0,0); window.inner_layout.setSpacing(0)
        else:
            print("[!] КРИТИЧЕСКАЯ ОШИБКА: main_widget не найден в update_interface_for_mode."); return
    t2 = time.time(); # print(f"[TIMING] -> Clear inner_layout: {t2-t1:.4f} s")

    # --- 2. Сброс ссылок на пересоздаваемые виджеты ---
    # print("Resetting widget references...")
    window.left_container=None; window.canvas=None; window.result_frame=None; window.result_label=None
    window.right_frame=None; window.selected_heroes_label=None; window.right_list_widget=None;
    window.hero_items.clear() # Очищаем словарь ссылок на элементы списка

    # --- 3. Загрузка/Получение изображений для нового режима ---
    t1 = time.time()
    try:
        # Функция get_images_for_mode использует кэш
        # print(f"Getting images for mode: {window.mode_manager.current_mode}")
        window.right_images, window.left_images, window.small_images, window.horizontal_images = get_images_for_mode(
            window.mode_manager.current_mode)
    except Exception as e: print(f"Критическая ошибка загрузки изображений для режима {window.mode_manager.current_mode}: {e}"); return
    t2 = time.time();  # print(f"[TIMING] -> Load/Get images: {t2-t1:.4f} s")

    # --- 4. Пересоздание левой панели (всегда видима) ---
    t1 = time.time()
    # print("Creating left panel...")
    window.left_container = QWidget(); window.left_container.setObjectName("left_container_widget")
    left_layout = QVBoxLayout(window.left_container); left_layout.setObjectName("left_container_layout")
    left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(0)
    # Создаем ScrollArea, ResultFrame и ResultLabel внутри контейнера
    window.canvas, window.result_frame, window.result_label, window.update_scrollregion = create_left_panel(window.left_container)
    left_layout.addWidget(window.canvas, stretch=1) # ScrollArea занимает все место
    # Устанавливаем минимальную ширину левой панели # window.mode
    window.left_container.setMinimumWidth(PANEL_MIN_WIDTHS.get(window.mode_manager.current_mode, {}).get('left', 0))
    # Добавляем левую панель в основной layout (inner_layout)
    window.inner_layout.addWidget(window.left_container, stretch=1) # Начальный stretch=1
    t2 = time.time();  # print(f"[TIMING] -> Create left panel: {t2-t1:.4f} s")

    # --- 5. Пересоздание/Скрытие правой панели ---
    t1 = time.time()
    if window.mode_manager.current_mode != "min":
        # print("Creating right panel...")
        window.right_frame, window.selected_heroes_label = create_right_panel(window, window.mode_manager.current_mode)
        window.right_frame.setMinimumWidth(PANEL_MIN_WIDTHS.get(window.mode_manager.current_mode, {}).get('right', 0))
        window.inner_layout.addWidget(window.right_frame, stretch=1) # Добавляем правую панель


        # Устанавливаем растяжение: левая панель в 2 раза шире правой
        window.inner_layout.setStretch(0, 2) # Индекс 0 - левая панель
        window.inner_layout.setStretch(1, 1) # Индекс 1 - правая панель
    else:
        # print("Skipping right panel creation (min mode).")
        window.right_frame = None; window.selected_heroes_label = None; window.right_list_widget = None
    t2 = time.time(); # print(f"[TIMING] -> Create/Hide right panel: {t2-t1:.4f} s")
    window.mode = window.mode_manager.current_mode
    # --- 6. Настройка окна (Frameless, Title, Min/Max Height) и видимости элементов TopPanel ---
    t1 = time.time()
    # print("Configuring window and top panel...")
    # Рассчитываем базовую высоту (TopPanel + IconsPanel)
    top_h = window.top_frame.sizeHint().height() if window.top_frame else 40
    h_icon_h = SIZES[window.mode_manager.current_mode]['horizontal'][1] if window.mode_manager.current_mode in SIZES and 'horizontal' in SIZES[window.mode_manager.current_mode] else 30
    icons_h = h_icon_h + 12 # Добавляем отступы
    window.icons_scroll_area.setFixedHeight(icons_h) # Устанавливаем высоту панели иконок

    spacing = window.main_layout.spacing() if window.main_layout and window.main_layout.spacing() >= 0 else 0
    base_h = top_h + icons_h + spacing # Складываем все высоты
    # Сбрасываем ограничения высоты перед расчетом новых
    window.setMinimumHeight(0); window.setMaximumHeight(16777215)

    # Находим элементы в top_frame для скрытия/показа (используем findChild)
    lang_label = window.top_frame.findChild(QLabel, "language_label")
    lang_combo = window.top_frame.findChild(QComboBox, "language_combo")
    version_label = window.top_frame.findChild(QLabel, "version_label")
    close_button = window.top_frame.findChild(QPushButton, "close_button")


    is_min_mode = (window.mode_manager.current_mode == "min")
    current_flags = window.windowFlags()
    frameless_changed = False # Флаг для отслеживания изменения frameless

    if is_min_mode:
        # print("Setting up MIN mode...")
        # Устанавливаем Frameless, если еще не установлен
        if not (current_flags & Qt.WindowType.FramelessWindowHint):
            window.setWindowFlags(current_flags | Qt.WindowType.FramelessWindowHint)
            frameless_changed = True
        # Скрываем ненужные элементы в TopPanel
        if lang_label: lang_label.hide()
        if lang_combo: lang_combo.hide()
        if version_label: version_label.hide()
        if window.author_button: window.author_button.hide()
        if window.rating_button: window.rating_button.hide()
        if close_button: close_button.show() # Показываем кнопку закрытия
        window.setWindowTitle("") # Убираем заголовок
        # Рассчитываем и устанавливаем ФИКСИРОВАННУЮ высоту
        calculated_fixed_min_height = base_h + 5 # Небольшой запас
        window.setMinimumHeight(calculated_fixed_min_height)
        window.setMaximumHeight(calculated_fixed_min_height)
        # print(f"Fixed height set for min mode: {calculated_fixed_min_height}")
        # Управляем видимостью основных панелей
        if window.main_widget: window.main_widget.show()
        if window.left_container: window.left_container.show() # Левая панель видима
        # Правая панель уже удалена

    else: # Режимы middle и max
        # print(f"Setting up {window.mode.upper()} mode...")
        # Убираем Frameless, если он был установлен
        if current_flags & Qt.WindowType.FramelessWindowHint:
            window.setWindowFlags(current_flags & ~Qt.WindowType.FramelessWindowHint)
            frameless_changed = True
        # Показываем нужные элементы в TopPanel
        if lang_label: lang_label.show()
        if lang_combo: lang_combo.show()
        if version_label: version_label.show()
        if close_button: close_button.hide() # Скрываем кнопку закрытия
        window.setWindowTitle(f"{get_text('title')} v{window.app_version}") # Восстанавливаем заголовок
        # Показываем основные панели
        if window.left_container: window.left_container.show()
        if window.right_frame: window.right_frame.show() # Правая панель видима
        # Устанавливаем минимальную высоту и видимость кнопок автора/рейтинга
        if window.mode_manager.current_mode == "max":
            calculated_min_h = base_h + 300  # Примерная минимальная высота для контента

            window.setMinimumHeight(calculated_min_h)
            if window.author_button: window.author_button.show()
            if window.rating_button: window.rating_button.show()
        else: # middle
            calculated_min_h = base_h + 200 # Примерная минимальная высота для контента
            window.setMinimumHeight(calculated_min_h)
            if window.author_button: window.author_button.hide()
            if window.rating_button: window.rating_button.hide()

    # Вызываем show() только если флаг frameless изменился, чтобы перерисовать рамку
    if frameless_changed:
        print("[LOG] Frameless flag changed, calling window.show()")
        window.show() # Показываем окно

    # --- 7. Обновление языка и геометрии ---
    t1 = time.time()
    # print("Updating language and geometry...")
    window.update_language() # Обновит тексты во всех видимых элементах
    # Активируем layout'ы, чтобы изменения применились
    window.main_layout.activate()
    window.inner_layout.activate()
    window.updateGeometry() # Пересчитываем геометрию окна и дочерних виджетов
    t2 = time.time(); # print(f"[TIMING] -> Update language/layout/geometry: {t2-t1:.4f} s")

    # --- 8. Установка размера окна ---
    t1 = time.time()
    target_size = MODE_DEFAULT_WINDOW_SIZES.get(window.mode_manager.current_mode, {'width': 800, 'height': 600})
    target_w = target_size['width']; target_h = target_size['height']

    # Получаем актуальные минимальные размеры ПОСЛЕ всех перестроек
    min_w = window.minimumSizeHint().width(); actual_min_h = window.minimumHeight()# window.mode

    # Для min режима используем рассчитанную фиксированную высоту
    if window.mode == 'min':
        final_w = max(target_w, min_w)
        final_h = window.minimumHeight() # Берем уже установленную фикс. высоту
        window.resize(final_w, final_h)
        # print(f"Resized to MIN: {final_w}x{final_h}")
    else:
        final_w = max(target_w, min_w)
        final_h = max(target_h, actual_min_h)
        window.resize(final_w, final_h)
        # print(f"Resized to {window.mode.upper()}: {final_w}x{final_h}")

    t2 = time.time(); # print(f"[TIMING] -> Resize window: {t2-t1:.4f} s")

    # --- 9. Восстановление состояния UI ---
    t1 = time.time()
    # print("Restoring UI state...")
    # Обновляем UI на основе текущего состояния logic
    window.update_ui_after_logic_change()
    # Фокус хоткея восстанавливается в _reset_hotkey_cursor_after_mode_change
    t2 = time.time(); # print(f"[TIMING] -> Restore UI state (update_ui_after_logic_change): {t2-t1:.4f} s")

    # --- 10. Перемещение окна ---
    # Перемещаем окно в сохраненную позицию для этого режима, если окно видимо
    if window.isVisible():
        target_pos = window.mode_positions.get(window.mode)
        if target_pos: window.move(target_pos)

    t_end = time.time()
    print(f"[TIMING] update_interface_for_mode: Finished (Total: {t_end - t0:.4f} s)")
