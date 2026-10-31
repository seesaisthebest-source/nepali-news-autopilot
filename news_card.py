
import json
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageOps,
    features,
)
from nepali_datetime import date as NepaliDate


# ============== SETTINGS ==============

INPUT_FILE = "news_candidates.json"
OUTPUT_DIR = Path("news_cards")
FONT_DIR = Path("fonts")

WIDTH = 1080
HEIGHT = 1350
MAX_CARDS = 20

BG = "#101C2C"
PANEL = "#172A40"
WHITE = "#FFFFFF"
YELLOW = "#F5C542"
GREY = "#B8C5D3"

OUTPUT_DIR.mkdir(exist_ok=True)
FONT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
    )
}

FONT_FILE = FONT_DIR / "NotoSansDevanagari.ttf"

FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/notosansdevanagari/"
    "NotoSansDevanagari%5Bwght%5D.ttf"
)


# ============== FONT SETUP ==============

def download_font():

    if FONT_FILE.exists():
        try:
            ImageFont.truetype(
                str(FONT_FILE),
                30,
                layout_engine=ImageFont.Layout.RAQM,
            )
            return
        except Exception:
            FONT_FILE.unlink(missing_ok=True)

    print("Downloading Nepali font...")

    response = requests.get(
        FONT_URL,
        headers=HEADERS,
        timeout=40,
    )

    response.raise_for_status()

    FONT_FILE.write_bytes(response.content)

    # Validate downloaded font
    ImageFont.truetype(
        str(FONT_FILE),
        30,
        layout_engine=ImageFont.Layout.RAQM,
    )

    print("Nepali font ready.")


def check_raqm():

    if not features.check_feature("raqm"):
        raise RuntimeError(
            "Pillow RAQM is unavailable. "
            "Install a Pillow build with libraqm support."
        )

    print("RAQM support: ENABLED")


def font(size):

    return ImageFont.truetype(
        str(FONT_FILE),
        size,
        layout_engine=ImageFont.Layout.RAQM,
    )


# ============== DATE ==============

def get_nepali_date():

    try:
        today = datetime.now(
            ZoneInfo("Asia/Kathmandu")
        )

        bs = NepaliDate.from_datetime(today)

        return (
            f"{bs.year} साल "
            f"{bs.month:02d} महिना "
            f"{bs.day:02d} गते"
        )

    except Exception as error:

        print("Date error:", error)

        return datetime.now().strftime("%Y-%m-%d")


# ============== READ NEWS JSON ==============

def extract_news():

    path = Path(INPUT_FILE)

    if not path.exists():
        print("News JSON file missing!")
        return []

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )

    except Exception as error:
        print("JSON READ ERROR:", error)
        return []

    results = []

    for item in data[:MAX_CARDS]:

        title = item.get("title", "").strip()

        if not title:
            continue

        results.append({
            "title": title,
            "source": item.get("source", ""),
            "url": (
                item.get("article_url")
                or item.get("rss_url")
                or ""
            ),
            "image_url": item.get("image_url") or "",
        })

    return results


# ============== FIND NEWS IMAGE ==============

def get_news_photo(article_url, saved_image_url=""):

    candidates = []

    if saved_image_url:
        candidates.append(saved_image_url)

    if article_url:
        candidates.append(article_url)

    for url in candidates:

        try:

            print("Checking photo source:", url[:100])

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=25,
                allow_redirects=True,
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.content,
                "html.parser",
            )

            image_url = ""

            meta_options = [
                ("property", "og:image"),
                ("property", "og:image:url"),
                ("name", "twitter:image"),
                ("property", "twitter:image"),
                ("itemprop", "image"),
            ]

            for attribute, value in meta_options:

                tag = soup.find(
                    "meta",
                    attrs={attribute: value},
                )

                if tag and tag.get("content"):

                    image_url = tag["content"].strip()
                    break

            # Fallback to link rel=image_src
            if not image_url:

                tag = soup.find(
                    "link",
                    rel="image_src",
                )

                if tag:
                    image_url = tag.get("href", "")

            if not image_url:
                print("No OG image found.")
                continue

            image_url = urljoin(
                response.url,
                image_url,
            )

            print("Found image:", image_url[:120])

            image_response = requests.get(
                image_url,
                headers=HEADERS,
                timeout=30,
            )

            image_response.raise_for_status()

            content_type = image_response.headers.get(
                "Content-Type", ""
            ).lower()

            if not content_type.startswith("image/"):
                print("Invalid image content type.")
                continue

            if len(image_response.content) > 15 * 1024 * 1024:
                print("Image too large.")
                continue

            img = Image.open(
                BytesIO(image_response.content)
            )

            img = ImageOps.exif_transpose(img)

            img.load()

            print("REAL NEWS PHOTO FOUND!")

            return img.convert("RGB")

        except Exception as error:

            print(
                "PHOTO ERROR:",
                str(error)[:180],
            )

    return None


# ============== TEXT WRAPPING ==============

def wrap_text(draw, text, selected_font, max_width):

    lines = []
    current = ""

    for word in text.split():

        test = (
            current + " " + word
            if current else word
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=selected_font,
            direction="ltr",
            language="ne",
        )

        if bbox[2] - bbox[0] <= max_width:

            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


def draw_wrapped(
    draw,
    text,
    x,
    y,
    selected_font,
    max_width,
    max_lines=5,
):

    lines = wrap_text(
        draw,
        text,
        selected_font,
        max_width,
    )

    lines = lines[:max_lines]

    for line in lines:

        draw.text(
            (x, y),
            line,
            font=selected_font,
            fill=WHITE,
            direction="ltr",
            language="ne",
        )

        box = draw.textbbox(
            (x, y),
            line,
            font=selected_font,
            direction="ltr",
            language="ne",
        )

        y += (box[3] - box[1]) + 24

    return y


# ============== CREATE NEWS CARD ==============

def create_card(item, number):

    card = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BG,
    )

    draw = ImageDraw.Draw(card)

    # HEADER

    draw.rectangle(
        (0, 0, WIDTH, 155),
        fill=(220, 35, 45),
    )

    draw.text(
        (55, 38),
        "नेपाली समाचार",
        font=font(52),
        fill=WHITE,
        direction="ltr",
        language="ne",
    )

    draw.text(
        (WIDTH - 320, 60),
        "ताजा अपडेट",
        font=font(28),
        fill=WHITE,
        direction="ltr",
        language="ne",
    )

    # NEWS LABEL

    draw.rectangle(
        (0, 155, WIDTH, 205),
        fill=BG,
    )

    draw.rounded_rectangle(
        (55, 165, 355, 235),
        radius=14,
        fill=YELLOW,
    )

    draw.text(
        (75, 175),
        "ताजा समाचार",
        font=font(38),
        fill=BG,
        direction="ltr",
        language="ne",
    )

    # PHOTO

    top = 270
    bottom = 780

    photo = get_news_photo(
        item["url"],
        item["image_url"],
    )

    if photo:

        photo = ImageOps.fit(
            photo,
            (WIDTH - 110, bottom - top),
            method=Image.Resampling.LANCZOS,
        )

        card.paste(
            photo,
            (55, top),
        )

    else:

        draw.rounded_rectangle(
            (55, top, WIDTH - 55, bottom),
            radius=15,
            fill=PANEL,
            outline=GREY,
            width=3,
        )

        draw.text(
            (WIDTH // 2, 500),
            "तस्बिर उपलब्ध छैन",
            font=font(48),
            fill=GREY,
            anchor="mm",
            direction="ltr",
            language="ne",
        )

    # HEADLINE

    draw.rectangle(
        (55, 815, 72, 950),
        fill=YELLOW,
    )

    draw_wrapped(
        draw,
        item["title"],
        95,
        815,
        font(55),
        WIDTH - 155,
        max_lines=5,
    )

    # SOURCE

    source = item["source"] or "नेपाल समाचार"

    draw.text(
        (55, 1120),
        "स्रोत: " + source,
        font=font(30),
        fill=GREY,
        direction="ltr",
        language="ne",
    )

    # FOOTER

    draw.rectangle(
        (0, 1235, WIDTH, HEIGHT),
        fill="#07111E",
    )

    draw.text(
        (55, 1270),
        get_nepali_date(),
        font=font(32),
        fill=YELLOW,
        direction="ltr",
        language="ne",
    )

    output = (
        OUTPUT_DIR
        / f"news_card_{number:02d}.png"
    )

    card.save(
        output,
        optimize=True,
    )

    print("CARD CREATED:", output)


# ============== MAIN ==============

def main():

    print("Starting News Card Generator...")

    check_raqm()
    download_font()

    news = extract_news()

    print("News found:", len(news))

    if not news:
        print("No news available!")
        return

    for number, item in enumerate(news, 1):

        try:
            create_card(item, number)

        except Exception as error:

            print(
                "CARD ERROR:",
                number,
                str(error)[:200],
            )

    print("NEWS CARD GENERATION COMPLETED!")


if __name__ == "__main__":
    main()
