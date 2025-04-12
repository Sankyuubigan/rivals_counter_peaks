# File: mode_manager.py
from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget
from PySide6.QtCore import Qt
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

    # Сохраняем позицию ПЕРЕД сменой режима
    if window.mode in window.mode_positions and window.isVisible():
        window.mode_positions[window.mode] = window.pos()

    window.mode = mode # Устанавливаем новый режим
    update_interface_for_mode(window) # Перестраиваем интерфейс

def update_interface_for_mode(window):
    """Перестраивает интерфейс для нового режима."""
    print(f"--- Начало перестроения UI для режима: {window.mode} ---")

    # --- Очистка старого UI (только внутренние панели left/right) ---
    print("Очистка старого UI (left/right)...")
    # Удаляем left_container и right_frame из inner_layout
    if window.inner_layout:
        while window.inner_layout.count():
            item = window.inner_layout.takeAt(0)
            widget = item.widget()
            if widget:
                print(f"Удаление виджета из inner_layout: {widget.__class__.__name__}")
                widget.deleteLater()
    else:
        # Если inner_layout нет, создаем его (случай первой инициализации или ошибки)
        if window.main_widget:
             window.inner_layout = QHBoxLayout(window.main_widget)
             window.inner_layout.setContentsMargins(0, 0, 0, 0)
             window.inner_layout.setSpacing(0)
             print("inner_layout создан.")
        else:
             print("[!] Ошибка: main_widget не найден для создания inner_layout.")
             return


    # Сбрасываем ссылки на удаленные виджеты и связанные данные
    window.left_container = None
    # window.icons_frame = None # НЕ сбрасываем, он теперь в main_layout
    # window.icons_layout = None # НЕ сбрасываем
    window.canvas = None
    window.result_frame = None
    window.result_label = None
    window.right_frame = None
    window.selected_heroes_label = None
    window.right_list_widget = None
    window.hero_items.clear()
    window._previous_selection = set()

    print("Старый UI (left/right) очищен и ссылки сброшены.")

    # --- Загрузка ресурсов ---
    try:
        print(f"Загрузка изображений для режима: {window.mode}")
        # Обновляем словари изображений в окне
        window.right_images, window.left_images, window.small_images, window.horizontal_images = get_images_for_mode(window.mode)
        print(f"Изображения для режима '{window.mode}' загружены.")
    except Exception as e:
        print(f"Критическая ошибка загрузки изображений для режима {window.mode}: {e}")
        return

    # --- Пересоздание левой панели ---
    print("Пересоздание левой панели...")
    window.left_container = QWidget()
    left_layout = QVBoxLayout(window.left_container)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(0)
    # icons_frame больше не здесь
    window.canvas, window.result_frame, window.result_label, window.update_scrollregion = create_left_panel(window.left_container)
    left_layout.addWidget(window.canvas, stretch=1)
    print("Левая панель пересоздана.")

    # --- Пересоздание правой панели (если режим не min) ---
    if window.mode != "min":
        print(f"Пересоздание правой панели для режима {window.mode}...")
        window.right_frame, window.selected_heroes_label = create_right_panel(window, window.mode)
        print("Правая панель пересоздана.")
    else:
        window.right_frame = None
        window.selected_heroes_label = None
        window.right_list_widget = None
        print("Правая панель не создается (режим min).")

    # --- Сборка UI (добавление панелей в inner_layout) ---
    if window.inner_layout: # Убедимся, что он существует
        window.inner_layout.addWidget(window.left_container, stretch=2 if window.mode != 'min' else 1)
        if window.right_frame:
            window.inner_layout.addWidget(window.right_frame, stretch=1)
        print("Левая и правая панели добавлены в inner_layout.")
    else:
        print("[!] Ошибка: inner_layout не существует для добавления панелей.")
        return

    # --- Настройка видимости и размеров ---
    print(f"Настройка видимости и размеров для режима '{window.mode}'...")
    min_h, max_h = 0, 16777215 # Высота по умолчанию (без ограничений)
    resize_w = window.width() # Базовая ширина - текущая

    # Получаем высоту top_frame и icons_frame (они всегда есть)
    top_h = window.top_frame.sizeHint().height() if window.top_frame else 40
    icons_h = window.icons_frame.sizeHint().height() if window.icons_frame else 30
    base_h = top_h + icons_h # Базовая высота нескрываемой части

    if window.mode == "max":
        window.left_container.setMinimumWidth(600)
        if window.right_frame: window.right_frame.setMinimumWidth(480)
        if window.author_button: window.author_button.setVisible(True)
        if window.rating_button: window.rating_button.setVisible(True)
        min_h = base_h + 300 # Минимальная разумная высота для контента
        resize_w = 1100 # Примерная ширина
    elif window.mode == "middle":
        window.left_container.setMinimumWidth(500)
        if window.right_frame: window.right_frame.setMinimumWidth(300)
        if window.author_button: window.author_button.setVisible(False)
        if window.rating_button: window.rating_button.setVisible(False)
        min_h = base_h + 200 # Минимальная разумная высота для контента
        resize_w = 880 # Примерная ширина
    elif window.mode == "min":
        window.left_container.setMinimumWidth(0) # Левая панель может сжиматься
        if window.author_button: window.author_button.setVisible(False)
        if window.rating_button: window.rating_button.setVisible(False)
        # Правая панель скрыта, контента в левой мало (только список)
        # Высота окна должна быть равна высоте top_frame + icons_frame + небольшой отступ
        fixed_h = base_h + 5 # + небольшой отступ
        min_h = fixed_h
        max_h = fixed_h # Фиксированная высота
        resize_w = 600 # Примерная ширина

    # Устанавливаем ограничения высоты
    window.setMinimumHeight(min_h)
    window.setMaximumHeight(max_h)
    print(f"Размеры окна: minH={min_h}, maxH={max_h}.")

    # --- Финальное обновление ---
    window.update_language() # Обновляем язык (может влиять на размеры)

    # Активируем layout'ы для пересчета размеров
    window.left_container.layout().activate()
    if window.right_frame: window.right_frame.layout().activate()
    window.inner_layout.activate()
    window.main_layout.activate()
    window.updateGeometry() # Обновляем геометрию окна

    # Изменяем размер окна до фиксированного для min режима
    if window.mode == 'min':
         print(f"Установка фиксированного размера для min режима: {resize_w}x{min_h}")
         window.resize(resize_w, min_h)
    # Для других режимов можно плавно изменять размер или оставить как есть
    # elif window.width() < resize_w or window.height() < min_h :
    #      window.resize(max(window.width(), resize_w), max(window.height(), min_h))


    # Восстанавливаем состояние UI (включая selection states)
    window.restore_hero_selections() # Вызовет update_ui_after_logic_change

    # Перемещаем окно в сохраненную позицию для этого режима, если она есть
    if window.isVisible():
        target_pos = window.mode_positions.get(window.mode)
        if target_pos:
            print(f"Перемещение окна в позицию для режима '{window.mode}': {target_pos.x()},{target_pos.y()}")
            window.move(target_pos)
        # Не сохраняем позицию здесь, т.к. она могла измениться при resize


    print(f"--- Перестроение UI для режима '{window.mode}' завершено ---")