import math
from PIL import Image, ImageDraw, ImageFont
import sys

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


def get_preview(track_points, map_image, map_metadata, outline_image, overlay_width):
    print("Making preview image...")

    m_px = map_metadata[6]
    arrow = [(-8,-6), (8,0), (-8,6)]

    height, width = overlay_width, overlay_width

    # Makes and scales ruler
    ruler_km = get_ruler_km(width * m_px / 1000)
    ruler_pixels = ruler_km * 1000 / m_px
    ruler_text = f"{ruler_km} km"
    font = ImageFont.truetype("arial.ttf", size=14)

    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)

    endpoint = round(len(track_points)*3/4)
    for i in range(0, endpoint):
        x = track_points[i][9]
        y = track_points[i][10]
        phi = track_points[i][5]
        
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
    text_width, text_height = draw3.textsize(ruler_text, font=font)
    draw3.text((width-18-ruler_pixels-text_width, height-8-text_height), ruler_text, fill="white", font=font)

    cropped_image.save('media/preview_minimap.png')

    # STEP 2: MAKE OUTLINE-MAP FRAME
    for i in range(0, endpoint):
        x_outline = track_points[i][11]
        y_outline = track_points[i][12]

        # Draws path on image with only path
        draw4 = ImageDraw.Draw(outline_image)
        if i > 0:
            draw4.line((last_x_outline, last_y_outline, x_outline, y_outline), fill='orange', width=1)
        last_x_outline, last_y_outline = x_outline, y_outline
    
    # Draws arrow at the end of path (but doesnt mess with path_image)
    outline_with_dot = outline_image.copy()
    draw5 = ImageDraw.Draw(outline_with_dot)
    draw5.ellipse([x_outline - 2, y_outline - 2, x_outline + 2, y_outline + 2], fill='red')
    outline_with_dot.save('media/preview_outline.png')

    # Now put all images together
    base_image = Image.open("media/preview_background.png").convert("RGBA")
    cropped_image = cropped_image.convert("RGBA")

    position_minimap = (0, base_image.size[1] - cropped_image.size[1])
    position_outline = (0, base_image.size[1] - cropped_image.size[1] - outline_image.size[1] - 50)

    base_image.paste(cropped_image, position_minimap, cropped_image)
    base_image.paste(outline_with_dot, position_outline, outline_with_dot)

    # Drawing text
    timedate, x, y, ele, v, phi, lat, lon, dist, *_ = track_points[endpoint]
    current_time = timedate.strftime("%H:%M")
    current_date = timedate.strftime("%Y-%m-%d")

    draw6 = ImageDraw.Draw(base_image)
    draw6.text((30,30), current_time, font=ImageFont.truetype("arial.ttf", 40), fill='white')
    draw6.text((38,76), current_date, font=ImageFont.truetype("arial.ttf", 16), fill='white')
    draw6.text((20,750), f"{round(ele)} m", font=ImageFont.truetype("arial.ttf", 24), fill='white')
    draw6.text((116,750), f"{round(v*3.6)} km/h", font=ImageFont.truetype("arial.ttf", 24), fill='white')
    draw6.text((220,750), f"{round(dist/1000)} km", font=ImageFont.truetype("arial.ttf", 24), fill='white')

    base_image.save("media/preview.png")
    user_input = input("Preview saved. Proceed? (y/n): ")
    if user_input.lower() != 'y':
        print("Terminating program.")
        sys.exit()

    return

