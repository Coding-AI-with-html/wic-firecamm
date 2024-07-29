import datetime
import os
import cv2
import numpy as np
from matplotlib import pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import configparser
import pystray
from pystray import MenuItem as item
from PIL import Image as PILImage
import threading
import sys
import logging
from Example2 import open_new_window
import CustomFormatter


# Set up logger
logger = logging.getLogger('customLogger')
logger.setLevel(logging.INFO)

# Create file handler and set level to info
log_file = 'logfile.log'
CustomFormatter.write_headers_if_needed(log_file)
fh = logging.FileHandler(log_file)
fh.setLevel(logging.INFO)

# Create formatter
formatter = CustomFormatter.CustomFormatter()
fh.setFormatter(formatter)

# Add handler to logger
logger.addHandler(fh)
# Global variables
horizontal_lines = [0.2, 0.4, 0.6, 0.8, 1.0]  # Default values in normalized coordinates
horizontal_lines_colors = ['blue', 'blue', 'blue', 'blue', 'blue']  # Default colors
horizontal_lines_names = ['1', '2', '3', '4', '5']  # Default names
vertical_line_positions = []
software_values = []
alert_messages = {
    'English': "Fire detected on the operator line.",
    'German': "Branddetektor auf dem Betreiber-Linie.",
    'Italian': "Detezione di fuoco sulla linea dell'operatore."
}
approx_curve = None  # To store the green curved line
resized_cropped_contour_image = None  # Initialize it as None

config = configparser.ConfigParser()
config.read('config.ini')

def get_current_language():
    return config.get('Settings', 'language', fallback='English')

# Function to update the current language setting
def set_current_language(language):
    if 'Settings' not in config:
        config.add_section('Settings')
    config.set('Settings', 'language', language)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
def minimize_to_tray():
    window.withdraw()
    image = PILImage.open("pijus/camera.png")  # Path to your icon image

    current_language = get_current_language()
    menu_text = {
        'English': {'show': 'Show', 'exit': 'Exit'},
        'German': {'show': 'Anzeigen', 'exit': 'Beenden'},
        'Italian': {'show': 'Mostra', 'exit': 'Esci'}
    }

    menu = (
        item(menu_text[current_language]['show'], on_show),
        item(menu_text[current_language]['exit'], on_exit)
    )

    icon = pystray.Icon("name", image, "Wic-FireCam", menu)
    threading.Thread(target=icon.run).start()


def on_show(icon, item):
    icon.stop()
    window.deiconify()

def on_exit(icon, item):
    icon.stop()
    window.quit()
    sys.exit()
# Function to load an image
def load_image():
    global image, left_image, right_image, resized_cropped_contour_image
    file_path = filedialog.askopenfilename()
    if not file_path:
        return

    image = cv2.imread(file_path)

    # Split the image into left and right sides
    height, width, _ = image.shape
    left_image = image[:, :width // 2].copy()  # Make sure to copy to avoid modifying original
    right_image = image[:, width // 2:].copy()  # Make sure to copy to avoid modifying original

    messagebox.showinfo("Info", "Image loaded successfully.")
    process_image(file_path)


# Function to detect fire regions
def detect_fire_regions(image):
    # Make a copy of the input image
    img_copy = image.copy()

    # Convert the image to HSV color space
    hsv = cv2.cvtColor(img_copy, cv2.COLOR_BGR2HSV)

    # Define the threshold for bright regions (typical for fire)
    lower_bright = np.array([0, 20, 225])
    upper_bright = np.array([35, 255, 255])

    # Threshold the HSV image to get only bright regions
    mask = cv2.inRange(hsv, lower_bright, upper_bright)

    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area to remove small regions and noise
    min_contour_area = 100  # Adjust this threshold based on image size and requirements
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

    return filtered_contours

# Function to calculate the Laplacian variance
def calculate_laplacian_variance(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var

def process_image(image_path):

    global resized_cropped_contour_image, vertical_line_positions, resized_cropped_contours, approx_curve, output_image, bottom_contour_full, software_values, file_name

    file_name = os.path.basename(image_path)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Initialize output_image with a default value
    output_image = None

    # Calculate the Laplacian variance for both images
    left_var = calculate_laplacian_variance(left_image)
    right_var = calculate_laplacian_variance(right_image)

    # Determine which image is better quality
    better_image = left_image if left_var > right_var else right_image

    # Analyze the resolution of the better image
    image_height, image_width = better_image.shape[:2]

    # Decide crop area based on the resolution to remove date and exit button
    bottom_crop = config.getint('Settings', 'bottom_crop')
    right_crop = config.getint('Settings', 'right_crop')
    resize_width = config.getint('Settings', 'resize_width')
    resize_height = config.getint('Settings', 'resize_height')



    # Crop the better image to remove date and exit button
    cropped_image = better_image[:image_height - bottom_crop, :image_width - right_crop]

    # Resize the cropped image
    resized_cropped_image = cv2.resize(cropped_image, (resize_width, resize_height))

    # Calculate the width of each piece
    piece_width = resize_width // 5

    # Create a list to store image pieces
    pieces = []

    for i in range(5):
        start_col = i * piece_width
        if i == 4:  # Ensure the last piece includes any remaining pixels
            end_col = resize_width
        else:
            end_col = (i + 1) * piece_width
        piece = resized_cropped_image[:, start_col:end_col]
        pieces.append(piece)

    # Plot the pieces and check for fire regions
    fig, axes = plt.subplots(1, 5, figsize=(20, 4))

    highest_points_all_pieces = []

    for i, ax in enumerate(axes):
        piece = pieces[i]
        contours = detect_fire_regions(piece)

        if contours:
            longest_contour = max(contours, key=lambda cnt: cv2.arcLength(cnt, True))

            # Find the lowest points of the contour
            lowest_points = []
            for point in longest_contour:
                if point[0][1] > piece.shape[0] * 0.61:  # Use bottom 40% of the image
                    lowest_points.append(point)

            if lowest_points:
                # Find the lowest point among the lowest points
                lowest_point = max(lowest_points, key=lambda point: point[0][1])
                lowest_y = lowest_point[0][1]

                # Draw a horizontal line starting from the bottom point of the highest point
                cv2.line(piece, (0, lowest_y), (piece.shape[1] - 1, lowest_y), (0, 255, 0), 4)

                # Print the y-coordinate of the lowest point
                normalized_y_coord = lowest_y / piece.shape[0]  # Normalize to 0-1 range
                print(f"Normalized y-coordinate of the lowest point {i + 1}:", normalized_y_coord)

                highest_points_all_pieces.append((i * piece_width, lowest_y))
        else:
            highest_points_all_pieces.append((i * piece_width, None))


    # Draw the almost straight contour on the entire image
    if highest_points_all_pieces:
        # Sort all highest points by x-coordinate
        highest_points_all_pieces = sorted(highest_points_all_pieces, key=lambda point: point[0])
        # Draw the contour on the original image
        bottom_contour_full = []
        for point in highest_points_all_pieces:
            if point[1] is not None:
                bottom_contour_full.append([point[0], point[1]])
        bottom_contour_full = np.array(bottom_contour_full, dtype=np.int32)
        #print("Bots contour:", bottom_contour_full)
        # Print the normalized y-coordinates of the bottom contour
        normalized_y_coords = [y / resized_cropped_image.shape[0] for x, y in bottom_contour_full]
       #print("Normalized y-coordinates of the bottom contour:", normalized_y_coords)

        software_values = []
        for x, y in highest_points_all_pieces:
            if y is not None:
                normalized_y_coord = y / resized_cropped_image.shape[0]
                round_num = round(normalized_y_coord,2)
                software_values.append(round_num)
            else:
                software_values.append(None)
        # Log example data
        data = {
            "timestamp": timestamp,
            "Software_values": software_values,
            "Operator_values": horizontal_lines,
            "image_id": file_name,
        }

        logger.info(data)


    # Detect fire regions in the resized better image
    resized_cropped_contours = detect_fire_regions(resized_cropped_image)

    # Create an output image to draw results
    resized_cropped_contour_image = resized_cropped_image.copy()

    # Draw 4 vertical red lines at equal intervals using normalized coordinates
    num_lines = 4
    vertical_line_positions = [int(i * (resized_cropped_image.shape[1] / (num_lines + 1))) for i in range(1, num_lines + 1)]

    update_plot()


# Function to update the plot when user inputs values for horizontal lines
def update_plot():
    global resized_cropped_contour_image
    if resized_cropped_contour_image is None:
        # passing error could be added messagebox.showwarning("Warning", "No image has been processed yet.")
        return
    display_image(resized_cropped_contour_image)

# Function to display image with x and y axes and adjustable horizontal lines in the GUI
def display_image(image):
    new_directory_image_save = config.get('Settings', 'directory_image_save')
    # Convert the image to RGB
    global file_name
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(image_rgb)

    # Create a figure for the matplotlib plot
    fig, ax = plt.subplots()
    ax.imshow(image_pil)
    ax.set_xticks([0, 200, 400, 600, 800, 1000])
    ax.set_xticklabels(['0', '0.2', '0.4', '0.6', '0.8', '1'])
    ax.set_yticks([0, 200, 400, 600, 800, 1000])
    ax.set_yticklabels(['0', '0.2', '0.4', '0.6', '0.8', '1'])
    ax.set_xlim(0, 1000)
    ax.set_ylim(1000, 0)  # Inverted y-axis
    ax.xaxis.set_ticks_position('top')
    ax.xaxis.set_label_position('top')
    ax.set_xlabel('X-axis')
    ax.set_ylabel('Y-axis')

    # Draw vertical lines
    for x in vertical_line_positions:
        ax.axvline(x=x, color='red', linestyle='-', linewidth=2)

    # Draw adjustable horizontal lines between vertical lines
    segment_width = vertical_line_positions[1] - vertical_line_positions[0]
    alert_shown = False
    for idx, (y, color, name) in enumerate(zip(horizontal_lines, horizontal_lines_colors, horizontal_lines_names)):
        y_pos = int(y * 1000)  # Scale normalized value to image dimension
        #in needs to log the image name, horizontal_lines values, normalized_y_coords values and timestamp in one line
        # Determine start and end x positions for the horizontal lines
        if idx == 0:
            start_x = 0
        else:
            start_x = vertical_line_positions[idx - 1]

        if idx < len(vertical_line_positions):
            end_x = vertical_line_positions[idx]
        else:
            end_x = 1000

        current_language = get_current_language()
        ax.plot([start_x, end_x], [y_pos, y_pos], color=color, linewidth=2)
        ax.text(start_x, y_pos, name, color=color, fontsize=10, ha='right')
        print(start_x, end_x, y_pos)


    # Embed the plot in the tkinter window
    for widget in frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack()

    if not os.path.exists(new_directory_image_save):
        os.makedirs(new_directory_image_save)


    plot_path = os.path.join(new_directory_image_save, f"{file_name}_processed.png")
    plt.savefig(plot_path)

    # Close the figure to free up memory
    plt.close(fig)

def check_for_alarms():
    global horizontal_lines, software_values, alert_messages

    for horizontal_line, software_value in zip(horizontal_lines, software_values):
        if software_value is not None and abs(horizontal_line - software_value) < 0.01:  # Adjust tolerance as needed
            current_language = get_current_language()
            message = alert_messages.get(current_language, "Alarm triggered.")
            messagebox.showwarning("Alarm", message)
            break  # Stop checking after the first alarm is triggered

# Function to handle language button press
def change_language(language):
    set_current_language(language)
    update_ui_language(language)

def update_ui_language(language):
    if language == 'English':
        labels_text = ['Horizontal Line A:', 'Horizontal Line B:', 'Horizontal Line C:', 'Horizontal Line D:', 'Horizontal Line E:']
        button_load.config(text='Load Image')
        button_minimize.config(text='Minimize Application')
        button_apply_entries.config(text='Apply Entry Values')
    elif language == 'German':
        labels_text = ['Horizontale Linie A:', 'Horizontale Linie B:', 'Horizontale Linie C:', 'Horizontale Linie D:',  'Horizontale Linie E:']
        button_load.config(text='Bild Laden')
        button_minimize.config(text='Anwendung minimieren')
        button_apply_entries.config(text='Eintragswerte Anwenden')
    elif language == 'Italian':
        labels_text = ['Linea Orizzontale A:', 'Linea Orizzontale B:', 'Linea Orizzontale C:', 'Linea Orizzontale D:',  'Linea Orizzontale E:']
        button_load.config(text='Carica Immagine')
        button_minimize.config(text='Riduci al minimo l\'applicazione')
        button_apply_entries.config(text='Applica Valori Inseriti')

    for i, label in enumerate(labels):
        label.config(text=labels_text[i])

# Function to check if a horizontal line intersects with the approximated curve

# Function to update horizontal line heights from sliders
def update_heights(*args):
    global horizontal_lines
    horizontal_lines = [slider.get() / 100 for slider in sliders]
    for i, entry_height in enumerate(entries_height):
        entry_height.delete(0, tk.END)
        entry_height.insert(0, f"{horizontal_lines[i]:.2f}")
    update_plot()
    check_for_alarms()

def set_line_color(index, color):
    horizontal_lines_colors[index] = color
    update_plot()
# Function to apply values from entries
def apply_entry_values():
    global horizontal_lines
    horizontal_lines = [float(entry_height.get()) for entry_height in entries_height]
    update_plot()
    check_for_alarms()


# Create the main window
window = tk.Tk()
window.title("Wic-FireCam")

# Create a frame to hold the preloaded photos
photo_frame = tk.Frame(window, bg='black', height=10)
photo_frame.grid(row=0, column=0, columnspan=5, sticky='nsew')

# Configure the columns in the photo_frame to expand equally
photo_frame.columnconfigure([0, 1, 2], weight=1)

# Load the preloaded photos and place them in the grid
photo1 = Image.open("icons/newIcon.png")
photo1 = photo1.resize((150, 100))
photo1 = ImageTk.PhotoImage(photo1)
label1 = tk.Label(photo_frame, image=photo1, borderwidth=2, relief='solid', bg='black')
label1.image = photo1
label1.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)

photo2 = Image.open("icons/fireIcon2.JPG")
photo2 = photo2.resize((100, 100))
photo2 = ImageTk.PhotoImage(photo2)
label2 = tk.Label(photo_frame, image=photo2, borderwidth=2, relief='solid', bg='black')
label2.image = photo2
label2.grid(row=0, column=1, sticky='nsew', padx=2, pady=2)

photo3 = Image.open("icons/tryicon.png")
photo3 = photo3.resize((100, 100))
photo3 = ImageTk.PhotoImage(photo3)
label3 = tk.Label(photo_frame, image=photo3, borderwidth=2, relief='solid', bg='black')
label3.image = photo3
label3.grid(row=0, column=2, sticky='nsew', padx=2, pady=2)

# Create a button to load an image
button_load = tk.Button(window, text="Load Image", command=load_image)
button_load.grid(row=12, column=0, columnspan=1, pady=10)

button_minimize = tk.Button(window, text="Minimize ", command=minimize_to_tray)
button_minimize.grid(row=12, column=1, columnspan=1, pady=10)

# Create a frame to hold the plot
frame = tk.Frame(window)
frame.grid(row=1, column=0, columnspan=4, sticky='nsew')

# Create sliders and entries to input the position of horizontal lines
sliders = []
entries_height = []
labels = []
labels_text = ['Horizontal Line A:', 'Horizontal Line B:', 'Horizontal Line C:', 'Horizontal Line D:', 'Horizontal Line E:']
for i in range(5):
    label_name = tk.Label(window, text=labels_text[i])
    label_name.grid(row=i+2, column=0, padx=5, pady=5, sticky='w')
    labels.append(label_name)

    slider = tk.Scale(window, from_=0, to=100, orient='horizontal', command=update_heights)
    slider.set(horizontal_lines[i] * 100)
    slider.grid(row=i+2, column=1, columnspan=3, padx=5, pady=5, sticky='ew')
    sliders.append(slider)

    entry_height = tk.Entry(window)
    entry_height.insert(0, f"{horizontal_lines[i]:.2f}")
    entry_height.grid(row=i+2, column=4, padx=5, pady=5, sticky='ew')
    entries_height.append(entry_height)

# Create entries for horizontal line colors and names
entries_color = []
entries_name = []
color_buttons = []
color_options = ['green', 'yellow', 'blue', '#C4A484', 'orange']  # Example colors
for i in range(5):

    entry_name = tk.Entry(window)
    entry_name.insert(0, horizontal_lines_names[i])
    entry_name.config(state='readonly')  # or 'disabled'
    entry_name.grid(row=i + 7, column=0, padx=5, pady=5, sticky='w')
    entries_name.append(entry_name)

    button_frame = tk.Frame(window)

    button_frame.grid(row=i + 7, column=1, columnspan=3, padx=5, pady=5, sticky='ew')

    for color in color_options:

        color_button = tk.Button(button_frame, bg=color, width=2, command=lambda idx=i, col=color: set_line_color(idx, col))

        color_button.pack(side='left', padx=2)

        color_buttons.append(color_button)


# Create a button to apply the values from entries
button_apply_entries = tk.Button(window, text="Apply Entry Values", command=apply_entry_values)
button_apply_entries.grid(row=12, column=2, columnspan=2, pady=10)

# Create language change buttons
button_english = tk.Button(window, text="English", command=lambda: change_language('English'))
button_english.grid(row=13, column=1, pady=10)

button_german = tk.Button(window, text="German", command=lambda: change_language('German'))
button_german.grid(row=13, column=2, pady=10)

button_italian = tk.Button(window, text="Italian", command=lambda: change_language('Italian'))
button_italian.grid(row=13, column=3, pady=10)

# Create a label to display the image
label_image = tk.Label(window)
label_image.grid(row=1, column=0, columnspan=4)

def initialize_ui():
    current_language = get_current_language()
    update_ui_language(current_language)


# Create a button to open another window

open_button = tk.Button(window, text="Open History Window", command=lambda: open_new_window(window))
open_button.grid(row=13, column=0, pady=10)
window_resizable_width = config.getboolean('Window', 'resizable_width')
window_resizable_height = config.getboolean('Window', 'resizable_height')
window.resizable(window_resizable_width, window_resizable_height)
initialize_ui()
window.mainloop()