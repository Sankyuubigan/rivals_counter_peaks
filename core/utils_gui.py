# File: core/utils_gui.py
from PySide6.QtWidgets import QMessageBox
from info import translations
import pyperclip

def copy_to_clipboard(logic, show_message=True):
    """Копирует рекомендуемую команду (effective_team) в буфер обмена."""
    effective_team = logic.effective_team
    if not effective_team and logic.selected_heroes:
        counter_scores = logic.calculate_counter_scores()
        effective_team = logic.calculate_effective_team(counter_scores)

    if effective_team:
        text_to_copy = 'we need these heroes: ' +', '.join(effective_team)
        try:
            pyperclip.copy(text_to_copy)
            # ИСПРАВЛЕНИЕ: Показываем сообщение только если флаг show_message равен True
            if show_message:
                QMessageBox.information(None,
                                         translations.get_text('success', language=logic.DEFAULT_LANGUAGE),
                                         translations.get_text('copied_to_clipboard', language=logic.DEFAULT_LANGUAGE))
        except Exception as e:
             if show_message:
                QMessageBox.warning(None, 
                                     translations.get_text('error', language=logic.DEFAULT_LANGUAGE), 
                                     translations.get_text('copy_error_detailed', e=str(e), language=logic.DEFAULT_LANGUAGE))
    else:
        if show_message:
            QMessageBox.warning(None, 
                                translations.get_text('warning', language=logic.DEFAULT_LANGUAGE), 
                                translations.get_text('no_data_to_copy', language=logic.DEFAULT_LANGUAGE))