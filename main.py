
track_file = "tracklogs/jama.igc"
speedup = 60 # Should be 24
fps = 59.94 # Should be 59.94
anim_height = 1080
overlay_width_percentage = 14 # should be 14
minimap_km = 4 # Should be 16? (before i liked 4)
map_scale = 1.0
transparent = False # Should be True
challenge = 1 # 1 = distance, 2 = out and return, 3 = circle, 4 = spot landing
pb = 9 # km, km, km^2


overlay_width = round(anim_height / 9 * 16 * overlay_width_percentage / 100)
minimap_width = round(1080 / 9 * 16 * overlay_width_percentage / 100 * map_scale)
dt = speedup / fps


from process_tracklog import process_tracklog
track_points, track_metadata = process_tracklog(track_file, dt, speedup)

from get_map import get_map
minimap_images, map_metadata = get_map(track_metadata, minimap_width, overlay_width, minimap_km, track_points)

from get_outline import get_outline
outline_image, outline_metadata = get_outline(track_points, overlay_width, anim_height)

from append_pixel_positions import append_pixel_positions
track_points = append_pixel_positions(track_points, map_metadata, outline_metadata)

from append_zoom_levels import append_zoom_levels
track_points = append_zoom_levels(track_points, overlay_width, fps)

from export_to_csv import export_to_csv
export_to_csv(track_points, 'track_points.csv')

from draw_path import draw_path # Unnecessary, but good for testing 
draw_path(minimap_images, track_points) 

from get_preview import get_preview
get_preview(track_points, minimap_images, map_metadata, outline_image, overlay_width, anim_height, challenge, pb)

from animate_path import animate_path
animate_path(track_points, minimap_images, map_metadata, outline_image, fps, overlay_width, anim_height, transparent, challenge, pb)

print("Done!")







