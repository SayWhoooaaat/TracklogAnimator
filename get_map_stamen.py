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

def get_map_stamen(lat, lon, scale_km, maptype='terrain'):
    zoom = km_to_zoom_level(scale_km, lat)
    x_center, y_center = lat_lon_to_tile_coords(lat, lon, zoom)
    img_size = get_tile_image(x_center, y_center, zoom, maptype).size
    img_width, img_height = img_size[0], img_size[1]
    img_stitched = Image.new('RGB', (img_width * 3, img_height * 3))

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            img = get_tile_image(x_center + dx, y_center + dy, zoom, maptype)
            if img is not None:
                img_stitched.paste(img, ((dx + 1) * img_width, (dy + 1) * img_height))

    img_stitched.save('map_stitched.png')

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

# To do: center around lat,lon and crop image.
# Add km scale on right side

