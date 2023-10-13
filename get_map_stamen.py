import requests
from PIL import Image
from io import BytesIO
import math
import os
import time
from hashlib import md5

# Add a cache directory if it doesn't exist
if not os.path.exists('tile_cache'):
    os.makedirs('tile_cache')

def get_tile_image(x, y, zoom, maptype='terrain', max_retries=3):
    base_url = 'http://tile.stamen.com'
    url = f"{base_url}/{maptype}/{zoom}/{x}/{y}.png"

    # Check cache first
    cache_key = md5(url.encode('utf-8')).hexdigest()
    cache_path = f"tile_cache/{cache_key}.png"
    if os.path.exists(cache_path):
        return Image.open(cache_path)

    # If not in cache, download
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


def get_map_stamen(track_metadata, zoom):
    cell_size = 256
    lat_min = track_metadata['min_latitude']
    lat_max = track_metadata['max_latitude']
    lon_min = track_metadata['min_longitude']
    lon_max = track_metadata['max_longitude']
    x_min, y_max = lat_lon_to_tile_coords(lat_min, lon_min, zoom)
    x_max, y_min = lat_lon_to_tile_coords(lat_max, lon_max, zoom)
    
    # Calculate the total number of tiles in x and y directions
    num_tiles_x = x_max - x_min + 3
    num_tiles_y = y_max - y_min + 3
    print("tiles are", num_tiles_x, "wide and", num_tiles_y, "tall")
    
    # Create a new image big enough to hold all the tiles
    width, height = num_tiles_x * 256, num_tiles_y * 256
    map_img = Image.new('RGB', (width, height))

    # Fetch each tile and paste it into the map image
    for x in range(x_min - 1, x_max + 2):
        for y in range(y_min - 1, y_max + 2):
            tile_img = get_tile_image(x,y,zoom)
            if tile_img is not None:  # Only paste if the image was successfully downloaded
                map_img.paste(tile_img, ((x - x_min + 1) * cell_size, (y - y_min + 1) * cell_size))

    # Save the stitched map image
    map_img.save('map_stitched.png')

    map_metadata = [zoom, x_min - 1, y_min - 1, cell_size]

    return(map_img, map_metadata)




