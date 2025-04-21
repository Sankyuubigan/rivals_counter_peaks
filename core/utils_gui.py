# File: utils_gui.py
from PySide6.QtWidgets import QMessageBox, QLabel, QPushButton
from translations import get_text
import pyperclip
# Импорт build убран

HERO_ICON_WIDTH = 60
ITEM_SPACING = 6

def copy_to_clipboard(logic):
    """Копирует рекомендуемую команду (effective_team) в буфер обмена."""
    print("Получение эффективной команды для копирования...")
    # Используем уже рассчитанную команду, если она есть, иначе считаем
    effective_team = []
    # Проверяем, есть ли атрибут и он не пустой
    if hasattr(logic, 'effective_team') and logic.effective_team:
        effective_team = logic.effective_team
    # Иначе, если есть выбранные герои, то считаем команду
    elif logic.selected_heroes:
        print("Пересчет эффективной команды для копирования...")
        counter_scores = logic.calculate_counter_scores()
        effective_team = logic.calculate_effective_team(counter_scores)
    else:
        print("Нет выбранных героев, команда не может быть рассчитана.")

    print(f"Эффективная команда для копирования: {effective_team}")

    if effective_team:
        text_to_copy = ', '.join(effective_team) # Просто список через запятую
        try:
            pyperclip.copy(text_to_copy)
            print(f"Скопировано в буфер: {text_to_copy}")
            # Показываем сообщение об успехе
            QMessageBox.information(None, # parent=None, чтобы сообщение было поверх всего
                                     get_text('success', language=logic.DEFAULT_LANGUAGE),
                                     get_text('copied_to_clipboard', language=logic.DEFAULT_LANGUAGE))
        except pyperclip.PyperclipException as e: 
            print(f"Ошибка pyperclip при копировании: {e}")
            QMessageBox.warning(None,
                                get_text('error', language=logic.DEFAULT_LANGUAGE),
                                get_text('copy_error_detailed', e=str(e), language=logic.DEFAULT_LANGUAGE))
        except Exception as e:
            print(f"Неожиданная ошибка при копировании: {e}")
            QMessageBox.warning(None, get_text('error', language=logic.DEFAULT_LANGUAGE), get_text('copy_error', language=logic.DEFAULT_LANGUAGE))
    else:
        # Если команда пуста (не рассчитана или нет рекомендаций)
        print("Нет данных для копирования (effective_team пуст или не рассчитана).")
        QMessageBox.warning(None, get_text('warning', language=logic.DEFAULT_LANGUAGE), get_text('no_data_to_copy', language=logic.DEFAULT_LANGUAGE))

def calculate_columns(self): 
    
    """Рассчитывает оптимальное количество колонок для QListWidget.

    Возвращает:
        int: Оптимальное количество колонок.
    """
    num_columns_cache = self._num_columns_cache  # Кэш количества колонок
    try:
        if self._check_min_mode():
            return 1  # В режиме min или если список скрыт - 1 колонка

        list_width = self._get_list_width()
        if list_width <= 0:
            return num_columns_cache  # Ширина нулевая - возвращаем кэш (может быть до отрисовки)

        item_width = self._get_item_width()
        num_columns = self._calculate_num_columns(list_width, item_width)
        if self.right_list_widget.count() < num_columns:
            if num_columns > 1:
                num_columns -= 1   
        return self._update_cache(num_columns)
    except Exception as e:
        print(f"[ERROR] Calculating columns: {e}")
        return num_columns_cache

    
def _check_min_mode(self):
    """Проверяет, находится ли приложение в режиме min или список скрыт."""
    return not self.right_list_widget or not self.right_list_widget.isVisible() or self.mode_manager.current_mode == 'min'

def _get_list_width(self):
    """Получает ширину списка, если он видим."""
    return self.right_list_widget.width() if self.right_list_widget and self.right_list_widget.isVisible() else 0

def _get_item_width(self):
    """Рассчитывает ширину элемента, включая иконку и отступы."""
    hero_icon_width = (
        list(self.small_images.values())[0].width()
        if self.small_images
        else HERO_ICON_WIDTH
    )
    return hero_icon_width + ITEM_SPACING + ITEM_SPACING

def _calculate_num_columns(self, list_width, item_width):
    """Рассчитывает количество колонок."""
    num_columns = floor(list_width / item_width)  # Округляем вниз
    return max(num_columns, 1)  # Минимум 1 колонка

def _update_cache(self, num_columns):
    """Обновляет кэш и возвращает количество колонок."""
    if self._num_columns_cache != num_columns:
        print(f"[INFO] Columns changed from {self._num_columns_cache} to {num_columns}")
        self._num_columns_cache = num_columns  # Обновляем кэш

    return num_columns
