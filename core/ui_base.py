"""
Базовые классы для UI компонентов
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent

class BaseWindow(QWidget):
    """Базовый класс для всех окон приложения"""
    window_closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def closeEvent(self, event: QCloseEvent):
        self.window_closed.emit()
        super().closeEvent(event)

class BaseDialog(QDialog):
    """Базовый класс для всех диалоговых окон"""
    dialog_accepted = Signal()
    dialog_rejected = Signal()
    
    def __init__(self, parent=None, title: str = ""):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.setWindowTitle(title)
        self.setModal(True)
        self._setup_ui()
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
    
    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.content_layout)
        
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.button_layout)
    
    def accept(self):
        self.dialog_accepted.emit()
        super().accept()
    
    def reject(self):
        self.dialog_rejected.emit()
        super().reject()