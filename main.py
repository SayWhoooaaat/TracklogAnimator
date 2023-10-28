
track_file = "tracklogs/gpx_loen.gpx"
speedup = 50
fps = 30
dt = speedup / fps

anim_pixels = 300
anim_km = 4


from parse_file import parse_file
track_points, track_metadata = parse_file(track_file, dt)

#import csv
#with open('array_output.csv', 'w', newline='') as f:
#    writer = csv.writer(f)
#    writer.writerows(track_points)

from get_outline import get_outline
get_outline(track_points)

from get_map_mapbox import get_map_mapbox
map_image, map_metadata = get_map_mapbox(track_metadata, anim_pixels, anim_km)

from draw_path import draw_path
path_image = draw_path(map_metadata, map_image, track_points) # Redundant, but good for testing 

# Make preview image here


from animate_path import animate_path
animate_path(map_metadata, map_image, track_points, fps, anim_pixels)

print("Done!")







