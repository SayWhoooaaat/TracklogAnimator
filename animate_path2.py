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


def animate_path2(track_points, map_image, map_metadata, outline_image, fps, overlay_width, total_height):
    transparent = False
    path_linewidth = 1
    arrow = [(-8,-6), (8,0), (-8,6)]

    m_px = map_metadata[6]
    height, width = overlay_width, overlay_width
    center_factor = 0.3
    center_radius = center_factor / 2 * min(height,width)

    # Initializes mini-map image
    path_image = map_image.copy()
    draw = ImageDraw.Draw(path_image)

    temp_folder = 'temp_frames'
    os.makedirs(temp_folder, exist_ok=True)

    # Initialize mode parameters
    camera = 1
    multicamera_start = 0
    t1 = 5
    t2 = 1
    t3 = 3
    t4 = 1
    t5 = 5
    x_pixels_min = track_points[0][10]
    x_pixels_max = track_points[0][10]
    y_pixels_min = track_points[0][11]
    y_pixels_max = track_points[0][11]

    # Estimate time
    est_time = len(track_points) / 10.0 * (1 + path_image.size[0] * path_image.size[1] / 21000000.0)
    user_input = input(f"Estimating {round(est_time/60)} minutes to animate. Proceed? (y/n): ")
    if user_input.lower() != 'y':
        print("Terminating program.")
        sys.exit()
    start_runtime = time.time()

    # Saving frames to pngs
    for i in range(0, len(track_points)):
        phi = track_points[i][5]
        # STEP 1: MAKE MINI-MAP FRAME
        x = track_points[i][10]
        y = track_points[i][11]
        # Draws path on image with only path
        if i > 0:
            draw.line((last_x, last_y, x, y), fill='red', width=path_linewidth)
        last_x, last_y = x, y

        # Draws arrow at the end of path (but doesnt mess with path_image)
        image_with_arrow = path_image.copy()
        draw2 = ImageDraw.Draw(image_with_arrow)
        angled_arrow = [(x + px * math.cos(phi) - py * math.sin(phi), y + px * math.sin(phi) + py * math.cos(phi)) for px, py in arrow]
        draw2.polygon(angled_arrow, fill='red', outline ='black')

        # Calculate big frame bounds (for highest zoom map)
        padding = 30
        if x > x_pixels_max:
            x_pixels_max = x
        elif x < x_pixels_min:
            x_pixels_min = x
        if y > y_pixels_max:
            y_pixels_max = y
        elif y < y_pixels_min:
            y_pixels_min = y
        
        pixel_width_big = 2*padding + max(x_pixels_max-x_pixels_min, y_pixels_max-y_pixels_min)    
        pixel_height_big = pixel_width_big
        frame_center_x_big = (x_pixels_max + x_pixels_min) / 2
        frame_center_y_big = (y_pixels_max + y_pixels_min) / 2

        # Determine camera 
        video_time_remaining = (len(track_points) - i) / fps
        video_time = (i - multicamera_start) / fps
        tm = video_time % (t1+t2+t3+t4)
        if pixel_width_big < 0.3 * width: # change to 2
            camera = 1
            multicamera_start = i # Delays multicamera start
        elif video_time_remaining <= t5:
            camera = 3
        elif video_time_remaining <= t5 + t2:
            camera = 2
        elif video_time_remaining <= t5 + t2 + t1: # Need tm to increase through t1 to fit with t2
            camera = 1
        elif tm < t1:
            camera = 1
            # Check if close to end time
            if video_time_remaining <= t5 + t2 + t1 + t4 + t3 + t2:
                multicamera_start = i # Locks tm before final zoomout, and keeps camera1
        elif (tm < t1 + t2):
            camera = 2
        elif (tm < t1 + t2 + t3):
            camera = 3
        else:
            camera = 4
        
        # Crop image based on camera angle
        if camera == 1:
            if tm == 0: # center for first iteration
                xc, yc = x, y
            # Crop out desired frame
            center_distance = math.sqrt((x-xc)**2+(y-yc)**2)
            if center_distance > center_radius: # Move frame center
                beta = math.atan2(y-yc,x-xc)
                xc = xc + (center_distance - center_radius) * math.cos(beta)
                yc = yc + (center_distance - center_radius) * math.sin(beta)
            cropped_image = image_with_arrow.crop((xc - width/2.0, yc - height/2.0, xc + width/2.0, yc + height/2.0))
            scale = 1
            
        elif camera == 2:
            # Zoom out
            fraction = (tm - t1) / t2
            fraction = 0.5 - 0.5 * math.cos(fraction * math.pi)
            pixel_width = width + (pixel_width_big - width) * fraction
            frame_center_x = xc + (frame_center_x_big - xc) * fraction
            frame_center_y = yc + (frame_center_y_big - yc) * fraction
            x_min = frame_center_x - pixel_width/2
            x_max = frame_center_x + pixel_width/2
            y_min = frame_center_y - pixel_width/2
            y_max = frame_center_y + pixel_width/2
            cropped_image = image_with_arrow.crop((x_min, y_min, x_max, y_max))
            cropped_image = cropped_image.resize((width, width))
            scale = pixel_width / width

        elif camera == 3:
            # Stay zoomed out
            x_min = frame_center_x_big - pixel_width_big/2
            x_max = frame_center_x_big + pixel_width_big/2
            y_min = frame_center_y_big - pixel_width_big/2
            y_max = frame_center_y_big + pixel_width_big/2
            cropped_image = image_with_arrow.crop((x_min, y_min, x_max, y_max))
            cropped_image = cropped_image.resize((width, width))
            scale = pixel_width_big / width

        else: # camera 4
            # Zoom in
            fraction = 1 - (tm - t1 - t2 - t3) / t4
            fraction = 0.5 - 0.5 * math.cos(fraction * math.pi)
            pixel_width = width + (pixel_width_big - width) * fraction
            frame_center_x = x + (frame_center_x_big - x) * fraction
            frame_center_y = y + (frame_center_y_big - y) * fraction
            x_min = frame_center_x - pixel_width/2
            x_max = frame_center_x + pixel_width/2
            y_min = frame_center_y - pixel_width/2
            y_max = frame_center_y + pixel_width/2
            cropped_image = image_with_arrow.crop((x_min, y_min, x_max, y_max))
            cropped_image = cropped_image.resize((width, width))
            scale = pixel_width / width

        # Redraw line if zoomed out
        draw3 = ImageDraw.Draw(cropped_image)
        if camera > 1:
            for j in range (1, i): # O^2 computing...
                x_reframed = (track_points[j][10] - x_min) / scale
                x_r_prev = (track_points[j-1][10] - x_min) / scale
                y_reframed = (track_points[j][11] - y_min) / scale
                y_r_prev = (track_points[j-1][11] - y_min) / scale
                draw3.line((x_r_prev, y_r_prev, x_reframed, y_reframed), fill='red', width=path_linewidth)
            angled_arrow = [(x_reframed + px * math.cos(phi) - py * math.sin(phi), y_reframed + px * math.sin(phi) + py * math.cos(phi)) for px, py in arrow]
            draw3.polygon(angled_arrow, fill='red', outline ='black')

        # Draw ruler on cropped image
        m_px2 = m_px * scale
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


# Script starts here. 
def parse_date(date_str):
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f%z', '%Y-%m-%d %H:%M:%S%z'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date format not recognized: {date_str}")

def parse_row(row):
    row[0] = parse_date(row[0])  # Parse the first value as a datetime object
    row[9] = parse_date(row[9])  # Parse the tenth value as a datetime object
    row[1:9] = [float(value) for value in row[1:9]]  # Parse values 2-9 as floats
    row[10:] = [float(value) for value in row[10:]]  # Parse values 11 onwards as floats
    return row

with open('array_output.csv', 'r', newline='') as f:
    reader = csv.reader(f)
    track_points = [parse_row(row) for row in reader]

fps = 30
anim_height = 1080
overlay_width = 300

radius = 6371000.0 #m
zoom = 11
cell_size = 512
lat = track_points[0][6]
m_px = 2*math.pi/(2**zoom)/cell_size*radius*math.cos(lat/180*math.pi) # Mercator imprecise
minimap_metadata = [0, 0, 0, 0, 0, 0, m_px]

Image.MAX_IMAGE_PIXELS = None
minimap_img = Image.open('media/map_stitched.png')
outline_img = Image.open('media/country_outline.png')

playtime = 25
offset = 30
start_point = offset * fps
end_point = (offset + playtime) * fps
animate_path2(track_points[start_point:end_point], minimap_img, minimap_metadata, outline_img, fps, overlay_width, anim_height)
