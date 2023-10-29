import requests
from PIL import Image
from io import BytesIO
import math
import os
import time
from hashlib import md5
from dotenv import load_dotenv
import sys

# Add a cache directory if it doesn't exist
if not os.path.exists('tile_cache'):
    os.makedirs('tile_cache')

def check_image_cache(x, y, zoom):
    cache_key = md5(f"{zoom}/{x}/{y}".encode('utf-8')).hexdigest()
    cache_path = f"tile_cache/{cache_key}.png"
    return os.path.exists(cache_path) # Returns true or false

def get_tile_image_mapbox(x, y, zoom, max_retries=3):
    load_dotenv()
    api_token = os.getenv('MAPBOX_API_TOKEN')  # Get my API key
    base_url = 'https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles'
    url = f"{base_url}/{zoom}/{x}/{y}?access_token={api_token}"

    # Check cache first
    # cache_key = md5(url.encode('utf-8')).hexdigest()
    cache_key = md5(f"{zoom}/{x}/{y}".encode('utf-8')).hexdigest()
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


def get_map(track_metadata, anim_pixels, anim_km, track_points):
    lat_min = track_metadata['min_latitude']
    lat_max = track_metadata['max_latitude']
    lon_min = track_metadata['min_longitude']
    lon_max = track_metadata['max_longitude']

    # Calculate zoom
    tile_img = get_tile_image_mapbox(2,1,2)
    cell_size = tile_img.size[0]
    n = 40075.0 / anim_km * anim_pixels / cell_size * math.cos((lat_max+lat_min)/2*math.pi/180)
    zoom = round(math.log2(n))
    n = 2 ** zoom
    anim_km_actual = 40075.0 / n * anim_pixels / cell_size * math.cos((lat_max+lat_min)/2*math.pi/180)
    print(f"zoom = {zoom}, n = {round(n,2)}, mapwidth = {round(anim_km_actual,2)}")

    # Create a blank image big enough
    x_min, y_max = lat_lon_to_tile_coords(lat_min, lon_min, zoom)
    x_max, y_min = lat_lon_to_tile_coords(lat_max, lon_max, zoom)
    num_tiles_x = x_max - x_min + 3
    num_tiles_y = y_max - y_min + 3
    width, height = num_tiles_x * cell_size, num_tiles_y * cell_size
    map_img = Image.new('RGB', (width, height))

    # Make list of needed tiles
    tile_list = []
    # List first 9 tiles
    x_tile, y_tile = lat_lon_to_tile_coords(track_points[0][7], track_points[0][8], zoom)
    for x in range(x_tile - 1, x_tile + 2):
        for y in range(y_tile - 1, y_tile + 2):
            tile_list.append([x, y])
    # List other tiles
    last_point = track_points[0][1], track_points[0][2]
    for point in track_points:
        segment_dist = math.sqrt((point[1]- last_point[0])**2 + (point[2]-last_point[1])**2)
        if segment_dist > anim_km * 1000 / 2: # Look for tiles if traveled 2 km ish
            last_point = point[1], point[2]
            x_tile, y_tile = lat_lon_to_tile_coords(point[7], point[8], zoom)
            for x in range(x_tile - 1, x_tile + 2):
                for y in range(y_tile - 1, y_tile + 2):
                    # Add to tile_list if not already included
                    if [x, y] not in tile_list:
                        tile_list.append([x, y])
    print(f"Need {len(tile_list)} tiles")

    # Checking how many tiles to download
    download_list = []
    for tile in tile_list:
        has_tile = check_image_cache(tile[0], tile[1], zoom)
        if has_tile == False:
            download_list.append(tile)
    if len(download_list) > 0:
        user_input = input(f"Need to download {len(download_list)} tiles. Proceed? (y/n): ")
        if user_input.lower() != 'y':
            print("Terminating program.")
            sys.exit()

    # Downloading maps
    for point in tile_list:
        x, y = point
        tile_img = get_tile_image_mapbox(x, y, zoom)
        if tile_img is not None:  # Pasting
            map_img.paste(tile_img, ((x - x_min + 1) * cell_size, (y - y_min + 1) * cell_size))

    # Save the stitched map image
    map_img.save('media/map_stitched.png')
    print("Saved map")

    # Calculate map_metadata
    radius = 6371000.0
    meters_per_degree = 2*math.pi/(2**zoom)/cell_size*radius*math.cos((lat_max+lat_min)/2/180*math.pi)
    
    # Get pixels from map edge to path edge
    x_0 = ((lon_min + 180.0) * 2**zoom / 360.0 - (x_min-1)) * cell_size
    y_0 = ((1.0 - math.log(math.tan(math.radians(lat_max)) + (1 / math.cos(math.radians(lat_max)))) / math.pi) / 2.0 * 2**zoom - (y_min-1)) * cell_size

    map_metadata = [meters_per_degree, x_0, y_0]

    return(map_img, map_metadata)




