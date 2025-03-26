import tkinter as tk
from gui import create_gui
from utils import validate_heroes

if __name__ == "__main__":
    validate_heroes()
    root = tk.Tk()
    create_gui(root)
    root.mainloop()