from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os

WIDTH = 1080
HEIGHT = 1350

BG = "#101820"
RED = "#E63946"
WHITE = "#FFFFFF"
GRAY = "#DDE3E8"
CARD = "#202B36"

OUTPUT_DIR = "news_cards"

FONT_REGULAR = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"


def load_font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR

    if not os.path.exists(path):
        path = FONT_REGULAR

    try:
        return ImageFont.truetype(
            path,
            size,
            layout_engine=ImageFont.Layout.RAQM
        )
    except (OSError, AttributeError):
        return ImageFont.truetype(path, size)


def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()
        box = draw.textbbox((0, 0), test, font=font)

        if box[2] - box[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def create_news_card(
    headline,
    category="ताजा समाचार",
    source="नेपाली समाचार",
    output="news_card.png"
):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    # Top red header
    draw.rectangle((0, 0, WIDTH, 190), fill=RED)

    category_font = load_font(52, bold=True)

    draw.text(
        (65, 55),
        category,
        font=category_font,
        fill=WHITE
    )

    # Headline
    headline_font = load_font(68, bold=True)

    lines = wrap_text(
        headline,
        headline_font,
        draw,
        WIDTH - 140
    )

    y = 330
    line_gap = 112

    for line in lines[:6]:
        draw.text(
            (70, y),
            line,
            font=headline_font,
            fill=WHITE,
            direction="ltr",
            language="ne"
        )
        y += line_gap

    # Decorative divider
    draw.rounded_rectangle(
        (70, 1030, WIDTH - 70, 1042),
        radius=6,
        fill=RED
    )

    # Footer
    draw.rectangle(
        (0, 1120, WIDTH, HEIGHT),
        fill=CARD
    )

    source_font = load_font(38, bold=True)
    date_font = load_font(28)

    draw.text(
        (70, 1160),
        source,
        font=source_font,
        fill=WHITE
    )

    draw.text(
        (70, 1240),
        "प्रकाशित मिति: " + datetime.now().strftime("%Y-%m-%d"),
        font=date_font,
        fill=GRAY
    )

    output_path = os.path.join(OUTPUT_DIR, output)
    image.save(output_path, quality=95)

    print("News card created:", output_path)


if __name__ == "__main__":
    create_news_card(
        headline="नेपाल र विश्वका ताजा समाचार",
        category="आजका मुख्य समाचार",
        source="नेपाली विश्व समाचार",
        output="sample_news.png"
    )
