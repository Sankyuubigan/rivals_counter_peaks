# File: core/dialogs.py
# <<< ИЗМЕНЕНО: Импортируем QTextBrowser вместо QTextEdit >>>
from PySide6.QtWidgets import QDialog, QTextBrowser, QPushButton, QVBoxLayout, QMessageBox, QScrollArea, QWidget, \
    QLabel, QHBoxLayout
# <<< -------------------------------------------------- >>>
from PySide6.QtCore import Qt, Slot, QTimer
from database import heroes_bd
from translations import get_text, TRANSLATIONS
# <<< ДОБАВЛЕНО: Импорт pyperclip для копирования логов >>>
import pyperclip
# <<< ------------------------------------------------ >>>
import logging # Для логов в диалоге


class AuthorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(get_text('about_author'))
        self.setGeometry(0, 0, 450, 300) # Начальный размер, можно настроить
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)

        current_lang = 'ru_RU'
        # Проверяем наличие logic и языка в родительском окне
        if hasattr(parent, 'logic') and hasattr(parent.logic, 'DEFAULT_LANGUAGE'):
             current_lang = parent.logic.DEFAULT_LANGUAGE
        translations_data = TRANSLATIONS.get(current_lang, TRANSLATIONS['ru_RU'])

        # Получаем данные для отображения из переводов
        tinkoff_card = translations_data.get('donate_tinkoff_card', 'N/A')
        donationalerts_url = translations_data.get('donate_donationalerts_url', '#')
        usdt_trc20_addr = translations_data.get('donate_usdt_trc20', 'N/A')
        usdt_ton_addr = translations_data.get('donate_usdt_ton', 'N/A')
        telegram_contact = translations_data.get('contact_telegram', '#')

        # Формируем HTML для донатов и контактов
        donate_html = get_text('donate_info_title') + "<br>"
        donate_html += f"{get_text('donate_tinkoff_label')} {tinkoff_card}<br>"
        donate_html += f"{get_text('donate_donationalerts_label')} <a href='{donationalerts_url}'>{donationalerts_url}</a><br>"
        donate_html += f"{get_text('donate_usdt_trc20_label')}<br>{usdt_trc20_addr}<br>"
        donate_html += f"{get_text('donate_usdt_ton_label')}<br>{usdt_ton_addr}<br><br>"
        donate_html += f"{get_text('contact_suggestions_label')}<br><a href='{telegram_contact}'>{telegram_contact}</a>"

        # Получаем версию из родительского окна
        app_version = parent.app_version if hasattr(parent, 'app_version') else 'N/A'
        author_text = get_text('author_info', version=app_version)
        full_html_text = f"<p>{author_text.replace(chr(10), '<br>')}</p><hr><p>{donate_html}</p>"

        # <<< ИЗМЕНЕНО: Используем QTextBrowser >>>
        self.text_browser = QTextBrowser()
        # <<< ---------------------------------- >>>
        self.close_button = QPushButton("OK")

        self._setup_widgets(full_html_text)
        self._setup_layout(layout)

    def center_on_parent(self):
        """Центрирует диалог относительно родительского окна."""
        if self.parent():
            parent_geometry = self.parent().geometry()
            # Рассчитываем центр родителя и вычитаем половину размера диалога
            center_point = parent_geometry.center() - self.rect().center()
            # Убедимся, что диалог не выходит за пределы доступной геометрии экрана
            screen_geometry = self.screen().availableGeometry()
            center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
            center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

    def _setup_widgets(self, full_html_text):
        """Настраивает виджеты диалога."""
        # <<< ИЗМЕНЕНО: Настраиваем QTextBrowser >>>
        self.text_browser.setHtml(full_html_text)
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(True) # Включаем открытие внешних ссылок
        # <<< --------------------------------- >>>
        self.close_button.clicked.connect(self.accept) # Закрыть диалог по кнопке OK

    def _setup_layout(self, layout):
        """Настраивает layout диалога."""
        # <<< ИЗМЕНЕНО: Добавляем QTextBrowser >>>
        layout.addWidget(self.text_browser)
        # <<< --------------------------------- >>>
        layout.addWidget(self.close_button)


class HeroRatingDialog(QDialog):
    def __init__(self, parent, app_version):
        super().__init__(parent)
        self.setWindowTitle(get_text('hero_rating_title', version=app_version))
        self.setGeometry(0, 0, 400, 600)
        self.setModal(True)
        self.center_on_parent()

        layout = QVBoxLayout(self)
        # Используем QTextBrowser и здесь, чтобы был скроллбар по умолчанию
        text_browser = QTextBrowser()
        text_browser.setReadOnly(True)
        # Разрешаем выделение текста
        text_browser.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)

        # Считаем, сколько раз каждый герой является контрпиком
        counter_counts = {hero: 0 for hero in heroes_bd.heroes}
        for counters_list in heroes_bd.heroes_counters.values():
            for counter_hero in counters_list:
                if counter_hero in counter_counts:
                     counter_counts[counter_hero] += 1

        # Сортируем героев по количеству раз, когда они являются контрпиком (по возрастанию)
        sorted_heroes = sorted(counter_counts.items(), key=lambda item: item[1])
        # Формируем строки для отображения
        rating_lines = [f"{hero} ({count})" for hero, count in sorted_heroes]
        text_browser.setText("\n".join(rating_lines))
        layout.addWidget(text_browser)

        close_button = QPushButton("OK")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def center_on_parent(self):
        """Центрирует диалог."""
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
            center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)


# <<< ДОБАВЛЕНО: Класс LogDialog для отображения логов >>>
class LogDialog(QDialog):
    """Диалоговое окно для отображения логов приложения."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text('logs_window_title'))
        self.setGeometry(150, 150, 900, 600) # Размер побольше
        self.setModal(False) # Не модальное, чтобы можно было работать с приложением

        self.layout = QVBoxLayout(self)
        self.log_browser = QTextBrowser(self)
        self.log_browser.setReadOnly(True)
        self.log_browser.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap) # Без переноса строк для читаемости
        # Установка моноширинного шрифта для лучшего выравнивания
        font = self.log_browser.font()
        font.setFamily("Courier New") # Или другой моноширинный шрифт
        font.setPointSize(10)
        self.log_browser.setFont(font)

        self.copy_button = QPushButton(get_text('copy_all_logs_button'))
        self.copy_button.clicked.connect(self.copy_logs)

        self.clear_button = QPushButton(get_text('clear_log_window_button')) # Кнопка очистки окна
        self.clear_button.clicked.connect(self.clear_log_display)

        # Горизонтальный layout для кнопок
        self.button_layout = QVBoxLayout() # Вертикальный для кнопок справа
        self.button_layout.addWidget(self.copy_button)
        self.button_layout.addWidget(self.clear_button)
        self.button_layout.addStretch(1) # Прижать кнопки к верху

        self.main_hbox_layout = QHBoxLayout() # Горизонтальный для браузера и кнопок
        self.main_hbox_layout.addWidget(self.log_browser, stretch=1) # Браузер занимает больше места
        self.main_hbox_layout.addLayout(self.button_layout) # Добавляем layout с кнопками

        self.layout.addLayout(self.main_hbox_layout) # Добавляем главный горизонтальный layout

    @Slot(str)
    def append_log(self, message):
        """Добавляет сообщение лога в QTextBrowser."""
        # Убедимся, что обновление происходит в GUI потоке (хотя сигнал/слот Qt обычно это гарантирует)
        self.log_browser.append(message)
        # Опционально: автопрокрутка только если скроллбар уже внизу
        # scroll_bar = self.log_browser.verticalScrollBar()
        # if scroll_bar.value() == scroll_bar.maximum():
        #     scroll_bar.setValue(scroll_bar.maximum())

    @Slot()
    def copy_logs(self):
        """Копирует все логи из QTextBrowser в буфер обмена."""
        all_logs = self.log_browser.toPlainText()
        if not all_logs:
            QMessageBox.information(self, get_text('info'), get_text('log_copy_no_logs'))
            return
        try:
            pyperclip.copy(all_logs)
            logging.info("Logs copied to clipboard.") # Лог в основное окно
            # Можно добавить временное сообщение в само окно логов или статусбар, если он есть
            # self.statusBar().showMessage(get_text('log_copy_success'), 2000)
        except pyperclip.PyperclipException as e:
            logging.error(f"Pyperclip error copying logs: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error copying logs: {e}")
            QMessageBox.warning(self, get_text('error'), f"{get_text('log_copy_error')}: {e}")

    @Slot()
    def clear_log_display(self):
        """Очищает QTextBrowser."""
        self.log_browser.clear()
        logging.info("Log display cleared by user.") # Лог в основное окно (он останется в файле/консоли)

    # Переопределяем closeEvent, чтобы окно скрывалось, а не удалялось
    def closeEvent(self, event):
        logging.debug("LogDialog close event: hiding window.")
        self.hide()
        event.ignore() # Предотвращаем фактическое закрытие диалога
# <<< --------------------------------------------------- >>>


# <<< ДОБАВЛЕНО: Класс HotkeysDialog >>>
class HotkeysDialog(QDialog):
    """Диалоговое окно для отображения списка горячих клавиш."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text('hotkeys_window_title'))
        self.setMinimumWidth(550)
        # self.setMinimumHeight(400)
        self.setModal(True) # Модальное

        self.layout = QVBoxLayout(self)

        # Используем QTextBrowser для форматирования и возможного скроллинга
        self.text_browser = QTextBrowser(self)
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(False) # Ссылки не нужны

        hotkeys_text_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; font-size: 10pt; }}
                h3 {{ margin-bottom: 5px; margin-top: 10px; }}
                ul {{ margin-top: 0px; padding-left: 20px; }}
                li {{ margin-bottom: 3px; }}
                code {{ background-color: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h3>{get_text('hotkeys_section_main')}</h3>
            <ul>
                <li><code>Tab + ↑/↓/←/→</code>: {get_text('hotkey_desc_navigation')}</li>
                <li><code>Tab + Num 0</code>: {get_text('hotkey_desc_select')}</li>
                <li><code>Tab + Num Del (*)</code>: {get_text('hotkey_desc_toggle_mode')}</li>
                <li><code>Tab + Num /</code>: {get_text('hotkey_desc_recognize')}</li>
                <li><code>Tab + Num -</code>: {get_text('hotkey_desc_clear')}</li>
                <li><code>Tab + Num 1</code>: {get_text('hotkey_desc_copy_team')}</li>
                <li><code>Tab + Num 7</code>: {get_text('hotkey_desc_toggle_topmost')}</li>
                <li><code>Tab + Num 9</code>: {get_text('hotkey_desc_toggle_mouse_ignore')}</li>
                <li><code>Tab + Num 3</code>: {get_text('hotkey_desc_debug_screenshot')}</li>
            </ul>
            <h3>{get_text('hotkeys_section_additional')}</h3>
            <ul>
                <li><code>{get_text('hotkey_desc_lmb')}</code>: {get_text('hotkey_desc_lmb_select')}</li>
                <li><code>{get_text('hotkey_desc_rmb')}</code>: {get_text('hotkey_desc_rmb_priority')}</li>
                <li><code>{get_text('hotkey_desc_drag')}</code>: {get_text('hotkey_desc_drag_window')}</li>
                <li><code>{get_text('hotkey_desc_slider')}</code>: {get_text('hotkey_desc_slider_transparency')}</li>
            </ul>
        </body>
        </html>
        """
        self.text_browser.setHtml(hotkeys_text_html)

        self.close_button = QPushButton("OK")
        self.close_button.clicked.connect(self.accept)

        self.layout.addWidget(self.text_browser)
        self.layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Центрируем после установки размера
        QTimer.singleShot(0, self.center_on_parent)

    def center_on_parent(self):
        """Центрирует диалог."""
        if self.parent():
            parent_geometry = self.parent().geometry()
            center_point = parent_geometry.center() - self.rect().center()
            screen_geometry = self.screen().availableGeometry()
            center_point.setX(max(screen_geometry.left(), min(center_point.x(), screen_geometry.right() - self.width())))
            center_point.setY(max(screen_geometry.top(), min(center_point.y(), screen_geometry.bottom() - self.height())))
            self.move(center_point)

# <<< ------------------------------- >>>


# Функции для вызова диалогов
def show_author_info(parent, app_version):
    dialog = AuthorDialog(parent)
    dialog.exec()

def show_hero_rating(parent, app_version):
    dialog = HeroRatingDialog(parent, app_version)
    dialog.exec()
