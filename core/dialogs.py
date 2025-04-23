# File: core/dialogs.py
from PySide6.QtWidgets import QDialog, QTextEdit, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt
# <<< ИСПРАВЛЕНО: Используем абсолютные импорты >>>
import translations
import heroes_bd
# <<< ----------------------------------------- >>>
from translations import get_text, TRANSLATIONS
import pyperclip

class AuthorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('about_author'))
        self.setGeometry(0, 0, 450, 300)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)

        current_lang = 'ru_RU'
        if hasattr(parent, 'logic') and hasattr(parent.logic, 'DEFAULT_LANGUAGE'):
             current_lang = parent.logic.DEFAULT_LANGUAGE
        translations_data = TRANSLATIONS.get(current_lang, TRANSLATIONS['ru_RU'])

        tinkoff_card = translations_data.get('donate_tinkoff_card', 'N/A')
        donationalerts_url = translations_data.get('donate_donationalerts_url', '#')
        usdt_trc20_addr = translations_data.get('donate_usdt_trc20', 'N/A')
        usdt_ton_addr = translations_data.get('donate_usdt_ton', 'N/A')
        telegram_contact = translations_data.get('contact_telegram', '#')

        donate_html = get_text('donate_info_title') + "<br>"
        donate_html += f"{get_text('donate_tinkoff_label')} {tinkoff_card}<br>"
        donate_html += f"{get_text('donate_donationalerts_label')} <a href='{donationalerts_url}'>{donationalerts_url}</a><br>"
        donate_html += f"{get_text('donate_usdt_trc20_label')}<br>{usdt_trc20_addr}<br>"
        donate_html += f"{get_text('donate_usdt_ton_label')}<br>{usdt_ton_addr}<br><br>"
        donate_html += f"{get_text('contact_suggestions_label')}<br><a href='{telegram_contact}'>{telegram_contact}</a>"

        app_version = parent.app_version
        author_text = get_text('author_info', version=app_version)
        full_html_text = f"<p>{author_text.replace(chr(10), '<br>')}</p><hr><p>{donate_html}</p>"

        # <<< ИСПРАВЛЕНО: Создаем виджеты перед настройкой layout >>>
        self.text_edit = QTextEdit()
        self.close_button = QPushButton("OK")
        self._setup_widgets(full_html_text) # Передаем текст сюда
        self._setup_layout(layout)
        # <<< ------------------------------------------------- >>>

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
            center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

    # <<< ИСПРАВЛЕНО: Метод переименован и принимает текст >>>
    def _setup_widgets(self, full_html_text):
        self.text_edit.setHtml(full_html_text)
        self.text_edit.setReadOnly(True)
        # <<< ИСПРАВЛЕНО: Удален setOpenExternalLinks >>>
        self.text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction |
            Qt.TextInteractionFlag.LinksAccessibleByKeyboard |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        # self.text_edit.setOpenExternalLinks(True) # <-- Удалено
        # <<< ------------------------------------ >>>
        self.close_button.clicked.connect(self.accept)

    # <<< ИСПРАВЛЕНО: Метод переименован >>>
    def _setup_layout(self, layout):
        layout.addWidget(self.text_edit)
        layout.addWidget(self.close_button)


class HeroRatingDialog(QDialog):
    def __init__(self, parent, app_version):
        super().__init__(parent)
        self.setWindowTitle(get_text('hero_rating_title', version=app_version))
        self.setGeometry(0, 0, 400, 600)
        self.setModal(True)
        self.center_on_parent()

        # <<< ИСПРАВЛЕНО: Используем импортированный heroes_bd >>>
        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)

        counter_counts = {hero: 0 for hero in heroes_bd.heroes}
        for counters_list in heroes_bd.heroes_counters.values():
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
        # <<< ----------------------------------------------- >>>

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
            center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

def show_author_info(parent, app_version):
    dialog = AuthorDialog(parent)
    dialog.exec()

def show_hero_rating(parent, app_version):
    dialog = HeroRatingDialog(parent, app_version)
    dialog.exec()