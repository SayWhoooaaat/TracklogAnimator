

from parse_gpx import parse_gpx
track_points, track_metadata = parse_gpx(open('testactivity.gpx', 'r'))

from get_map_stamen import get_map_stamen
zoom = 13
map_image, map_metadata = get_map_stamen(track_metadata, zoom)

from draw_path import draw_path
path_image = draw_path(map_metadata, map_image, track_points) # Redundant, but good for testing 

from animate_path import animate_path
animate_path(map_metadata, map_image, track_points)

#print(f"track_metadata: {track_metadata}")
print(f"map_metadata: {map_metadata}")
print("Done!")







