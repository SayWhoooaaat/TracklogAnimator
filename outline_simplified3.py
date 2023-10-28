import geopandas as gpd
from PIL import Image, ImageDraw
from shapely.geometry import box, Polygon, MultiPolygon
from shapely.ops import transform
import pyproj

lat = 60
lon = 8

d_lat = 8
d_lon = 8

lat_min=lat - d_lat/2
lat_max=lat + d_lat/2
lon_min=lon - d_lon/2
lon_max=lon + d_lon/2

# Function saves section of map from coordinates
def save_borders(lat_min, lat_max, lon_min, lon_max):

    width = 300
    height = 500

    bbox = box(lon_min, lat_min, lon_max, lat_max)
    # Load GeoJSON of World Countries
    world_gdf = gpd.read_file("countries.geojson")
    
    # Filter geometries that intersect with the bounding box and clip them
    clipped_geoms = []
    for _, row in world_gdf.iterrows():
        if row.geometry.intersects(bbox):
            clipped_geoms.append(row.geometry.intersection(bbox))
    
    # Create a new GeoDataFrame with the clipped geometries and set the CRS
    clipped_gdf = gpd.GeoDataFrame(geometry=clipped_geoms)
    clipped_gdf.crs = world_gdf.crs  # Set the CRS to match world_gdf
    
    # Convert clipped geometries to Mercator
    clipped_gdf = clipped_gdf.to_crs(epsg=3395)

    # Collect all x and y coordinates from all geometries
    all_x = []
    all_y = []
    for geom in clipped_gdf.geometry:
        if isinstance(geom, Polygon):
            x, y = geom.exterior.xy
            all_x.extend(x)
            all_y.extend(y)
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                all_x.extend(x)
                all_y.extend(y)

    # Calculate scaling factors
    # Convert a geometry from one CRS to another
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3395", always_xy=True).transform
    bbox_mercator = transform(project, bbox) # Convert the bounding box to Mercator
    bbox_minx, bbox_miny, bbox_maxx, bbox_maxy = bbox_mercator.bounds
    x_scale = (bbox_maxx - bbox_minx) / width
    y_scale = (bbox_maxy - bbox_miny) / height
    scale = max(x_scale, y_scale)

    # Initialize the image
    img = Image.new("RGBA", (width, height), (250, 250, 250, 250))
    draw = ImageDraw.Draw(img)

    # Draw each geometry on the image with normalized coordinates
    for geom in clipped_gdf.geometry:
        if isinstance(geom, Polygon):
            x, y = geom.exterior.xy
            normalized_x = [(i - bbox_minx) / scale for i in x]
            normalized_y = [height - (i - bbox_miny) / scale for i in y]
            draw.polygon(list(zip(normalized_x, normalized_y)), fill=None, outline=(255, 0, 0, 255))
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                normalized_x = [(i - bbox_minx) / scale for i in x]
                normalized_y = [height - (i - bbox_miny) / scale for i in y]
                draw.polygon(list(zip(normalized_x, normalized_y)), fill=None, outline=(255, 0, 0, 255))

    img.save("media/world_section.png")


# Call the function with your coordinates
save_borders(lat_min, lat_max, lon_min, lon_max)
