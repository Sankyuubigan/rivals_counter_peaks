from PySide6.QtWidgets import QDialog, QTextEdit, QPushButton, QVBoxLayout
from heroes_bd import heroes_counters, heroes
from translations import get_text
import pyperclip

class AuthorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('about_author'))
        self.setGeometry(0, 0, 400, 200)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        from build import version
        text = QTextEdit(f"{get_text('author_info').replace('1.01', version)}\n\n{get_text('donate_info')}")
        text.setReadOnly(True)
        layout.addWidget(text)

        close_button = QPushButton("OK")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        text.copyAvailable.connect(lambda: pyperclip.copy(text.textCursor().selectedText()) if text.textCursor().hasSelection() else None)

    def center_on_parent(self):
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
        text = QTextEdit()
        text.setReadOnly(True)
        counter_counts = {hero: len(heroes_counters.get(hero, [])) for hero in heroes}
        sorted_heroes = sorted(counter_counts.items(), key=lambda x: x[1])
        text.setText("\n".join([f"{hero} ({count})" for hero, count in sorted_heroes]))
        layout.addWidget(text)

    def center_on_parent(self):
        parent_geometry = self.parent().geometry()
        self.move(parent_geometry.center() - self.rect().center())

def show_author_info(parent):
    dialog = AuthorDialog(parent)
    dialog.exec()

def show_hero_rating(parent):
    dialog = HeroRatingDialog(parent)
    dialog.exec()