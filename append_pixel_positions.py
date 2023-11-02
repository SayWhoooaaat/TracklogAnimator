import math

def append_pixel_positions(track_points, map_metadata, outline_metadata):
    print("Calculating path pixels on maps...")
    for i in range(0, len(track_points)):
        timestamp, x, y, alt, v, phi, dt, lat, lon, *_ = track_points[i]
        # Outline
        lon_min, lat_min, lon_max, lat_max, width, height = outline_metadata

        x_pixels = (lon - lon_min)/(lon_max - lon_min) * width
        
        yp = math.log(math.tan(lat/180*math.pi) + (1 / math.cos(lat/180*math.pi)))
        y_bottom = math.log(math.tan(lat_min/180*math.pi) + (1 / math.cos(lat_min/180*math.pi)))
        y_top = math.log(math.tan(lat_max/180*math.pi) + (1 / math.cos(lat_max/180*math.pi)))
        y_pixels = (y_top - yp)/(y_top - y_bottom) * height
        
        track_points[i].append(x_pixels)
        track_points[i].append(y_pixels)


    return track_points

