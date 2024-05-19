import math
from PIL import Image, ImageDraw, ImageFont
import sys
import csv
import json
from datetime import datetime
from animation_utils import make_altibar_frame

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


def get_preview(track_points, map_images, map_metadata, outline_image_static, overlay_width, anim_height, challenge, pb):
    print("Making preview image...")

    scale = anim_height / 1080
    m_px = map_metadata[0][6]
    arrow = [(-8,-6), (8,0), (-8,6)]

    height, width = overlay_width, overlay_width

    # Makes and scales ruler
    ruler_km = get_ruler_km(width * m_px / 1000)
    ruler_pixels = ruler_km * 1000 / m_px
    ruler_text = f"{ruler_km} km"
    textsize = 14
    font = ImageFont.truetype("arial.ttf", textsize)

    path_image = map_images[0].copy()
    draw = ImageDraw.Draw(path_image)

    endpoint = round(len(track_points)*1/4)
    for i in range(0, endpoint):
        x = track_points[i]["map_coordinate"][0]["x"]
        y = track_points[i]["map_coordinate"][0]["y"]
        phi = track_points[i]["direction"]
        
        # Draws path on image with only path
        if i > 0:
            draw.line((last_x, last_y, x, y), fill='red', width=1)
        last_x, last_y = x, y

    # Draws arrow at the end of path (but doesnt mess with path_image)
    image_with_arrow = path_image.copy()
    draw2 = ImageDraw.Draw(image_with_arrow)
    angled_arrow = [(x + px * math.cos(phi) - py * math.sin(phi), y + px * math.sin(phi) + py * math.cos(phi)) for px, py in arrow]
    draw2.polygon(angled_arrow, fill='red', outline ='black')

    # Crop out desired frame
    xc, yc = x, y
    cropped_image = image_with_arrow.crop((xc - width/2.0, yc - height/2.0, xc + width/2.0, yc + height/2.0))
    
    # Draw ruler on cropped image
    draw3 = ImageDraw.Draw(cropped_image)
    draw3.line((width-8, height-14, width-8, height-8), fill='white', width=1)
    draw3.line((width-8, height-8, width-8-ruler_pixels, height-8), fill='white', width=1)
    draw3.line((width-8-ruler_pixels, height-8, width-8-ruler_pixels, height-14), fill='white', width=1)
    text_width = draw3.textlength(ruler_text, font=font)
    draw3.text((width-18-ruler_pixels-text_width, height-8-textsize), ruler_text, fill="white", font=font)

    cropped_image.save('media/preview_minimap.png')

    # STEP 2: MAKE OUTLINE-MAP FRAME
    outline_image = outline_image_static.copy()
    for i in range(0, endpoint):
        x_outline = track_points[i]["outline_x"]
        y_outline = track_points[i]["outline_y"]

        # Draws path on image with only path
        draw4 = ImageDraw.Draw(outline_image)
        if i > 0:
            draw4.line((last_x_outline, last_y_outline, x_outline, y_outline), fill=(255,0,0,50), width=1)
        last_x_outline, last_y_outline = x_outline, y_outline
    
    # Draws arrow at the end of path (but doesnt mess with path_image)
    outline_with_dot = outline_image.copy()
    draw5 = ImageDraw.Draw(outline_with_dot)
    draw5.ellipse([x_outline - 2, y_outline - 2, x_outline + 2, y_outline + 2], fill='red')
    outline_with_dot.save('media/preview_outline.png')

    # Now put all images together
    base_image = Image.open("media/preview_background.png").convert("RGBA")
    base_image = base_image.resize((round(anim_height / 9 * 16), anim_height))
    cropped_image = cropped_image.convert("RGBA")

    position_minimap = (0, base_image.size[1] - cropped_image.size[1])
    position_outline = (round(10*scale), round(anim_height*0.1))

    base_image.paste(cropped_image, position_minimap, cropped_image)
    base_image.paste(outline_with_dot, position_outline, outline_with_dot)

    # Extract data
    localtime = track_points[i]["local_time"]
    ele = track_points[i]["elevation"]
    agl = track_points[i]["agl"]
    v = track_points[i]["velocity"]
    dist = track_points[i]["distance"]
    vario = track_points[i]["vario"]
    vario_lr = track_points[i]["vario_low_refresh"]
    sl_distance = track_points[i]["sl_distance"]

    # Draw datetime
    current_time = localtime.strftime("%H:%M")
    current_date = localtime.strftime("%Y-%m-%d")

    draw6 = ImageDraw.Draw(base_image)
    draw6.text((30*scale,30*scale), current_time, font=ImageFont.truetype("arial.ttf", round(40*scale)), fill='white')
    draw6.text((38*scale,76*scale), current_date, font=ImageFont.truetype("arial.ttf", round(16*scale)), fill='white')
    
    # Draw altibar
    max_elevation = max(point["elevation"] for point in track_points)
    altibar_height = round(280 * scale)
    altibar_image = make_altibar_frame(width, altibar_height, scale, ele, agl, vario, vario_lr, max_elevation)
    altibar_y = position_minimap[1] - altibar_height - round(anim_height*0.05)
    base_image.paste(altibar_image, (0,altibar_y), altibar_image)

    # Draw goal
    textsize = round(18*scale)
    font = ImageFont.truetype("arial.ttf", textsize)
    if challenge == 1: # Straight line distance
        goal_text = f"Distance from start: {round(sl_distance/1000)} km\nPB: {round(pb)} km"
    elif challenge == 2: # Out and return
        goal_text = f"Out and return\nNot yet programmed."
    
    draw6.text((8*scale, position_minimap[1] - anim_height*0.05), goal_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    

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
    #print(track_points[30])

    # Read maps
    map_image = Image.open("media/map_stitched0.png").convert("RGB")
    map_images = []
    map_images.append(map_image)

    outline_image_static = Image.open("media/country_outline.png").convert("RGBA")

    overlay_width = 250
    anim_height = 1080
    challenge = 1
    pb = 9

    map_metadata = []
    map_metadata.append([0, 0, 0, 0, 0, 0, 16])

    get_preview(track_points, map_images, map_metadata, outline_image_static, overlay_width, anim_height, challenge, pb)



