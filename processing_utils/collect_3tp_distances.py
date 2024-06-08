import numpy as np
import math
import csv
from scipy.interpolate import interp1d
from datetime import datetime
import json

def calculate_distance(point1, point2):
    radius = 6371000.0
    lat = (point1[1] + point2[1]) / 2
    y_distance = (point1[1] - point2[1]) / 180 * math.pi * radius
    x_distance = (point1[0] - point2[0]) / 180 * math.pi * math.cos(lat / 180 * math.pi) * radius
    sl_distance = math.sqrt(y_distance * y_distance + x_distance * x_distance)
    return sl_distance

def precompute_distances(tracklog):
    n = len(tracklog)
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dist_matrix[i][j] = calculate_distance(tracklog[i], tracklog[j])
    return dist_matrix

def compute_3tp_distance(tracklog, dist_matrix, end_idx):
    n = end_idx + 1  # Number of points up to and including end_idx
    
    # Initialize distance and path tables
    dist = np.full((n, 4), -np.inf)
    path = np.full((n, 4), -1)
    
    # Base case: the distance with only the first point
    for i in range(1, n - 1):  # Only consider up to the second-to-last point in this range
        dist[i][1] = dist_matrix[0][i]
    
    # Fill the table
    for j in range(2, 4):  # Iterate over the number of points to select (2 to 4)
        for i in range(j, n - 1):  # Iterate over possible endpoints (up to the second-to-last point)
            for k in range(j-1, i):  # Iterate over previous points to form the path
                current_dist = dist[k][j-1] + dist_matrix[k][i]
                if current_dist > dist[i][j]:
                    dist[i][j] = current_dist
                    path[i][j] = k  # Record the previous point
    
    # Find the optimal path to the second-to-last point, then add the last point
    max_distance = -np.inf
    last_index = -1
    for i in range(3, n - 1):  # Find the best path ending at the second-to-last point
        current_dist = dist[i][3] + dist_matrix[i][end_idx]
        if current_dist > max_distance:
            max_distance = current_dist
            last_index = i
    
    # Reconstruct the path
    selected_indexes = [end_idx]
    current_index = last_index
    for j in range(3, 0, -1):
        selected_indexes.append(current_index)
        current_index = path[current_index][j]
    selected_indexes.append(0)
    
    selected_indexes.reverse()
    selected_points = [tracklog[i] for i in selected_indexes]
    
    return max_distance, selected_points, selected_indexes


def collect_3tp_distances(track_points, dt):
    print('finding 3pt distances...')
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
        #print(total_time.total_seconds(), dt, course_dt, step_size)
        course_coords = lon_lat_points[::step_size]

    # Precomputing 3tp distances
    print('reduced from ',len(lon_lat_points), ' to ',len(course_coords)," trackpoints. Precomputing...")
    dist_matrix = precompute_distances(course_coords)
    print("Precomputing complete, finding 3tp distances...")

    # Computing 3tp distances
    calc_interval_seconds = 200
    calc_step_size = int(calc_interval_seconds / course_dt)
    distances_3tp = []
    indices_3tp = []
    time_est = len(course_coords) ** 3 / calc_step_size / 2 / 10**8
    print('estimated time: ', round(time_est,1), ' minutes')
    for end_idx in range(4, len(course_coords), calc_step_size): # Index relative to course_coords
        distance_3tp, selected_points, selected_indexes = compute_3tp_distance(course_coords, dist_matrix, end_idx)
        distances_3tp.append(distance_3tp)
        indices_3tp.append(end_idx * step_size) # Index now relative to lon_lat_points again

    # Adding first and last indices manually
    indices_3tp = [0] + indices_3tp + [len(track_points) - 1]
    distances_3tp = [0] + distances_3tp + [distances_3tp[-1]]

    # Interpolate 5pt distances
    interp_func = interp1d(indices_3tp, distances_3tp, kind='linear', bounds_error=False, fill_value=(0, distances_3tp[-1]))

    # Populate track_points with interpolated values from five_pt_list
    for i, point in enumerate(track_points):
        point["3tp_dist"] = int(interp_func(i))
    
    # Now calculate the last point exactly
    print('Computing 3tp-distance precisely...')
    max_res = 8000
    if len(lon_lat_points) < max_res:
        time_est = len(lon_lat_points) ** 2 / 10**8 * 1.9
        print('estimated time: ', round(time_est,1), ' minutes.')
        dist_matrix = precompute_distances(lon_lat_points)
        distance_3tp, selected_points, selected_indexes = compute_3tp_distance(lon_lat_points, dist_matrix, len(lon_lat_points)-1)
    else:
        course_dt = total_time.total_seconds() / max_res
        print('Too long tracklog, increasing dt to ', round(course_dt,1))
        step_size = int(course_dt / dt)
        course_coords = lon_lat_points[::step_size]
        if lon_lat_points[-1] not in course_coords:
            course_coords.append(lon_lat_points[-1])
        time_est = len(course_coords) ** 2 / 10**8 * 1.9
        print('estimated time: ', round(time_est,1), ' minutes.')
        dist_matrix = precompute_distances(course_coords)
        distance_3tp, selected_points, selected_indexes = compute_3tp_distance(course_coords, dist_matrix, len(course_coords)-1)
    track_points[-1]["3tp_dist"] = int(distance_3tp)
    track_points[-2]["3tp_dist"] = int(distance_3tp) # Redundancy
    
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

    updated_track_points = collect_3tp_distances(track_points, dt)
    inspect_interval = int(60/dt)
    for i in range(0, len(track_points), inspect_interval):
        print(track_points[i]["3tp_dist"])
    print(track_points[-3]["3tp_dist"])
    print(track_points[-1]["3tp_dist"])


