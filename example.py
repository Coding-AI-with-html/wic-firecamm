import datetime
import os
import shutil
import cv2
import numpy as np
from matplotlib import pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import configparser
import pystray
from pystray import MenuItem as item
from PIL import Image as PILImage
import threading
import sys
import logging
from Example2 import open_new_window
from AreaSelection import RectangleCropper
import CustomFormatter
import time

def get_config_path():
    if getattr(sys, 'frozen', False):  # Check if the program is running as a PyInstaller bundle
        base_path = sys._MEIPASS  # _MEIPASS is where PyInstaller bundles the files
        return os.path.join(base_path, 'configuration', 'config.ini')
    else:
        base_path = os.path.dirname(__file__)  # Development environment
        return os.path.join(base_path, 'config.ini')

# Read configuration
config = configparser.ConfigParser()
config_path = get_config_path()
config.read(config_path)

# Set up logger
logger = logging.getLogger('customLogger')
logger.setLevel(logging.INFO)


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
image = None

def move_png_files():
    while True:
        current_time = datetime.datetime.now().time()
        if current_time.hour == 23 and current_time.minute == 58:
            today = datetime.datetime.now().strftime('%d.%m.%Y')
            folder_path = os.path.join(config.get('Settings', 'root_image'), today)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            # Move logfile with the current date to the created folder
            log_file_name = f'logfile_{today}.log'
            log_file_path = os.path.join(config.get('Settings', 'root_image'), log_file_name)
            if os.path.exists(log_file_path):
                shutil.move(log_file_path, folder_path)

            for root, dirs, files in os.walk(config.get('Settings', 'root_image')):
                for file in files:
                    if file.endswith('.png'):
                        shutil.move(os.path.join(root, file), folder_path)
            time.sleep(60)  # wait for 1 minute to avoid infinite loop
        else:
            time.sleep(1)  # wait for 1 second and check again

# Run the function in a separate thread to avoid blocking the main thread
threading.Thread(target=move_png_files).start()


def create_log_file(data):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    base_directory = config.get('Settings', 'root_image')
    folder_path = os.path.join(base_directory, today)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    log_file = os.path.join(folder_path, f'logfile_{today}.log')
    CustomFormatter.write_headers_if_needed(log_file)
    logger = logging.getLogger('customLogger')
    logger.handlers.clear()  # Remove all existing handlers
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    formatter = CustomFormatter.CustomFormatter()
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info(data)


def create_folder_for_today(plot, filename):
    # Get the current date and format it as 'DD-MM'
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    base_dir = config.get('Settings', 'root_image')

    # Create the full path for the folder to be created
    folder_path = os.path.join(base_dir, today)

    # Check if the folder already exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    plot_path = os.path.join(folder_path, f"{filename}")
    plot.savefig(plot_path)


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
    image_min = resource_path('icons/camera.png')
    image = PILImage.open(image_min)  # Path to your icon image

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
    os._exit(0)
# Function to load an image
def load_image():
    global image, resized_cropped_contour_image
    file_path = filedialog.askopenfilename()
    if not file_path:
        return

    image = cv2.imread(file_path)

    messagebox.showinfo("Info", "Image loaded successfully.")
    process_image_with_multiple_sub_images(file_path)


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


def process_image_with_multiple_sub_images(image_path):
    global resized_cropped_contour_image, vertical_line_positions, resized_cropped_contours, approx_curve, output_image, bottom_contour_full, software_values, file_name

    file_name = os.path.basename(image_path)
    file_name_no_ext, file_ext = os.path.splitext(file_name)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    output_image = None

    image = cv2.imread(image_path)
    if image is None:
        print(f"Error loading image {file_name}")
        return

    # Read the rectangles' coordinates from the config file
    config.read('config.ini')
    rectangles = config.items('Cropped_Rectangles')
    rectangles = [(int(coords.split(',')[0][1:]), int(coords.split(',')[1]), int(coords.split(',')[2]), int(coords.split(',')[3][:-1])) for key, coords in rectangles]
    print("Recs: ", rectangles)

    resize_width = config.getint('Settings', 'resize_width')
    resize_height = config.getint('Settings', 'resize_height')
    number_of_tracks = config.getint('Settings', 'number_of_tracks')

    max_variance = 100.0

    for idx, (x1, y1, x2, y2) in enumerate(rectangles):
        # Crop the rectangle from the image
        cropped_image = image[y1:y2, x1:x2]
        resized_cropped_image = cv2.resize(cropped_image, (resize_width, resize_height))

        laplacian_variance = calculate_laplacian_variance(resized_cropped_image)
        quality = round(min(laplacian_variance / max_variance, 1.0), 2)  # Round quality to 2 decimal places

        piece_width = resize_width // number_of_tracks
        pieces = [resized_cropped_image[:, i * piece_width:(i + 1) * piece_width] for i in range(number_of_tracks)]

        fig, axes = plt.subplots(1, number_of_tracks, figsize=(20, 4))
        highest_points_all_pieces = []

        for i, ax in enumerate(axes):
            piece = pieces[i]
            contours = detect_fire_regions(piece)

            if contours:
                longest_contour = max(contours, key=lambda cnt: cv2.arcLength(cnt, True))
                lowest_points = [point for point in longest_contour if point[0][1] > piece.shape[0] * 0.61]

                if lowest_points:
                    lowest_point = max(lowest_points, key=lambda point: point[0][1])
                    lowest_y = lowest_point[0][1]
                    cv2.line(piece, (0, lowest_y), (piece.shape[1] - 1, lowest_y), (0, 255, 0), 4)
                    normalized_y_coord = lowest_y / piece.shape[0]
                    highest_points_all_pieces.append((i * piece_width, lowest_y))
                else:
                    highest_points_all_pieces.append((i * piece_width, None))
            else:
                highest_points_all_pieces.append((i * piece_width, None))

        software_values = []
        for point in highest_points_all_pieces:
            if point[1] is not None:
                normalized_y_coord = point[1] / resized_cropped_image.shape[0]
                round_num = round(normalized_y_coord, 2)
                software_values.append(round_num)
            else:
                software_values.append(None)

        view = f"{file_name_no_ext}_#{idx + 1}{file_ext}" if len(rectangles) > 1 else f"{file_name_no_ext}_#{idx + 1}{file_ext}"
        data = {
            "timestamp": timestamp,
            'num_tracks': number_of_tracks,
            "Software_values": software_values,
            "Operator_values": horizontal_lines,  # Replace with your actual horizontal lines data if available
            "quality": quality,  # Ensure quality is logged with two decimal places
            "image_id": file_name,
            "view": view
        }

        create_log_file(data)

        resized_cropped_contour_image = resized_cropped_image.copy()

        if number_of_tracks > 1:
            num_lines = number_of_tracks - 1
        else:
            num_lines = number_of_tracks

        vertical_line_positions = [int(i * (resized_cropped_image.shape[1] / (num_lines + 1))) for i in range(1, num_lines + 1)]

        save_view_as_image(resized_cropped_image, vertical_line_positions, view)

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



    # Embed the plot in the tkinter window
    for widget in frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack()

    # Close the figure to free up memory
    plt.close(fig)


def save_view_as_image(image, vertical_lines, view):
    global horizontal_lines, horizontal_lines_colors, horizontal_lines_names
    # Convert the image to RGB
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
    for x in vertical_lines:
        ax.axvline(x=x, color='red', linestyle='-', linewidth=2)

    # Draw adjustable horizontal lines between vertical lines
    segment_width = vertical_lines[1] - vertical_lines[0]
    alert_shown = False
    for idx, (y, color, name) in enumerate(zip(horizontal_lines, horizontal_lines_colors, horizontal_lines_names)):
        y_pos = int(y * 1000)  # Scale normalized value to image dimension

        # Determine start and end x positions for the horizontal lines
        if idx == 0:
            start_x = 0
        else:
            start_x = vertical_lines[idx - 1]

        if idx < len(vertical_lines):
            end_x = vertical_lines[idx]
        else:
            end_x = 1000

        current_language = get_current_language()
        ax.plot([start_x, end_x], [y_pos, y_pos], color=color, linewidth=2)
        ax.text(start_x, y_pos, name, color=color, fontsize=10, ha='right')

    # Save the plot
    create_folder_for_today(fig, view)

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
        button_config.config(text="Configuration")
        open_button.config(text="Open History Window")
    elif language == 'German':
        labels_text = ['Horizontale Linie A:', 'Horizontale Linie B:', 'Horizontale Linie C:', 'Horizontale Linie D:',  'Horizontale Linie E:']
        button_load.config(text='Bild Laden')
        button_minimize.config(text='Anwendung minimieren')
        button_apply_entries.config(text='Eintragswerte Anwenden')
        button_config.config(text="Konfiguration")
        open_button.config(text="Öffnen Sie das Verlaufsfenster")
    elif language == 'Italian':
        labels_text = ['Linea Orizzontale A:', 'Linea Orizzontale B:', 'Linea Orizzontale C:', 'Linea Orizzontale D:',  'Linea Orizzontale E:']
        button_load.config(text='Carica Immagine')
        button_minimize.config(text='Riduci al minimo l\'applicazione')
        button_apply_entries.config(text='Applica Valori Inseriti')
        button_config.config(text="Configurazione")
        open_button.config(text="Apri la finestra della cronologia")

    for i, label in enumerate(labels):
        label.config(text=labels_text[i])


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

def open_original_image():
    global image

    if image is not None:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        photo = Image.fromarray(image_rgb)

        # Get the screen width and height
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # Calculate the scale factor to make the image fit in fullscreen
        scale_factor = min(screen_width / photo.width, screen_height / photo.height)

        # Resize the image using the scale factor
        new_width = int(photo.width * scale_factor)
        new_height = int(photo.height * scale_factor)

        # Create a photo image for Tkinter
        resized_photo = photo.resize((new_width, new_height))
        resized_photo_tk = ImageTk.PhotoImage(resized_photo)

        window_original_image = tk.Toplevel()
        window_original_image.title("Area Of Interest Picking")
        window_original_image.geometry(f"{new_width}x{new_height+150}")

        canvas = tk.Canvas(window_original_image, width=new_width, height=new_height, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, anchor=tk.NW, image=resized_photo_tk)

        # Allow window to be resizable
        window_original_image.resizable(True, True)

        # Keep a reference of the resized photo to prevent garbage collection
        label_original_image = tk.Label(window_original_image, image=resized_photo_tk)
        label_original_image.image = resized_photo_tk

        # Add cropping functionality
        rectangles = []
        current_rectangle = None

        # Drop-down menu for selecting the number of rectangles
        rectangle_count_var = tk.IntVar(value=3)  # Default to 3
        rectangle_count_menu = tk.OptionMenu(window_original_image, rectangle_count_var, 1, 2, 3, 4, 5, 6)
        rectangle_count_menu.pack(side=tk.TOP)

        def on_button_press(event):
            nonlocal current_rectangle
            if len(rectangles) < rectangle_count_var.get():  # Limit based on user selection
                current_rectangle = [event.x, event.y, event.x, event.y]
                rectangles.append(current_rectangle)
                redraw_rectangles()

        def on_mouse_drag(event):
            nonlocal current_rectangle
            if current_rectangle:
                current_rectangle[2] = event.x
                current_rectangle[3] = event.y
                redraw_rectangles()

        def on_button_release(event):
            nonlocal current_rectangle
            if current_rectangle:
                current_rectangle = None

        def redraw_rectangles():
            canvas.delete("rect")
            for i, rect in enumerate(rectangles):
                canvas.create_rectangle(rect[0], rect[1], rect[2], rect[3], outline="blue", tags="rect")
                canvas.create_text(rect[0], rect[1], text=f"Rect {i+1}", anchor=tk.NW, fill="blue")

        def reset_selection():
            nonlocal rectangles, current_rectangle
            rectangles.clear()
            current_rectangle = None
            canvas.delete("all")  # Clear the canvas
            canvas.create_image(0, 0, anchor=tk.NW, image=resized_photo_tk)  # Redraw the image
            redraw_rectangles()  # Redraw the rectangles (which are now empty)


        def close_window():
            window_original_image.destroy()

        def crop_rectangles():
            if len(rectangles) == 0:
                messagebox.showwarning("No Views", "Please pick view first.")
                return

            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            config.read('config.ini')

            if 'Cropped_Rectangles' not in config:
                config.add_section('Cropped_Rectangles')

            # Remove excess rectangles from config file
            for i in range(len(rectangles), len(config.options('Cropped_Rectangles'))):
                config.remove_option('Cropped_Rectangles', f'Rectangle_{i + 1}')

            for i, rect in enumerate(rectangles):
                x1, y1, x2, y2 = map(int, rect)
                crop_rectangle = (
                    int(x1 * photo.width / new_width),
                    int(y1 * photo.height / new_height),
                    int(x2 * photo.width / new_width),
                    int(y2 * photo.height / new_height)
                )

                cropped_image = photo.crop(crop_rectangle)
                # cropped_image.save(f"cropped_rectangle_{i + 1}.png")

                config.set('Cropped_Rectangles', f'Rectangle_{i + 1}', str(crop_rectangle))

            with open('config.ini', 'w') as configfile:
                config.write(configfile)

            messagebox.showinfo("Success",
                                f"Cropped {len(rectangles)} saved coordinates to config.ini")

        canvas.bind("<ButtonPress-1>", on_button_press)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_button_release)

        reset_button = tk.Button(window_original_image, text="Reset Selection", command=reset_selection)
        reset_button.pack(side=tk.BOTTOM, padx=10, pady=10)

        crop_button = tk.Button(window_original_image, text="Save Views", command=crop_rectangles)
        crop_button.pack(side=tk.BOTTOM, padx=10, pady=10)

        close_button = tk.Button(window_original_image, text="Close Configuration", command=close_window)
        close_button.pack()

        window_original_image.mainloop()

    else:
        messagebox.showinfo("Info", "No image has been loaded yet.")


def config_area():
    global entries_config
    entries_config = []
    open_original_image()  # Open the original image in a new window

def resource_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



image_path = resource_path('icons/newIcon.png')
# Load the preloaded photos and place them in the grid
photo1 = Image.open(image_path)
photo1 = photo1.resize((150, 100))
photo1 = ImageTk.PhotoImage(photo1)
label1 = tk.Label(photo_frame, image=photo1, borderwidth=2, relief='solid', bg='black')
label1.image = photo1
label1.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
image_path2 = resource_path('icons/fireIcon2.JPG')
photo2 = Image.open(image_path2)
photo2 = photo2.resize((100, 100))
photo2 = ImageTk.PhotoImage(photo2)
label2 = tk.Label(photo_frame, image=photo2, borderwidth=2, relief='solid', bg='black')
label2.image = photo2
label2.grid(row=0, column=1, sticky='nsew', padx=2, pady=2)
image_path3 = resource_path('icons/tryicon.png')
photo3 = Image.open(image_path3)
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
button_apply_entries.grid(row=12, column=2, columnspan=1, pady=10)

button_config = tk.Button(window, text="Configuration", command=config_area)
button_config.grid(row=12, column=3, columnspan=2, pady=10)

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

def CloseAll():
    window.quit()


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
