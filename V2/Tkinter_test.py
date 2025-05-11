import tkinter as tk
from tkinter import simpledialog

root = tk.Tk()
root.withdraw()
result = simpledialog.askstring("Test", "Is Tkinter working?")
print("Result:", result)
