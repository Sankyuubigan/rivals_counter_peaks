from PySide6.QtWidgets import QMessageBox, QLabel
from translations import get_text, set_language, DEFAULT_LANGUAGE
from build import version
import pyperclip

def update_language(window, result_label, selected_heroes_label, logic, author_button, rating_button, top_frame):
    window.setWindowTitle(f"{get_text('title')} v{version}")
    result_label.setText(get_text('select_heroes'))
    selected_heroes_label.setText(get_text('selected'))
    author_button.setText(get_text('about_author'))
    rating_button.setText(get_text('hero_rating'))
    if not logic.selected_heroes:
        result_label.setText(get_text('no_heroes_selected'))
    logic.update_display_language()

    for child in top_frame.children():
        if isinstance(child, QLabel):
            if child.text().startswith("Прозрачность") or child.text().startswith("Transparency"):
                child.setText("Прозрачность" if DEFAULT_LANGUAGE == 'ru_RU' else get_text('transparency', 'Transparency:'))
            elif child.text() == "Режим:" or child.text() == "Mode:":
                child.setText("Режим:" if DEFAULT_LANGUAGE == 'ru_RU' else "Mode:")
            elif child.text() == get_text('language'):
                child.setText(get_text('language'))

def switch_language(window, lang, logic, result_label, selected_heroes_label, author_button, rating_button, top_frame, update_counters_wrapper):
    set_language(lang)
    update_language(window, result_label, selected_heroes_label, logic, author_button, rating_button, top_frame)
    update_counters_wrapper()  # Удаляем параметры

def copy_to_clipboard(logic):
    effective_team = logic.calculate_effective_team(logic.calculate_counter_scores())
    if effective_team:
        text_to_copy = f"we need to get these heroes:\n{', '.join(effective_team)}"
        pyperclip.copy(text_to_copy)
    else:
        QMessageBox.warning(None, "Ошибка", "Нет данных для копирования.")