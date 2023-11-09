import math
from PIL import ImageDraw, ImageFont, Image
import os
import subprocess
import sys
import json
import time
import numpy as np
from sklearn.linear_model import LinearRegression

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


def animate_path(track_points, map_image, map_metadata, outline_image, fps, overlay_width, total_height):
    transparent = False
    m_px = map_metadata[6]
    arrow = [(-8,-6), (8,0), (-8,6)]

    height, width = overlay_width, overlay_width
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

    # Estimate time
    start_time = time.time()
    timing_data_file = 'timing_data.json'
    try:
        with open(timing_data_file, 'r') as f:
            timing_data = json.load(f)
            times = np.array([row[0] + row[1] for row in timing_data][-8:])
            lens = np.array([row[2] for row in timing_data][-8:])
            pixels = np.array([row[3] for row in timing_data][-8:])
            X = np.vstack((lens, lens * pixels)).T
            model = LinearRegression()
            model.fit(X, times)
            a, b = model.coef_
            c = model.intercept_
            est_time = len(track_points) * a * (1 + path_image.size[0] * path_image.size[1] * b) + c
    except:
        timing_data = []
        est_time = len(track_points) / 10.0 * (1 + path_image.size[0] * path_image.size[1] / 21000000.0)
    
    print(f"Making animation frames. Estimating {round(est_time/60)} minutes...") 
    # Saving frames to pngs
    for i in range(0, len(track_points)):
        phi = track_points[i][5]
        # STEP 1: MAKE MINI-MAP FRAME
        x = track_points[i][10]
        y = track_points[i][11]
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
        x_outline = track_points[i][12]
        y_outline = track_points[i][13]
        # Draws path on image with only path
        draw4 = ImageDraw.Draw(outline_image)
        if i > 0:
            draw4.line((last_x_outline, last_y_outline, x_outline, y_outline), fill=(255,0,0,200), width=1)
        last_x_outline, last_y_outline = x_outline, y_outline
        # Draws arrow at the end of path (but doesnt mess with path_image)
        outline_with_dot = outline_image.copy()
        draw5 = ImageDraw.Draw(outline_with_dot)
        draw5.ellipse([x_outline - 2, y_outline - 2, x_outline + 2, y_outline + 2], fill='red')

        # STEP 3: PUT IMAGES TOGETHER
        animation_frame = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
        cropped_image = cropped_image.convert("RGBA")

        position_minimap = (0, animation_frame.size[1] - cropped_image.size[1])
        position_outline = (0, animation_frame.size[1] - cropped_image.size[1] - outline_image.size[1] - 50)

        animation_frame.paste(cropped_image, position_minimap, cropped_image)
        animation_frame.paste(outline_with_dot, position_outline, outline_with_dot)

        # Drawing text
        timedate, x, y, ele, v, phi, lat, lon, dist, localtime, *_ = track_points[i]
        current_time = localtime.strftime("%H:%M")
        current_date = localtime.strftime("%Y-%m-%d")

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
        if i == round(len(track_points)/3):
            animation_frame.save('media/frame_example.png')

    time_inbetween = time.time()

    # Use FFmpeg to compile PNGs into a video with ProRes 4444 codec
    print("Stitching frames to video...")
    if transparent == True:
        ffmpeg_command = [
            'ffmpeg',
            '-y',
            '-framerate', str(fps),
            '-i', f'{temp_folder}/frame_%06d.png',
            '-vcodec', 'prores_ks',
            '-profile:v', '4444',  # This is for ProRes 4444
            '-pix_fmt', 'yuva444p10le',  # This enables the alpha channel
            'media/animation.mov'
        ]
    else:
        ffmpeg_command = [
            'ffmpeg',
            '-y',
            '-framerate', str(fps),
            '-i', f'{temp_folder}/frame_%06d.png',
            '-vcodec', 'prores_ks',
            '-profile:v', '4444',  # This is for ProRes 4444
            '-pix_fmt', 'yuv444p10le',  # No alpha channel
            'media/animation.mov'
        ]
    subprocess.run(ffmpeg_command)

    # Remove temporary frames
    for file_name in os.listdir(temp_folder):
        os.remove(os.path.join(temp_folder, file_name))
    #os.rmdir(temp_folder)

    # Save spent time
    with open(timing_data_file, 'w') as f:
        timing_data.append([time_inbetween-start_time, time.time() - time_inbetween, len(track_points), path_image.size[0] * path_image.size[1]])
        json.dump(timing_data, f)

    return
