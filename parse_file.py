import os
import math
from datetime import datetime
from datetime import timedelta

def parse_file(file_path, dt):
    # Find file type
    _, file_extension = os.path.splitext(file_path)
    file_type = file_extension[1:].lower()
    if file_type == 'gpx':
        from parse_gpx import parse_gpx
        track_points = parse_gpx(open(file_path, 'r'))
    elif file_type == 'igc':
        from parse_igc import parse_igc
        track_points = parse_igc(file_path) # We get gps-altitude!
    elif file_type == 'tcx':
        from parse_tcx import parse_tcx
        track_points = parse_tcx(open(file_path, 'r')) # We get velocity directly!
    else:
        print("Unsupported file type.")
        track_points = None, None

    # Store metadata
    track_metadata = { # This is a dictionary
        'max_latitude': -float('inf'),
        'min_latitude': float('inf'),
        'max_longitude': -float('inf'),
        'min_longitude': float('inf'),
        'dt': dt, #seconds
    }
    for i in range(0, len(track_points)):
        lat = track_points[i][1]
        lon = track_points[i][2]
        track_metadata['max_latitude'] = max(track_metadata['max_latitude'], lat)
        track_metadata['min_latitude'] = min(track_metadata['min_latitude'], lat)
        track_metadata['max_longitude'] = max(track_metadata['max_longitude'], lon)
        track_metadata['min_longitude'] = min(track_metadata['min_longitude'], lon)
    
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
            vx = 0
            vy = 0
        else:
            time_delta = (track_points[i][0]-track_points[i-1][0]).total_seconds()
            x_prev = track_points[i-1][4]
            y_prev = track_points[i-1][5]
            if time_delta == 0: # old velocities
                vx = track_points[i-1][6]
                vy = track_points[i-1][7]
            else:
                vx = (x-x_prev)/time_delta
                vy = (y-y_prev)/time_delta
            
        track_points[i].append(vx)
        track_points[i].append(vy)

    # Making contant interval matrix
    track_points2 = []
    current_time = track_points[0][0]
    i = 0 # index of old array
    while current_time < track_points[-1][0]:  # Loop until the last of the original track_points
    
        # Find the appropriate i such that track_points[i][0] <= current_time < track_points[i+1][0]
        while i < len(track_points) - 1 and current_time >= track_points[i + 1][0]:
            i += 1
        t1, lat1, lon1, ele1, x1, y1, vx1, vy1 = track_points[i]
        t2, lat2, lon2, ele2, x2, y2, vx2, vy2 = track_points[i + 1]
        fraction = (current_time - t1).total_seconds() / (t2 - t1).total_seconds()
        
        # Interpolate
        x = x1 + fraction * (x2 - x1)
        y = y1 + fraction * (y2 - y1)
        ele = ele1 + fraction * (ele2 - ele1)
        vx = vx1 + fraction * (vx2 - vx1)
        vy = vy1 + fraction * (vy2 - vy1)

        v = math.sqrt(vx*vx+vy*vy)
        if (vx == 0) & (vy == 0):
            if len(track_points2) > 0:
                phi = track_points2[-1][5] # old angle
            else:
                phi = 0
        else:
            phi = math.atan2(vy,vx)

        if len(track_points2) > 0: # Just double checking the increments..
            dt_check = (current_time - track_points2[-1][0]).total_seconds()
        else:
            dt_check = dt

        # append values to new array
        track_points2.append([current_time, x, y, ele, v, phi, dt_check])

        # Increment the "current time" by the frame duration
        current_time += timedelta(seconds=dt)

    
    return track_points2, track_metadata

