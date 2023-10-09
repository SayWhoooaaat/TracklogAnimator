

from parse_gpx import parse_gpx
track_points, track_metadata = parse_gpx(open('testactivity.gpx', 'r'))


from get_map_stamen import get_map_stamen
zoom = 13
map_image, map_metadata = get_map_stamen(track_metadata, zoom)

print(map_metadata)

from draw_path import draw_path
path_image = draw_path(map_metadata, map_image, track_points)

from animate_path import animate_path
animate_path(map_metadata, map_image, track_points)

print("Done!")







