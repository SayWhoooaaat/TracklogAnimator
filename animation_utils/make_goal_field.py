import math
from PIL import Image, ImageDraw, ImageFont
import csv
import json
from datetime import datetime


def make_goal_field(goal_type, track_point, width, height, res_scale, goal_text_reference): # Height should be 54-ish
    sl_distance = track_point["sl_distance"]
    open_distance = track_point["open_dist"]
    distance_3tp = track_point["3tp_dist"]
    target_distance = track_point["target_distance"]

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    textsize = round(18*res_scale)
    font = ImageFont.truetype("arial.ttf", textsize)
    
    # Choose goal type
    if goal_type == '3tp_distance': 
        # 3tp-distance
        line1_text = f"Distance (3tp): {round(distance_3tp/1000)} km"
        line2_text = goal_text_reference
    elif goal_type == 'open_distance': 
        # Open distance
        line1_text = f"Open distance: {round(open_distance/1000)} km"
        line2_text = goal_text_reference
    elif goal_type == 'declared_goal':
        # Declared goal
        line1_text = f"Open distance: {round(open_distance/1000)} km"
        line2_text = f"Distance to goal: {round(target_distance/1000)} km"
    else:
        print('No goal declared')
        line1_text = ""
        line2_text = ""

    line1_text_width = draw.textlength(line1_text, font=font)
    line2_text_width = draw.textlength(line2_text, font=font)
    clearance = width - max(line1_text_width, line2_text_width)
    if clearance < 0:
        print(f"Problem: Goal text {round(clearance)} pixels wider than animation frame.")

    draw.text((8*res_scale, 4*res_scale), line1_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    draw.text((8*res_scale, 4*res_scale + textsize*1.4), line2_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    
    return image


# Testing purposes:
if __name__ == "__main__":
    filename = 'track_points.csv'
    # read track points
    track_points = []
    datetime_fields = ['local_time', 'timestamp']
    with open(filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, value in row.items():
                try:
                    # Try converting to float if possible
                    row[key] = float(value)
                except ValueError:
                    # Check if it's a datetime field and convert
                    if key in datetime_fields:
                        row[key] = datetime.fromisoformat(value)
                    else:
                        # If conversion fails, check if it's a JSON string
                        try:
                            row[key] = json.loads(value)
                        except json.JSONDecodeError:
                            # If it's not JSON, leave it as the original string
                            pass
            track_points.append(row)

    track_point = track_points[int(len(track_points)*0.7)]

    # make up rest of data
    width = 250
    height = 60
    res_scale = 1 # for 1080p
    goal_type = 'declared_goal' # open_distance, 3tp_distance, declared_goal
    goal_text_reference = 'PB: 9 km'

    
    goal_field_frame = make_goal_field(goal_type, track_point, width, height, res_scale, goal_text_reference)
    

    goal_field_frame.save("media/goal_field_test.png")
    
