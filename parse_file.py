import os
import math
from datetime import datetime
from datetime import timedelta
import random
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
import time
import sys


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
    
    # Expand the array with more parameters
    radius = 6371000.0
    for i in range(0, len(track_points)):
        timestamp, latitude, longitude, *_ = track_points[i]
        if i==0:
            vx = 0
            vy = 0
        else:
            time_delta = (track_points[i][0]-track_points[i-1][0]).total_seconds()
            lon_prev = track_points[i-1][2]
            lat_prev = track_points[i-1][1]
            if time_delta == 0: # old velocities
                vx = track_points[i-1][4]
                vy = track_points[i-1][5]
            else:
                vx = (longitude-lon_prev) * math.pi * radius / 180 / time_delta * math.cos(lat*math.pi/180)
                vy = (lat_prev-latitude) * math.pi * radius / 180 / time_delta
            
        track_points[i].append(vx)
        track_points[i].append(vy)

    # calculate distance (should do in constant int matrix)
    dist = 0
    dist_threshold = 300
    prev_lat = track_points[0][1]
    prev_lon = track_points[0][2]
    print("Calculating distances...")
    for i in range(0, len(track_points)):
        # find distance between current point and prev_lat, prev_lon
        d_y = (prev_lat - track_points[i][1]) / 180 * math.pi * radius
        d_x = (track_points[i][2] - prev_lon) / 180 * math.pi * math.cos(prev_lat/180*math.pi) * radius
        new_dist = math.sqrt(d_y*d_y + d_x*d_x)
        if new_dist > dist_threshold:
            dist = dist + new_dist
            prev_lat = track_points[i][1]
            prev_lon = track_points[i][2]
        track_points[i].append(dist)

    print(f"Distance: {round(dist/1000)} km. Finishing 2D-array...")

    # Making contant interval matrix
    track_points3 = []
    current_time = track_points[0][0]
    i = 0 # index of old array
    while current_time < track_points[-1][0]:  # Loop until the last of the original track_points
        
        # Find the appropriate i such that track_points[i][0] <= current_time < track_points[i+1][0]
        while i < len(track_points) - 1 and current_time >= track_points[i + 1][0]:
            i += 1
        t1, lat1, lon1, ele1, vx1, vy1, dist1 = track_points[i]
        t2, lat2, lon2, ele2, vx2, vy2, dist2 = track_points[i + 1]
        fraction = (current_time - t1).total_seconds() / (t2 - t1).total_seconds()
        
        # Interpolate
        ele = ele1 + fraction * (ele2 - ele1)
        vx = vx1 + fraction * (vx2 - vx1)
        vy = vy1 + fraction * (vy2 - vy1)
        lat = lat1 + fraction * (lat2 - lat1)
        lon = lon1 + fraction * (lon2 - lon1)
        dist = dist1 + fraction * (dist2 - dist1)

        v = math.sqrt(vx*vx+vy*vy)
        if (vx == 0) & (vy == 0):
            if len(track_points3) > 0:
                phi = track_points3[-1]["direction"] # old angle
            else:
                phi = 0
        else:
            phi = math.atan2(vy,vx)

        # append values to new array
        track_point = {
            "timestamp": current_time,
            "lat": lat,
            "lon": lon,
            "elevation": ele,
            "velocity": v,
            "direction": phi,
            "distance": dist
        }
        track_points3.append(track_point)

        # Increment the "current time" by the frame duration
        current_time += timedelta(seconds=dt)
    
    # Smooth v & elev
    update_interval_realtime = 0.5
    interval = timedelta(seconds=speedup*update_interval_realtime)
    start_time = track_points3[0]["timestamp"]
    sum_velocity = 0
    sum_ele = 0
    count = 0
    for i, point in enumerate(track_points3):
        timepoint = point["timestamp"]
        ele = point["elevation"]
        velocity = point["velocity"]
        if timepoint < start_time + interval:
            # Accumulate velocity
            sum_velocity += velocity
            sum_ele += ele
            count += 1
        else:
            # Insert average velocity
            for j in range(i - count, i):
                track_points3[j]["velocity"] = sum_velocity / count
                track_points3[j]["elevation"] = sum_ele / count

            # Reset interval data for the new interval
            sum_velocity = velocity
            sum_ele = ele
            count = 1
            start_time = timepoint
    
    # Update the last interval if not already done
    if count > 0:
        for j in range(len(track_points3) - count, len(track_points3)):
            track_points3[j]["velocity"] = sum_velocity / count
            track_points3[j]["elevation"] = sum_ele / count
    
    # Add local time
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=track_points3[0]["lat"], lng=track_points3[0]["lon"])
    for point in track_points3:
        utc_time = point["timestamp"]
        local_time = utc_time.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(timezone_str))
        #point.append(local_time)
        point["local_time"] = local_time
    
    print("Made 2D-array from trackfile")
    return track_points3, track_metadata

