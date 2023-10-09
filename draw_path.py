import math
from PIL import ImageDraw

def draw_path(map_data, map_image, gpx_points):
    zoom = map_data[0]
    xmin = map_data[1]
    ymin = map_data[2]
    cell_size = 256
    n = 2.0 ** zoom

    print(zoom, xmin, ymin, cell_size, n)

    # Create a drawing object
    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)
    
    first_timestamp, first_latitude, first_longitude, first_elevation = gpx_points[0]
    last_x = ((first_longitude + 180.0) * n / 360.0 - xmin) * cell_size
    last_y = ((1.0 - math.log(math.tan(math.radians(first_latitude)) + (1 / math.cos(math.radians(first_latitude)))) / math.pi) / 2.0 * n - ymin) * cell_size

    
    # Loop through the track points to draw them on the map
    for point in gpx_points[1:]:
        timestamp, latitude, longitude, elevation = point  # Extract information from each point
        
        # Convert latitude and longitude to x and y coordinates
        
        x = ((longitude + 180.0) * n / 360.0 - xmin) * cell_size
        y = ((1.0 - math.log(math.tan(math.radians(latitude)) + (1 / math.cos(math.radians(latitude)))) / math.pi) / 2.0 * n - ymin) * cell_size

        # Draw the point on the map image
        draw.line((last_x, last_y, x, y), fill='red')
        last_x, last_y = x, y
    
    # Save or return the new image
    path_image.save('map_with_path.png')  # Save the image with the path
    return path_image
