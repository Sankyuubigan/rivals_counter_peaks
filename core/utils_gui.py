# File: core/utils_gui.py
from PySide6.QtWidgets import QMessageBox
# <<< ИСПРАВЛЕНО: Используем абсолютный импорт >>>
import translations
# <<< ----------------------------------------- >>>
import pyperclip

# Константы можно оставить здесь, если они используются только в GUI
HERO_ICON_WIDTH = 60
ITEM_SPACING = 6

def copy_to_clipboard(logic):
    """Копирует рекомендуемую команду (effective_team) в буфер обмена."""
    print("Получение эффективной команды для копирования...")
    effective_team = []
    if hasattr(logic, 'effective_team') and logic.effective_team:
        effective_team = logic.effective_team
    elif logic.selected_heroes:
        print("Пересчет эффективной команды для копирования...")
        counter_scores = logic.calculate_counter_scores()
        effective_team = logic.calculate_effective_team(counter_scores)
    else:
        print("Нет выбранных героев, команда не может быть рассчитана.")

    print(f"Эффективная команда для копирования: {effective_team}")

    if effective_team:
        text_to_copy = ', '.join(effective_team)
        try:
            pyperclip.copy(text_to_copy)
            print(f"Скопировано в буфер: {text_to_copy}")
            # <<< ИСПРАВЛЕНО: Используем translations.get_text >>>
            QMessageBox.information(None,
                                     translations.get_text('success', language=logic.DEFAULT_LANGUAGE),
                                     translations.get_text('copied_to_clipboard', language=logic.DEFAULT_LANGUAGE))
        except pyperclip.PyperclipException as e:
             print(f"Ошибка pyperclip при копировании: {e}")
             QMessageBox.warning(None,
                                 translations.get_text('error', language=logic.DEFAULT_LANGUAGE),
                                 translations.get_text('copy_error_detailed', e=str(e), language=logic.DEFAULT_LANGUAGE))
        except Exception as e:
             print(f"Неожиданная ошибка при копировании: {e}")
             QMessageBox.warning(None, translations.get_text('error', language=logic.DEFAULT_LANGUAGE), translations.get_text('copy_error', language=logic.DEFAULT_LANGUAGE))
    else:
        print("Нет данных для копирования (effective_team пуст или не рассчитана).")
        QMessageBox.warning(None, translations.get_text('warning', language=logic.DEFAULT_LANGUAGE), translations.get_text('no_data_to_copy', language=logic.DEFAULT_LANGUAGE))
    # <<< --------------------------------------------------- >>>

# Функции calculate_columns и связанные с ней больше не нужны здесь