import requests
from PIL import ImageDraw, ImageFont, Image
from io import BytesIO
import math
import os
import time
from hashlib import md5
from dotenv import load_dotenv
import sys
import csv
from datetime import datetime
import json

# Add a cache directory if it doesn't exist
if not os.path.exists('tile_cache'):
    os.makedirs('tile_cache')

def check_image_cache(x, y, zoom):
    tile_type = 'saywhoooaaat/clok9ytkg006501pl9gima19q'
    cache_key = md5(f"{tile_type}/{zoom}/{x}/{y}".encode('utf-8')).hexdigest()
    cache_path = f"tile_cache/{cache_key}.png"
    return os.path.exists(cache_path) # Returns true or false

def get_tile_image_mapbox(x, y, zoom, max_retries=3):
    load_dotenv()
    api_token = os.getenv('MAPBOX_API_TOKEN')  # Get my API key
    #tile_type = 'mapbox/satellite-v9' # Standard satellite map
    #tile_type = 'saywhoooaaat/clok9xop3006701qy7n8s8s8t' # Custom outdoors-map
    tile_type = 'saywhoooaaat/clok9ytkg006501pl9gima19q' # Custom satellite-map
    base_url = f"https://api.mapbox.com/styles/v1/{tile_type}/tiles"
    url = f"{base_url}/{zoom}/{x}/{y}?access_token={api_token}"

    # Check cache first
    cache_key = md5(f"{tile_type}/{zoom}/{x}/{y}".encode('utf-8')).hexdigest()
    cache_path = f"tile_cache/{cache_key}.png"
    if os.path.exists(cache_path):
        return Image.open(cache_path)

    # If not in cache, download
    print("Downloading map tile")
    retries = 0
    while retries < max_retries:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.save(cache_path)  # Save to cache
            return img
        retries += 1
        time.sleep(1)  # Sleep for 1 second before retrying

    print(f'Unable to download map image for tile ({x}, {y}, {zoom})')
    return None


def lat_lon_to_tile_coords(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x_tile = ((lon_deg + 180.0) / 360.0 * n)
    y_tile = ((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return int(x_tile), int(y_tile)


def get_map(track_metadata, anim_pixels, overlay_width, anim_km, track_points, target_coords):
    scale = overlay_width / anim_pixels
    lat_min = track_metadata['min_latitude']
    lat_max = track_metadata['max_latitude']
    lon_min = track_metadata['min_longitude']
    lon_max = track_metadata['max_longitude']

    radius = 6371000.0

    # Calculate max zoom
    tile_img = get_tile_image_mapbox(2,1,2)
    cell_size = tile_img.size[0]
    n = 40075.0 / anim_km * anim_pixels / cell_size * math.cos((lat_max+lat_min)/2*math.pi/180)
    zoom_max = round(math.log2(n))
    n = 2 ** zoom_max

    # Calculate min zoom
    n2 = anim_pixels / cell_size * 360 / max(lon_max - lon_min, (lat_max - lat_min) / math.cos((lat_max+lat_min)/2*math.pi/180))
    zoom_min = int(math.log2(n2))
    zoom_min = min(zoom_min, zoom_max)
    print(lat_min, lat_max, lon_min, lon_max, n2)
    print(f"zoom_max = {zoom_max}, zoom_min = {zoom_min}")

    # Make list of needed tiles
    tile_list = []
    for zoom in range(zoom_max, zoom_min - 1, -1):
        # List first 9 tiles
        x_tile, y_tile = lat_lon_to_tile_coords(track_points[0]["lat"], track_points[0]["lon"], zoom)
        for x in range(x_tile - 1, x_tile + 2):
            for y in range(y_tile - 1, y_tile + 2):
                tile_list.append([x, y, zoom])
        # List other tiles
        prev_lat = track_points[0]["lat"]
        prev_lon = track_points[0]["lon"]
        for point in track_points:
            d_y = (prev_lat - point["lat"]) / 180 * math.pi * radius
            d_x = (point["lon"] - prev_lon) / 180 * math.pi * math.cos(prev_lat/180*math.pi) * radius
            segment_dist = math.sqrt(d_x**2 + d_y**2)            
            if segment_dist > anim_km * 1000 / 2: # Look for tiles if traveled half map length
                prev_lat = point["lat"]
                prev_lon = point["lon"]
                x_tile, y_tile = lat_lon_to_tile_coords(point["lat"], point["lon"], zoom)
                for x in range(x_tile - 1, x_tile + 2):
                    for y in range(y_tile - 1, y_tile + 2):
                        # Add to tile_list if not already included
                        if [x, y, zoom] not in tile_list:
                            tile_list.append([x, y, zoom])
    print(f"Need {len(tile_list)} tiles")
    
    # Checking how many tiles to download
    download_list = []
    for tile in tile_list:
        has_tile = check_image_cache(tile[0], tile[1], tile[2])
        if has_tile == False:
            download_list.append(tile)
    if len(download_list) > 0:
        user_input = input(f"Need to download {len(download_list)} tiles. Proceed? (y/n): ")
        if user_input.lower() != 'y':
            print("Terminating program.")
            sys.exit()
    else:
        print("All tiles are stored in cache. Stitching images...")
    
    # Stitching maps
    map_images = []
    map_metadata = []
    for zoom in range(zoom_max, zoom_min - 1, -1):
        i = zoom_max - zoom
        # Create a blank image big enough
        x_min, y_max = lat_lon_to_tile_coords(lat_min, lon_min, zoom)
        x_max, y_min = lat_lon_to_tile_coords(lat_max, lon_max, zoom)
        num_tiles_x = x_max - x_min + 3
        num_tiles_y = y_max - y_min + 3
        width, height = num_tiles_x * cell_size, num_tiles_y * cell_size
        map_images.append(Image.new('RGB', (width, height)))
        for point in tile_list:
            if point[2] == zoom:
                x, y, zoom = point
                tile_img = get_tile_image_mapbox(x, y, zoom)
                if tile_img is not None:  # Pasting
                    map_images[i].paste(tile_img, ((x - x_min + 1) * cell_size, (y - y_min + 1) * cell_size))
        # Some stuff
        width = round(map_images[i].size[0] * scale)
        height = round(map_images[i].size[1] * scale)
        new_size = (width, height)
        map_images[i] = map_images[i].resize(new_size, Image.Resampling.LANCZOS)

        
        # Calculate map_metadata
        m_px = 2*math.pi/(2**zoom)/cell_size/scale*radius*math.cos((lat_max+lat_min)/2/180*math.pi) # Mercator imprecise
        lon_min_tile = (x_min - 1) * 360 / 2.0**zoom - 180
        lon_max_tile = (x_max + 2) * 360 / 2.0**zoom - 180
        lat_max_tile = 360 / math.pi * (math.atan(math.exp(math.pi * (1 - 2 * (y_min - 1) / 2.0**zoom))) - math.pi / 4)
        lat_min_tile = 360 / math.pi * (math.atan(math.exp(math.pi * (1 - 2 * (y_max + 2) / 2.0**zoom))) - math.pi / 4)

        # Draw target on map
        target_radius_km = 400
        if target_coords != None:
            # Find pixel points
            x_target = (target_coords[1] - lon_min_tile)/(lon_max_tile - lon_min_tile) * width
            
            yp = math.log(math.tan(math.pi/4 + target_coords[0]/360*math.pi))
            y_bottom = math.log(math.tan(math.pi/4 + lat_min_tile/360*math.pi))
            y_top = math.log(math.tan(math.pi/4 + lat_max_tile/360*math.pi))
            y_target = (y_top - yp)/(y_top - y_bottom) * height

            # make transparent overlay
            map_images[i] = map_images[i].convert("RGBA")
            trans_image = Image.new('RGBA', (width, height))
            draw = ImageDraw.Draw(trans_image)
            target_radius = target_radius_km / m_px
            target_radius = max(target_radius, 10*scale)
            target_pos = [x_target-target_radius, y_target-target_radius, x_target+target_radius, y_target+target_radius]
            draw.ellipse(target_pos, fill=(0,128,0,100), outline ='white')

            combined = Image.alpha_composite(map_images[i], trans_image)
            map_images[i] = combined
            map_images[i] = map_images[i].convert("RGB")
        else:
            x_target = None
            y_target = None

        map_metadata.append([lon_min_tile, lat_min_tile, lon_max_tile, lat_max_tile, width, height, m_px, x_target, y_target])

        # Save map
        map_images[i].save(f'media/map_stitched{i}.png')

    print("Saved maps")

    # Save metadata
    with open('minimap_metadata.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(map_metadata)


    return(map_images, map_metadata)




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

    # Find track metadata
    track_metadata = {
        'max_latitude': -float('inf'),
        'min_latitude': float('inf'),
        'max_longitude': -float('inf'),
        'min_longitude': float('inf'),
        'dt': 1, # dummy, not used
    }
    for i in range(0, len(track_points)):
        lat = track_points[i]['lat']
        lon = track_points[i]['lon']
        track_metadata['max_latitude'] = max(track_metadata['max_latitude'], lat)
        track_metadata['min_latitude'] = min(track_metadata['min_latitude'], lat)
        track_metadata['max_longitude'] = max(track_metadata['max_longitude'], lon)
        track_metadata['min_longitude'] = min(track_metadata['min_longitude'], lon)

    # make up rest of data
    width = round(1080 / 9 * 16 * 14 / 100)
    anim_km = 4 # Should be 16
    target_coords = [28.101484, -16.750003]

    get_map(track_metadata, width, width, anim_km, track_points, target_coords)
    



