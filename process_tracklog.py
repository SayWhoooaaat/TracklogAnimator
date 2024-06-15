import os
import math
from datetime import timedelta
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

from processing_utils import get_ground_elevation
from processing_utils import collect_3tp_distances, collect_open_distances
from processing_utils import parse_gpx, parse_igc, parse_tcx
from processing_utils import smooth_data, smooth_angles


def process_tracklog(file_path, dt, speedup, target_coords):
    # Find file type
    _, file_extension = os.path.splitext(file_path)
    file_type = file_extension[1:].lower()

    if file_type == 'gpx':
        track_points_temp = parse_gpx(open(file_path, 'r'))
    elif file_type == 'igc':
        track_points_temp = parse_igc(file_path)
    elif file_type == 'tcx':
        track_points_temp = parse_tcx(open(file_path, 'r')) # We get velocity directly!
    else:
        print("Unsupported file type.")
        track_points_temp = None, None
    print(f"Parsing {file_type} file to 2D-array...")

    # Store metadata
    track_metadata = { # This is a dictionary
        'max_latitude': -float('inf'),
        'min_latitude': float('inf'),
        'max_longitude': -float('inf'),
        'min_longitude': float('inf'),
        'dt': dt, #seconds
    }
    for i in range(0, len(track_points_temp)):
        lat = track_points_temp[i][1]
        lon = track_points_temp[i][2]
        track_metadata['max_latitude'] = max(track_metadata['max_latitude'], lat)
        track_metadata['min_latitude'] = min(track_metadata['min_latitude'], lat)
        track_metadata['max_longitude'] = max(track_metadata['max_longitude'], lon)
        track_metadata['min_longitude'] = min(track_metadata['min_longitude'], lon)
    
    # Calculate velocities
    radius = 6371000.0
    for i in range(0, len(track_points_temp)):
        timestamp, latitude, longitude, *_ = track_points_temp[i]
        if i==0:
            vx = 0
            vy = 0
        else:
            time_delta = (track_points_temp[i][0]-track_points_temp[i-1][0]).total_seconds()
            lon_prev = track_points_temp[i-1][2]
            lat_prev = track_points_temp[i-1][1]
            if time_delta == 0: # old velocities
                vx = track_points_temp[i-1][4]
                vy = track_points_temp[i-1][5]
            else:
                vx = (longitude-lon_prev) * math.pi * radius / 180 / time_delta * math.cos(lat*math.pi/180)
                vy = (lat_prev-latitude) * math.pi * radius / 180 / time_delta
            
        track_points_temp[i].append(vx)
        track_points_temp[i].append(vy)

    # Calculate distance
    dist = 0
    dist_threshold = 300
    prev_lat = track_points_temp[0][1]
    prev_lon = track_points_temp[0][2]
    print("Calculating distances...")
    for i in range(0, len(track_points_temp)):
        # find distance between current point and prev_lat, prev_lon
        d_y = (prev_lat - track_points_temp[i][1]) / 180 * math.pi * radius
        d_x = (track_points_temp[i][2] - prev_lon) / 180 * math.pi * math.cos(prev_lat/180*math.pi) * radius
        new_dist = math.sqrt(d_y*d_y + d_x*d_x)
        if new_dist > dist_threshold:
            dist = dist + new_dist
            prev_lat = track_points_temp[i][1]
            prev_lon = track_points_temp[i][2]
        track_points_temp[i].append(dist)

    print(f"Distance: {round(dist/1000)} km. Finishing 2D-array...")

    # Store data with uniform time step
    track_points = []
    current_time = track_points_temp[0][0]
    i = 0 # index of old array
    while current_time < track_points_temp[-1][0]:  # Loop until the last of the original track_points
        
        # Find the appropriate i such that track_points[i][0] <= current_time < track_points[i+1][0]
        while i < len(track_points_temp) - 1 and current_time >= track_points_temp[i + 1][0]:
            i += 1
        t1, lat1, lon1, alt1, vx1, vy1, dist1 = track_points_temp[i]
        t2, lat2, lon2, alt2, vx2, vy2, dist2 = track_points_temp[i + 1]
        fraction = (current_time - t1).total_seconds() / (t2 - t1).total_seconds()
        
        # Interpolate
        altitude = alt1 + fraction * (alt2 - alt1)
        vx = vx1 + fraction * (vx2 - vx1)
        vy = vy1 + fraction * (vy2 - vy1)
        lat = lat1 + fraction * (lat2 - lat1)
        lon = lon1 + fraction * (lon2 - lon1)
        dist = dist1 + fraction * (dist2 - dist1)

        v = math.sqrt(vx*vx+vy*vy)
        if (vx == 0) & (vy == 0):
            if len(track_points) > 0:
                phi = track_points[-1]["direction"] # old angle
            else:
                phi = 0
        else:
            phi = math.atan2(vy,vx)
        
        if len(track_points) == 0:
            vario = 0
        else:
            vario = -(altitude - alt_old) / dt
        alt_old = altitude

        # Find straight line distances
        y_distance = (track_points_temp[0][1] - lat) / 180 * math.pi * radius
        x_distance = (lon - track_points_temp[0][2]) / 180 * math.pi * math.cos(lat/180*math.pi) * radius
        sl_distance = math.sqrt(y_distance**2 + x_distance**2)

        # Find distance to target
        target_distance = None
        if target_coords != None:
            y_distance = (target_coords[0] - lat) / 180 * math.pi * radius
            x_distance = (lon - target_coords[1]) / 180 * math.pi * math.cos(lat/180*math.pi) * radius
            target_distance = int(math.sqrt(y_distance**2 + x_distance**2))

        # append values to new array
        track_point = {
            "timestamp": current_time,
            "lat": lat,
            "lon": lon,
            "altitude": altitude,
            "velocity": v,
            "direction": phi,
            "distance": dist,
            "vario": vario,
            "sl_distance": sl_distance, 
            "target_distance": target_distance
        }
        track_points.append(track_point)

        # Increment the "current time" by the frame duration
        current_time += timedelta(seconds=dt)

    # Find 3pt distances
    track_points = collect_3tp_distances(track_points, dt)

    # Find open distances
    track_points = collect_open_distances(track_points, dt)

    # Smooth vario and direction
    smoothing_time_vario = 20
    smoothing_time_phi = 10
    window_size = round(smoothing_time_vario / dt / 2) * 2 - 1
    
    vario_data = [point["vario"] for point in track_points]
    smoothed_vario = smooth_data(vario_data, window_size)
    for i, point in enumerate(track_points):
        if i < len(smoothed_vario):
            point["vario"] = smoothed_vario[i]
    
    window_size = round(smoothing_time_phi / dt / 2) * 2 - 1
    direction_data = [point["direction"] for point in track_points]
    smoothed_direction = smooth_angles(direction_data, window_size)
    for i, point in enumerate(track_points):
        if i < len(smoothed_direction):
            point["direction"] = smoothed_direction[i]

    # Find ground elevation
    print("Finding ground elevation...")
    heightmap_resolution = 500 # meters
    resolution_lat = round(heightmap_resolution / radius / math.pi * 180, 5)
    resolution_lon = round(heightmap_resolution / radius / math.pi * 180 / math.cos(lat*math.pi/180), 5)
    coordinates = []
    for point in track_points:
        lat = point["lat"]
        lon = point["lon"]
        coordinates.append([lat, lon])
    ground_heights = get_ground_elevation(coordinates, resolution_lat, resolution_lon)
    for i, point in enumerate(track_points):
        track_points[i]["elevation"] = max(ground_heights[i], 0)


    # Limit refresh rate of v, elev and vario
    update_interval_playback = 1
    interval = timedelta(seconds=speedup*update_interval_playback)
    start_time = track_points[0]["timestamp"]
    sum_velocity = 0
    sum_altitude = 0
    sum_elevation = 0
    sum_vario = 0
    count = 0
    for i, point in enumerate(track_points):
        timepoint = point["timestamp"]
        altitude = point["altitude"]
        elevation = point["elevation"]
        velocity = point["velocity"]
        vario = point["vario"]
        if timepoint < start_time + interval:
            # Accumulate velocity
            sum_velocity += velocity
            sum_altitude += altitude
            sum_elevation += elevation
            sum_vario += vario
            count += 1
        else:
            # Insert average velocity
            for j in range(i - count, i):
                track_points[j]["velocity_lr"] = sum_velocity / count
                track_points[j]["altitude_lr"] = sum_altitude / count
                track_points[j]["elevation_lr"] = sum_elevation / count
                track_points[j]["vario_lr"] = sum_vario / count

            # Reset interval data for the new interval
            sum_velocity = velocity
            sum_altitude = altitude
            sum_elevation = elevation
            sum_vario = vario
            count = 1
            start_time = timepoint
    
    # Update the last interval if not already done
    if count > 0:
        for j in range(len(track_points) - count, len(track_points)):
            track_points[j]["velocity_lr"] = sum_velocity / count
            track_points[j]["altitude_lr"] = sum_altitude / count
            track_points[j]["elevation_lr"] = sum_elevation / count
            track_points[j]["vario_lr"] = sum_vario / count
    
    # Add local time
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=track_points[0]["lat"], lng=track_points[0]["lon"])
    for point in track_points:
        utc_time = point["timestamp"]
        local_time = utc_time.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(timezone_str))
        #point.append(local_time)
        point["local_time"] = local_time
    
    print("Made 2D-array from trackfile")
    return track_points, track_metadata

