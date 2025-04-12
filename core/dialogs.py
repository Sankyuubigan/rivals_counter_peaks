# File: dialogs.py
from PySide6.QtWidgets import QDialog, QTextEdit, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt # Добавил Qt
from heroes_bd import heroes_counters, heroes
from translations import get_text
from build import version # Импортируем версию из build.py
import pyperclip

class AuthorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('about_author'))
        # Делаем размер чуть больше для информации о донатах
        self.setGeometry(0, 0, 450, 300) # Увеличил размер
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        # Используем get_text для форматирования версии
        author_text = get_text('author_info', version=version)
        donate_text = get_text('donate_info')
        full_text = f"{author_text}\n\n{donate_text}"

        text_edit = QTextEdit(full_text)
        text_edit.setReadOnly(True)
        # Устанавливаем поддержку ссылок
        text_edit.setOpenExternalLinks(True)
        text_edit.setTextInteractionFlags(Qt.TextBrowserInteraction) # Разрешить клики и выделение

        layout.addWidget(text_edit)

        close_button = QPushButton("OK") # Текст OK обычно не переводят
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        # Убрал обработку copyAvailable, т.к. стандартное копирование работает
        # text_edit.copyAvailable.connect(lambda available: print(f"Copy available: {available}"))


    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            self.move(parent_geometry.center() - self.rect().center())
        # Если родителя нет, можно центрировать на экране (но у нас он есть)


class HeroRatingDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('hero_rating_title'))
        self.setGeometry(0, 0, 400, 600) # Оставляем размер
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        text_edit = QTextEdit() # Используем QTextEdit для копирования
        text_edit.setReadOnly(True)
        text_edit.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard) # Только выделение

        # Считаем, сколько раз каждый герой является контрпиком для кого-то
        counter_counts = {hero: 0 for hero in heroes}
        for counters_list in heroes_counters.values():
            for counter_hero in counters_list:
                 if counter_hero in counter_counts:
                     counter_counts[counter_hero] += 1

        # Сортируем по возрастанию количества раз, когда герой был контрпиком
        # (менее популярные контрпики = более "неуязвимые")
        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1]) # Сортировка по значению (количеству)

        # Формируем текст рейтинга
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


# Функции для вызова диалогов
def show_author_info(parent):
    dialog = AuthorDialog(parent)
    dialog.exec()

def show_hero_rating(parent):
    dialog = HeroRatingDialog(parent)
    dialog.exec()