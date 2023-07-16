import requests
from PIL import Image
from io import BytesIO
import math

def lat_lon_to_tile_coords(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x_tile = ((lon_deg + 180.0) / 360.0 * n)
    y_tile = ((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return int(x_tile), int(y_tile)

def get_tile_image(x, y, zoom, maptype='terrain'):
    base_url = 'http://tile.stamen.com'
    url = f"{base_url}/{maptype}/{zoom}/{x}/{y}.png"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        return img
    else:
        print(f'Unable to download map image for tile ({x}, {y}, {zoom})')
        return None


def km_to_zoom_level(km, lat):
    # Estimate the zoom level based on scale at the equator
    equator_circumference = 40075  # in km
    zoom_level_equator = math.log(equator_circumference / km, 2)
    
    # Adjust the zoom level based on latitude
    zoom_level = round(zoom_level_equator + math.log(math.cos(math.radians(lat)), 2))

    km_equator = equator_circumference / (2 ** zoom_level)
    km = km_equator * math.cos(math.radians(lat))
    print(km)

    return zoom_level


def get_map_stamen(lat_min, lat_max, lon_min, lon_max, scale_km, maptype='terrain'):
    zoom = km_to_zoom_level(scale_km, lat_min)
    print(zoom)
    x_min, y_max = lat_lon_to_tile_coords(lat_min, lon_min, zoom)
    x_max, y_min = lat_lon_to_tile_coords(lat_max, lon_max, zoom)
    print(x_min,y_min)
    print(x_max,y_max)
    
    # Calculate the total number of tiles in x and y directions
    num_tiles_x = x_max - x_min + 3
    num_tiles_y = y_max - y_min + 3
    print(num_tiles_x,num_tiles_y)
    
    # Create a new image big enough to hold all the tiles
    width, height = num_tiles_x * 256, num_tiles_y * 256
    map_img = Image.new('RGB', (width, height))

    # Fetch each tile and paste it into the map image
    for x in range(x_min - 1, x_max + 2):
        for y in range(y_min - 1, y_max + 2):
            tile_img = get_tile_image(x,y,zoom)
            if tile_img is not None:  # Only paste if the image was successfully downloaded
                map_img.paste(tile_img, ((x - x_min + 1) * 256, (y - y_min + 1) * 256))

    # Save the stitched map image
    map_img.save('map_stitched.png')



# To do: center around lat,lon and crop image.
# Add km scale on right side

