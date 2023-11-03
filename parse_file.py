import os
import math
from datetime import datetime
from datetime import timedelta
import random

def total_distance(points):
    dist = 0
    for i in range(len(points) - 1):
        x1, y1 = points[i][0], points[i][1]
        x2, y2 = points[i+1][0], points[i+1][1]
        dist += math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return dist

def get_5pt_distance(xy_positions, previous_best_points):
    temp = 10000
    cooling_rate = 0.8 # 0.995 = 1800 iter. 0.98 = 450 iter. 0.8 = 41

    current_points = previous_best_points[0:4] + [xy_positions[-1]]
    current_distance = total_distance(current_points)
    best_points = current_points
    best_distance = current_distance
    
    while temp > 1: # Seems stupid. Takes random points and checks if they are better..
        sampled_indexes = sorted(random.sample(range(1, len(xy_positions) - 1), 3))
        new_points = [xy_positions[i] for i in [0] + sampled_indexes + [-1]]
        new_distance = total_distance(new_points)
        
        if new_distance > current_distance or math.exp((new_distance - current_distance) / temp) > random.random():
            current_points = new_points
            current_distance = new_distance

            # Do local maxima-algorithm
            
            if new_distance > best_distance:
                best_points = new_points
                best_distance = new_distance
        
        temp *= cooling_rate
    
    return best_distance, best_points


def parse_file(file_path, dt, speedup):
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
    print(f"Parsing {file_type} file to 2D-array...")

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
        y_ish = (lat0 - latitude) / 180 * math.pi * radius
        x_ish = (longitude - lon0) / 180 * math.pi * math.cos(lat0/180*math.pi) * radius
        track_points[i].append(x_ish)
        track_points[i].append(y_ish)
        if i==0:
            vx = 0
            vy = 0
        else:
            time_delta = (track_points[i][0]-track_points[i-1][0]).total_seconds()
            lon_prev = track_points[i-1][2]
            lat_prev = track_points[i-1][1]
            if time_delta == 0: # old velocities
                vx = track_points[i-1][6]
                vy = track_points[i-1][7]
            else:
                vx = (longitude-lon_prev) * math.pi * radius / 180 / time_delta * math.cos(lat*math.pi/180)
                vy = (lat_prev-latitude) * math.pi * radius / 180 / time_delta
            
        track_points[i].append(vx)
        track_points[i].append(vy)

    # 5-pt distance
    print("Calculating 5-point distances...")
    for i in range(0, len(track_points)):
        if i < 10:
            dist = 0
            previous_best_points = [[track_points[0][4], track_points[0][5]], [track_points[0][4], track_points[0][5]], [track_points[0][4], track_points[0][5]], [track_points[0][4], track_points[0][5]], [track_points[0][4], track_points[0][5]]]
        else:
            xy_positions = [[point[4], point[5]] for point in track_points[:i+1]]
            dist, previous_best_points = get_5pt_distance(xy_positions, previous_best_points)
        if i % 2000 == 0: 
            print(f"Progress: {round(i/len(track_points)*100)}%")
        track_points[i].append(dist)
    print(f"Best 5-point distance: {round(dist/1000)} km. Finishing 2D-array...")

    # Making contant interval matrix
    track_points2 = []
    current_time = track_points[0][0]
    i = 0 # index of old array
    while current_time < track_points[-1][0]:  # Loop until the last of the original track_points
    
        # Find the appropriate i such that track_points[i][0] <= current_time < track_points[i+1][0]
        while i < len(track_points) - 1 and current_time >= track_points[i + 1][0]:
            i += 1
        t1, lat1, lon1, ele1, x1, y1, vx1, vy1, dist1 = track_points[i]
        t2, lat2, lon2, ele2, x2, y2, vx2, vy2, dist2 = track_points[i + 1]
        fraction = (current_time - t1).total_seconds() / (t2 - t1).total_seconds()
        
        # Interpolate
        x_ish = x1 + fraction * (x2 - x1)
        y_ish = y1 + fraction * (y2 - y1)
        ele = ele1 + fraction * (ele2 - ele1)
        vx = vx1 + fraction * (vx2 - vx1)
        vy = vy1 + fraction * (vy2 - vy1)
        lat = lat1 + fraction * (lat2 - lat1)
        lon = lon1 + fraction * (lon2 - lon1)
        dist = dist1 + fraction * (dist2 - dist1)

        v = math.sqrt(vx*vx+vy*vy)
        if (vx == 0) & (vy == 0):
            if len(track_points2) > 0:
                phi = track_points2[-1][5] # old angle
            else:
                phi = 0
        else:
            phi = math.atan2(vy,vx)

        # append values to new array
        track_points2.append([current_time, x_ish, y_ish, ele, v, phi, lat, lon, dist])

        # Increment the "current time" by the frame duration
        current_time += timedelta(seconds=dt)
    
    # Smooth v & elev
    update_interval_realtime = 0.5
    interval = timedelta(seconds=speedup*update_interval_realtime)
    start_time = track_points2[0][0]
    sum_velocity = 0
    sum_ele = 0
    count = 0
    for i, (timepoint, xish, yish, ele, velocity, *_) in enumerate(track_points2):
        if timepoint < start_time + interval:
            # Accumulate velocity
            sum_velocity += velocity
            sum_ele += ele
            count += 1
        else:
            # Insert average velocity
            for j in range(i - count, i):
                track_points2[j][4] = sum_velocity / count
                track_points2[j][3] = sum_ele / count

            # Reset interval data for the new interval
            sum_velocity = velocity
            sum_ele = ele
            count = 1
            start_time = timepoint

    # Update the last interval if not already done
    if count > 0:
        for j in range(len(track_points2) - count, len(track_points2)):
            track_points2[j][4] = sum_velocity / count
            track_points2[j][3] = sum_ele / count

    
    print("Made 2D-array from trackfile")
    return track_points2, track_metadata

