# File: mode_manager.py
from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget
from PySide6.QtCore import Qt, QSize
from right_panel import create_right_panel
from left_panel import create_left_panel
from images_load import get_images_for_mode
from horizontal_list import update_horizontal_icon_list
from heroes_bd import heroes

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
    print("Очистка старого UI (left/right)...")
    if window.inner_layout:
        while window.inner_layout.count():
            item = window.inner_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
    else: # Создаем, если layout нет
        if window.main_widget:
             window.inner_layout = QHBoxLayout(window.main_widget)
             window.inner_layout.setContentsMargins(0, 0, 0, 0)
             window.inner_layout.setSpacing(0)
        else: print("[!] Ошибка: main_widget не найден."); return

    # Сброс ссылок на виджеты внутри left/right
    window.left_container = None
    window.canvas = None; window.result_frame = None; window.result_label = None
    window.right_frame = None; window.selected_heroes_label = None
    window.right_list_widget = None; window.hero_items.clear()

    # --- Загрузка ресурсов ---
    try:
        print(f"Загрузка изображений для режима: {window.mode}")
        window.right_images, window.left_images, window.small_images, window.horizontal_images = get_images_for_mode(window.mode)
    except Exception as e: print(f"Критическая ошибка загрузки изображений: {e}"); return

    # --- Пересоздание левой панели ---
    window.left_container = QWidget()
    left_layout = QVBoxLayout(window.left_container); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(0)
    window.canvas, window.result_frame, window.result_label, window.update_scrollregion = create_left_panel(window.left_container)
    left_layout.addWidget(window.canvas, stretch=1)
    print("Левая панель пересоздана.")

    # --- Пересоздание/Скрытие правой панели ---
    if window.mode != "min":
        window.right_frame, window.selected_heroes_label = create_right_panel(window, window.mode)
        print(f"Правая панель пересоздана для режима {window.mode}.")
    else: # Скрываем правую часть в min режиме
        window.right_frame = None # Убедимся, что ссылки нет
        print("Правая панель не создается (режим min).")

    # --- Сборка UI (добавление панелей в inner_layout) ---
    window.inner_layout.addWidget(window.left_container, stretch=2 if window.mode != 'min' else 1)
    if window.right_frame:
        window.inner_layout.addWidget(window.right_frame, stretch=1)
        window.right_frame.setVisible(True) # Убедимся, что она видима
        window.left_container.setVisible(True) # И левая тоже
        window.main_widget.setVisible(True) # Весь контейнер видим

    # --- Настройка видимости и размеров ---
    print(f"Настройка видимости и размеров для режима '{window.mode}'...")
    top_h = window.top_frame.sizeHint().height() if window.top_frame else 40
    icons_h = window.icons_frame.sizeHint().height() if window.icons_frame else 30
    margins = window.main_layout.contentsMargins()
    spacing = window.main_layout.spacing()
    # Базовая высота нескрываемой части (top + icons + отступы/spacing между ними)
    base_h = top_h + icons_h + spacing # + margins.top() + margins.bottom()

    # Сбрасываем ограничения по высоте перед установкой новых
    window.setMinimumHeight(0)
    window.setMaximumHeight(16777215)

    if window.mode == "max":
        if window.right_frame: window.right_frame.show()
        window.left_container.show()
        window.main_widget.show()
        window.setMinimumHeight(base_h + 300) # Минимум для контента
        if window.author_button: window.author_button.setVisible(True)
        if window.rating_button: window.rating_button.setVisible(True)
    elif window.mode == "middle":
        if window.right_frame: window.right_frame.show()
        window.left_container.show()
        window.main_widget.show()
        window.setMinimumHeight(base_h + 200) # Минимум для контента
        if window.author_button: window.author_button.setVisible(False)
        if window.rating_button: window.rating_button.setVisible(False)
    elif window.mode == "min":
        # Скрываем main_widget, содержащий left/right панели
        window.main_widget.hide()
        # Фиксируем высоту окна = высота top + icons + отступы
        fixed_h = base_h + 5 # Добавим небольшой запас
        window.setMinimumHeight(fixed_h)
        window.setMaximumHeight(fixed_h)
        window.resize(window.width(), fixed_h) # Принудительно ставим высоту
        print(f"Установлена ФИКСИРОВАННАЯ высота для min режима: {fixed_h}")
        if window.author_button: window.author_button.setVisible(False)
        if window.rating_button: window.rating_button.setVisible(False)

    # --- Финальное обновление ---
    window.update_language() # Обновляем язык
    window.left_container.layout().activate()
    if window.right_frame: window.right_frame.layout().activate()
    window.inner_layout.activate()
    window.main_layout.activate()
    window.updateGeometry() # Обновляем геометрию

    # Восстанавливаем состояние UI
    window.restore_hero_selections()

    # Перемещаем окно
    if window.isVisible():
        target_pos = window.mode_positions.get(window.mode)
        if target_pos: window.move(target_pos)

    print(f"--- Перестроение UI для режима '{window.mode}' завершено ---")