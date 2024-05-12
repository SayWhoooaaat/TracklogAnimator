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

    # Define t0; start time where distance traveled is so long that we need zoom:
    t0 = t_total
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
        track_points[i]["pixel_distance_line"] = pixels_traveled
        if pixels_traveled > 0.6 * map_width and t0 == t_total:
            t0 = round(i / fps)

    # Find key times
    tx = t_total - t0 - t1 - t5 - t2
    n = max(0, math.floor(tx / (t2 + t3 + t4 + t1)))
    no_maps = len(track_points[0]["map_coordinate"])
    print(f"n: {n}, t_tot = {t_total}, t0 = {t0}, tx = {tx}, no_maps = {no_maps}")
    padding = 40

    # ALLOCATE ZOOM FRACTIONS
    # All values
    for point in track_points:
        point["fraction"] = 0
        point["zoom_level"] = 0

    # Last values
    scale = (track_points[-1]["pixel_distance_line"] + padding) / map_width
    zoom_level = min(max(math.ceil(math.log2(max(1,scale))), 0), no_maps-1)
    for i in range(0, min(len(track_points), int(fps * t5))): # Last big map
        track_points[-1 - i]["fraction"] = 1
        track_points[-1 - i]["zoom_level"] = zoom_level
    if len(track_points) > int(fps * (t5 + t2)):
        for i in range(0, int(fps * t2)): # last zoom out
            j = len(track_points) - int(fps * (t5 + t2)) + i
            track_points[j]["fraction"] = i / (fps * t2)
            track_points[j]["zoom_level"] = track_points[j]["fraction"] * zoom_level
    else: # super short tracklog
        for point in track_points:
            point["fraction"] = 1
            point["zoom_level"] = zoom_level
    
    # Values every cycle
    for p in range(0, n):
        i_crit = int(fps * (t0 + (p + 1) * (t1 + t2 + t3 + t4)))
        scale = (track_points[i_crit]["pixel_distance_line"] + padding) / map_width
        zoom_level = min(max(math.ceil(math.log2(max(1,scale))), 0), no_maps-1)
        print(p, scale, zoom_level)
        for i in range(0, int(fps * (t2 + t3 + t4 + t1))):
            j = int(fps * (t0 + t1 + p*(t2 + t3 + t4 + t1))) + i
            if i < int(fps * t2): # zoom out
                track_points[j]["fraction"] = i / (fps * t2)
                track_points[j]["zoom_level"] = track_points[j]["fraction"] * zoom_level
            elif i < int(fps * (t2 + t3)): # big map
                track_points[j]["fraction"] = 1
                track_points[j]["zoom_level"] = zoom_level
            elif i < int(fps * (t2 + t3 + t4)): # zoom in
                track_points[j]["fraction"] = 1 - (i - fps * (t2 + t3)) / (fps * t4)
                track_points[j]["zoom_level"] = track_points[j]["fraction"] * zoom_level
            else: # small map
                track_points[j]["fraction"] = 0
                track_points[j]["zoom_level"] = 0


    return track_points




