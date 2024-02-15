import csv
import json

def export_to_csv(track_points, filename='track_points.csv'):

    if not track_points:
        print("The track_points list is empty.")
        return

    # Dynamically determine the headers from the keys of the first dictionary
    fieldnames = list(track_points[0].keys())

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()

        for point in track_points:
            # Convert nested structures to JSON strings to ensure compatibility with CSV format
            flattened_point = {key: (json.dumps(value) if isinstance(value, (dict, list)) else value) for key, value in point.items()}
            writer.writerow(flattened_point)

    print(f"Data exported to {filename}.")
