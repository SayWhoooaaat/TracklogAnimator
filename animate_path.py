import cv2
import numpy as np
import math
from PIL import ImageDraw

def animate_path(map_metadata, map_image, track_points, fps):
    m_px = map_metadata[0]
    x0 = map_metadata[1]
    y0 = map_metadata[2]
    arrow = [(-8,-6), (8,0), (-8,6)]

    height, width = 512, 512
    center_factor = 0.3
    center_radius = center_factor / 2 * min(height,width)

    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('animation.mp4', fourcc, fps, (height, width))

    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)

    for i in range(0, len(track_points)):
        x_meters = track_points[i][1]
        y_meters = track_points[i][2]
        phi = track_points[i][5]
        
        x = x0 + x_meters / m_px
        y = y0 + y_meters / m_px

        # Draws path on image with only path
        if i > 0:
            draw.line((last_x, last_y, x, y), fill='red', width=2)
        last_x, last_y = x, y

        # Draws arrow at the end of path (but doesnt mess with path_image)
        image_with_arrow = path_image.copy()
        draw2 = ImageDraw.Draw(image_with_arrow)
        angled_arrow = [(x + px * math.cos(phi) - py * math.sin(phi), y + px * math.sin(phi) + py * math.cos(phi)) for px, py in arrow]
        draw2.polygon(angled_arrow, fill='red', outline ='black')

        # Crop out desired frame
        if i == 0: # center for first iteration
            xc, yc = x, y
        center_distance = math.sqrt((x-xc)**2+(y-yc)**2)
        if center_distance > center_radius: # Move frame center
            beta = math.atan2(y-yc,x-xc)
            xc = xc + (center_distance - center_radius) * math.cos(beta)
            yc = yc + (center_distance - center_radius) * math.sin(beta)
        cropped_image = image_with_arrow.crop((xc - width/2.0, yc - height/2.0, xc + width/2.0, yc + height/2.0))

        # Convert PIL image to NumPy array and write to video
        frame = np.array(cropped_image)
        out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    # Release the video writer
    out.release()

    return
