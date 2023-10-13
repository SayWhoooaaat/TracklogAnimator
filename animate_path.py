import cv2
import numpy as np
import math
from PIL import ImageDraw

def animate_path(map_metadata, map_image, track_points):
    zoom, xmin, ymin, cell_size = map_metadata
    n = 2.0 ** zoom
    fps = 30

    # Initialize video writer
    height, width = map_image.size
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('animation.mp4', fourcc, fps, (height, width))

    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)

    first_timestamp, first_latitude, first_longitude, *_ = track_points[0]
    last_x = ((first_longitude + 180.0) * n / 360.0 - xmin) * cell_size
    last_y = ((1.0 - math.log(math.tan(math.radians(first_latitude)) + (1 / math.cos(math.radians(first_latitude)))) / math.pi) / 2.0 * n - ymin) * cell_size

    for point in track_points[2:]:
        timestamp, latitude, longitude, *_ = point

        x = ((longitude + 180.0) * n / 360.0 - xmin) * cell_size
        y = ((1.0 - math.log(math.tan(math.radians(latitude)) + (1 / math.cos(math.radians(latitude)))) / math.pi) / 2.0 * n - ymin) * cell_size

        # Draws path on image with only path
        draw.line((last_x, last_y, x, y), fill='red')
        last_x, last_y = x, y

        # Draws dot at the end of path (but doesnt mess with path_image)
        image_with_dot = path_image.copy()
        draw2 = ImageDraw.Draw(image_with_dot)
        draw2.ellipse((x - 4, y - 4, x + 4, y + 4), fill='red', outline ='red')

        # Convert PIL image to NumPy array and write to video
        frame = np.array(image_with_dot)
        out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    # Release the video writer
    out.release()

    return
