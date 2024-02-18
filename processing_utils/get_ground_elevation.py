import requests
import math
import json
import os
import time

def get_ground_elevation(locations):
    url = "https://api.opentopodata.org/v1/aster30m"
    # Joining locations as a pipe-separated string of lat,lon pairs
    locations_param = '|'.join([f"{lat},{lon}" for lat, lon in locations])
    print("Calling API for elevation data")
    response = requests.get(url, params={"locations": locations_param})
    if response.status_code == 200:
        data = response.json()
        # Extract just the elevation from each result and return as a list
        elevations = [result['elevation'] for result in data['results']]
        return elevations
    else:
        print(f"Error: {response.status_code}")
        return []


def get_elevation_from_cache(coordinates, precision_lat=0.01, precision_lon=0.01):
    filename = 'elevation_cache.json'
    # Check if json exists
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            elevation_data = json.load(file)
    else:
        elevation_data = []
    cached_coordinates = [sublist[:2] for sublist in elevation_data]

    # Make list with all desired coordinates
    coordinate_list = []
    for point in coordinates:
        lat, lon = point
        # Round the coordinates to the specified precision to create grid keys
        lat_low = round(math.floor(lat / precision_lat) * precision_lat, 5)
        lat_high = round(math.ceil(lat / precision_lat) * precision_lat, 5)
        lon_low = round(math.floor(lon / precision_lon) * precision_lon, 5)
        lon_high = round(math.ceil(lon / precision_lon) * precision_lon, 5)
        keys = [[lat_low, lon_low], [lat_low, lon_high], [lat_high, lon_low], [lat_high, lon_high]]

        for i, key in enumerate(keys):
            if key not in coordinate_list:
                coordinate_list.append(key)
    
    # Make list of coordinates not found locally
    coordinate_list_api = []
    for point in coordinate_list:
        if point not in cached_coordinates:
            coordinate_list_api.append(point)

    # Get elevations from API
    batch_size = 100
    elevations = []
    for i in range(0, len(coordinate_list_api), batch_size):
        batch = coordinate_list_api[i:i+batch_size]
        elevations.extend(get_ground_elevation(batch))
        time.sleep(1)  # Respect the 1 call per second limit
    
    # Store new elevations in json
    for i, point in enumerate(coordinate_list_api):
        elevation_data.append(point + [elevations[i]])
        with open(filename, 'w') as file:
            json.dump(elevation_data, file, indent=4)

    # Interpolate all trackpoints from elevation grid
    trackpoint_elevations = []
    for point in coordinates:
        lat, lon = point
        
        lat_low = round(math.floor(lat / precision_lat) * precision_lat, 5)
        lat_high = round(math.ceil(lat / precision_lat) * precision_lat, 5)
        lon_low = round(math.floor(lon / precision_lon) * precision_lon, 5)
        lon_high = round(math.ceil(lon / precision_lon) * precision_lon, 5)

        ele_ll = next(item for item in elevation_data if item[:2] == [lat_low, lon_low])[2]
        ele_lh = next(item for item in elevation_data if item[:2] == [lat_low, lon_high])[2]
        ele_hl = next(item for item in elevation_data if item[:2] == [lat_high, lon_low])[2]
        ele_hh = next(item for item in elevation_data if item[:2] == [lat_high, lon_high])[2]

        # Bilinear interpolation
        den = (lon_high - lon_low) * (lat_high - lat_low)
        fxy1 = ((lon_high - lon) * (lat_high - lat) / den * ele_ll +
                (lon - lon_low) * (lat_high - lat) / den * ele_lh)
        fxy2 = ((lon_high - lon) * (lat - lat_low) / den * ele_hl +
                (lon - lon_low) * (lat - lat_low) / den * ele_hh)
        
        trackpoint_elevations.append(fxy1 + fxy2)

    return trackpoint_elevations








