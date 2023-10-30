import math
from PIL import ImageDraw

def draw_path(map_metadata, map_image, track_points):
    m_px = map_metadata[0]
    x0 = map_metadata[1]
    y0 = map_metadata[2]

    # Create a drawing object
    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)

    print("Drawing path on map for fun...")
    for i in range(0, len(track_points)):
        x_meters = track_points[i][1]
        y_meters = track_points[i][2]
        
        x = x0 + x_meters / m_px
        y = y0 + y_meters / m_px

        if i > 0:
            draw.line((last_x, last_y, x, y), fill='red', width=2)
        last_x, last_y = x, y
    
    # Save and return the new image
    path_image.save('media/map_with_path.png')
    print("Made map with path")
    return path_image
