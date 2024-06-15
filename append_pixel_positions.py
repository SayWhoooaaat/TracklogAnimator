import math

def append_pixel_positions(track_points, map_metadata, outline_metadata):
    print("Calculating path pixels on maps...")
    for i in range(0, len(track_points)):
        lat = track_points[i]["lat"]
        lon = track_points[i]["lon"]

        # Outline
        lon_min_out, lat_min_out, lon_max_out, lat_max_out, width_out, height_out = outline_metadata

        x_pixels = (lon - lon_min_out)/(lon_max_out - lon_min_out) * width_out
        
        yp = math.log(math.tan(math.pi/4 + lat/360*math.pi))
        y_bottom = math.log(math.tan(math.pi/4 + lat_min_out/360*math.pi))
        y_top = math.log(math.tan(math.pi/4 + lat_max_out/360*math.pi))
        y_pixels = (y_top - yp)/(y_top - y_bottom) * height_out
        
        track_points[i]["outline_x"] = x_pixels
        track_points[i]["outline_y"] = y_pixels

        # Mini-map
        track_points[i]["map_coordinate"] = []
        for metadata_zoom in map_metadata:
            lon_min, lat_min, lon_max, lat_max, width, height, *_ = metadata_zoom

            x_pixels = (lon - lon_min)/(lon_max - lon_min) * width
            
            yp = math.log(math.tan(math.pi/4 + lat/360*math.pi))
            y_bottom = math.log(math.tan(math.pi/4 + lat_min/360*math.pi))
            y_top = math.log(math.tan(math.pi/4 + lat_max/360*math.pi))
            y_pixels = (y_top - yp)/(y_top - y_bottom) * height
            
            track_points[i]["map_coordinate"].append({"x": x_pixels, "y": y_pixels})

        

    return track_points

