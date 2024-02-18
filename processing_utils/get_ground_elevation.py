import requests
import math
import json
import os

def get_ground_elevation(lat, lon):
    url = f"https://api.opentopodata.org/v1/test-dataset?locations={lat},{lon}"
    print("Calling Elevation-API")
    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()
        # The API returns a list of results for each location. We'll just take the first.
        elevation = result['results'][0]['elevation']
        return elevation
    else:
        print(f"Error querying Open Topo Data API: {response.status_code}")
        return None


def get_elevation_from_cache(lat, lon, precision_lat=0.01, precision_lon=0.01):
    filename = 'elevation_cache.json'
    # Check if json exists
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            elevation_data = json.load(file)
    else:
        elevation_data = []
    cached_coordinates = [sublist[:2] for sublist in elevation_data]

    # Round the coordinates to the specified precision to create grid keys
    keys = []
    lat_low = round(math.floor(lat / precision_lat) * precision_lat, 5)
    lat_high = round(math.ceil(lat / precision_lat) * precision_lat, 5)
    lon_low = round(math.floor(lon / precision_lon) * precision_lon, 5)
    lon_high = round(math.ceil(lon / precision_lon) * precision_lon, 5)
    keys = [[lat_low, lon_low], [lat_low, lon_high], [lat_high, lon_low], [lat_high, lon_high]]

    # Retrieve or cache elevations
    for i, key in enumerate(keys):
        if key not in [sublist[:2] for sublist in elevation_data]:
            # add to list of keys instead----------------
            elevation = get_ground_elevation(*key)
            elevation_data.append(key + [elevation])
        else:
            # If already in cache, update key with elevation from cache
            print("Took elevation from cache")
            elevation = next(item for item in elevation_data if item[:2] == key)[2]
        keys[i].append(elevation)  # Make sure keys has updated elevation data

    # Save updated elevation data back to file
    with open(filename, 'w') as file:
        json.dump(elevation_data, file, indent=4)

    # Bilinear interpolation
    den = (lon_high - lon_low) * (lat_high - lat_low)
    fxy1 = ((lon_high - lon) * (lat_high - lat) / den * keys[0][2] +
            (lon - lon_low) * (lat_high - lat) / den * keys[1][2])
    fxy2 = ((lon_high - lon) * (lat - lat_low) / den * keys[2][2] +
            (lon - lon_low) * (lat - lat_low) / den * keys[3][2])
    
    return fxy1 + fxy2








