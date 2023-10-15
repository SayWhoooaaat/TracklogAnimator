
track_file = "testactivity.tcx"
speedup = 50
fps = 30
dt = speedup / fps

from parse_file import parse_file
track_points, track_metadata = parse_file(track_file, dt)

#import csv
#with open('array_output.csv', 'w', newline='') as f:
#    writer = csv.writer(f)
#    writer.writerows(track_points)

from get_map_stamen import get_map_stamen
zoom = 13
map_image, map_metadata = get_map_stamen(track_metadata, zoom)

from draw_path import draw_path
path_image = draw_path(map_metadata, map_image, track_points) # Redundant, but good for testing 

from animate_path import animate_path
animate_path(map_metadata, map_image, track_points, fps)

print(f"map_metadata: {map_metadata}")
print("dt =", dt)







