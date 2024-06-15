import math
from PIL import ImageDraw, ImageFont, Image
import os
import subprocess
import sys
import time
import csv
from datetime import datetime
import json
from animation_utils import make_altibar_frame
from animation_utils import make_minimap_frame
from animation_utils import initialize_minimap


def animate_path(track_points, map_images, map_metadata, outline_image, fps, width, anim_height, transparent, goal_type, goal_text_reference):
    res_scale = anim_height / 1080

    temp_folder = 'temp_frames'
    os.makedirs(temp_folder, exist_ok=True)

    # Initialize minimap-maker
    no_maps = len(map_images)
    no_points =len(track_points)
    path_images = [img.copy() for img in map_images]
    frame_memory = initialize_minimap(track_points[0], no_maps, res_scale, width)

    # Estimate time
    est_time = len(track_points) / 20.0 * (1 + map_images[0].size[0] * map_images[0].size[1] / 17000000.0)
    user_input = input(f"Estimating {round(est_time/60)} minutes to animate. Proceed? (y/n): ")
    if user_input.lower() != 'y':
        print("Terminating program.")
        sys.exit()
    start_runtime = time.time()

    # Saving frames to pngs
    for i in range(0, len(track_points)):
        animation_frame = Image.new("RGBA", (width, anim_height), (0, 0, 0, 0))

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

        # STEP 1: MINI-MAP
        track_point = track_points[i]
        if i == 0:
            track_point_prev = track_point
        # Get minimap frame
        minimap_frame, path_images, frame_memory = make_minimap_frame(frame_memory, path_images, i, no_points, track_point, track_point_prev, map_metadata, res_scale, width)
        track_point_prev = track_point
        position_minimap = (0, animation_frame.size[1] - minimap_frame.size[1])
        animation_frame.paste(minimap_frame, position_minimap, minimap_frame)


        # STEP 2: OUTLINE-MAP
        x_outline = track_points[i]["outline_x"]
        y_outline = track_points[i]["outline_y"]
        # Draws path on image with only path
        draw4 = ImageDraw.Draw(outline_image)
        if i > 0:
            draw4.line((last_x_outline, last_y_outline, x_outline, y_outline), fill=(255,0,0,200), width=round(res_scale))
        last_x_outline, last_y_outline = x_outline, y_outline
        # Draws dot at the end of path (but doesnt mess with outline_image)
        outline_with_dot = outline_image.copy()
        draw5 = ImageDraw.Draw(outline_with_dot)
        draw5.ellipse([x_outline - 3*res_scale, y_outline - 3*res_scale, x_outline + 3*res_scale, y_outline + 3*res_scale], fill='red', outline ='black')

        position_outline = (round(10*res_scale), round(anim_height*0.1))
        animation_frame.paste(outline_with_dot, position_outline, outline_with_dot)


        # STEP 3: ALTIBAR
        max_altitude = max(point["altitude"] for point in track_points)
        altibar_height = round(280 * res_scale)
        if i == 0 or i == len(track_points)-1:
            elevation_active = False
        else:
            elevation_active = True
        altibar_image = make_altibar_frame(width, altibar_height, res_scale, altitude, elevation, vario, vario_lr, max_altitude, altitude_lr, elevation_lr, elevation_active)
        altibar_y = position_minimap[1] - altibar_height - round(anim_height*0.05)
        animation_frame.paste(altibar_image, (0,altibar_y), altibar_image)

        # STEP 5: DRAW TEXT
        # Draw datetime
        current_time = localtime.strftime("%H:%M")
        current_date = localtime.strftime("%Y-%m-%d")

        draw6 = ImageDraw.Draw(animation_frame)
        draw6.text((30*res_scale,30*res_scale), current_time, font=ImageFont.truetype("arial.ttf", round(40*res_scale)), fill='white')
        draw6.text((38*res_scale,76*res_scale), current_date, font=ImageFont.truetype("arial.ttf", round(16*res_scale)), fill='white')

        # Draw goal
        textsize = round(18*res_scale)
        font = ImageFont.truetype("arial.ttf", textsize)
        if goal_type == '3tp_distance': # 3tp-distance
            goal_text = f"Distance (3tp): {round(distance_3tp/1000)} km\n{goal_text_reference}"
        elif goal_type == 'open_distance': # open distance
            goal_text = f"Open distance: {round(open_distance/1000)} km\n{goal_text_reference}"
        
        draw6.text((8*res_scale, position_minimap[1] - anim_height*0.05), goal_text, font=font, fill='white', stroke_width=1, stroke_fill='black')

        # STEP 6: SAVE FRAME
        frame_path = os.path.join(temp_folder, f'frame_{i:06d}.png')
        animation_frame.save(frame_path, 'PNG')

        if ((i % 400 == 0) and (i != 0)) or (i == 50): 
            time_left = (time.time() - start_runtime) * (len(track_points) / i - 1)
            print(f"Progress: {round(i/len(track_points)*100)}%, {round(time_left/60)} min remaining...")
        if i == round(len(track_points)/3):
            animation_frame.save('media/frame_example.png')
        elif i == 0:
            animation_frame.save('media/frame_first.png')
        elif i == len(track_points)-1:
            animation_frame.save('media/frame_last.png')
    

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

    anim_height = 1080
    overlay_width = 250
    fps = 30
    transparent = False
    goal_type = '3tp_distance'
    goal_text_reference = 'PB: 22 km'

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

    animate_path(track_points, map_images, map_metadata, outline_image_static, fps, overlay_width, anim_height, transparent, goal_type, goal_text_reference)


