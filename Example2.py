import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from tkinter import Toplevel
import configparser as Conf

# Sample data: a list of tuples with image paths and information fields
data = [
    ("1.png", {"Title": "Sunset", "Description": "A FIRE.", "Date": "2023-07-01", "Location": "Beach",
               "Tags": "sunset, beach, nature"}),
    ("2.png", {"Title": "Mountains", "Description": "FIRE mountains.", "Date": "2023-07-02", "Location": "Alps",
               "Tags": "mountains, snow, winter"}),
    ("3.png", {"Title": "Forest", "Description": "FIRE green forest.", "Date": "2023-07-03", "Location": "Amazon",
               "Tags": "forest, green, nature"}),
]


class PhotoListApp(tk.Frame):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.parent = parent
        self.pack(fill='both', expand=True, padx=10, pady=10)

        # Loop through the data and create UI elements for each item
        for i, (photo_path, info) in enumerate(data):
            self.create_item(photo_path, info, i)

    def create_item(self, photo_path, info, row):
        # Load and resize image
        image = Image.open(photo_path)
        image = image.resize((200, 200), Image.LANCZOS)  # Use LANCZOS instead of ANTIALIAS
        photo = ImageTk.PhotoImage(image)

        # Create image label
        img_label = tk.Label(self, image=photo)
        img_label.image = photo  # Keep a reference to prevent garbage collection
        img_label.grid(row=row, column=0, padx=5, pady=5)

        # Create info frame
        info_frame = ttk.Frame(self)
        info_frame.grid(row=row, column=1, padx=5, pady=5, sticky='w')

        # Display info fields
        for idx, (field, value) in enumerate(info.items()):
            field_label = tk.Label(info_frame, text=f"{field}: {value}", anchor='w', justify='left')
            field_label.grid(row=idx, column=0, sticky='w')


def open_new_window(root):
    new_window = Toplevel(root)
    new_window.title("Second Window")
    app = PhotoListApp(new_window, data)
    app.pack()


# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Main Window")

    # Button to open new window
    open_window_button = tk.Button(root, text="Open New Window", command=lambda: open_new_window(root))
    open_window_button.pack(pady=20)

    root.mainloop()
