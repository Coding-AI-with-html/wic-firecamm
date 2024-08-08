import logging
from datetime import datetime
import os

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Extract message components
        timestamp = record.msg['timestamp']
        num_tracks = record.msg['num_tracks']
        operator_values = ', '.join(map(str, record.msg['Operator_values']))
        software_values = ', '.join(map(str, record.msg['Software_values']))
        quality = f"{record.msg['quality']:.2f}"
        image_id = record.msg['image_id']
        view = record.msg['view']

        # Calculate required lengths dynamically
        timestamp_len = 20
        num_tracks_len = 10
        operator_values_len = max(50, len(operator_values))
        software_values_len = max(52, len(software_values))
        quality_len = 10
        image_id_len = max(25, len(image_id))
        view_len = max(30, len(view))

        # Format the log entry with proper alignment
        log_entry = (
            f"{timestamp:<{timestamp_len}} "
            f"{num_tracks:<{num_tracks_len}} "
            f"{operator_values:<{operator_values_len}} "
            f"{software_values:<{software_values_len}} "
            f"{quality:<{quality_len}} "
            f"{image_id:<{image_id_len}} "
            f"{view:<{view_len}}\n"
        )
        return log_entry

# Function to write headers if not present
def write_headers_if_needed(log_file):
    if not os.path.isfile(log_file) or os.path.getsize(log_file) == 0:
        with open(log_file, 'w') as f:
            header = (
                f"{'Timestamp':<20} "
                f"{'Num_Tracks':<10} "
                f"{'Operator_values':<50} "
                f"{'Software_values':<52} "
                f"{'Quality':<10} "
                f"{'Image_ID':<25} "
                f"{'View':<30}\n"
            )
            f.write(header)