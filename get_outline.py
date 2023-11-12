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

    bbox = box(lon_min, lat_min, lon_max, lat_max)

    # Dictionary to store information about countries
    # Each entry will hold a list of tuples: (count, [(inside_point_lat, inside_point_lon)])
    country_info = {}
    for _, row in world_gdf.iterrows():
        geom = row['geometry']
        admin = row['ADMIN']  # Country name
        if isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                if poly.intersects(bbox):
                    inside_point = poly.representative_point()
                    if admin in country_info:
                        country_info[admin][0] += 1  # Increment count
                        country_info[admin][1].append((inside_point.y, inside_point.x))  # Append inside point lat, lon
                    else:
                        country_info[admin] = [1, [(inside_point.y, inside_point.x)]]  # Initialize count and inside point list
        elif isinstance(geom, Polygon):
            if geom.intersects(bbox):
                inside_point = geom.representative_point()
                if admin in country_info:
                    country_info[admin][0] += 1
                    country_info[admin][1].append((inside_point.y, inside_point.x))
                else:
                    country_info[admin] = [1, [(inside_point.y, inside_point.x)]]

    return country_info


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
    height_max = anim_height - width - 150
    coords = [(point[6], point[7]) for point in track_points]

    print("Finding country...")
    bounds, countries = get_bounding_coordinates(coords)
    lon_min, lat_min, lon_max, lat_max = bounds

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
        countries2 = find_countries(lon_min, lat_min, lon_max, lat_max)
        
        # See if more polygons for relevant countries
        rescale_huge = False
        for country, count in countries.items():
            newislands = countries2.get(country, 0)
            count2 = newislands[0]
            newcoords = newislands[1:]
            if count2 > count:
                # We have more islands of same country
                # Rescale to include all these islands 
                rescale_huge = True
                for lat, lon in newcoords[0]:
                    coords.append((lat, lon))
                bounds, countries = get_bounding_coordinates(coords)
                lon_min, lat_min, lon_max, lat_max = bounds
        
        # See if nothing more has been added
        if (len(countries2) == len(countries)) and (rescale_huge == False):
            # Lonely island. Revert to original coordinates
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





