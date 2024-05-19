import geopandas as gpd
from shapely.geometry import box, Point, Polygon, MultiPolygon
from shapely.ops import unary_union, transform
from PIL import Image, ImageDraw
import pyproj
import math
import sys

# Fundtion finds bounding coordinates on country/island from coordinate list
def get_bounding_coordinates(coords):
    world_gdf = gpd.read_file("countries.geojson")
    track_gdf = gpd.GeoDataFrame(geometry=[Point(coord[1], coord[0]) for coord in coords])
    track_gdf.crs = "EPSG:4326"
    
    # Decompose MultiPolygons into individual polygons and include country name
    all_polygons = []
    country_names = []
    for _, row in world_gdf.iterrows():
        geom = row.geometry
        admin = row['ADMIN']
        if isinstance(geom, Polygon):
            all_polygons.append(geom)
            country_names.append(admin)
        elif isinstance(geom, MultiPolygon):
            for sub_geom in geom.geoms:
                all_polygons.append(sub_geom)
                country_names.append(admin)
    
    decomposed_gdf = gpd.GeoDataFrame({'geometry': all_polygons, 'ADMIN': country_names}, crs=world_gdf.crs)
    
    # Perform the spatial join
    joined = gpd.sjoin(track_gdf, decomposed_gdf, how="inner", predicate="within")

    # Create a dictionary to count intersecting polygons per country
    country_dict = {}
    for index in joined.index_right.unique():
        country_name = decomposed_gdf.loc[index, 'ADMIN']  # Now we use decomposed_gdf
        country_dict[country_name] = country_dict.get(country_name, 0) + 1

    # Combine the polygons into one
    combined_polygon = unary_union([decomposed_gdf.loc[index, 'geometry'] for index in joined.index_right.unique()])

    return combined_polygon.bounds, country_dict


def find_countries(lon_min, lat_min, lon_max, lat_max):
    # Load the GeoJSON file into a GeoDataFrame
    world_gdf = gpd.read_file("countries.geojson")

    # Reproject to a CRS that allows for area calculation (equal-area projection)
    world_gdf = world_gdf.to_crs('EPSG:6933')  # EPSG:6933 is an equal-area projection

    bbox = box(lon_min, lat_min, lon_max, lat_max)
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    bbox = transform(project, bbox)

    # Transformer to convert back to WGS84
    project_back = pyproj.Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True).transform

    # Dictionary to store information about countries
    polygon_dict = {}
    for _, row in world_gdf.iterrows():
        geom = row['geometry']
        admin = row['ADMIN']  # Country name
        if isinstance(geom, MultiPolygon) or isinstance(geom, Polygon):
            geoms_to_check = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
            for poly in geoms_to_check:
                if poly.intersects(bbox):
                    # Get the centroid of the intersecting polygon in the 6933 projection
                    centroid = poly.representative_point()  # Use 'poly' instead of 'geom'
                    lon, lat = project_back(centroid.x, centroid.y)
                    area = poly.area / 10**6  # Convert area from square meters to square kilometers
                    if admin not in polygon_dict:
                        polygon_dict[admin] = {'count': 0, 'points': [], 'areas': []}
                    # Update country information
                    polygon_dict[admin]['count'] += 1
                    polygon_dict[admin]['points'].append((lat, lon))
                    polygon_dict[admin]['areas'].append(area)

    return polygon_dict


# Function saves section of map from bounding coordinates
def get_borders(lat_min, lat_max, lon_min, lon_max, width, height_max):

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

    height = width * (bbox_maxy - bbox_miny) / (bbox_maxx - bbox_minx)
    height = min(int(height+1), height_max)

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
    return (img, adjusted_bbox.bounds, height)

def get_outline(track_points, width, anim_height):
    height_max = anim_height * 0.85 - width
    width = round(width * 0.5) # scaling down outline image

    # Simplify tracklog
    timeinterval = 120
    current_time = track_points[0]["timestamp"]
    coords = []
    for point in track_points:
        if (point["timestamp"] - current_time).total_seconds() > timeinterval:
            current_time = point["timestamp"]
            coords.append((point["lat"], point["lon"]))

    print("Finding country...")
    bounds, countries = get_bounding_coordinates(coords)
    lon_min, lat_min, lon_max, lat_max = bounds

    # Find polygon area
    polygon_dict = find_countries(lon_min, lat_min, lon_max, lat_max)
    area = 0
    for country_dict in polygon_dict.values():
        area += sum(country_dict['areas'])

    # Logic for increasing size if island:
    radius = 6371.0 # km
    polygon_height = (lat_max - lat_min) / 180 * math.pi * radius
    polygon_width = (lon_max - lon_min) / 180 * math.pi * math.cos((lat_min + lat_max)/2/180*math.pi) * radius
    threshold = 100
    th2 = 200
    if (polygon_width < threshold) and (polygon_height < threshold):
        # Small island. Check larger 200x200 km square
        lon = (lon_max + lon_min) / 2
        lat = (lat_max + lat_min) / 2
        lat_max = lat + th2/2 / radius * 180 / math.pi
        lat_min = lat - th2/2 / radius * 180 / math.pi
        lon_max = lon + th2/2 / radius * 180 / math.pi / math.cos(lat/180*math.pi)
        lon_min = lon - th2/2 / radius * 180 / math.pi / math.cos(lat/180*math.pi)
        polygon_dict2 = find_countries(lon_min, lat_min, lon_max, lat_max)
        # See if more polygons for relevant countries
        rescale_huge = False
        for country, count in countries.items():
            country_info = polygon_dict2.get(country)
            count2 = country_info.get('count')
            coords2 = country_info.get('points')
            if count2 > count:
                # We have more islands of same country
                # Rescale to include all these islands 
                rescale_huge = True
                # Adding coordinates of islands of same country
                for lat, lon in coords2:
                    coords.append((lat, lon))
                bounds, countries = get_bounding_coordinates(coords)
                lon_min, lat_min, lon_max, lat_max = bounds
                # Find polygon area
                polygon_dict = find_countries(lon_min, lat_min, lon_max, lat_max)
                area = 0
                for country_dict in polygon_dict.values():
                    area += sum(country_dict['areas'])
        
        # If nothing more has been added
        if (len(polygon_dict2) == len(countries)) and (rescale_huge == False):
            # Remote island. Revert to original coordinates
            lon_min, lat_min, lon_max, lat_max = bounds
    bounds = [lon_min, lat_min, lon_max, lat_max]

    # Check if large island of same country nearby
    rescale_huge = False
    th3 = 1000
    lon = (lon_max + lon_min) / 2
    lat = (lat_max + lat_min) / 2
    lat_max = lat + th3/2 / radius * 180 / math.pi
    lat_min = lat - th3/2 / radius * 180 / math.pi
    lon_max = lon + th3/2 / radius * 180 / math.pi / math.cos(lat/180*math.pi)
    lon_min = lon - th3/2 / radius * 180 / math.pi / math.cos(lat/180*math.pi)
    polygon_dict2 = find_countries(lon_min, lat_min, lon_max, lat_max)
    # See if more polygons for relevant countries
    for country, count in countries.items():
        country_info = polygon_dict2.get(country)
        count2 = country_info.get('count')
        coords2 = country_info.get('points')
        area2 = country_info.get('areas')
        if count2 > count:
            # We have more islands of same country
            # Checking if they are big enough to include
            for i in range(0, len(coords2)):
                polygon_area = area2[i]
                lat, lon = coords2[i]
                if polygon_area > area * 0.3:
                    # Huge land area, must include in outline
                    rescale_huge = True
                    coords.append((lat, lon))
    if rescale_huge == True:
        bounds, countries = get_bounding_coordinates(coords)
        lon_min, lat_min, lon_max, lat_max = bounds
    else:
        # No large island to include, use initial coordinates. 
        lon_min, lat_min, lon_max, lat_max = bounds

    # Add padding around coordinates
    padding_percentage = 2 
    lon_min = lon_min - (lon_max - lon_min) * padding_percentage / 100
    lon_max = lon_max + (lon_max - lon_min) * padding_percentage / 100
    lat_min = lat_min - (lat_max - lat_min) * padding_percentage / 100
    lat_max = lat_max + (lat_max - lat_min) * padding_percentage / 100
    
    print("Generating country outline...")
    outline_image, bounding_coords, height = get_borders(lat_min, lat_max, lon_min, lon_max, width, height_max)
    lon_min, lat_min, lon_max, lat_max = bounding_coords
    print("Saved country map")
    
    outline_metadata = [lon_min, lat_min, lon_max, lat_max, width, height]

    return(outline_image, outline_metadata)





