import gpxpy

def parse_gpx(gpx_file):
    gpx = gpxpy.parse(gpx_file)
    track_points = [] 
    
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                track_points.append([point.time, point.latitude, point.longitude, point.elevation if point.elevation else 0])
    return track_points


