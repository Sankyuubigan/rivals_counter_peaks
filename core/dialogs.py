# File: dialogs.py
from PySide6.QtWidgets import QDialog, QTextEdit, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters, heroes
from translations import get_text, TRANSLATIONS # Импортируем полные переводы для форматирования ссылок
from build import version
import pyperclip

class AuthorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('about_author'))
        self.setGeometry(0, 0, 450, 300)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)

        # Получаем тексты
        author_text = get_text('author_info', version=version)
        # Получаем ключи URL из основного словаря (не из get_text, т.к. нам нужен сам URL)
        # Используем язык по умолчанию окна или 'ru_RU' как fallback
        current_lang = parent.logic.DEFAULT_LANGUAGE if hasattr(parent.logic, 'DEFAULT_LANGUAGE') else 'ru_RU'
        translations = TRANSLATIONS.get(current_lang, TRANSLATIONS['ru_RU'])

        tinkoff_card = translations.get('donate_tinkoff_card', '2200 7007 5813 1881')
        donationalerts_url = translations.get('donate_donationalerts_url', 'https://www.donationalerts.com/r/nildencorp')
        usdt_trc20_addr = translations.get('donate_usdt_trc20', 'TQ4jTGfTpd3qMMHzBKrxmaCmaeJdjvEqky')
        usdt_ton_addr = translations.get('donate_usdt_ton', 'UQDKxUPol48B__NQvvTxKKFtr6PTwZH7i9BWWjVb9iFuNb7k')
        telegram_contact = translations.get('contact_telegram', 'https://t.me/dron_maredon')

        # Формируем HTML для донатов и контактов
        donate_html = get_text('donate_info_title') + "<br>" # "Купить мне кофе..."
        donate_html += f"{get_text('donate_tinkoff_label')} {tinkoff_card}<br>"
        donate_html += f"{get_text('donate_donationalerts_label')} <a href='{donationalerts_url}'>{donationalerts_url}</a><br>"
        donate_html += f"{get_text('donate_usdt_trc20_label')}<br>{usdt_trc20_addr}<br>"
        donate_html += f"{get_text('donate_usdt_ton_label')}<br>{usdt_ton_addr}<br><br>"
        donate_html += f"{get_text('contact_suggestions_label')}<br><a href='{telegram_contact}'>{telegram_contact}</a>"

        # Объединяем тексты (авторский текст как обычный, остальное HTML)
        # Используем toHtml() для авторского текста, чтобы сохранить переносы строк
        full_html_text = f"<p>{author_text.replace(chr(10), '<br>')}</p><hr><p>{donate_html}</p>"


        text_edit = QTextEdit()
        text_edit.setHtml(full_html_text) # Устанавливаем HTML
        text_edit.setReadOnly(True)
        # Этот флаг включает обработку ссылок
        text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        # Убираем неверный вызов setOpenExternalLinks
        # text_edit.setOpenExternalLinks(True) # <-- Удалено

        layout.addWidget(text_edit)

        close_button = QPushButton("OK")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            self.move(parent_geometry.center() - self.rect().center())


class HeroRatingDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('hero_rating_title'))
        self.setGeometry(0, 0, 400, 600)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)

        counter_counts = {hero: 0 for hero in heroes}
        for counters_list in heroes_counters.values():
            for counter_hero in counters_list:
                 if counter_hero in counter_counts:
                     counter_counts[counter_hero] += 1

        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1])
        rating_lines = [f"{hero} ({count})" for hero, count in sorted_heroes]
        text_edit.setText("\n".join(rating_lines))
        layout.addWidget(text_edit)

        close_button = QPushButton("OK")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def center_on_parent(self):
         if self.parent():
            parent_geometry = self.parent().geometry()
            self.move(parent_geometry.center() - self.rect().center())

def show_author_info(parent):
    dialog = AuthorDialog(parent)
    dialog.exec()

def show_hero_rating(parent):
    dialog = HeroRatingDialog(parent)
    dialog.exec()