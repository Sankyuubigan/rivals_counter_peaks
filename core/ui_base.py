"""
Базовые классы для UI компонентов
"""
import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCloseEvent

class BaseWindow(QWidget):
    """Базовый класс для всех окон приложения"""
    
    window_closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Настройка UI (переопределяется в наследниках)"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
    
    def _connect_signals(self):
        """Подключение сигналов (переопределяется в наследниках)"""
        pass
    
    def closeEvent(self, event: QCloseEvent):
        """Обработка закрытия окна"""
        self.window_closed.emit()
        super().closeEvent(event)
    
    def set_loading_state(self, loading: bool):
        """Устанавливает состояние загрузки"""
        self.setEnabled(not loading)
        if loading:
            self.setCursor(Qt.WaitCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

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
        self._connect_signals()
    
    def _setup_ui(self):
        """Настройка UI (переопределяется в наследниках)"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Контейнер для контента
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        
        # Контейнер для кнопок
        self.button_widget = QWidget()
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(10)
        
        # Кнопки по умолчанию
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addWidget(self.button_widget)
    
    def _connect_signals(self):
        """Подключение сигналов (переопределяется в наследниках)"""
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
    
    def accept(self):
        """Принять диалог"""
        self.dialog_accepted.emit()
        super().accept()
    
    def reject(self):
        """Отклонить диалог"""
        self.dialog_rejected.emit()
        super().reject()

class BasePanel(QFrame):
    """Базовый класс для панелей приложения"""
    
    panel_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Настройка UI (переопределяется в наследниках)"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        self.setFrameShape(QFrame.StyledPanel)
    
    def _connect_signals(self):
        """Подключение сигналов (переопределяется в наследниках)"""
        pass
    
    def update_ui(self):
        """Обновление UI (вызывается при изменении данных)"""
        self.panel_updated.emit()

class BaseInfoDialog(BaseDialog):
    """Базовый класс для информационных диалогов"""
    
    def __init__(self, parent=None, title: str = "", content: str = ""):
        super().__init__(parent, title)
        self.content = content
        self._setup_content()
    
    def _setup_content(self):
        """Настройка контента"""
        self.content_label = QLabel(self.content)
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.RichText)
        self.content_label.setOpenExternalLinks(True)
        
        self.content_layout.addWidget(self.content_label)
        self.content_layout.addStretch()
    
    def set_content(self, content: str):
        """Установить контент"""
        self.content = content
        self.content_label.setText(content)