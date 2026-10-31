
import os
import re
import textwrap
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont, ImageOps
from nepali_datetime import date as NepaliDate

# ================ SETTINGS ================

INPUT_FILE = "news_candidates.md"
OUTPUT_DIR = "news_cards"

WIDTH = 1080
HEIGHT = 1350
MAX_CARDS = 20

BACKGROUND = "#101C2C"
CARD_BG = "#172A40"
WHITE = "#FFFFFF"
YELLOW = "#F5C542"
GREY = "#B8C5D3"

Path(OUTPUT_DIR).mkdir(exist_ok=True)

# ================ FONT SETTINGS ================

FONT_URLS = [
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/NotoSansDevanagari%5Bwght%5D.ttf",
]

FONT_FILE = "NotoSansDevanagari.ttf"

def setup_font():
    if not os.path.exists(FONT_FILE):
        for url in FONT_URLS:
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                Path(FONT_FILE).write_bytes(response.content)
                break
            except Exception as error:
                print("Font download failed:", error)

    if os.path.exists(FONT_FILE):
        return FONT_FILE

    return None

FONT_PATH = setup_font()

def get_font(size, bold=False):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass

    return ImageFont.load_default()

# ================ NEPALI DATE ================

def nepali_date():
    today = datetime.now(timezone.utc).astimezone()
    bs = NepaliDate.from_datetime(today)
    return f"{bs.year}/{bs.month:02d}/{bs.day:02d}"

# ================ NEWS EXTRACTION ================

def extract_news():
    if not os.path.exists(INPUT_FILE):
        print("news_candidates.md not found!")
        return []

    content = Path(INPUT_FILE).read_text(
        encoding="utf-8",
        errors="replace"
    )

    news = []

    blocks = re.split(r"(?m)^##\s+", content)

    for block in blocks:
        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        title = lines[0].strip("# -*")

        if len(title) < 15:
            continue

        url_match = re.search(
            r"https?://[^\s)]+",
            block
        )

        image_match = re.search(
            r"!\[[^\]]*\]\((https?://[^)]+)\)",
            block
        )

        news.append({
            "title": title,
            "url": url_match.group(0) if url_match else "",
            "image": image_match.group(1) if image_match else ""
        })

        if len(news) >= MAX_CARDS:
            break

    return news

# ================ TEXT WRAPPING ================

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = current + " " + word if current else word

        bbox = draw.textbbox((0, 0), test, font=font)

        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

def draw_wrapped(draw, text, position, font, fill, max_width, spacing=18):
    x, y = position
    lines = wrap_text(draw, text, font, max_width)

    for line in lines:
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=0
        )

        bbox = draw.textbbox((x, y), line, font=font)
        y += bbox[3] - bbox[1] + spacing

    return y

# ================ IMAGE DOWNLOAD ================

def download_image(url):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        response.raise_for_status()

        image = Image.open(BytesIO(response.content))
        return image.convert("RGB")

    except Exception as error:
        print("Image unavailable:", error)
        return None

# ================ CREATE NEWS CARD ================

def create_card(item, number):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND
    )

    draw = ImageDraw.Draw(image)

    # Header
    draw.rectangle(
        (0, 0, WIDTH, 150),
        fill=CARD_BG
    )

    draw.rectangle(
        (0, 0, 14, HEIGHT),
        fill=YELLOW
    )

    draw.text(
        (65, 48),
        "NEWS UPDATE",
        font=get_font(55, True),
        fill=YELLOW
    )

    draw.text(
        (WIDTH - 320, 65),
        "NEPALI NEWS",
        font=get_font(28),
        fill=WHITE
    )

    # Main image
    news_image = download_image(item["image"])

    image_top = 185
    image_bottom = 790

    if news_image:
        news_image = ImageOps.fit(
            news_image,
            (WIDTH - 100, image_bottom - image_top),
            method=Image.Resampling.LANCZOS
        )

        image.paste(news_image, (50, image_top))
    else:
        draw.rounded_rectangle(
            (50, image_top, WIDTH - 50, image_bottom),
            radius=22,
            fill=CARD_BG
        )

        draw.text(
            (WIDTH // 2, 470),
            "समाचार",
            font=get_font(75),
            fill=GREY,
            anchor="mm"
        )

    # Headline
    draw.text(
        (65, 835),
        "मुख्य समाचार",
        font=get_font(35),
        fill=YELLOW
    )

    draw_wrapped(
        draw,
        item["title"],
        (65, 900),
        get_font(58, True),
        WHITE,
        WIDTH - 130,
        spacing=25
    )

    # Footer
    draw.line(
        (65, 1190, WIDTH - 65, 1190),
        fill=GREY,
        width=2
    )

    draw.text(
        (65, 1220),
        "मिति: " + nepali_date(),
        font=get_font(32),
        fill=WHITE
    )

    draw.text(
        (WIDTH - 250, 1225),
        f"NEWS  {number:02d}",
        font=get_font(27),
        fill=YELLOW
    )

    output_file = Path(OUTPUT_DIR) / f"news_{number:02d}.jpg"

    image.save(
        output_file,
        "JPEG",
        quality=95,
        optimize=True
    )

    print("Created:", output_file)

# ================ MAIN ================

def main():
    news = extract_news()

    if not news:
        print("No news candidates found.")
        return

    for number, item in enumerate(news, start=1):
        try:
            create_card(item, number)
        except Exception as error:
            print(f"Card {number} failed:", error)

    print(f"Completed. Processed {len(news)} news candidates.")

if __name__ == "__main__":
    main()
