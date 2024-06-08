import math
import csv
from scipy.interpolate import interp1d
from datetime import datetime
import json

def calculate_distance(point1, point2): # Haversine is more precise but 80% slower
    radius = 6371000.0
    lat = (point1[1] + point2[1]) / 2
    y_distance = (point1[1] - point2[1]) / 180 * math.pi * radius
    x_distance = (point1[0] - point2[0]) / 180 * math.pi * math.cos(lat / 180 * math.pi) * radius
    sl_distance = math.sqrt(y_distance * y_distance + x_distance * x_distance)
    return sl_distance 

def find_open_distance(tracklog):
    n = len(tracklog)
    max_distance = 0
    for i in range(n):
        for j in range(i + 1, n):
            distance = calculate_distance(tracklog[i], tracklog[j])
            if distance > max_distance:
                max_distance = distance
    return max_distance


def collect_open_distances(track_points, dt):
    print('finding open distances...')
    lon_lat_points = [(point['lon'], point['lat']) for point in track_points]

    # Reducing number of points
    max_res = 1500
    course_dt = 10 # seconds
    step_size = int(course_dt / dt)
    course_coords = lon_lat_points[::step_size]
    if len(course_coords) > max_res:
        total_time = track_points[-1]['timestamp'] - track_points[0]['timestamp']
        course_dt = total_time.total_seconds() / max_res
        step_size = int(course_dt / dt)
        course_coords = lon_lat_points[::step_size]

    # Precomputing 3tp distances
    print('reduced from ',len(lon_lat_points), ' to ',len(course_coords)," trackpoints. finding open distances...")

    # Computing 3tp distances
    calc_interval_seconds = 200
    calc_step_size = int(calc_interval_seconds / course_dt)
    open_distances = []
    open_distance_indices = []
    time_est = len(course_coords) ** 3 / calc_step_size / 10**8 * 0.14
    print('estimated time: ', round(time_est,1), ' minutes')
    for end_idx in range(4, len(course_coords), calc_step_size): # Index relative to course_coords
        open_distance = find_open_distance(course_coords[:end_idx])
        open_distances.append(open_distance)
        open_distance_indices.append(end_idx * step_size) # Index now relative to lon_lat_points again

    # Adding first and last indices manually
    open_distance_indices = [0] + open_distance_indices + [len(track_points) - 1]
    open_distances = [0] + open_distances + [open_distances[-1]]

    # Interpolate open distances
    interp_func = interp1d(open_distance_indices, open_distances, kind='linear', bounds_error=False, fill_value=(0, open_distances[-1]))

    # Populate track_points with interpolated values
    for i, point in enumerate(track_points):
        point["open_dist"] = int(interp_func(i))
    
    # Now calculate the last point exactly
    print('Computing open distance precisely...')
    max_res = 10000
    if len(lon_lat_points) < max_res:
        time_est = len(lon_lat_points) ** 2 / 10**8 * 0.5
        print('estimated time: ', round(time_est,1), ' minutes.')
        open_distance = find_open_distance(lon_lat_points)
    else:
        course_dt = total_time.total_seconds() / max_res
        print('Too long tracklog, increasing dt to ', round(course_dt,1))
        step_size = int(course_dt / dt)
        course_coords = lon_lat_points[::step_size]
        if lon_lat_points[-1] not in course_coords:
            course_coords.append(lon_lat_points[-1])
        time_est = len(course_coords) ** 2 / 10**8 * 0.5
        print('estimated time: ', round(time_est,1), ' minutes.')
        open_distance = find_open_distance(course_coords)
    track_points[-1]["open_dist"] = int(open_distance)
    track_points[-2]["open_dist"] = int(open_distance) # Redundancy

    return track_points


# Testing:
if __name__ == "__main__":
    filename = 'track_points.csv'
    # read track points
    track_points = []
    datetime_fields = ['local_time', 'timestamp']
    with open(filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, value in row.items():
                try:
                    # Try converting to float if possible
                    row[key] = float(value)
                except ValueError:
                    # Check if it's a datetime field and convert
                    if key in datetime_fields:
                        row[key] = datetime.fromisoformat(value)
                    else:
                        # If conversion fails, check if it's a JSON string
                        try:
                            row[key] = json.loads(value)
                        except json.JSONDecodeError:
                            # If it's not JSON, leave it as the original string
                            pass
            track_points.append(row)

    # Find dt in log
    delta_time = track_points[1]['timestamp'] - track_points[0]['timestamp']
    dt = delta_time.total_seconds()
    print(dt)

    updated_track_points = collect_open_distances(track_points, dt)
    inspect_interval = int(600/dt)
    for i in range(0, len(track_points), inspect_interval):
        print(track_points[i]["open_dist"])
    print(track_points[-3]["open_dist"])
    print(track_points[-1]["open_dist"])


