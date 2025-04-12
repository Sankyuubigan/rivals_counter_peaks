# File: utils_gui.py
from PySide6.QtWidgets import QMessageBox, QLabel, QPushButton
from translations import get_text
import pyperclip
# Импорт build убран, версия используется в dialogs.py

def copy_to_clipboard(logic):
    """Копирует рекомендуемую команду (effective_team) в буфер обмена."""
    print("Получение эффективной команды для копирования...")
    # Используем уже рассчитанную команду, если она есть, иначе считаем
    if not hasattr(logic, 'effective_team') or not logic.effective_team:
         print("Пересчет...")
         counter_scores = logic.calculate_counter_scores()
         effective_team = logic.calculate_effective_team(counter_scores)
    else:
         effective_team = logic.effective_team

    print(f"Эффективная команда для копирования: {effective_team}")

    if effective_team:
        # header = get_text('copy_team_header', "Рекомендуемая команда:") # Можно добавить заголовок
        text_to_copy = ', '.join(effective_team) # Просто список через запятую
        try:
            pyperclip.copy(text_to_copy)
            print(f"Скопировано в буфер: {text_to_copy}")
            QMessageBox.information(None,
                                     get_text('success'),
                                     get_text('copied_to_clipboard')) # Используем новый текст
        except pyperclip.PyperclipException as e:
             print(f"Ошибка pyperclip при копировании: {e}")
             QMessageBox.warning(None,
                                 get_text('error'),
                                 get_text('copy_error_detailed', e=e)) # Передаем ошибку в перевод
        except Exception as e:
             print(f"Неожиданная ошибка при копировании: {e}")
             QMessageBox.warning(None, get_text('error'), get_text('copy_error'))

    else:
        print("Нет данных для копирования (effective_team пуст).")
        QMessageBox.warning(None, get_text('warning'), get_text('no_data_to_copy'))