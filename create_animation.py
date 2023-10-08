import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
import gpxpy

def create_animation(img_path='map_stitched.png', out_path='animation.mp4'):
    fps = 10
    interval = 1000 / fps
    tracklog = parse_gpx('testactivity.gpx')
    
    # Load the map image
    img = plt.imread(img_path)

    # Create a new figure and axis
    fig, ax = plt.subplots()

    # Display the image
    ax.imshow(img)

    # Create the arrow
    x0, y0, dx, dy = 0, 0, 1, 1  # replace with actual values
    arrow = patches.FancyArrow(x0, y0, dx, dy)
    ax.add_patch(arrow)

    # Define the update function
    def update(frame):
        # Calculate the new position of the arrow
        time, lat, lon = tracklog[frame]
        x, y = lat_lon_to_xy(lat, lon)  # replace with your actual function

        # Update the position of the arrow
        arrow.set_xy([x, y])

    # Create the animation
    ani = animation.FuncAnimation(fig, update, frames=len(tracklog))

    # Save the animation as an MP4 file
    writer = animation.FFMpegWriter(fps=fps)
    ani.save(out_path, writer=writer)

    # Display the animation
    plt.show()



def parse_gpx(file_path):
    """Parse a GPX file and return a list of (time, latitude, longitude) tuples."""
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append((point.time, point.latitude, point.longitude))

    return data



