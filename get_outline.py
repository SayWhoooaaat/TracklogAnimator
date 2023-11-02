import geopandas as gpd
from shapely.geometry import box, Point, Polygon, MultiPolygon
from shapely.ops import unary_union, transform
from PIL import Image, ImageDraw
import pyproj
import math

# Fundtion finds extreme coordinates on country/island from coordinate list
def get_bounding_coordinates(coords):
    world_gdf = gpd.read_file("countries.geojson")
    # Create a GeoDataFrame from the list of coordinates
    track_gdf = gpd.GeoDataFrame(geometry=[Point(coord[1], coord[0]) for coord in coords])
    track_gdf.crs = "EPSG:4326"
    
    # Decompose MultiPolygons into individual polygons
    all_polygons = []
    for _, row in world_gdf.iterrows():
        geom = row.geometry
        if isinstance(geom, Polygon):
            all_polygons.append(geom)
        elif isinstance(geom, MultiPolygon):
            all_polygons.extend(list(geom.geoms))
    
    decomposed_gdf = gpd.GeoDataFrame(geometry=all_polygons, crs=world_gdf.crs)
    
    # Perform the spatial join
    joined = gpd.sjoin(track_gdf, decomposed_gdf, how="inner", predicate="within")
    
    # Get the individual polygons that contain the points
    containing_polygons = decomposed_gdf.loc[joined['index_right'], 'geometry'].unique()
    # Combine the polygons into one
    combined_polygon = unary_union(containing_polygons)
    return combined_polygon.bounds


# Function saves section of map from extreme coordinates
def get_borders(lat_min, lat_max, lon_min, lon_max, width, height):

    bbox = box(lon_min, lat_min, lon_max, lat_max)
    # Load GeoJSON of World Countries
    world_gdf = gpd.read_file("countries.geojson")
    
    # Filter geometries that intersect with the bounding box and clip them
    geoms_to_draw = []
    for _, row in world_gdf.iterrows():
        if row.geometry.within(bbox) or row.geometry.intersects(bbox):
            geoms_to_draw.append(row.geometry)
    
    # Convert geoms_to_draw to Mercator and create a GeoDataFrame
    gdf_to_draw = gpd.GeoDataFrame(geometry=geoms_to_draw)
    gdf_to_draw.crs = world_gdf.crs  # Set the CRS to match world_gdf
    gdf_to_draw = gdf_to_draw.to_crs(epsg=3395)

    # Calculate scaling factors
    # Convert a geometry from one CRS to another
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3395", always_xy=True).transform
    bbox_mercator = transform(project, bbox) # Convert the bounding box to Mercator
    bbox_minx, bbox_miny, bbox_maxx, bbox_maxy = bbox_mercator.bounds
    x_scale = (bbox_maxx - bbox_minx) / width
    y_scale = (bbox_maxy - bbox_miny) / height
    scale = max(x_scale, y_scale)

    # Update bounding coordinates
    bbox2_xmax = (bbox_maxx + bbox_minx + scale * width) / 2
    bbox2_xmin = (bbox_maxx + bbox_minx - scale * width) / 2
    bbox2_ymax = (bbox_maxy + bbox_miny + scale * height) / 2
    bbox2_ymin = (bbox_maxy + bbox_miny - scale * height) / 2
    project_inverse = pyproj.Transformer.from_crs("EPSG:3395", "EPSG:4326", always_xy=True).transform
    adjusted_bbox = transform(project_inverse, box(bbox2_xmin, bbox2_ymin, bbox2_xmax, bbox2_ymax))
    lon_min, lat_min, lon_max, lat_max = adjusted_bbox.bounds

    # Initialize the image
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw each geometry on the image with normalized coordinates
    for geom in gdf_to_draw.geometry:
        if isinstance(geom, Polygon):
            x, y = geom.exterior.xy
            normalized_x = [(i - bbox2_xmin) / scale for i in x]
            normalized_y = [height - (i - bbox2_ymin) / scale for i in y]
            draw.polygon(list(zip(normalized_x, normalized_y)), fill=None, outline=(255, 255, 255, 255))
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                normalized_x = [(i - bbox2_xmin) / scale for i in x]
                normalized_y = [height - (i - bbox2_ymin) / scale for i in y]
                draw.polygon(list(zip(normalized_x, normalized_y)), fill=None, outline=(255, 255, 255, 255))

    img.save("media/country_outline.png")
    return (img, adjusted_bbox.bounds)

def get_outline(track_points, width=300, height=400):
    coords = [(point[7], point[8]) for point in track_points]

    print("Finding country...")
    lon_min, lat_min, lon_max, lat_max = get_bounding_coordinates(coords)
    padding_percentage = 2 # Add padding around coordinates
    lon_min = lon_min - (lon_max - lon_min) * padding_percentage / 100
    lon_max = lon_max + (lon_max - lon_min) * padding_percentage / 100
    lat_min = lat_min - (lat_max - lat_min) * padding_percentage / 100
    lat_max = lat_max + (lat_max - lat_min) * padding_percentage / 100
    
    print("Generating country outline...")
    outline_image, bounding_coords = get_borders(lat_min, lat_max, lon_min, lon_max, width, height)
    lon_min, lat_min, lon_max, lat_max = bounding_coords
    print("Saved country map")
    
    outline_metadata = [lon_min, lat_min, lon_max, lat_max, width, height]

    return(outline_image, outline_metadata)





