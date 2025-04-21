# File: utils_gui.py
from PySide6.QtWidgets import QMessageBox, QLabel, QPushButton
from translations import get_text, translate_text
import pyperclip
# Импорт build убран

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


def calculate_columns(hero_count):
    """
    Рассчитывает оптимальное количество колонок для отображения героев.

    Args:
        hero_count (int): Общее количество героев.

    Returns:
        int: Количество колонок.
    """
    # Рассчитываем количество колонок в зависимости от количества героев
    if hero_count <= 5:
        # Если героев 5 и меньше, то 1 колонка
        columns = 1
    elif hero_count <= 10:
        # Если героев от 6 до 10, то 2 колонки
        columns = 2
    elif hero_count <= 15:
        # Если героев от 11 до 15, то 3 колонки
        columns = 3
    elif hero_count <= 20:
        # Если героев от 16 до 20, то 4 колонки
        columns = 4
    elif hero_count <= 30:
        columns = 5
    elif hero_count <= 40:
        columns = 6
    elif hero_count <= 50:
        columns = 7
    elif hero_count <= 60:
        columns = 8
    elif hero_count <= 70:
        columns = 9
    else:
        columns = 10
    return columns