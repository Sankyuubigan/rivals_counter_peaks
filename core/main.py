import tkinter as tk
from gui import create_gui
from utils import validate_heroes

if __name__ == "__main__":
    validate_heroes()
    root = tk.Tk()
    root.attributes('-topmost', True)  # Окно всегда поверх
    root.attributes('-alpha', 0.2)    # Начальная прозрачность 20%
    create_gui(root)
    root.mainloop()
