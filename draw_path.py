import math
from PIL import ImageDraw

def draw_path(map_metadata, map_image, track_points):
    zoom = map_metadata[0]
    xmin = map_metadata[1]
    ymin = map_metadata[2]
    cell_size = map_metadata[3]
    m_px = map_metadata[4]
    n = 2.0 ** zoom

    print("zoom", zoom, ",", n, "by", n, "cells on map and cell origin:", xmin, ymin, )

    # Create a drawing object
    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)
    
    first_timestamp, first_latitude, first_longitude, *_ = track_points[0]
    last_x = ((first_longitude + 180.0) * n / 360.0 - xmin) * cell_size
    last_y = ((1.0 - math.log(math.tan(math.radians(first_latitude)) + (1 / math.cos(math.radians(first_latitude)))) / math.pi) / 2.0 * n - ymin) * cell_size

    
    # Loop through the track points to draw them on the map
    for point in track_points[1:]:
        timestamp, latitude, longitude, *_ = point  # Extract information from each point
        
        # Convert latitude and longitude to x and y coordinates
        
        x = ((longitude + 180.0) * n / 360.0 - xmin) * cell_size
        y = ((1.0 - math.log(math.tan(math.radians(latitude)) + (1 / math.cos(math.radians(latitude)))) / math.pi) / 2.0 * n - ymin) * cell_size

        # Draw the point on the map image
        draw.line((last_x, last_y, x, y), fill='red')
        last_x, last_y = x, y
    
    # Save or return the new image
    path_image.save('map_with_path.png')  # Save the image with the path
    return path_image
