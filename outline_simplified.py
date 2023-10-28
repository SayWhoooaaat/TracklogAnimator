import geopandas as gpd
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, MultiPolygon

# Shows a single island contour (random from multi-island countries)

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
geometry = country_gdf.geometry.iloc[0]

# Initialize the image
img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Function to normalize coordinates to fit the image dimensions
def normalize_coords(x, y, img_width, img_height):
    x_scale = (max(x) - min(x)) / img_width
    y_scale = (max(y) - min(y)) / img_height
    scale = max(x_scale, y_scale)

    # Apply scaling to x and y
    normalized_x = [(i - min(x)) / scale for i in x]
    normalized_y = [img_height - (i - min(y)) / scale for i in y]
    normalized = list(zip(normalized_x, normalized_y))
    return normalized

# Handle both Polygon and MultiPolygon geometries
if isinstance(geometry, Polygon):
    x, y = geometry.exterior.xy
    xy = normalize_coords(x, y, width2, height2)
    draw.line(xy, fill=(255, 0, 0, 255), width=2)
elif isinstance(geometry, MultiPolygon):
    # Get only the first polygon from the MultiPolygon geometry
    first_poly = geometry.geoms[0]
    x, y = first_poly.exterior.xy
    xy = normalize_coords(x, y, width2, height2)
    draw.line(xy, fill=(255, 0, 0, 255), width=2)
    #for poly in geometry.geoms:
    #    x, y = poly.exterior.xy
    #    xy = normalize_coords(x, y, width-4, height-4)
    #    draw.line(xy, fill=(255, 0, 0, 255), width=2)

img.save("media/outline_country.png")
