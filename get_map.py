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


def get_map(track_metadata, anim_pixels, anim_km, track_points):
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
    anim_km_actual = 40075.0 / n * anim_pixels / cell_size * math.cos((lat_max+lat_min)/2*math.pi/180)

    # Calculate min zoom
    n2 = anim_pixels / cell_size * 360 / max(lon_max - lon_min, (lat_max - lat_min) / math.cos((lat_max+lat_min)/2*math.pi/180))
    zoom_min = int(math.log2(n2))
    print(lat_min, lat_max, lon_min, lon_max, n2)
    print(f"zoom_max = {zoom_max}, zoom_min = {zoom_min}")

    # Make list of needed tiles
    tile_list = []
    map_images = []
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
    
    # Downloading maps
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
        #map_images[i] = Image.new('RGB', (width, height))
        for point in tile_list:
            if point[2] == zoom:
                x, y, zoom = point
                tile_img = get_tile_image_mapbox(x, y, zoom)
                if tile_img is not None:  # Pasting
                    map_images[i].paste(tile_img, ((x - x_min + 1) * cell_size, (y - y_min + 1) * cell_size))
        # Save the stitched map image
        map_images[i].save(f'media/map_stitched{i}.png')
    
        # Calculate map_metadata
        m_px = 2*math.pi/(2**zoom)/cell_size*radius*math.cos((lat_max+lat_min)/2/180*math.pi) # Mercator imprecise
        
        lon_min_tile = (x_min - 1) * 360 / 2.0**zoom - 180
        lon_max_tile = (x_max + 2) * 360 / 2.0**zoom - 180
        lat_max_tile = 360 / math.pi * (math.atan(math.exp(math.pi * (1 - 2 * (y_min - 1) / 2.0**zoom))) - math.pi / 4)
        lat_min_tile = 360 / math.pi * (math.atan(math.exp(math.pi * (1 - 2 * (y_max + 2) / 2.0**zoom))) - math.pi / 4)
        map_metadata.append([lon_min_tile, lat_min_tile, lon_max_tile, lat_max_tile, width, height, m_px])
    
    print("Saved maps")

    import csv # For testing with animate_path2
    with open('minimap_metadata.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(map_metadata)

    #map_img = map_images[0] # Remove later
    #map_metadata = map_metadata[0]

    return(map_images, map_metadata)




