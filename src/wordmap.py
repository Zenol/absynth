from PIL import Image, ImageDraw, ImageFont

font = None

def build_text_block(w, h, msg, color=(0, 0, 0), bg_color=(255, 255, 255)):
    import operator
    # Create a temporary image
    size = tuple(map(operator.add, font.getsize(msg), (0, 0)))
    tmp = Image.new("RGB", size, bg_color)
    # Draw msg on this image
    draw = ImageDraw.Draw(tmp)
    draw.text((0, 0), msg, color, font=font)
    # Resize
    return tmp.resize((w, h), Image.ANTIALIAS)

def generate_block(iw, ih, words, lvls = 4,
                   bg_color = (255, 255, 255),
                   fg_color1 = (40, 200, 100),
                   fg_color2 = (0, 50, 200),
                   font_name = "font/DroidSansMono.ttf"):
    global font
    font = ImageFont.truetype(font_name, 120)
    step_size = int(ih / lvls)
    out = Image.new("RGB", (iw, ih), bg_color)
    draw = ImageDraw.Draw(out)
    word_id = 0
    sum_h = 0
    for i in range(0, lvls):
        w = int(iw / (2**i))
        h = int(ih / 2**(i + 1))
        for j in range(0, 2**i):
            # Compute location
            x = j * w
            y = sum_h
            # Compute color
            fb = i / lvls
            fa = 1.0 - fb
            wmean = lambda a, b: int((fa * a + fb * b) / (fa + fb))
            color = tuple(map(wmean, fg_color1, fg_color2))
            # Compute image block
            block = build_text_block(w, h, words[word_id],
                                     color=color, bg_color=bg_color)
            out.paste(block, (x, y , x + w, y + h))
            # Switch to next word
            word_id += 1
        sum_h += h
    return out


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 2:
        print(sys.argv[0] + ' nb_levels big list of words to use...')
        exit(1)
    generate_block(600, 300, sys.argv[2:], lvls=int(sys.argv[1])).show()

