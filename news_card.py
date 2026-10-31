
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps
from nepali_datetime import date as NepaliDate

# ---------------- SETTINGS ----------------

INPUT_FILE = "news_candidates.md"
OUTPUT_DIR = "news_cards"

WIDTH = 1080
HEIGHT = 1350
MAX_CARDS = 20

BACKGROUND = "#101C2C"
WHITE = "#FFFFFF"
YELLOW = "#F5C542"
RED = "#D92736"
MUTED = "#B8C5D3"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

Path(OUTPUT_DIR).mkdir(exist_ok=True)

NEPALI_MONTHS = [
    "",
    "बैशाख", "जेठ", "असार", "साउन",
    "भदौ", "असोज", "कार्तिक", "मंसिर",
    "पुष", "माघ", "फागुन", "चैत"
]

DIGITS = str.maketrans(
    "0123456789",
    "०१२३४५६७८९"
)


# ---------------- FONT ----------------

def load_font(size, bold=False):

    fonts = []

    if bold:
        fonts.extend([
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Bold.ttf",
        ])
    else:
        fonts.extend([
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf",
        ])

    fonts.extend([
        "fonts/NotoSansDevanagari-Bold.ttf" if bold
        else "fonts/NotoSansDevanagari-Regular.ttf"
    ])

    for font_path in fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(
                    font_path,
                    size,
                    layout_engine=ImageFont.Layout.RAQM
                )
            except Exception:
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    pass

    raise FileNotFoundError(
        "Noto Sans Devanagari font not found. "
        "Check fonts installation in news.yml."
    )


# ---------------- NEPALI DATE ----------------

def get_nepali_date():

    today = NepaliDate.today()

    month_name = NEPALI_MONTHS[today.month]

    date_text = (
        f"{today.year} साल "
        f"{month_name} "
        f"{today.day} गते"
    )

    return date_text.translate(DIGITS)


# ---------------- NEWS PARSER ----------------

def read_news():

    path = Path(INPUT_FILE)

    if not path.exists():
        print("ERROR: news_candidates.md not found.")
        return []

    content = path.read_text(encoding="utf-8")

    articles = []
    current = None

    for line in content.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):

            headline = re.sub(
                r"^#+\s*",
                "",
                line
            ).strip()

            if headline.lower() in [
                "nepali + world news candidates",
                "nepali world news candidates"
            ]:
                continue

            if current:
                articles.append(current)

            current = {
                "title": headline,
                "source": "समाचार स्रोत",
                "link": ""
            }

        elif current:

            url_match = re.search(
                r"https?://\S+",
                line
            )

            if url_match and not current["link"]:
                current["link"] = (
                    url_match.group(0).rstrip(")>,")
                )

            if line.lower().startswith("source:"):
                current["source"] = (
                    line.split(":", 1)[1].strip()
                )

    if current:
        articles.append(current)

    unique = []
    seen = set()

    for article in articles:

        title = article["title"].strip()
        key = title.lower()

        if title and key not in seen:
            seen.add(key)
            article["title"] = title
            unique.append(article)

    print("News articles found:", len(unique))

    return unique[:MAX_CARDS]


# ---------------- PHOTO DOWNLOAD ----------------

def get_article_photo(article):

    url = article.get("link", "")

    if not url:
        print("No article link available.")
        return create_placeholder()

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=25,
            allow_redirects=True
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        image_url = None

        # Search common image metadata
        for property_name in [
            "og:image",
            "og:image:url",
            "twitter:image",
            "twitter:image:src"
        ]:

            tag = soup.find(
                "meta",
                attrs={"property": property_name}
            )

            if not tag:
                tag = soup.find(
                    "meta",
                    attrs={"name": property_name}
                )

            if tag and tag.get("content"):
                image_url = tag["content"].strip()
                break

        # Try JSON-LD image if metadata is missing
        if not image_url:

            for script in soup.find_all(
                "script",
                type="application/ld+json"
            ):

                try:
                    import json

                    data = json.loads(script.string or script.get_text())

                    if isinstance(data, list):
                        data = data[0]

                    if isinstance(data, dict):
                        image = data.get("image")

                        if isinstance(image, str):
                            image_url = image

                        elif isinstance(image, list) and image:
                            image_url = image[0]

                        elif isinstance(image, dict):
                            image_url = image.get("url")

                    if image_url:
                        break

                except Exception:
                    continue

        if not image_url:
            print("Article has no image metadata.")
            return create_placeholder()

        image_url = urljoin(
            response.url,
            image_url
        )

        photo_response = requests.get(
            image_url,
            headers=HEADERS,
            timeout=25
        )

        photo_response.raise_for_status()

        photo = Image.open(
            BytesIO(photo_response.content)
        )

        photo = ImageOps.exif_transpose(
            photo
        ).convert("RGB")

        if photo.width < 200 or photo.height < 150:
            raise ValueError("Image is too small.")

        print("Real news photo downloaded:", image_url)

        return photo

    except Exception as error:

        print(
            "Photo unavailable:",
            str(error)[:180]
        )

        return create_placeholder()


# ---------------- PLACEHOLDER ----------------

def create_placeholder():

    placeholder = Image.new(
        "RGB",
        (WIDTH, 570),
        "#263746"
    )

    draw = ImageDraw.Draw(placeholder)

    draw.rectangle(
        (100, 70, 980, 500),
        outline="#526879",
        width=8
    )

    draw.ellipse(
        (750, 140, 850, 240),
        fill="#526879"
    )

    draw.line(
        (160, 440, 400, 250, 600, 390,
         760, 280, 920, 440),
        fill="#526879",
        width=12
    )

    text = "तस्बिर उपलब्ध छैन"
    font = load_font(42, True)

    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]

    draw.text(
        ((WIDTH - text_width) // 2, 510),
        text,
        font=font,
        fill=WHITE
    )

    return placeholder


# ---------------- IMAGE FIT ----------------

def crop_photo(photo, target_width, target_height):

    return ImageOps.fit(
        photo.convert("RGB"),
        (target_width, target_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5)
    )


# ---------------- TEXT WRAPPING ----------------

def wrap_text(draw, text, font, max_width):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        test = (
            current + " " + word
            if current else word
        )

        box = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        if box[2] - box[0] <= max_width:
            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


# ---------------- HEADLINE FIT ----------------

def get_headline_layout(draw, headline):

    for size in [62, 56, 50, 46, 42, 38]:

        font = load_font(size, True)

        lines = wrap_text(
            draw,
            headline,
            font,
            920
        )

        if len(lines) <= 5:
            return font, lines, size + 28

    font = load_font(38, True)

    lines = wrap_text(
        draw,
        headline,
        font,
        920
    )

    return font, lines[:5], 66


# ---------------- NEWS CARD ----------------

def create_news_card(article, index):

    canvas = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND
    )

    draw = ImageDraw.Draw(canvas)

    # Header
    draw.rectangle(
        (0, 0, WIDTH, 105),
        fill=RED
    )

    draw.text(
        (45, 20),
        "नेपाली समाचार",
        font=load_font(46, True),
        fill=WHITE
    )

    draw.text(
        (790, 35),
        "NEWS UPDATE",
        font=load_font(30, True),
        fill=WHITE
    )

    # News label
    draw.rounded_rectangle(
        (45, 125, 345, 190),
        radius=12,
        fill=YELLOW
    )

    draw.text(
        (65, 135),
        "ताजा समाचार",
        font=load_font(34, True),
        fill=BACKGROUND
    )

    # Main photo
    photo = get_article_photo(article)

    photo = crop_photo(
        photo,
        WIDTH,
        570
    )

    canvas.paste(
        photo,
        (0, 205)
    )

    # Headline background
    draw.rectangle(
        (0, 775, WIDTH, 1235),
        fill=BACKGROUND
    )

    draw.rectangle(
        (45, 810, 60, 940),
        fill=YELLOW
    )

    headline = article.get(
        "title",
        "आजका मुख्य समाचार"
    )

    headline_font, lines, line_height = (
        get_headline_layout(draw, headline)
    )

    y = 805

    for line in lines:

        draw.text(
            (90, y),
            line,
            font=headline_font,
            fill=WHITE
        )

        y += line_height

    # Footer
    draw.rectangle(
        (0, 1235, WIDTH, HEIGHT),
        fill="#07111E"
    )

    source = article.get(
        "source",
        "समाचार स्रोत"
    )

    source_font = load_font(27, True)
    date_font = load_font(29, True)

    draw.text(
        (45, 1255),
        "स्रोत: " + source[:30],
        font=source_font,
        fill=MUTED
    )

    date_text = get_nepali_date()

    date_width = draw.textbbox(
        (0, 0),
        date_text,
        font=date_font
    )[2]

    draw.text(
        (WIDTH - date_width - 45, 1300),
        date_text,
        font=date_font,
        fill=YELLOW
    )

    # Save
    output_path = os.path.join(
        OUTPUT_DIR,
        f"news_card_{index:02d}.png"
    )

    canvas.save(
        output_path,
        "PNG",
        optimize=True
    )

    print("Saved:", output_path)


# ---------------- MAIN ----------------

def main():

    print("Starting Nepali News Card Generator...")

    articles = read_news()

    if not articles:
        print("No news articles found.")
        return

    print("Nepali date:", get_nepali_date())

    success = 0

    for index, article in enumerate(
        articles,
        start=1
    ):

        try:

            create_news_card(
                article,
                index
            )

            success += 1

        except Exception as error:

            print(
                f"Card {index} failed:",
                str(error)[:200]
            )

    print("==============================")
    print("News cards created:", success)
    print("Output folder:", OUTPUT_DIR)
    print("==============================")


if __name__ == "__main__":
    main()
