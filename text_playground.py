import math
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

track_points = []
track_points.append([datetime.now(), 3.1, 3.2, 870.203498, 9.4987345, -0.2, 0.7, 61.1, 9.1])

current_timedate, x, y, ele, v, phi, dt_check, lat, lon = track_points[0]
base_image = Image.open("media/dummy.png").convert("RGBA")

current_time = current_timedate.strftime("%H:%M")
current_date = current_timedate.strftime("%Y-%m-%d")

draw5 = ImageDraw.Draw(base_image)
text_color = (255, 255, 255, 255)
draw5.text((30,30), current_time, font=ImageFont.truetype("arial.ttf", 40), fill=text_color)
draw5.text((40,76), current_date, font=ImageFont.truetype("arial.ttf", 16), fill=text_color)
draw5.text((60,750), f"{round(ele)} msl", font=ImageFont.truetype("arial.ttf", 20), fill='black')
draw5.text((160,750), f"{round(v,2)} m/s", font=ImageFont.truetype("arial.ttf", 20), fill='black')

base_image.save("media/text_preview.png")
