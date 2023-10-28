
track_file = "tracklogs/gpx_loen.gpx"
speedup = 50
fps = 30
dt = speedup / fps

overlay_width = 300
minimap_km = 4


from parse_file import parse_file
track_points, track_metadata = parse_file(track_file, dt)

#import csv
#with open('array_output.csv', 'w', newline='') as f:
#    writer = csv.writer(f)
#    writer.writerows(track_points)

from get_outline import get_outline
get_outline(track_points, width=overlay_width)
# Should return with image and metadata for animating

from get_map_mapbox import get_map_mapbox
map_image, map_metadata = get_map_mapbox(track_metadata, overlay_width, minimap_km)

from draw_path import draw_path # Redundant, but good for testing 
path_image = draw_path(map_metadata, map_image, track_points) 

# Make preview image here
from get_preview import get_preview
get_preview(map_metadata, map_image, track_points, overlay_width)

exit()

from animate_path import animate_path
animate_path(map_metadata, map_image, track_points, fps, overlay_width)

print("Done!")







