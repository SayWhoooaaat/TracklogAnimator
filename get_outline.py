import geopandas as gpd
from shapely.geometry import Point
from PIL import Image, ImageDraw

def get_outline(track_points):
    width = 300
    height = 1000
    # Load GeoJSON of World Countries
    world_gdf = gpd.read_file("countries.geojson")

    # Convert Coordinates to GeoDataFrame
    #track_coords = [(row[1], row[2]) for row in track_points]
    track_coords = [(61,10)]
    track_gdf = gpd.GeoDataFrame(geometry=[Point(xy) for xy in track_coords], crs="EPSG:4326")

    # Perform spatial joint
    joined = gpd.sjoin(track_gdf, world_gdf, predicate="within")
    # The 'joined' dataframe will have an additional column with the country name for each point

    # Get unique countries
    unique_countries = joined['ADMIN'].unique()  # Admin is name in countries.geojson
    # Filter for mutiple countries
    countries_gdf = world_gdf[world_gdf['ADMIN'].isin(unique_countries)] 
    countries_gdf = world_gdf[world_gdf['ADMIN'] == 'Norway']  # debugger
    # Mercator projection
    countries_gdf = countries_gdf.to_crs(epsg=3395)

    print(joined.shape)
    print(countries_gdf.shape)
    # Convert from GeoDataFrame to x,y-pairs
    x, y = countries_gdf.geometry.iloc[0].exterior.xy  # Assuming single geometry

    # Normalizing x and y
    normalized_x = [(i - min(x)) * width / (max(x) - min(x)) for i in x]
    normalized_y = [(i - min(y)) * height / (max(y) - min(y)) for i in y]
    country_coords = list(zip(normalized_x, normalized_y))

    # Draw outline
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.line(country_coords, fill=(255, 0, 0, 255), width=2)
    img.save("media/country.png")







