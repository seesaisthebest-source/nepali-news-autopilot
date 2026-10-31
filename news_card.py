import os
import re
import textwrap
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps
from nepali_datetime import date as NepaliDate

# ============== SETTINGS ==============

INPUT_FILE = "news_candidates.md"
OUTPUT_DIR = "news_cards"

WIDTH = 1080
HEIGHT = 1350
MAX_CARDS = 20

BG = "#101C2C"
WHITE = "#FFFFFF"
YELLOW = "#F5C542"
RED = "#D92736"
MUTED = "#B8C5D3"
PANEL = "#17283D"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

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


# ============== FONT ==============

def load_font(size, bold=False):

    names = (
        [
            "/usr/share/fonts/truetype/noto/"
            "NotoSansDevanagari-Bold.ttf",
            "fonts/NotoSansDevanagari-Bold.ttf"
        ]
        if bold else
        [
            "/usr/share/fonts/truetype/noto/"
            "NotoSansDevanagari-Regular.ttf",
            "fonts/NotoSansDevanagari-Regular.ttf"
        ]
    )

    for path in names:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(
                    path,
                    size,
                    layout_engine=ImageFont.Layout.RAQM
                )
            except Exception:
                return ImageFont.truetype(path, size)

    raise FileNotFoundError(
        "Noto Sans Devanagari font not found."
    )


# ============== NEPALI DATE ==============

def get_nepali_date():

    today = NepaliDate.today()

    month = NEPALI_MONTHS[today.month]

    value = (
        f"{today.year} साल "
        f"{month} "
        f"{today.day} गते"
    )

    return value.translate(DIGITS)


# ============== NEWS PARSER ==============

def read_news():

    path = Path(INPUT_FILE)

    if not path.exists():
        print("ERROR: news_candidates.md not found.")
        return []

    content = path.read_text(encoding="utf-8")

    articles = []
    current = None

    ignored = [
        "nepali + world news candidates",
        "nepali world news candidates",
        "nepali + world news report",
        "recent candidates",
        "needs manual date check",
        "summary",
        "feed errors"
    ]

    for line in content.splitlines():

        line = line.strip()

        if not line:
            continue

        # Article heading
        if line.startswith("##"):

            title = re.sub(
                r"^#+\s*",
                "",
                line
            ).strip()

            if title.lower() in ignored:
                current = None
                continue

            if title.lower().startswith("checked at"):
                current = None
                continue

            if title.lower().startswith("fetched at"):
                current = None
                continue

            if title.lower().startswith("freshness"):
                current = None
                continue

            if title.lower().startswith("verification"):
                current = None
                continue

            current = {
                "title": title,
                "source": "News",
                "published": "",
                "url": ""
            }

            articles.append(current)
            continue

        if current is None:
            continue

        # Source
        if line.lower().startswith("- source"):
            current["source"] = re.sub(
                r"^- source(?: feed)?\s*:\s*",
                "",
                line,
                flags=re.I
            ).strip()

        # Published date
        elif line.lower().startswith("- published"):
            current["published"] = re.sub(
                r"^- published\s*:\s*",
                "",
                line,
                flags=re.I
            ).strip()

        # News URL
        elif line.lower().startswith("- link"):
            current["url"] = re.sub(
                r"^- link\s*:\s*",
                "",
                line,
                flags=re.I
            ).strip()

    articles = [
        a for a in articles
        if a["title"] and a["url"].startswith("http")
    ]

    print(f"Found {len(articles)} news articles.")

    return articles[:MAX_CARDS]


# ============== DOWNLOAD NEWS IMAGE ==============

def get_news_image(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        image_url = None

        for attr in [
            {"property": "og:image"},
            {"name": "twitter:image"},
            {"property": "og:image:url"}
        ]:

            tag = soup.find("meta", attrs=attr)

            if tag and tag.get("content"):
                image_url = tag["content"]
                break

        if not image_url:
            return None

        image_url = urljoin(url, image_url)

        image_response = requests.get(
            image_url,
            headers=HEADERS,
            timeout=20
        )

        image_response.raise_for_status()

        if len(image_response.content) > 12 * 1024 * 1024:
            return None

        image = Image.open(
            BytesIO(image_response.content)
        ).convert("RGB")

        if image.width < 300 or image.height < 200:
            return None

        return image

    except Exception as error:

        print("Image download failed:", error)

        return None


# ============== IMAGE DESIGN ==============

def make_background():

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BG
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (0, 0, WIDTH, 15),
        fill=RED
    )

    draw.rectangle(
        (0, 15, WIDTH, 23),
        fill=YELLOW
    )

    return image


# ============== TEXT WRAPPING ==============

def wrap_text(text, font, max_width, draw):

    words = text.split()

    lines = []
    line = ""

    for word in words:

        test = word if not line else line + " " + word

        box = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        if box[2] - box[0] <= max_width:
            line = test

        else:

            if line:
                lines.append(line)

            line = word

    if line:
        lines.append(line)

    return lines


def draw_headline(draw, title):

    font_size = 65

    while font_size >= 40:

        font = load_font(font_size, bold=True)

        lines = wrap_text(
            title,
            font,
            940,
            draw
        )

        line_height = font_size + 23

        if len(lines) <= 5:
            if len(lines) * line_height <= 400:
                break

        font_size -= 3

    y = 785

    for line in lines[:5]:

        draw.text(
            (70, y),
            line,
            font=font,
            fill=WHITE,
            stroke_width=1,
            stroke_fill=BG
        )

        y += line_height

    return y


# ============== CREATE NEWS CARD ==============

def create_card(article, number):

    image = make_background()

    draw = ImageDraw.Draw(image)

    # Top header
    header_font = load_font(42, bold=True)
    small_font = load_font(26)
    date_font = load_font(27, bold=True)

    draw.rounded_rectangle(
        (55, 55, 360, 125),
        radius=15,
        fill=RED
    )

    draw.text(
        (78, 66),
        "BREAKING NEWS",
        font=load_font(29, bold=True),
        fill=WHITE
    )

    draw.text(
        (690, 76),
        "नेपाल | विश्व",
        font=header_font,
        fill=WHITE
    )

    # News photo
    news_image = get_news_image(article["url"])

    photo_box = (55, 165, 1025, 740)

    if news_image:

        photo = ImageOps.fit(
            news_image,
            (970, 575),
            method=Image.Resampling.LANCZOS
        )

        image.paste(photo, (55, 165))

    else:

        draw.rounded_rectangle(
            photo_box,
            radius=20,
            fill=PANEL
        )

        draw.text(
            (300, 390),
            "NEPALI WORLD NEWS",
            font=load_font(48, bold=True),
            fill=YELLOW
        )

    # Photo border
    draw.rounded_rectangle(
        photo_box,
        radius=20,
        outline=YELLOW,
        width=4
    )

    # Headline background
    draw.rectangle(
        (0, 755, WIDTH, 1240),
        fill=BG
    )

    draw.rectangle(
        (55, 770, 65, 1200),
        fill=YELLOW
    )

    # Headline
    end_y = draw_headline(
        draw,
        article["title"]
    )

    # Source
    source = article["source"][:65]

    draw.line(
        (55, 1235, 1025, 1235),
        fill="#52647A",
        width=2
    )

    draw.text(
        (65, 1260),
        f"स्रोत: {source}",
        font=small_font,
        fill=MUTED
    )

    # Nepali date
    nepali_date = get_nepali_date()

    date_text = f"मिति: {nepali_date}"

    draw.text(
        (65, 1300),
        date_text,
        font=date_font,
        fill=YELLOW
    )

    # Card number
    draw.text(
        (890, 1305),
        f"NEWS {number:02d}",
        font=small_font,
        fill=WHITE
    )

    output_file = (
        Path(OUTPUT_DIR)
        / f"news_card_{number:02d}.png"
    )

    image.save(
        output_file,
        format="PNG",
        optimize=True
    )

    print("Created:", output_file)


# ============== MAIN ==============

def main():

    print("Starting Nepali News Card Generator...")

    # Remove previous generated cards
    for old_file in Path(OUTPUT_DIR).glob("news_card_*.png"):
        old_file.unlink()

    articles = read_news()

    if not articles:
        print("No valid news articles found.")
        return

    for index, article in enumerate(articles, start=1):

        try:

            print(
                f"Creating card {index}: "
                f"{article['title']}"
            )

            create_card(article, index)

        except Exception as error:

            print(
                f"Card {index} failed:",
                error
            )

    print("News card generation completed.")


if __name__ == "__main__":
    main()
