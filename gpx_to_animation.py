import gpxpy
import gpxpy.gpx

# Parsing an existing file:
with open('testactivity.gpx', 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)

    count = 0
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                print('Time: {0} -- Latitude: {1} -- Longitude: {2} -- Elevation: {3}'.format(point.time, point.latitude, point.longitude, point.elevation))
                count += 1
                if count >= 5:
                    break
