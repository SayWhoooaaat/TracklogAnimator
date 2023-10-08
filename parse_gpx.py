import gpxpy

def parse_gpx(gpx_file):
    gpx = gpxpy.parse(gpx_file)
    
    gpx_points = []
    gpx_metadata = {
        'max_latitude': -float('inf'),
        'min_latitude': float('inf'),
        'max_longitude': -float('inf'),
        'min_longitude': float('inf'),
    }
    
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                # Update max and min values
                gpx_metadata['max_latitude'] = max(gpx_metadata['max_latitude'], point.latitude)
                gpx_metadata['min_latitude'] = min(gpx_metadata['min_latitude'], point.latitude)
                gpx_metadata['max_longitude'] = max(gpx_metadata['max_longitude'], point.longitude)
                gpx_metadata['min_longitude'] = min(gpx_metadata['min_longitude'], point.longitude)
                
                # Add to 2D array
                gpx_points.append([point.time, point.latitude, point.longitude, point.elevation if point.elevation else 0])
                
    # Calculate the averages if needed
    gpx_metadata['avg_latitude'] = (gpx_metadata['max_latitude'] + gpx_metadata['min_latitude']) / 2
    gpx_metadata['avg_longitude'] = (gpx_metadata['max_longitude'] + gpx_metadata['min_longitude']) / 2
    
    return gpx_points, gpx_metadata
