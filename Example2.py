import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import re
import os
from datetime import datetime
from tkcalendar import DateEntry

logfile_path = 'C:/Users/kreke/PycharmProjects/pythonDetect/logfile.log'
original_logfile_path = 'C:/Users/kreke/PycharmProjects/pythonDetect/logfile.log'

# Function to load the log file and return headers and entries
def load_logfile(filepath):
    headers = ['Timestamp', 'Num_Tracks', 'Operator_values', 'Software_values', 'Quality', 'Image_ID', 'View']
    log_entries = []

    if not os.path.exists(filepath):
        return headers, log_entries

    with open(filepath, 'r') as file:
        lines = file.readlines()
        for line in lines[1:]:  # Skip the header line
            if line.strip():  # Skip empty lines
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) == len(headers):
                    log_entry = dict(zip(headers, parts))
                    log_entries.append(log_entry)
    return headers, log_entries


class LogfileViewerApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Load the log file first to initialize headers and log entries
        self.headers, self.log_entries = load_logfile(logfile_path)

        self.pack(fill='both', expand=True, padx=10, pady=10)

        # Create UI elements
        self.create_widgets()
        # self.images = preload_images(self.log_entries)

        # Display log entries based on current date and time
        self.set_default_filters()
        self.filter_log_entries()

    def create_widgets(self):
        # Create a frame for the Treeview and image display
        content_frame = ttk.Frame(self)
        content_frame.pack(fill='both', expand=True)

        # Frame for time filter widgets
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, pady=10)

        # Button to choose folder
        choose_folder_button = ttk.Button(filter_frame, text="Choose Folder", command=self.choose_folder)
        choose_folder_button.grid(row=0, column=0, padx=5, pady=5)

        # Start Date and Time
        ttk.Label(filter_frame, text="Start Date:").grid(row=1, column=0, padx=5)
        self.start_date_entry = DateEntry(filter_frame, width=20, background='darkblue', foreground='white', borderwidth=2)
        self.start_date_entry.grid(row=1, column=1, padx=5)

        ttk.Label(filter_frame, text="Start Hour:").grid(row=1, column=2, padx=5)
        self.start_hour_combobox = ttk.Combobox(filter_frame, values=[f"{i:02}" for i in range(24)], width=5)
        self.start_hour_combobox.grid(row=1, column=3, padx=5)
        self.start_hour_combobox.set("00")  # Default to 00

        ttk.Label(filter_frame, text="Start Minute:").grid(row=1, column=4, padx=5)
        self.start_minute_combobox = ttk.Combobox(filter_frame, values=[f"{i:02}" for i in range(60)], width=5)
        self.start_minute_combobox.grid(row=1, column=5, padx=5)
        self.start_minute_combobox.set("00")  # Default to 00

        # End Date and Time
        ttk.Label(filter_frame, text="End Date:").grid(row=2, column=0, padx=5)
        self.end_date_entry = DateEntry(filter_frame, width=20, background='darkblue', foreground='white', borderwidth=2)
        self.end_date_entry.grid(row=2, column=1, padx=5)

        ttk.Label(filter_frame, text="End Hour:").grid(row=2, column=2, padx=5)
        self.end_hour_combobox = ttk.Combobox(filter_frame, values=[f"{i:02}" for i in range(24)], width=5)
        self.end_hour_combobox.grid(row=2, column=3, padx=5)
        self.end_hour_combobox.set("23")  # Default to 23

        ttk.Label(filter_frame, text="End Minute:").grid(row=2, column=4, padx=5)
        self.end_minute_combobox = ttk.Combobox(filter_frame, values=[f"{i:02}" for i in range(60)], width=5)
        self.end_minute_combobox.grid(row=2, column=5, padx=5)
        self.end_minute_combobox.set("59")  # Default to 59

        # Buttons: Filter, Reset, Set to Current Date/Time
        filter_button = ttk.Button(filter_frame, text="Filter", command=self.filter_log_entries)
        filter_button.grid(row=3, column=0, columnspan=3, pady=5)

        reset_button = ttk.Button(filter_frame, text="See whole pictures", command=self.reset_filters)
        reset_button.grid(row=3, column=3, columnspan=2, pady=5)

        current_datetime_button = ttk.Button(filter_frame, text="Set to Current Date/Time", command=self.set_to_current_datetime)
        current_datetime_button.grid(row=3, column=5, columnspan=1, pady=5)

        reset_folder_button = ttk.Button(filter_frame, text="Reset folder",command=self.reset_default_folder)
        reset_folder_button.grid(row=3, column=6, columnspan=1, pady=5)

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

    def choose_folder(self):
        global logfile_path

        # Open a dialog to select the folder
        folder_selected = filedialog.askdirectory()

        if folder_selected:
            # Find the first file with a .log extension in the selected folder
            for file_name in os.listdir(folder_selected):
                if file_name.endswith(".log"):
                    logfile_path = os.path.join(folder_selected, file_name)
                    break
            else:
                # If no .log file is found, you might want to handle this case
                messagebox.showinfo("Info", "No .log file found in the selected folder.")
                return

            # Assuming load_logfile() is a function that loads the logfile data
            self.headers, self.log_entries = load_logfile(logfile_path)
            self.display_log_entries()
            self.reset_filters()

    def set_default_filters(self):
        # Set the start and end dates and times to current date and time
        now = datetime.now()
        self.start_date_entry.set_date(now.date())
        self.end_date_entry.set_date(now.date())

    def set_to_current_datetime(self):
        # Update the filters to the current date and time
        self.set_default_filters()
        self.filter_log_entries()

    def reset_default_folder(self):
        global logfile_path, original_logfile_path
        if logfile_path != original_logfile_path:
            logfile_path = original_logfile_path
            self.headers, self.log_entries = load_logfile(logfile_path)
            self.display_log_entries()
            self.reset_filters()

    def display_log_entries(self, entries=None):
        if entries is None:
            entries = self.log_entries

        self.log_entries_list.delete(*self.log_entries_list.get_children())
        for log_entry in entries:
            log_entry_values = [log_entry[header] for header in self.headers]
            self.log_entries_list.insert('', 'end', values=log_entry_values)

    def filter_log_entries(self):
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        start_hour = self.start_hour_combobox.get()
        start_minute = self.start_minute_combobox.get()
        end_hour = self.end_hour_combobox.get()
        end_minute = self.end_minute_combobox.get()

        try:
            start_time = datetime.strptime(f"{start_date} {start_hour}:{start_minute}:00", "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(f"{end_date} {end_hour}:{end_minute}:00", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please ensure all fields are filled correctly.")
            return

        filtered_entries = [
            entry for entry in self.log_entries
            if start_time <= datetime.strptime(entry['Timestamp'], "%Y-%m-%d %H:%M:%S") <= end_time
        ]

        self.display_log_entries(filtered_entries)

    def reset_filters(self):
        self.set_default_filters()
        self.display_log_entries()


# Function to open a new window
def open_new_window(root):
    new_window = tk.Toplevel(root)
    new_window.title("History Window")
    app = LogfileViewerApp(new_window)

    app.pack()




