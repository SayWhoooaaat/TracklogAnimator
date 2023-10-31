
track_file = "tracklogs/gpx_loen.gpx"
speedup = 61
fps = 30
dt = speedup / fps

overlay_width = 300
minimap_km = 8


from parse_file import parse_file
track_points, track_metadata = parse_file(track_file, dt)

import csv
with open('array_output.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(track_points)

from get_map import get_map
map_image, map_metadata = get_map(track_metadata, overlay_width, minimap_km, track_points)

from get_outline import get_outline
outline_image, outline_metadata = get_outline(track_points, track_metadata, width=overlay_width)

# Expand track_points with xy pixels metadata & xy pixels outlinedata
# track_points = append_pixel_positions(track_points, map_metadata, outline_metadata)

from draw_path import draw_path # Redundant, but good for testing 
path_image = draw_path(map_metadata, map_image, track_points) 

from get_preview import get_preview
get_preview(track_points, map_image, map_metadata, outline_image, outline_metadata, overlay_width)

from animate_path import animate_path
animate_path(track_points, map_image, map_metadata, outline_image, outline_metadata, fps, overlay_width)

print("Done!")







