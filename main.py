
track_file = "tracklogs/gpx_grott.gpx"
speedup = 25
fps = 30
anim_height = 1080
overlay_width = 300
minimap_km = 4
# Speedup should be 25. minimap_km should be 4-6. 

dt = speedup / fps


from process_tracklog import process_tracklog
track_points, track_metadata = process_tracklog(track_file, dt, speedup)

from get_map import get_map
minimap_images, map_metadata = get_map(track_metadata, overlay_width, minimap_km, track_points)

from get_outline import get_outline
outline_image, outline_metadata = get_outline(track_points, overlay_width, anim_height)

from append_pixel_positions import append_pixel_positions
track_points = append_pixel_positions(track_points, map_metadata, outline_metadata)

from export_to_csv import export_to_csv
export_to_csv(track_points, 'track_points.csv')

from draw_path import draw_path # Unnecessary, but good for testing 
draw_path(minimap_images, track_points) 

from get_preview import get_preview
get_preview(track_points, minimap_images, map_metadata, outline_image, overlay_width)

from animate_path import animate_path
animate_path(track_points, minimap_images, map_metadata, outline_image, fps, overlay_width, anim_height)

print("Done!")







