import cv2
import numpy as np
from matplotlib import pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Global variables
horizontal_lines = [0.2, 0.4, 0.6, 0.8, 1.0]  # Default values in normalized coordinates
horizontal_lines_colors = ['blue', 'blue', 'blue', 'blue', 'blue']  # Default colors
horizontal_lines_names = ['Line A', 'Line B', 'Line C', 'Line D', 'Line E']  # Default names
vertical_line_positions = []
approx_curve = None  # To store the green curved line

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
    process_image()

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

# Function to process the image
def process_image():
    global resized_cropped_contour_image, vertical_line_positions, resized_cropped_contours, approx_curve

    # Calculate the Laplacian variance for both images
    left_var = calculate_laplacian_variance(left_image)
    right_var = calculate_laplacian_variance(right_image)

    # Determine which image is better quality
    better_image = left_image if left_var > right_var else right_image

    # Analyze the resolution of the better image
    image_height, image_width = better_image.shape[:2]

    # Decide crop area based on the resolution to remove date and exit button
    bottom_crop = 150
    right_crop = 100

    # Crop the better image to remove date and exit button
    cropped_image = better_image[:image_height - bottom_crop, :image_width - right_crop]

    # Detect fire regions in the cropped better image
    cropped_contours = detect_fire_regions(cropped_image)

    # Resize the cropped image to 1024x1024
    resized_cropped_image = cv2.resize(cropped_image, (1024, 1024))

    # Draw a line at the bottom of the resized image
    cv2.line(resized_cropped_image, (0, resized_cropped_image.shape[0]),
             (resized_cropped_image.shape[1], resized_cropped_image.shape[0]),
             (0, 255, 0), thickness=3)

    # Detect fire regions in the resized better image
    resized_cropped_contours = detect_fire_regions(resized_cropped_image)

    # Create an output image to draw results
    resized_cropped_contour_image = resized_cropped_image.copy()

    # Draw 4 vertical red lines at equal intervals using normalized coordinates
    num_lines = 4
    vertical_line_positions = [int(i * (resized_cropped_image.shape[1] / (num_lines + 1))) for i in
                               range(1, num_lines + 1)]

    for x in vertical_line_positions:
        cv2.line(resized_cropped_contour_image, (x, 0), (x, resized_cropped_image.shape[0]),
                 (0, 0, 255), thickness=3)

    # Find the longest contour
    if resized_cropped_contours:
        longest_contour = max(resized_cropped_contours, key=lambda cnt: cv2.arcLength(cnt, True))
    else:
        longest_contour = None

    # Draw a curve that approximates the bottom of the longest contour
    if longest_contour is not None:
        # Extract the bottom half of the contour points
        bottom_half_points = []
        for point in longest_contour:
            if point[0][1] > resized_cropped_image.shape[0] // 1.6:
                bottom_half_points.append(point)

        bottom_half_points = np.array(bottom_half_points)

        if len(bottom_half_points) > 0:
            epsilon = 0.01 * cv2.arcLength(bottom_half_points, True)
            approx_curve = cv2.approxPolyDP(bottom_half_points, epsilon, closed=False)

            # Draw the approximated curve
            cv2.polylines(resized_cropped_contour_image, [approx_curve], isClosed=False,
                          color=(0, 255, 0), thickness=3)

    update_plot()

# Function to update the plot when user inputs values for horizontal lines
def update_plot():
    display_image(resized_cropped_contour_image)

# Function to display image with x and y axes and adjustable horizontal lines in the GUI
def display_image(image):
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
    for x in vertical_line_positions:
        ax.axvline(x=x, color='red', linestyle='-', linewidth=2)

    # Draw adjustable horizontal lines between vertical lines
    segment_width = vertical_line_positions[1] - vertical_line_positions[0]
    alert_shown = False
    for idx, (y, color, name) in enumerate(zip(horizontal_lines, horizontal_lines_colors, horizontal_lines_names)):
        y_pos = int(y * 1000)  # Scale normalized value to image dimension

        # Determine start and end x positions for the horizontal lines
        if idx == 0:
            start_x = 0
        else:
            start_x = vertical_line_positions[idx - 1]

        if idx < len(vertical_line_positions):
            end_x = vertical_line_positions[idx]
        else:
            end_x = 1000

        ax.plot([start_x, end_x], [y_pos, y_pos], color=color, linewidth=2)
        ax.text(start_x, y_pos, name, color=color, fontsize=10, ha='right')

        # Check for intersection with the approximated curve
        if check_intersection_with_curve(start_x, end_x, y_pos):
            if not alert_shown:
                messagebox.showinfo("Alert", "Fire detected on the operator line.")
                alert_shown = True

    # Embed the plot in the tkinter window
    for widget in frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack()

    # Close the figure to free up memory
    plt.close(fig)

# Function to check if a horizontal line intersects with the approximated curve
def check_intersection_with_curve(start_x, end_x, y_pos):
    if approx_curve is None:
        return False

    for i in range(len(approx_curve) - 1):
        x1, y1 = approx_curve[i][0]
        x2, y2 = approx_curve[i + 1][0]

        # Check if the horizontal line is within the x bounds of the curve segment
        if min(x1, x2) <= end_x and max(x1, x2) >= start_x:
            # Calculate the y value of the curve at the start and end x positions of the horizontal line
            y_at_start_x = interpolate_y(x1, y1, x2, y2, start_x)
            y_at_end_x = interpolate_y(x1, y1, x2, y2, end_x)

            # Check if the horizontal line intersects the curve segment
            if (y1 <= y_pos <= y2 or y2 <= y_pos <= y1) and (y_at_start_x <= y_pos <= y_at_end_x or y_at_end_x <= y_pos <= y_at_start_x):
                return True

    return False

# Function to interpolate the y value of a point on a line segment given x
def interpolate_y(x1, y1, x2, y2, x):
    if x1 == x2:  # Avoid division by zero
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

# Function to apply user input values for colors and names of horizontal lines
def apply_values():
    global horizontal_lines_colors, horizontal_lines_names
    horizontal_lines_colors = [entry_color.get() for entry_color in entries_color]
    horizontal_lines_names = [entry_name.get() for entry_name in entries_name]
    update_plot()

# Function to update horizontal line heights from sliders
def update_heights(*args):
    global horizontal_lines
    horizontal_lines = [slider.get() / 100 for slider in sliders]
    for i, entry_height in enumerate(entries_height):
        entry_height.delete(0, tk.END)
        entry_height.insert(0, f"{horizontal_lines[i]:.2f}")
    update_plot()

# Function to apply values from entries
def apply_entry_values():
    global horizontal_lines
    horizontal_lines = [float(entry_height.get()) for entry_height in entries_height]
    update_plot()

# Create the main window
window = tk.Tk()
window.title("Fire Detection and Image Processing")

# Configure grid layout for expanding frames
window.columnconfigure(1, weight=1)
window.rowconfigure(1, weight=1)

# Create a button to load an image
button_load = tk.Button(window, text="Load Image", command=load_image)
button_load.grid(row=0, column=0, padx=5, pady=5)

# Create a frame to hold the plot
frame = tk.Frame(window)
frame.grid(row=1, column=0, columnspan=4, sticky='nsew')

# Create sliders and entries to input the position of horizontal lines
sliders = []
entries_height = []
for i in range(5):
    label_name = tk.Label(window, text=f'Horizontal Line {chr(65 + i)}:')
    label_name.grid(row=i+2, column=0, padx=5, pady=5, sticky='w')

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
for i in range(5):
    entry_name = tk.Entry(window)
    entry_name.insert(0, horizontal_lines_names[i])
    entry_name.grid(row=i + 7, column=0, padx=5, pady=5, sticky='w')
    entries_name.append(entry_name)

    entry_color = tk.Entry(window)
    entry_color.insert(0, horizontal_lines_colors[i])
    entry_color.grid(row=i + 7, column=1, columnspan=3, padx=5, pady=5, sticky='ew')
    entries_color.append(entry_color)

# Create a button to apply the input values
button_apply = tk.Button(window, text="Apply Values", command=apply_values)
button_apply.grid(row=12, column=0, columnspan=2, pady=10)

# Create a button to apply the values from entries
button_apply_entries = tk.Button(window, text="Apply Entry Values", command=apply_entry_values)
button_apply_entries.grid(row=12, column=2, columnspan=2, pady=10)

# Create a label to display the image
label_image = tk.Label(window)
label_image.grid(row=1, column=0, columnspan=4)


window.mainloop()
