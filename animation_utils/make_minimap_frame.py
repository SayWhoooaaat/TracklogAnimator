import math
from PIL import ImageDraw, ImageFont, Image
import os
import subprocess
import sys
import time
import csv
from datetime import datetime
import json


def get_ruler_km(map_km):
    ruler_0 = map_km / 2
    basis = 10 ** math.floor(math.log10(ruler_0))
    mantissa = ruler_0 / basis
    if mantissa > 5:
        ruler_km = 5 * basis
    elif mantissa > 2:
        ruler_km = 2 * basis
    else:
        ruler_km = basis
    return ruler_km

def initialize_minimap(track_point, no_maps, res_scale, width):
    # Initializes positions and mini-map images
    center_pilot_x = []
    center_pilot_y = []
    for p in range(0, no_maps): # all maps
        center_pilot_x.append(0)
        center_pilot_y.append(0)

    # Find map offsets (should move to map_metadata)
    x_offsets = []
    y_offsets = []
    for i in range(0, no_maps):
        scale = 2 ** i
        x_offsets.append(track_point["map_coordinate"][i]["x"] * scale - track_point["map_coordinate"][0]["x"])
        y_offsets.append(track_point["map_coordinate"][i]["y"] * scale - track_point["map_coordinate"][0]["y"])

    # Initialize minmax pixel positions
    x_pixels_min = track_point["map_coordinate"][0]["x"]
    x_pixels_max = track_point["map_coordinate"][0]["x"]
    y_pixels_min = track_point["map_coordinate"][0]["y"]
    y_pixels_max = track_point["map_coordinate"][0]["y"]

    arrow = [(-8*res_scale,-6*res_scale), (8*res_scale,0), (-8*res_scale,6*res_scale)]
    center_factor = 0.3
    center_radius = center_factor / 2 * width

    target_arrow_base = [(-1,6), (1,6), (1,3), (2,3), (0,0), (-2,3), (-1,3)]
    target_arrow_base = [(px*7, -width*0.49 + py*4) for px, py in target_arrow_base]

    frame_memory = {
    'center_pilot_x': center_pilot_x,
    'center_pilot_y': center_pilot_y,
    'x_offsets': x_offsets,
    'y_offsets': y_offsets,
    'x_pixels_min': x_pixels_min,
    'x_pixels_max': x_pixels_max,
    'y_pixels_min': y_pixels_min,
    'y_pixels_max': y_pixels_max,
    'arrow': arrow,
    'center_radius': center_radius,
    'target_arrow_base': target_arrow_base
}
    return frame_memory



def make_minimap_frame(frame_memory, path_images, i, no_points, track_point, track_point_prev, map_metadata, res_scale, width):
    # Unpack memory dictionary
    center_pilot_x = frame_memory['center_pilot_x']
    center_pilot_y = frame_memory['center_pilot_y']
    x_offsets = frame_memory['x_offsets']
    y_offsets = frame_memory['y_offsets']
    x_pixels_min = frame_memory['x_pixels_min']
    x_pixels_max = frame_memory['x_pixels_max']
    y_pixels_min = frame_memory['y_pixels_min']
    y_pixels_max = frame_memory['y_pixels_max']
    arrow = frame_memory['arrow']
    center_radius = frame_memory['center_radius']
    target_arrow_base = frame_memory['target_arrow_base']

    phi = track_point["direction"]
    height = width
    path_linewidth = round(res_scale)
    m_px = map_metadata[0][6]
    no_maps = len(map_metadata)

    # Initializes path drawing for all maps
    draw = []
    for p in range(0, no_maps):
        draw.append(ImageDraw.Draw(path_images[p]))
    
    # Draw path on all maps:
    x_pixel = []
    y_pixel = []
    x_pixel_last = []
    y_pixel_last = []
    center_path_x = []
    center_path_y = []
    center_frame_x = []
    center_frame_y = []
    for p in range(0, no_maps):
        x_pixel.append(track_point["map_coordinate"][p]["x"])
        y_pixel.append(track_point["map_coordinate"][p]["y"])
        # Drawing path
        if i > 0:
            x_pixel_last.append(track_point_prev["map_coordinate"][p]["x"])
            y_pixel_last.append(track_point_prev["map_coordinate"][p]["y"])
            draw[p].line((x_pixel_last[p], y_pixel_last[p], x_pixel[p], y_pixel[p]), fill='red', width=path_linewidth)

    # Frame center pilot: 
    if i == 0: # center for first iteration
        center_pilot_x[0], center_pilot_y[0] = x_pixel[0], y_pixel[0]
    center_distance = math.sqrt((x_pixel[0]-center_pilot_x[0])**2+(y_pixel[0]-center_pilot_y[0])**2)
    if center_distance > center_radius: # Move frame center
        beta = math.atan2(y_pixel[0]-center_pilot_y[0],x_pixel[0]-center_pilot_x[0])
        center_pilot_x[0] = center_pilot_x[0] + (center_distance - center_radius) * math.cos(beta)
        center_pilot_y[0] = center_pilot_y[0] + (center_distance - center_radius) * math.sin(beta)
    
    if no_maps > 1: # Apply new coordinates to all other maps (only to map number(?))
        for p in range(1, no_maps): 
            center_pilot_x[p] = (center_pilot_x[0] + x_offsets[p]) / (2 ** p)
            center_pilot_y[p] = (center_pilot_y[0] + y_offsets[p]) / (2 ** p)
    
    # Frame center path:
    x = track_point["map_coordinate"][0]["x"]
    y = track_point["map_coordinate"][0]["y"]
    # Find pixels traveled
    if x > x_pixels_max:
        x_pixels_max = x
    elif x < x_pixels_min:
        x_pixels_min = x
    if y > y_pixels_max:
        y_pixels_max = y
    elif y < y_pixels_min:
        y_pixels_min = y
    center_path_x.append((x_pixels_max + x_pixels_min) / 2)
    center_path_y.append((y_pixels_max + y_pixels_min) / 2)

    if no_maps > 1: # Apply new coordinates to all other maps (only to map number(?))
        for p in range(1, no_maps): 
            center_path_x.append((center_path_x[0] + x_offsets[p]) / (2 ** p))
            center_path_y.append((center_path_y[0] + y_offsets[p]) / (2 ** p))

    # Interpolate path center (only to map number(?))
    for p in range(0, no_maps):
        center_frame_x.append(center_pilot_x[p] * (1 - track_point["fraction"]) + center_path_x[p] * track_point["fraction"])
        center_frame_y.append(center_pilot_y[p] * (1 - track_point["fraction"]) + center_path_y[p] * track_point["fraction"])
    
    # Choose appropriate sized map
    map_number = int(track_point["zoom_level"]) # rounds down

    # Draws arrow at the end of path (but doesnt mess with path_images) 
    image_with_arrow = path_images[map_number].copy()
    draw2 = ImageDraw.Draw(image_with_arrow)
    angled_arrow = [(x_pixel[map_number] + px * math.cos(phi) - py * math.sin(phi), y_pixel[map_number] + px * math.sin(phi) + py * math.cos(phi)) for px, py in arrow]
    if i == 0 or i == no_points-1:
        dot_radius = 6*res_scale
        pilot_dot = [x_pixel[map_number]-dot_radius, y_pixel[map_number]-dot_radius, x_pixel[map_number]+dot_radius, y_pixel[map_number]+dot_radius]
        draw2.ellipse(pilot_dot, fill='red', outline ='black')
    else:
        draw2.polygon(angled_arrow, fill='red', outline ='black', width = round(2*res_scale))

    # Crop and scale
    temp_width = width * 2**track_point["zoom_level"] / 2**map_number
    cropped_image = image_with_arrow.crop((center_frame_x[map_number] - temp_width/2.0, center_frame_y[map_number] - temp_width/2.0, center_frame_x[map_number] + temp_width/2.0, center_frame_y[map_number] + temp_width/2.0))
    cropped_image = cropped_image.resize((width, width))
    draw3 = ImageDraw.Draw(cropped_image)

    # Draw ruler on cropped image
    m_px2 = m_px * 2**track_point["zoom_level"] # Instead of scale?
    ruler_km = get_ruler_km(width * m_px2 / 1000)
    ruler_pixels = ruler_km * 1000 / m_px2
    ruler_text = f"{ruler_km} km"
    font = ImageFont.truetype("arial.ttf", size=round(14*res_scale))

    draw3.line((width-8*res_scale, height-14*res_scale, width-8*res_scale, height-8*res_scale), fill='white', width=round(res_scale))
    draw3.line((width-8*res_scale, height-8*res_scale, width-8*res_scale-ruler_pixels, height-8*res_scale), fill='white', width=round(res_scale))
    draw3.line((width-8*res_scale-ruler_pixels, height-8*res_scale, width-8*res_scale-ruler_pixels, height-14*res_scale), fill='white', width=round(res_scale))
    bbox = draw3.textbbox((0, 0), ruler_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw3.text((width-18*res_scale-ruler_pixels-text_width, height-8*res_scale-text_height), ruler_text, fill="white", font=font)


    # Draw target if applicable
    x_target = map_metadata[map_number][7]
    y_target = map_metadata[map_number][8]
    if x_target != None:
        x_target_dist = x_target - center_frame_x[map_number]
        y_target_dist = -y_target + center_frame_y[map_number]
        if x_target_dist**2 + y_target_dist**2 > (width*0.6)**2: # Far away from target
            # Draw target arrow
            angle = math.atan2(x_target_dist, y_target_dist)
            target_arrow = [(width/2 + px * math.cos(angle) - py * math.sin(angle), height/2 + px * math.sin(angle) + py * math.cos(angle)) for px, py in target_arrow_base]
            draw3.polygon(target_arrow, fill='green', outline ='black', width = round(2*res_scale))
            # draw target text
            target_text = f'{round(track_point["target_distance"]/1000)} km'
            bbox = draw3.textbbox((0, 0), target_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            tr = width*0.4
            target_text_pos = (width/2 + tr*math.sin(angle) - text_width/2, width/2 - tr*math.cos(angle) - text_height/2)
            draw3.text(target_text_pos, target_text, fill="white", font=font)

    cropped_image = cropped_image.convert("RGBA")

    # Save memory for next iteration
    frame_memory['center_pilot_x'] = center_pilot_x
    frame_memory['center_pilot_y'] = center_pilot_y
    frame_memory['x_offsets'] = x_offsets
    frame_memory['y_offsets'] = y_offsets
    frame_memory['x_pixels_min'] = x_pixels_min
    frame_memory['x_pixels_max'] = x_pixels_max
    frame_memory['y_pixels_min'] = y_pixels_min
    frame_memory['y_pixels_max'] = y_pixels_max
    frame_memory['arrow'] = arrow
    frame_memory['center_radius'] = center_radius
    frame_memory['target_arrow_base'] = target_arrow_base

    return cropped_image, path_images, frame_memory



# Testing purposes:
if __name__ == "__main__":
    filename = 'track_points.csv'
    # read track points
    track_points = []
    datetime_fields = ['local_time', 'timestamp']
    with open(filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, value in row.items():
                try:
                    # Try converting to float if possible
                    row[key] = float(value)
                except ValueError:
                    # Check if it's a datetime field and convert
                    if key in datetime_fields:
                        row[key] = datetime.fromisoformat(value)
                    else:
                        # If conversion fails, check if it's a JSON string
                        try:
                            row[key] = json.loads(value)
                        except json.JSONDecodeError:
                            # If it's not JSON, leave it as the original string
                            pass
            track_points.append(row)

    # Read maps
    no_maps = len(track_points[0]["map_coordinate"])
    print("number of maps: ",  no_maps)
    map_images = []
    for k in range(0, no_maps):
        map_image = Image.open(f"media/map_stitched{k}.png").convert("RGB")
        map_images.append(map_image)

    # Read minimap metadata
    with open('minimap_metadata.csv', mode='r') as file:
        reader = csv.reader(file)
        map_metadata = [
            [
                float(row[0]),  # lon_min_tile
                float(row[1]),  # lat_min_tile
                float(row[2]),  # lon_max_tile
                float(row[3]),  # lat_max_tile
                int(row[4]),    # width
                int(row[5]),    # height
                float(row[6]),  # m_px
                float(row[7]),  # x_target
                float(row[8])   # y_target
            ]
            for row in reader
        ]
    # make up rest of data
    width = 250
    #m_px = 16
    res_scale = 1 # for 1080p

    # Initiallize
    no_points = len(track_points)
    path_images = map_images
    frame_memory = initialize_minimap(track_points[0], no_maps, res_scale, width)

    i_max = 500
    i_max = min(i_max, len(track_points))
    iters = 50
    step_size = int(i_max/iters)

    
    for i in range(0, i_max, step_size):
        track_point = track_points[i]
        if i == 0:
            track_point_prev = track_point
        minimap_frame, path_images, frame_memory = make_minimap_frame(frame_memory, path_images, i, no_points, track_point, track_point_prev, map_metadata, res_scale, width)
        track_point_prev = track_point

    minimap_frame.save("media/minimap_test.png")
    




