import math
from PIL import ImageDraw, ImageFont, Image
import os
import subprocess
import sys
import time
import csv
from datetime import datetime

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


def animate_path(track_points, map_images, map_metadata, outline_image, fps, overlay_width, total_height, transparent):
    res_scale = total_height / 1080
    path_linewidth = 1
    arrow = [(-8,-6), (8,0), (-8,6)]
    vertical_arrow = [(-1,-3), (1,-3), (1,0), (2,0), (0,3), (-2,0), (-1,0)]
    horizontal_arrow = [(-3,-1), (-3,1), (0,1), (0,2), (3,0), (0,-2), (0,-1)]
    horizontal_arrow = [(160 + px*3, 762 + py*3) for px, py in horizontal_arrow]

    temp_folder = 'temp_frames'
    os.makedirs(temp_folder, exist_ok=True)

    m_px = map_metadata[0][6]
    height, width = overlay_width, overlay_width
    center_factor = 0.3
    center_radius = center_factor / 2 * min(height,width)

    # Find map offsets (should move to map_metadata)
    x_offsets = []
    y_offsets = []
    for i in range(0,len(map_images)):
        scale = 2 ** i
        x_offsets.append(track_points[0]["map_coordinate"][i]["x"] * scale - track_points[0]["map_coordinate"][0]["x"])
        y_offsets.append(track_points[0]["map_coordinate"][i]["y"] * scale - track_points[0]["map_coordinate"][0]["y"])

    # Initialize mode parameters
    x_pixels_min = track_points[0]["map_coordinate"][0]["x"]
    x_pixels_max = track_points[0]["map_coordinate"][0]["x"]
    y_pixels_min = track_points[0]["map_coordinate"][0]["y"]
    y_pixels_max = track_points[0]["map_coordinate"][0]["y"]

    # Initializes positions and mini-map images
    path_image = []
    center_pilot_x = []
    center_pilot_y = []
    draw = []
    for p in range(0, len(map_images)): # all maps
        path_image.append(map_images[p].copy())
        draw.append(ImageDraw.Draw(path_image[p]))
        center_pilot_x.append(0)
        center_pilot_y.append(0)
    
    # Estimate time
    est_time = len(track_points) / 20.0 * (1 + path_image[0].size[0] * path_image[0].size[1] / 21000000.0)
    user_input = input(f"Estimating {round(est_time/60)} minutes to animate. Proceed? (y/n): ")
    if user_input.lower() != 'y':
        print("Terminating program.")
        sys.exit()
    start_runtime = time.time()

    # Saving frames to pngs
    for i in range(0, len(track_points)):
        phi = track_points[i]["direction"]
        # STEP 1: MINI-MAP
        # Draw path on all maps:
        x_pixel = []
        y_pixel = []
        x_pixel_last = []
        y_pixel_last = []
        center_path_x = []
        center_path_y = []
        center_frame_x = []
        center_frame_y = []
        for p in range(0, len(map_images)):
            x_pixel.append(track_points[i]["map_coordinate"][p]["x"])
            y_pixel.append(track_points[i]["map_coordinate"][p]["y"])
            # Drawing path
            if i > 0:
                x_pixel_last.append(track_points[i-1]["map_coordinate"][p]["x"])
                y_pixel_last.append(track_points[i-1]["map_coordinate"][p]["y"])
                draw[p].line((x_pixel_last[p], y_pixel_last[p], x_pixel[p], y_pixel[p]), fill='red', width=path_linewidth)

        # Frame center pilot: 
        if i == 0: # center for first iteration
            center_pilot_x[0], center_pilot_y[0] = x_pixel[0], y_pixel[0]
        center_distance = math.sqrt((x_pixel[0]-center_pilot_x[0])**2+(y_pixel[0]-center_pilot_y[0])**2)
        if center_distance > center_radius: # Move frame center
            beta = math.atan2(y_pixel[0]-center_pilot_y[0],x_pixel[0]-center_pilot_x[0])
            center_pilot_x[0] = center_pilot_x[0] + (center_distance - center_radius) * math.cos(beta)
            center_pilot_y[0] = center_pilot_y[0] + (center_distance - center_radius) * math.sin(beta)
        
        if len(map_images) > 1: # Apply new coordinates to all other maps (only to map number(?))
            for p in range(1, len(map_images)): 
                center_pilot_x[p] = (center_pilot_x[0] + x_offsets[p]) / (2 ** p)
                center_pilot_y[p] = (center_pilot_y[0] + y_offsets[p]) / (2 ** p)
        
        # Frame center path:
        x = track_points[i]["map_coordinate"][0]["x"]
        y = track_points[i]["map_coordinate"][0]["y"]
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

        if len(map_images) > 1: # Apply new coordinates to all other maps (only to map number(?))
            for p in range(1, len(map_images)): 
                center_path_x.append((center_path_x[0] + x_offsets[p]) / (2 ** p))
                center_path_y.append((center_path_y[0] + y_offsets[p]) / (2 ** p))

        # Interpolate path center (only to map number(?))
        for p in range(0, len(map_images)):
            center_frame_x.append(center_pilot_x[p] * (1 - track_points[i]["fraction"]) + center_path_x[p] * track_points[i]["fraction"])
            center_frame_y.append(center_pilot_y[p] * (1 - track_points[i]["fraction"]) + center_path_y[p] * track_points[i]["fraction"])
        
        # Choose appropriate sized map
        map_number = int(track_points[i]["zoom_level"]) # rounds down

        # Draws arrow at the end of path (but doesnt mess with path_images) 
        image_with_arrow = path_image[map_number].copy()
        draw2 = ImageDraw.Draw(image_with_arrow)
        angled_arrow = [(x_pixel[map_number] + px * math.cos(phi) - py * math.sin(phi), y_pixel[map_number] + px * math.sin(phi) + py * math.cos(phi)) for px, py in arrow]
        draw2.polygon(angled_arrow, fill='red', outline ='black')

        # Crop and scale
        temp_width = width * 2**track_points[i]["zoom_level"] / 2**map_number
        cropped_image = image_with_arrow.crop((center_frame_x[map_number] - temp_width/2.0, center_frame_y[map_number] - temp_width/2.0, center_frame_x[map_number] + temp_width/2.0, center_frame_y[map_number] + temp_width/2.0))
        cropped_image = cropped_image.resize((width, width))
        draw3 = ImageDraw.Draw(cropped_image)

        # Draw ruler on cropped image
        m_px2 = m_px * 2**track_points[i]["zoom_level"] # Instead of scale?
        ruler_km = get_ruler_km(width * m_px2 / 1000)
        ruler_pixels = ruler_km * 1000 / m_px2
        ruler_text = f"{ruler_km} km"
        font = ImageFont.truetype("arial.ttf", size=14)

        draw3.line((width-8, height-14, width-8, height-8), fill='white', width=1)
        draw3.line((width-8, height-8, width-8-ruler_pixels, height-8), fill='white', width=1)
        draw3.line((width-8-ruler_pixels, height-8, width-8-ruler_pixels, height-14), fill='white', width=1)
        bbox = draw3.textbbox((0, 0), ruler_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw3.text((width-18-ruler_pixels-text_width, height-8-text_height), ruler_text, fill="white", font=font)


        # STEP 2: MAKE OUTLINE-MAP FRAME
        x_outline = track_points[i]["outline_x"]
        y_outline = track_points[i]["outline_y"]
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
        position_outline = (0, animation_frame.size[1] - cropped_image.size[1] - outline_image.size[1] - 70)

        animation_frame.paste(cropped_image, position_minimap, cropped_image)
        animation_frame.paste(outline_with_dot, position_outline, outline_with_dot)

        # Drawing text
        localtime = track_points[i]["local_time"]
        ele = track_points[i]["elevation"]
        agl = track_points[i]["agl"]
        v = track_points[i]["velocity"]
        dist = track_points[i]["distance"]
        vario = track_points[i]["vario"]
        vario_lr = track_points[i]["vario_low_refresh"]

        current_time = localtime.strftime("%H:%M")
        current_date = localtime.strftime("%Y-%m-%d")

        draw6 = ImageDraw.Draw(animation_frame)
        draw6.text((30,30), current_time, font=ImageFont.truetype("arial.ttf", 40), fill='white')
        draw6.text((38,76), current_date, font=ImageFont.truetype("arial.ttf", 16), fill='white')
        draw6.text((30,720), f"{round(agl/10)*10} m", font=ImageFont.truetype("arial.ttf", 24), fill='white')
        # Draw vario-arrow
        arrow_scale = -min(6, 3 - vario / 2) if vario < 0 else 3
        scaled_arrow = [(160 + px * arrow_scale, 736 + py * arrow_scale) for px, py in vertical_arrow]
        draw6.polygon(scaled_arrow, outline ='white', width=2)
        draw6.text((180,720), f"{round(abs(vario_lr*3.6))} km/h", font=ImageFont.truetype("arial.ttf", 24), fill='white')
        # Draw static speed arrow
        draw6.polygon(horizontal_arrow, outline ='white', width=2)
        draw6.text((180,750), f"{round(v*3.6)} km/h", font=ImageFont.truetype("arial.ttf", 24), fill='white')
        draw6.text((30,750), f"{round(dist/1000)} km", font=ImageFont.truetype("arial.ttf", 24), fill='white')

        # Save frame as png:
        frame_path = os.path.join(temp_folder, f'frame_{i:06d}.png')
        animation_frame.save(frame_path, 'PNG')

        if ((i % 400 == 0) and (i != 0)) or (i == 50): 
            time_left = (time.time() - start_runtime) * (len(track_points) / i - 1)
            print(f"Progress: {round(i/len(track_points)*100)}%, {round(time_left/60)} min remaining...")
        if i == round(len(track_points)/3):
            animation_frame.save('media/frame_example.png')

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

    return

