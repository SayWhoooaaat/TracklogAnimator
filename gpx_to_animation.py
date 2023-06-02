import math
import gpxpy
import gpxpy.gpx

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # radius of the Earth in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    res = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    return res  # returns the distance in kilometers

# Parsing an existing file:
with open('testactivity.gpx', 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)

    max_latitude = max_longitude = -float('inf')
    min_latitude = min_longitude = float('inf')

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                # print('Time: {0} -- Latitude: {1} -- Longitude: {2} -- Elevation: {3}'.format(point.time, point.latitude, point.longitude, point.elevation))
                max_latitude = max(max_latitude, point.latitude)
                min_latitude = min(min_latitude, point.latitude)
                max_longitude = max(max_longitude, point.longitude)
                min_longitude = min(min_longitude, point.longitude)

    print('Max Latitude: {0}, Min Latitude: {1}, Max Longitude: {2}, Min Longitude: {3}'.format(
        max_latitude, min_latitude, max_longitude, min_longitude))
    avg_latitude = (max_latitude-min_latitude)/2
    avg_longitude = (max_longitude-min_longitude)/2
    NS_distance = haversine(max_latitude, min_longitude, min_latitude, min_longitude)
    EW_distance = haversine(min_latitude, max_longitude, min_latitude, min_longitude)
    NS_scale = NS_distance / (max_latitude-min_latitude) # km/degree
    EW_scale = EW_distance / (max_longitude-min_longitude) # km/degree

    print('North-South distance: {0} km, East-West distance: {1} km'.format(NS_distance, EW_distance))



