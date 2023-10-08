

from parse_gpx import parse_gpx
gpx_points, gpx_metadata = parse_gpx(open('testactivity.gpx', 'r'))


from get_map_stamen import get_map_stamen
zoom = 13
map_image, map_data = get_map_stamen(gpx_metadata, zoom)

print(map_data)

from draw_path import draw_path
path_image = draw_path(map_data, map_image, gpx_points)








