from PySide6.QtWidgets import QApplication
import sys
from gui import create_gui
from utils import validate_heroes

if __name__ == "__main__":
    validate_heroes()
    app = QApplication(sys.argv)
    window = create_gui()
    window.show()
    sys.exit(app.exec())