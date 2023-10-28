import geopandas as gpd
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, MultiPolygon

# This code displays Norway WITH Dr. Mauds Land etc...

width = 300
height = 500

width2 = width - 4
height2 = height - 4

# Load GeoJSON of World Countries
world_gdf = gpd.read_file("countries.geojson")

# Extract Country
country_gdf = world_gdf[world_gdf['ADMIN'] == 'Norway']

# Project to Mercator
country_gdf = country_gdf.to_crs(epsg=3395)

# Retrieve the geometry for Country
country_geometry = country_gdf.geometry.iloc[0]
all_coords = []

min_x, min_y, max_x, max_y = country_geometry.bounds

if isinstance(country_geometry, Polygon):
    x, y = country_geometry.exterior.xy
    all_coords.append(list(zip(x, y)))
elif isinstance(country_geometry, MultiPolygon):
    for poly in country_geometry.geoms:
        x, y = poly.exterior.xy
        all_coords.append(list(zip(x, y)))

# Function to normalize coordinates to fit the image dimensions
def normalize_polygon_coords(coords):
    x, y = zip(*coords)
    scale = max((max_x - min_x) / width2, (max_y - min_y) / height2)
    normalized_x = [(i - min_x) / scale for i in x]
    normalized_y = [height2 - (i - min_y) / scale for i in y]
    return list(zip(normalized_x, normalized_y))

# Initialize the image
img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw each polygon with normalized coordinates
for coords in all_coords:
    normalized_coords = normalize_polygon_coords(coords)
    draw.polygon(normalized_coords, fill=None, outline=(255, 0, 0, 255))

img.save("media/outline_country2.png")
