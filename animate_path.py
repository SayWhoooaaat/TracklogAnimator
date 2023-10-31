import math
from PIL import ImageDraw, ImageFont, Image
import os
import subprocess

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


def animate_path(track_points, map_image, map_metadata, outline_image, outline_metadata, fps, overlay_width):
    m_px_outline = outline_metadata[0]
    x_pixels_outline = outline_metadata[1]
    y_pixels_outline = outline_metadata[2]
    
    m_px = map_metadata[0]
    x_pixels = map_metadata[1]
    y_pixels = map_metadata[2]
    arrow = [(-8,-6), (8,0), (-8,6)]

    height, width = overlay_width, overlay_width
    total_height = 1080 # Should be passed in..
    center_factor = 0.3
    center_radius = center_factor / 2 * min(height,width)

    # Makes and scales ruler
    ruler_km = get_ruler_km(width * m_px / 1000)
    ruler_pixels = ruler_km * 1000 / m_px
    ruler_text = f"{ruler_km} km"
    font = ImageFont.truetype("arial.ttf", size=14)

    # Initializes mini-map image
    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)

    temp_folder = 'temp_frames'
    os.makedirs(temp_folder, exist_ok=True)

    print("Making animation frames...")
    for i in range(1, len(track_points)):
        x_meters = track_points[i][1]
        y_meters = track_points[i][2]
        phi = track_points[i][5]
        
        # STEP 1: MAKE MINI-MAP FRAME
        x = x_pixels + x_meters / m_px
        y = y_pixels + y_meters / m_px

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
        if i == 0: # center for first iteration
            xc, yc = x, y
        center_distance = math.sqrt((x-xc)**2+(y-yc)**2)
        if center_distance > center_radius: # Move frame center
            beta = math.atan2(y-yc,x-xc)
            xc = xc + (center_distance - center_radius) * math.cos(beta)
            yc = yc + (center_distance - center_radius) * math.sin(beta)
        cropped_image = image_with_arrow.crop((xc - width/2.0, yc - height/2.0, xc + width/2.0, yc + height/2.0))
        
        # Draw ruler on cropped image
        draw3 = ImageDraw.Draw(cropped_image)
        draw3.line((width-8, height-14, width-8, height-8), fill='white', width=1)
        draw3.line((width-8, height-8, width-8-ruler_pixels, height-8), fill='white', width=1)
        draw3.line((width-8-ruler_pixels, height-8, width-8-ruler_pixels, height-14), fill='white', width=1)
        text_width, text_height = draw3.textsize(ruler_text, font=font)
        draw3.text((width-18-ruler_pixels-text_width, height-8-text_height), ruler_text, fill="white", font=font)

        # STEP 2: MAKE OUTLINE-MAP FRAME
        x_outline = x_pixels_outline + x_meters / m_px_outline
        y_outline = y_pixels_outline + y_meters / m_px_outline
        # Draws path on image with only path
        draw4 = ImageDraw.Draw(outline_image)
        if i > 0:
            draw4.line((last_x_outline, last_y_outline, x_outline, y_outline), fill='orange', width=1)
        last_x_outline, last_y_outline = x_outline, y_outline
        # Draws arrow at the end of path (but doesnt mess with path_image)
        outline_with_dot = outline_image.copy()
        draw5 = ImageDraw.Draw(outline_with_dot)
        draw5.ellipse([x_outline - 1, y_outline - 1, x_outline + 1, y_outline + 1], fill='red')

        # STEP 3: PUT IMAGES TOGETHER
        animation_frame = Image.new('RGBA', (width, total_height))
        cropped_image = cropped_image.convert("RGBA")

        position_minimap = (0, animation_frame.size[1] - cropped_image.size[1])
        position_outline = (0, animation_frame.size[1] - cropped_image.size[1] - outline_image.size[1] - 50)

        animation_frame.paste(cropped_image, position_minimap, cropped_image)
        animation_frame.paste(outline_with_dot, position_outline, outline_with_dot)

        # Drawing text
        timedate, x, y, ele, v, phi, dt_check, lat, lon, dist = track_points[i]
        current_time = timedate.strftime("%H:%M")
        current_date = timedate.strftime("%Y-%m-%d")

        draw6 = ImageDraw.Draw(animation_frame)
        draw6.text((30,30), current_time, font=ImageFont.truetype("arial.ttf", 40), fill='white')
        draw6.text((38,76), current_date, font=ImageFont.truetype("arial.ttf", 16), fill='white')
        draw6.text((20,750), f"{round(ele)} m", font=ImageFont.truetype("arial.ttf", 24), fill='white')
        draw6.text((116,750), f"{round(v*3.6)} km/h", font=ImageFont.truetype("arial.ttf", 24), fill='white')
        draw6.text((220,750), f"{round(dist/1000)} km", font=ImageFont.truetype("arial.ttf", 24), fill='white')

        # Save frame as png:
        frame_path = os.path.join(temp_folder, f'frame_{i:06d}.png')
        animation_frame.save(frame_path, 'PNG')

        if i % 300 == 0: 
            print(f"Progress: {round(i/len(track_points)*100)}%")

    # Use FFmpeg to compile PNGs into a video with ProRes 4444 codec
    print("Stitching frames into transparent video...")
    ffmpeg_command = [
        'ffmpeg',
        '-framerate', str(fps),
        '-i', f'{temp_folder}/frame_%06d.png',
        '-vcodec', 'prores_ks',
        '-profile:v', '4444',  # This is for ProRes 4444
        '-pix_fmt', 'yuva444p10le',  # This enables the alpha channel
        'media/animation2.mov'
    ]
    subprocess.run(ffmpeg_command)

    # Remove temporary frames
    for file_name in os.listdir(temp_folder):
        os.remove(os.path.join(temp_folder, file_name))
    os.rmdir(temp_folder)

    return
