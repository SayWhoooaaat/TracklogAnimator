
from datetime import datetime, timedelta

def parse_igc(igc_file_path):
    track_points = []
    base_time = None  # Base time for the flight

    with open(igc_file_path, 'r') as f:
        for line in f:
            if line.startswith('HFDTEDATE:'):
                line = line.strip()
                day, month, year = map(int, [line[10:12], line[12:14], line[14:16]])
                base_time = datetime(year + 2000, month, day)  # Assuming year 2000+

            elif line.startswith('B'):  # Fix line
                time_str = line[1:7]
                time_delta = timedelta(hours=int(time_str[0:2]), minutes=int(time_str[2:4]), seconds=int(time_str[4:6]))
                timestamp = base_time + time_delta if base_time else None
                
                lat = int(line[7:9]) + float(line[9:14]) / 60000
                if line[14] == 'S':
                    lat = -lat

                lon = int(line[15:18]) + float(line[18:23]) / 60000
                if line[23] == 'W':
                    lon = -lon

                alt = int(line[25:30]) # Works for most, but 0 from gpsdump!
                gps_alt = int(line[30:35]) # Usually more precise

                # Add the point to the track_points array
                track_points.append([timestamp, lat, lon, gps_alt])

    return track_points

