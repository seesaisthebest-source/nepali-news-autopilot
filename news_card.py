
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import feedparser
import requests
import nepali_datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from io import BytesIO
import os
import re

WIDTH, HEIGHT = 1080, 1350
OUTPUT_DIR = "news_cards"

BG = "#101820"
RED = "#E63946"
WHITE = "#FFFFFF"
GRAY = "#DDE3E8"

FONT_REGULAR = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NepaliNewsCard/1.0)"
}

FEEDS = [
    ("नेपाल समाचार",
     "https://news.google.com/rss/search?q=नेपाल&hl=ne&gl=NP&ceid=NP:ne"),
    ("विश्व समाचार",
     "https://news.google.com/rss/search?q=विश्व+समाचार&hl=ne&gl=NP&ceid=NP:ne")
]


def nepali_digits(value):
    digits = "०१२३४५६७८९"
    return str(value).translate(str.maketrans("0123456789", digits))


def nepali_date():
    today = nepali_datetime.date.today()
    months = [
        "बैशाख", "जेठ", "असार", "साउन",
        "भदौ", "असोज", "कार्तिक", "मंसिर",
        "पुस", "माघ", "फागुन", "चैत"
    ]
    return (
        f"{nepali_digits(today.year)} "
        f"{months[today.month - 1]} "
        f"{nepali_digits(today.day)}"
    )


def load_font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR
    if not os.path.exists(path):
        path = FONT_REGULAR

    return ImageFont.truetype(
        path,
        size,
        layout_engine=ImageFont.Layout.RAQM
    )


def get_photo(entry):
    candidates = []

    for item in entry.get("media_content", []):
        if item.get("url"):
            candidates.append(item["url"])

    for item in entry.get("media_thumbnail", []):
        if item.get("url"):
            candidates.append(item["url"])

    for item in entry.get("enclosures", []):
        if item.get("href"):
            candidates.append(item["href"])

    article_url = entry.get("link", "")

    if article_url:
        try:
            response = requests.get(
                article_url,
                headers=HEADERS,
                timeout=15
            )
            soup = BeautifulSoup(response.text, "html.parser")

            for selector in [
                {"property": "og:image"},
                {"name": "twitter:image"}
            ]:
                tag = soup.find("meta", attrs=selector)
                if tag and tag.get("content"):
                    candidates.append(
                        urljoin(response.url, tag["content"])
                    )
        except requests.RequestException:
            pass

    for url in candidates:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=15
            )
            response.raise_for_status()

            if "image" not in response.headers.get(
                "Content-Type", ""
            ):
                continue

            photo = Image.open(BytesIO(response.content)).convert("RGB")

            if photo.width >= 300 and photo.height >= 200:
                return photo

        except Exception:
            continue

    return None


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


def create_card(title, source, photo, number):
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)

    # Photo area
    photo = photo.copy()
    photo.thumbnail((WIDTH, 720))

    photo_canvas = Image.new("RGB", (WIDTH, 720), "#202B36")
    x = (WIDTH - photo.width) // 2
    y = (720 - photo.height) // 2
    photo_canvas.paste(photo, (x, y))
    image.paste(photo_canvas, (0, 0))

    draw = ImageDraw.Draw(image)

    # Breaking news header
    draw.rectangle((0, 720, WIDTH, 850), fill=RED)

    category_font = load_font(48, True)
    draw.text(
        (55, 755),
        "ताजा समाचार",
        font=category_font,
        fill=WHITE
    )

    # Headline
    headline_font = load_font(54, True)
    lines = wrap_text(title, headline_font, draw, WIDTH - 120)

    y = 900
    for line in lines[:4]:
        draw.text(
            (60, y),
            line,
            font=headline_font,
            fill=WHITE,
            direction="ltr",
            language="ne"
        )
        y += 70

    # Footer
    draw.rectangle((0, 1190, WIDTH, HEIGHT), fill="#202B36")

    source_font = load_font(34, True)
    date_font = load_font(30)

    draw.text((60, 1210), source, font=source_font, fill=WHITE)
    draw.text(
        (60, 1270),
        "मिति: " + nepali_date(),
        font=date_font,
        fill=GRAY
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"news_{number:02d}.png"
    path = os.path.join(OUTPUT_DIR, filename)

    image.save(path, quality=95)
    print("Created:", path)


def main():
    count = 0
    seen = set()

    for source, feed_url in FEEDS:
        print("Checking:", source)
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:10]:
            title = entry.get("title", "").strip()

            if not title or title in seen:
                continue

            seen.add(title)

            print("Finding photo:", title)
            photo = get_photo(entry)

            if photo is None:
                print("Skipped: no usable photo")
                continue

            count += 1
            create_card(title, source, photo, count)

    print("Total cards created:", count)


if __name__ == "__main__":
    main()
