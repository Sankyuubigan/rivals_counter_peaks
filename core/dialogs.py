# File: core/dialogs.py
from PySide6.QtWidgets import (QDialog, QTextBrowser, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout,
                               QLabel, QFileDialog, QWidget)
# ИСПРАВЛЕНО: Удален ненужный и неверный импорт QCloseEvent из QtCore
from PySide6.QtCore import Qt, Slot
from info.translations import get_text
import pyperclip
import logging
import datetime

from core.ui_components.hotkey_capture_line_edit import HotkeyCaptureLineEdit 

# LogDialog теперь QWidget, а не QDialog, для встраивания во вкладку
class LogDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.log_browser = QTextBrowser(self)
        self.log_browser.setReadOnly(True)
        
        self.copy_button = QPushButton(get_text('copy_all_logs_button'))
        self.copy_button.clicked.connect(self.copy_logs)
        
        self.save_button = QPushButton(get_text('save_logs_to_file_button'))
        self.save_button.clicked.connect(self.save_logs_to_file)
        
        self.clear_button = QPushButton(get_text('clear_log_window_button'))
        self.clear_button.clicked.connect(self.clear_log_display)
        
        button_layout = QHBoxLayout() 
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch(1)
        
        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.log_browser, stretch=1)

    @Slot(str)
    def append_log(self, message):
        self.log_browser.append(message)

    @Slot()
    def copy_logs(self):
        pyperclip.copy(self.log_browser.toPlainText())
        QMessageBox.information(self, get_text('success'), get_text('log_copy_success'))

    @Slot()
    def save_logs_to_file(self):
        logs = self.log_browser.toPlainText()
        if not logs: return
        
        filename = f"rcp_logs_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
        path, _ = QFileDialog.getSaveFileName(self, get_text('log_save_dialog_title'), filename)
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(logs)
                QMessageBox.information(self, get_text('success'), get_text('log_save_success', filepath=path))
            except IOError as e:
                QMessageBox.warning(self, get_text('error'), str(e))

    @Slot()
    def clear_log_display(self):
        self.log_browser.clear()

# Остальные диалоги (About, Author, HeroRating) удалены, так как их функциональность
# теперь реализована через вкладки в MainWindowRefactored.
# HotkeyDisplayDialog также удален, его заменила вкладка настроек.