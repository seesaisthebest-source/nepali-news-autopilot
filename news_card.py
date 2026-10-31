
import os
import re
from io import BytesIO
from pathlib import Path

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
    "User-Agent": "Mozilla/5.0 NepaliNewsCardBot/2.0"
}

Path(OUTPUT_DIR).mkdir(exist_ok=True)

# Nepali month names
NEPALI_MONTHS = [
    "",
    "बैशाख",
    "जेठ",
    "असार",
    "साउन",
    "भदौ",
    "असोज",
    "कार्तिक",
    "मंसिर",
    "पुष",
    "माघ",
    "फागुन",
    "चैत",
]

# Convert English digits to Nepali digits
DIGITS = str.maketrans(
    "0123456789",
    "०१२३४५६७८९"
)


# ---------------- FONTS ----------------

def load_font(size, bold=False):
    possible_fonts = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return ImageFont.truetype(
                font_path,
                size,
                layout_engine=ImageFont.Layout.RAQM
            )

    raise FileNotFoundError(
        "Nepali Unicode font not found."
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

    content = path.read_text(
        encoding="utf-8"
    )

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

            if headline and headline.lower() not in [
                "nepali + world news candidates",
                "nepali world news candidates",
            ]:

                if current:
                    articles.append(current)

                current = {
                    "title": headline,
                    "source": "समाचार स्रोत",
                    "link": "",
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

    return unique[:MAX_CARDS]


# ---------------- PHOTO ----------------

def get_article_photo(article):
    url = article.get("link", "")

    if url:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            image_url = None

            # Open Graph image
            for property_name in [
                "og:image",
                "og:image:url",
                "twitter:image",
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
                    image_url = tag["content"]
                    break

            if image_url:

                photo_response = requests.get(
                    image_url,
                    headers=HEADERS,
                    timeout=20,
                )

                photo_response.raise_for_status()

                photo = Image.open(
                    BytesIO(photo_response.content)
                )

                photo = ImageOps.exif_transpose(
                    photo
                ).convert("RGB")

                if photo.width > 200 and photo.height > 150:
                    print("Real news photo downloaded.")
                    return photo

        except Exception as error:
            print(
                "Photo unavailable:",
                str(error)[:150]
            )

    return create_placeholder()


def create_placeholder():
    placeholder = Image.new(
        "RGB",
        (WIDTH, 650),
        "#263746"
    )

    draw = ImageDraw.Draw(placeholder)

    draw.rectangle(
        (100, 70, 980, 560),
        outline="#526879",
        width=8
    )

    draw.ellipse(
        (750, 160, 850, 260),
        fill="#526879"
    )

    draw.line(
        (160, 490, 400, 270, 600, 420,
         760, 300, 920, 490),
        fill="#526879",
        width=12
    )

    draw.text(
        (350, 570),
        "तस्बिर उपलब्ध छैन",
        font=load_font(42, True),
        fill=WHITE
    )

    return placeholder


# ---------------- IMAGE FIT ----------------

def crop_photo(photo, target_width, target_height):
    photo = photo.convert("RGB")

    return ImageOps.fit(
        photo,
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


# ---------------- CREATE NEWS CARD ----------------

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

    # Breaking news label
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

    # Save card
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

    print(
        "News articles found:",
        len(articles)
    )

    print(
        "Nepali date:",
        get_nepali_date()
    )

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

    print("================================")
    print("News cards created:", success)
    print("Output folder:", OUTPUT_DIR)
    print("================================")


if __name__ == "__main__":
    main()
