import math

def append_zoom_levels(track_points, map_width, fps):
    # Goal is to make graph zoom level VS time
    print("Calculating zoom levels...")
    t1 = 60
    t2 = 1
    t3 = 8
    t4 = 1
    t5 = 10
    t_total = len(track_points) / fps
    # actual seconds: (track_points[-1]["timestamp"] - track_points[0]["timestamp"]).total_seconds()

    # Define t0; start time where distance traveled is so long that we need zoom:
    x_pixels_min = track_points[0]["map_coordinate"][0]["x"]
    x_pixels_max = track_points[0]["map_coordinate"][0]["x"]
    y_pixels_min = track_points[0]["map_coordinate"][0]["y"]
    y_pixels_max = track_points[0]["map_coordinate"][0]["y"]
    for i in range(0, len(track_points)):
        x = track_points[i]["map_coordinate"][0]["x"]
        y = track_points[i]["map_coordinate"][0]["y"]
        # Find pixels traveled
        if x > x_pixels_max:
            x_pixels_max = x
        elif x < x_pixels_min:
            x_pixels_min = x
        if y > y_pixels_max:
            y_pixels_max = y
        elif y < y_pixels_min:
            y_pixels_min = y
        pixels_traveled = max(x_pixels_max-x_pixels_min, y_pixels_max-y_pixels_min)
        if pixels_traveled > 0.6 * map_width: # We want changing camera
            t0 = round(i / fps)
            break

    # Find key times
    tx = t_total - t0 - t1 - t5 - t2
    n = max(0, math.floor(tx / (t2 + t3 + t4 + t1)))
    print(f"n: {n}, t_tot = {t_total}, t0 = {t0}, tx = {tx}")

    # Allocate zoom fractions
    for point in track_points:
        point["fraction"] = 0
    for i in range(0, min(len(track_points), fps * t5)): # last big map
        track_points[-1 - i]["fraction"] = 1
    if len(track_points) > fps * (t5 + t2):
        for i in range(0, fps * t2):
            j = len(track_points) - fps * (t5 + t2) + i
            #print(i,j,i/(fps*t2))
            track_points[j]["fraction"] = i / (fps * t2) # last zoom out
    else: # super short tracklog
        for point in track_points:
            point["fraction"] = 1
    
    for p in range(0, n):
        for i in range(0, fps * (t2 + t3 + t4 + t1)):
            j = fps * (t0 + t1 + p*(t2 + t3 + t4 + t1)) + i
            if i < fps * t2: # zoom out
                track_points[j]["fraction"] = i / (fps * t2)
            elif i < fps * (t2 + t3): # big map
                track_points[j]["fraction"] = 1
            elif i < fps * (t2 + t3 + t4): # zoom in
                track_points[j]["fraction"] = 1 - (i - fps * (t2 + t3)) / (fps * t4)
            else: # small map
                track_points[j]["fraction"] = 0


    return track_points




