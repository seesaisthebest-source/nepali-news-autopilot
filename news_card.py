from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
import textwrap

# Nepali News Card Generator
# Facebook / Instagram Portrait News Card
# Size: 1080 x 1350

WIDTH = 1080
HEIGHT = 1350

BG_COLOR = "#101820"
RED = "#E63946"
WHITE = "#FFFFFF"
GRAY = "#DDE3E8"
CARD_COLOR = "#202B36"

OUTPUT_DIR = "news_cards"


def load_font(size, bold=False):
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass

    return ImageFont.load_default()


def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word
        test_line = test_line.strip()

        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def create_news_card(
    headline,
    category="ताजा समाचार",
    source="Nepali World News",
    output="news_card.png"
):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BG_COLOR
    )

    draw = ImageDraw.Draw(image)

    # Header
    draw.rectangle(
        (0, 0, WIDTH, 170),
        fill=RED
    )

    header_font = load_font(55, bold=True)

    draw.text(
        (55, 45),
        category,
        font=header_font,
        fill=WHITE
    )

    # Main headline
    headline_font = load_font(66, bold=True)

    lines = wrap_text(
        headline,
        headline_font,
        draw,
        WIDTH - 120
    )

    y = 300

    for line in lines:
        draw.text(
            (60, y),
            line,
            font=headline_font,
            fill=WHITE
        )

        y += 105

    # Footer
    draw.rectangle(
        (0, 1160, WIDTH, HEIGHT),
        fill=CARD_COLOR
    )

    source_font = load_font(38)
    date_font = load_font(30)

    draw.text(
        (60, 1200),
        source,
        font=source_font,
        fill=GRAY
    )

    draw.text(
        (60, 1260),
        datetime.now().strftime("%Y-%m-%d"),
        font=date_font,
        fill=GRAY
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output
    )

    image.save(output_path)

    print("News card created:", output_path)


if __name__ == "__main__":
    create_news_card(
        headline="नेपाल र विश्वका ताजा समाचार",
        category="आजको मुख्य समाचार",
        source="Nepali World News",
        output="sample_news.png"
    )
