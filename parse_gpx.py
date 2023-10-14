import gpxpy
import math
from datetime import datetime
from datetime import timedelta

def parse_gpx(gpx_file):
    gpx = gpxpy.parse(gpx_file)
    
    track_points = [] # This is an array
    track_metadata = { # This is a dictionary
        'max_latitude': -float('inf'),
        'min_latitude': float('inf'),
        'max_longitude': -float('inf'),
        'min_longitude': float('inf'),
    }
    
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                # Update max and min values
                track_metadata['max_latitude'] = max(track_metadata['max_latitude'], point.latitude)
                track_metadata['min_latitude'] = min(track_metadata['min_latitude'], point.latitude)
                track_metadata['max_longitude'] = max(track_metadata['max_longitude'], point.longitude)
                track_metadata['min_longitude'] = min(track_metadata['min_longitude'], point.longitude)
                
                # Add to 2D array
                track_points.append([point.time, point.latitude, point.longitude, point.elevation if point.elevation else 0])

    lat0 = track_metadata['max_latitude']
    lon0 = track_metadata['min_longitude']
    
    # Expand the array with more parameters
    radius = 6371000.0
    for i in range(0, len(track_points)):
        timestamp, latitude, longitude, *_ = track_points[i]
        y = (lat0 - latitude) / 180 * math.pi * radius # Positive is further south
        x = (longitude - lon0) / 180 * math.pi * math.cos(lat0/180*math.pi) * radius # Pos furth east
        track_points[i].append(x)
        track_points[i].append(y)
        if i==0:
            v = 0
            phi = 0
        else:
            dt = (track_points[i][0]-track_points[i-1][0]).total_seconds()
            x_prev = track_points[i-1][4]
            y_prev = track_points[i-1][5]
            if dt == 0:
                v = track_points[i-1][6] # old velocity
            else:
                v = math.sqrt((x-x_prev)**2 + (y-y_prev)**2)/dt
            if (x == x_prev) & (y == y_prev):
                phi = track_points[i-1][7] # old angle
            else:
                phi = math.atan2(y-y_prev,x-x_prev)
            
        track_points[i].append(v)
        track_points[i].append(phi)

    # Making contant interval matrix
    track_points2 = []
    frame_duration = 0.5 # seconds
    current_time = track_points[0][0]
    i = 0
    while i < len(track_points) - 1:
        
        t1, lat1, lon1, ele1, x1, y1, v1, phi1 = track_points[i]
        t2, lat2, lon2, ele2, x2, y2, v2, phi2 = track_points[i + 1]
        fraction = (current_time - t1).total_seconds() / (t2 - t1).total_seconds()

        x = x1 + fraction * (x2 - x1)
        y = y1 + fraction * (y2 - y1)
        ele = ele1 + fraction * (ele2 - ele1)
        v = v1 + fraction * (v2 - v1)
        phi = phi1 + fraction * (phi2 - phi1)

        # append values to new array
        track_points2.append([current_time, x, y, ele, v, phi])
    
        # Move to the next recorded point if the current_time has passed it
        if current_time >= t2:
            i += 1

        # Increment the "current time" by the frame duration
        current_time += timedelta(seconds=frame_duration)

    
    return track_points2, track_metadata
