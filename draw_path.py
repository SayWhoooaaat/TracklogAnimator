from PIL import ImageDraw

def draw_path(map_images, track_points):

    # Create a drawing object
    path_image = map_images[0].copy()
    draw = ImageDraw.Draw(path_image)

    print("Drawing path on map for fun...")
    for i in range(0, len(track_points)):        
        x = track_points[i][12]
        y = track_points[i][13]
        if i > 0:
            draw.line((last_x, last_y, x, y), fill='red', width=2)
        last_x, last_y = x, y
    
    # Save and return the new image
    path_image.save('media/map_with_path.png')
    print("Made map with path")
    
    return
