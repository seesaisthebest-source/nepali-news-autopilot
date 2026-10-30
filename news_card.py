
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os

WIDTH = 1080
HEIGHT = 1350

BACKGROUND = "#101820"
ACCENT = "#E63946"
WHITE = "#FFFFFF"
LIGHT = "#DDE3E8"

def create_news_card(
    headline="नेपाल र विश्वका ताजा समाचार",
    category="BREAKING NEWS",
    output="news_card.png"
):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND
    )

    draw = ImageDraw.Draw(image)

    # Header
    draw.rectangle(
        (0, 0, WIDTH, 150),
        fill=ACCENT
    )

    draw.text(
        (60, 45),
        category,
        fill=WHITE
    )

    # Headline area
    draw.text(
        (60, 250),
        "ताजा समाचार",
        fill=ACCENT
    )

    # Headline
    words = headline.split()
    lines = []
    current = ""

    for word in words:
        test = current + " " + word

        if len(test) > 22:
            lines.append(current)
            current = word
        else:
            current = test.strip()

    if current:
        lines.append(current)

    y = 350

    for line in lines:
        draw.text(
            (60, y),
            line,
            fill=WHITE
        )
        y += 100

    # Footer
    draw.rectangle(
        (0, 1180, WIDTH, HEIGHT),
        fill="#202B36"
    )

    draw.text(
        (60, 1230),
        "NEPALI WORLD NEWS",
        fill=LIGHT
    )

    draw.text(
        (60, 1280),
        datetime.now().strftime("%Y-%m-%d"),
        fill=LIGHT
    )

    image.save(output)

    print("News card created:", output)


if __name__ == "__main__":
    create_news_card()
