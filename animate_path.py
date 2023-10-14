import cv2
import numpy as np
import math
from PIL import ImageDraw

def animate_path(map_metadata, map_image, track_points):
    m_px = map_metadata[0]
    x0 = map_metadata[1]
    y0 = map_metadata[2]
    fps = 30

    # Initialize video writer
    height, width = map_image.size
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('animation.mp4', fourcc, fps, (height, width))

    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)

    for i in range(0, len(track_points)):
        x_meters = track_points[i][4]
        y_meters = track_points[i][5]
        
        x = x0 + x_meters / m_px
        y = y0 + y_meters / m_px

        # Draws path on image with only path
        if i > 0:
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
