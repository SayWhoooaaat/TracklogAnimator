from PIL import Image, ImageDraw, ImageFont

def make_altibar_frame(w, h, scale, altitude, elevation, vario, vario_lr, max_altitude, altitude_lr, elevation_lr, elevation_active):
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    textsize = round(20*scale)
    font = ImageFont.truetype("arial.ttf", textsize)

    bar_max = max(2000, int(max_altitude/1000 + 1) * 1000)

    bar_width = 30*scale
    bar_height = round(h*0.8)
    bar_x = 86 * scale
    bar_y = round(h*0.1)

    # Find y-positions
    altibar_pilot = altitude / bar_max * bar_height
    altibar_ground = elevation / bar_max * bar_height

    # Draw bar
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(240, 240, 240, 180), outline ='black', width=round(2*scale))
    draw.rectangle([bar_x, bar_y + bar_height - altibar_ground, bar_x + bar_width, bar_y + bar_height], fill=(200, 255, 200, 120), outline ='black', width=round(2*scale))
    
    # Draw arrow
    arrow = [(-1,0), (1,0), (1,3), (2,3), (0,6), (-2,3), (-1,3)]
    arrow_width = 8
    ah_max = round(h*0.2)
    if vario < -0.5: # lift
        arrow_height = -min(5,-vario) / 5 * ah_max / 6
    elif vario > 5: # sink
        arrow_height = ah_max/2/6
    else: # calm
        arrow_height = 0
    
    arrow_x = bar_x + bar_width/2
    arrow_y = bar_y + bar_height - altibar_pilot
    scaled_arrow = [(arrow_x + px * arrow_width, arrow_y + py * arrow_height) for px, py in arrow]
    draw.polygon(scaled_arrow, fill=(255, 40, 40, 220), outline ='black', width=round(2*scale))

    # Draw pilot bar
    draw.rectangle([bar_x, bar_y + bar_height - altibar_pilot - 3*scale, bar_x + bar_width, bar_y + bar_height - altibar_pilot + 3*scale], fill="red", outline ='black', width=round(2*scale))


    # Find text positions
    pilot_text = f"{round(altitude_lr/10)*10} m"
    if elevation_active:
        ground_text = f"{round(elevation_lr/10)*10}"
    else:
        ground_text = ""

    barmax_text = f"{bar_max}"
    if arrow_height == 0:
        vario_text = ""
    else:
        vario_text = f"{abs(round(vario_lr))} m/s"
    
    ground_text_width = draw.textlength(ground_text, font=font)
    pilot_text_width = draw.textlength(pilot_text, font=font)
    barmax_text_width = draw.textlength(barmax_text, font=font)

    # Draw text
    draw.text((bar_x-ground_text_width-8*scale, bar_y + bar_height-altibar_ground - textsize/2), ground_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    draw.text((bar_x-barmax_text_width-8*scale, bar_y - textsize/2), barmax_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    draw.text((bar_x-pilot_text_width-8*scale, bar_y + bar_height-altibar_pilot - textsize/2), pilot_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    draw.text((bar_x+bar_width+8*scale, bar_y + bar_height-altibar_pilot + 3*arrow_height - textsize/2), vario_text, font=font, fill='white', stroke_width=1, stroke_fill='black')
    
    return image



# Testing purposes:
if __name__ == "__main__":
    w = 250
    h = 280
    scale = 1.001
    altitude = 911
    elevation = 340
    vario = -3 # negative is up
    altitude_lr = altitude
    elevation_lr = elevation
    vario_lr = vario
    max_altitude = 1401
    elevation_active = True

    base_image = Image.open("media/preview_background.png").convert("RGBA")

    # Calling function
    altibar_image = make_altibar_frame(w,h,scale,altitude,elevation,vario, vario_lr, max_altitude, altitude_lr, elevation_lr, elevation_active)

    base_image.paste(altibar_image, (0, round(1080*0.4)), altibar_image)
    base_image.save("media/altibar_test.png")

