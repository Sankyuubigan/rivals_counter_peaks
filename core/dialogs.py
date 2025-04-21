# File: dialogs.py
from PySide6.QtWidgets import QDialog, QTextEdit, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt
from heroes_bd import heroes_counters, heroes
from translations import get_text, TRANSLATIONS # Импортируем полные переводы для форматирования ссылок
from build import version # Предполагается, что версия берется из build.py
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
        try:
            app_version = parent.logic.APP_VERSION # Получаем версию из logic, если она там есть
        except AttributeError:
             app_version = version # Используем версию из build.py как fallback
        author_text = get_text('author_info', version=app_version)

        # Получаем ключи URL из основного словаря (не из get_text, т.к. нам нужен сам URL)
        # Используем язык по умолчанию из logic, если он там есть
        current_lang = 'ru_RU' # Fallback
        if hasattr(parent, 'logic') and hasattr(parent.logic, 'DEFAULT_LANGUAGE'):
             current_lang = parent.logic.DEFAULT_LANGUAGE
        translations = TRANSLATIONS.get(current_lang, TRANSLATIONS['ru_RU'])


        tinkoff_card = translations.get('donate_tinkoff_card', 'N/A')
        donationalerts_url = translations.get('donate_donationalerts_url', '#')
        usdt_trc20_addr = translations.get('donate_usdt_trc20', 'N/A')
        usdt_ton_addr = translations.get('donate_usdt_ton', 'N/A')
        telegram_contact = translations.get('contact_telegram', '#')

        # Формируем HTML для донатов и контактов
        donate_html = get_text('donate_info_title') + "<br>" # "Купить мне кофе..."
        donate_html += f"{get_text('donate_tinkoff_label')} {tinkoff_card}<br>"
        donate_html += f"{get_text('donate_donationalerts_label')} <a href='{donationalerts_url}'>{donationalerts_url}</a><br>"
        donate_html += f"{get_text('donate_usdt_trc20_label')}<br>{usdt_trc20_addr}<br>"
        donate_html += f"{get_text('donate_usdt_ton_label')}<br>{usdt_ton_addr}<br><br>"
        donate_html += f"{get_text('contact_suggestions_label')}<br><a href='{telegram_contact}'>{telegram_contact}</a>"

        # Объединяем тексты (авторский текст как обычный, остальное HTML)
        # Используем replace для переносов строк в авторском тексте
        full_html_text = f"<p>{author_text.replace(chr(10), '<br>')}</p><hr><p>{donate_html}</p>"


        text_edit = QTextEdit()
        text_edit.setHtml(full_html_text) # Устанавливаем HTML
        text_edit.setReadOnly(True)
        # Этот флаг включает обработку ссылок и их активацию
        text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction | Qt.TextInteractionFlag.LinksAccessibleByKeyboard | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        # Включаем открытие внешних ссылок в браузере
        text_edit.setOpenExternalLinks(True)

        layout.addWidget(text_edit)

        close_button = QPushButton("OK") # Используем стандартный текст "OK"
        close_button.clicked.connect(self.accept) # self.accept закрывает QDialog с результатом Accepted
        layout.addWidget(close_button)

    def center_on_parent(self):
        """Центрирует диалог относительно родительского окна."""
        if self.parent():
            parent_geometry = self.parent().geometry()
            # Рассчитываем позицию для центрирования
            center_point = parent_geometry.center() - self.rect().center()
            # Убедимся, что окно не уходит за пределы экрана (простая проверка)
            screen_geometry = self.screen().availableGeometry()
            center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
            center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)


class HeroRatingDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('hero_rating_title'))
        self.setGeometry(0, 0, 400, 600) # Начальные размеры
        self.setModal(True)
        self.center_on_parent() # Центрируем после установки геометрии

        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        # Разрешаем выделение текста
        text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)

        # Считаем, сколько раз каждый герой встречается в списках контрпиков
        counter_counts = {hero: 0 for hero in heroes}
        for counters_list in heroes_counters.values():
            for counter_hero in counters_list:
                 if counter_hero in counter_counts:
                     counter_counts[counter_hero] += 1

        # Сортируем героев по возрастанию количества раз, когда они являются контрпиком
        # (чем меньше, тем "неуязвимее" по этой метрике)
        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1])

        # Формируем строки для отображения
        rating_lines = [f"{hero} ({count})" for hero, count in sorted_heroes]
        text_edit.setText("\n".join(rating_lines))
        layout.addWidget(text_edit)

        close_button = QPushButton("OK") # Стандартный текст
        close_button.clicked.connect(self.accept) # Закрыть диалог
        layout.addWidget(close_button)

    def center_on_parent(self):
        """Центрирует диалог относительно родительского окна."""
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
            center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

def show_author_info(parent):
    """Показывает диалог 'Об авторе'."""
    dialog = AuthorDialog(parent)
    dialog.exec() # Используем exec() для модальных диалогов

def show_hero_rating(parent):
    """Показывает диалог 'Рейтинг героев'."""
    dialog = HeroRatingDialog(parent)
    dialog.exec() # Используем exec() для модальных диалогов