import math
from PIL import Image, ImageDraw, ImageFont
import sys
import csv
import json
from datetime import datetime
from animation_utils import make_altibar_frame
from animation_utils import initialize_minimap
from animation_utils import make_minimap_frame

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


def get_preview(track_points, map_images, map_metadata, outline_image_static, width, anim_height, goal_type, goal_text_reference):
    print("Making preview image...")
    animation_frame = Image.new("RGBA", (width, anim_height), (0, 0, 0, 0))
    res_scale = anim_height / 1080

    # STEP 1: MINI-MAP
    no_maps = len(map_images)
    no_points =len(track_points)
    m_px = map_metadata[0][6]
    path_images = [img.copy() for img in map_images]
    frame_memory = initialize_minimap(track_points[0], no_maps, res_scale, width)

    endpoint = int(no_points/3*2)
    endpoint = min(endpoint, no_points)
    step_size = int(endpoint/100) # reduce to 100 calculation points

    for i in range(0, endpoint, step_size):
        track_point = track_points[i]
        if i == 0:
            track_point_prev = track_point
        # Get minimap frame
        minimap_frame, path_images, frame_memory = make_minimap_frame(frame_memory, path_images, i, no_points, track_point, track_point_prev, m_px, no_maps, res_scale, width)
        track_point_prev = track_point

    position_minimap = (0, animation_frame.size[1] - minimap_frame.size[1])
    animation_frame.paste(minimap_frame, position_minimap, minimap_frame)

    # STEP 2: MAKE OUTLINE-MAP FRAME
    outline_image = outline_image_static.copy()
    for i in range(0, endpoint, step_size):
        x_outline = track_points[i]["outline_x"]
        y_outline = track_points[i]["outline_y"]
        # Draws path on image with only path
        draw4 = ImageDraw.Draw(outline_image)
        if i > 0:
            draw4.line((last_x_outline, last_y_outline, x_outline, y_outline), fill=(255,0,0,200), width=round(res_scale))
        last_x_outline, last_y_outline = x_outline, y_outline
    # Draws arrow at the end of path (but doesnt mess with outline_image)
    outline_with_dot = outline_image.copy()
    draw5 = ImageDraw.Draw(outline_with_dot)
    draw5.ellipse([x_outline - 3*res_scale, y_outline - 3*res_scale, x_outline + 3*res_scale, y_outline + 3*res_scale], fill='red', outline='black')
    outline_with_dot.save('media/preview_outline.png')

    position_outline = (round(10*res_scale), round(anim_height*0.1))
    animation_frame.paste(outline_with_dot, position_outline, outline_with_dot)

    # Extract data
    localtime = track_points[i]["local_time"]
    altitude = track_points[i]["altitude"]
    elevation = track_points[i]["elevation"]
    v = track_points[i]["velocity"]
    dist = track_points[i]["distance"]
    vario = track_points[i]["vario"]
    altitude_lr = track_points[i]["altitude_lr"]
    elevation_lr = track_points[i]["elevation_lr"]
    vario_lr = track_points[i]["vario_lr"]
    sl_distance = track_points[i]["sl_distance"]
    open_distance = track_points[i]["open_dist"]
    distance_3tp = track_points[i]["3tp_dist"]

    # Draw datetime
    current_time = localtime.strftime("%H:%M")
    current_date = localtime.strftime("%Y-%m-%d")

    draw6 = ImageDraw.Draw(animation_frame)
    draw6.text((30*res_scale,30*res_scale), current_time, font=ImageFont.truetype("arial.ttf", round(40*res_scale)), fill='white')
    draw6.text((38*res_scale,76*res_scale), current_date, font=ImageFont.truetype("arial.ttf", round(16*res_scale)), fill='white')
    
    # Draw altibar
    max_altitude = max(point["altitude"] for point in track_points)
    altibar_height = round(280 * res_scale)
    if i == 0 or i == len(track_points)-1:
        elevation_active = False
    else:
        elevation_active = True
    altibar_image = make_altibar_frame(width, altibar_height, res_scale, altitude, elevation, vario, vario_lr, max_altitude, altitude_lr, elevation_lr, elevation_active)
    altibar_y = position_minimap[1] - altibar_height - round(anim_height*0.05)
    animation_frame.paste(altibar_image, (0,altibar_y), altibar_image)

    # Draw goal
    textsize = round(18*res_scale)
    font = ImageFont.truetype("arial.ttf", textsize)
    if goal_type == '3tp_distance': # 3tp-distance
        goal_text = f"Distance (3tp): {round(distance_3tp/1000)} km\n{goal_text_reference}"
    elif goal_type == 'open_distance': # open distance
        goal_text = f"Open distance: {round(open_distance/1000)} km\n{goal_text_reference}"
    
    draw6.text((8*res_scale, position_minimap[1] - anim_height*0.05), goal_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    
    # Paste animation frame as an overlay
    base_image = Image.open("media/preview_background.png").convert("RGBA")
    base_image = base_image.resize((round(anim_height / 9 * 16), anim_height))
    base_image.paste(animation_frame, (0,0), animation_frame)
    base_image.save("media/preview.png")
    print("Preview saved.")

    return




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
    no_map_images = len(track_points[0]["map_coordinate"])
    map_images = []
    for i in range(no_map_images):
        map_image = Image.open(f"media/map_stitched{i}.png").convert("RGB")
        map_images.append(map_image) 

    outline_image_static = Image.open("media/country_outline.png").convert("RGBA")

    overlay_width = 250
    anim_height = 1080
    goal_type = '3tp_distance'
    goal_text_reference = 'PB: 22 km'

    map_metadata = []
    map_metadata.append([0, 0, 0, 0, 0, 0, 16])

    get_preview(track_points, map_images, map_metadata, outline_image_static, overlay_width, anim_height, goal_type, goal_text_reference)



