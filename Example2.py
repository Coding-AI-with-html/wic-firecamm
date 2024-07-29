import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import re
import os


# Function to load the log file and return headers and entries
def load_logfile():
    logfile_path = 'C:/Users/kreke/PycharmProjects/pythonDetect/logfile.log'
    with open(logfile_path, 'r') as file:
        lines = file.readlines()
        headers = ['Timestamp', 'Operator_values', 'Software_values', 'image_id']
        log_entries = []
        for line in lines[1:]:  # Skip the header line
            if line.strip():  # Skip empty lines
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) == len(headers):
                    log_entry = dict(zip(headers, parts))
                    log_entries.append(log_entry)
        return headers, log_entries


# Function to preload all images into a dictionary
def preload_images(log_entries):
    images = {}
    for entry in log_entries:
        image_id = entry['image_id']
        image_path = os.path.join('C:/Users/kreke/PycharmProjects/pythonDetect/wic-cam', f'{image_id}_processed.png')
        if os.path.exists(image_path):
            pil_image = Image.open(image_path)
            tk_image = ImageTk.PhotoImage(pil_image)
            images[image_id] = tk_image
    return images


class LogfileViewerApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Load the log file first to initialize headers and log entries
        self.headers, self.log_entries = load_logfile()

        self.pack(fill='both', expand=True, padx=10, pady=10)

        # Create UI elements
        self.create_widgets()
        self.images = preload_images(self.log_entries)
        self.display_log_entries()

    def create_widgets(self):
        # Create a frame for the Treeview and image display
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Create a Treeview for log entries with columns
        self.log_entries_frame = ttk.Frame(content_frame, padding="10")
        self.log_entries_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_entries_list = ttk.Treeview(self.log_entries_frame, show='headings')

        # Set up the columns and headings in the Treeview
        self.log_entries_list['columns'] = self.headers
        for header in self.headers:
            self.log_entries_list.heading(header, text=header)
            self.log_entries_list.column(header, width=150, anchor=tk.W)

        self.log_entries_list.pack(expand=True, fill=tk.BOTH)

        # Create a Label for displaying the image
        self.image_label = ttk.Label(content_frame)
        self.image_label.pack(side=tk.RIGHT, padx=10, pady=10)

        # Create a Text widget for displaying log entry information
        self.log_text = tk.Text(self, wrap=tk.WORD, height=10, width=80)
        self.log_text.pack(padx=10, pady=10, fill=tk.X)

        # Bind the selection event to display the image and info
        self.log_entries_list.bind('<<TreeviewSelect>>', lambda event: self.show_image_and_info())

    def display_log_entries(self):
        for log_entry in self.log_entries:
            log_entry_values = [log_entry[header] for header in self.headers]
            self.log_entries_list.insert('', 'end', values=log_entry_values)

    def show_image_and_info(self):
        selected_item = self.log_entries_list.selection()
        if not selected_item:
            return  # No item selected, exit the function

        selected_item = selected_item[0]
        selected_log_entry = self.log_entries_list.item(selected_item, 'values')
        image_id = selected_log_entry[3]  # Assuming image_id is the fourth column

        # Update the image label with the selected image
        if image_id in self.images:
            tk_image = self.images[image_id]
            self.image_label.config(image=tk_image)
            self.image_label.image = tk_image  # Keep a reference to avoid garbage collection
        else:
            self.image_label.config(image='', text='Image not found.')
            self.image_label.image = None

        # Display log entry information in the text widget
        log_info = "\n".join([f"{header}: {value}" for header, value in zip(self.headers, selected_log_entry)])
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, log_info)


# Function to open a new window
def open_new_window(root):
    new_window = tk.Toplevel(root)
    new_window.title("Logfile Viewer")
    app = LogfileViewerApp(new_window)
    app.pack()


# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Main Window")

    # Button to open new window
    open_window_button = tk.Button(root, text="Open Logfile Viewer", command=lambda: open_new_window(root))
    open_window_button.pack(pady=20)

    root.mainloop()