
import re
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps, features
from nepali_datetime import date as NepaliDate

# ============== SETTINGS ==============

INPUT_FILE = "news_candidates.md"
OUTPUT_DIR = Path("news_cards")

WIDTH = 1080
HEIGHT = 1350
MAX_CARDS = 20

BG = "#101C2C"
PANEL = "#172A40"
WHITE = "#FFFFFF"
YELLOW = "#F5C542"
GREY = "#B8C5D3"

OUTPUT_DIR.mkdir(exist_ok=True)

# ============== NEPALI FONT ==============

FONT_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf",
    "NotoSansDevanagari.ttf",
]

FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/notosansdevanagari/NotoSansDevanagari%5Bwght%5D.ttf"
)

FONT_FILE = None

for path in FONT_PATHS:
    if Path(path).exists():
        FONT_FILE = path
        break

if FONT_FILE is None:
    try:
        r = requests.get(FONT_URL, timeout=40)
        r.raise_for_status()
        Path("NotoSansDevanagari.ttf").write_bytes(r.content)
        FONT_FILE = "NotoSansDevanagari.ttf"
    except Exception as e:
        print("FONT DOWNLOAD ERROR:", e)

if not features.check_feature("raqm"):
    print("WARNING: RAQM support is missing!")

if not FONT_FILE:
    raise RuntimeError(
        "Nepali font unavailable. Check fonts-noto-core installation."
    )

def font(size):
    return ImageFont.truetype(
        FONT_FILE,
        size,
        layout_engine=ImageFont.Layout.RAQM
    )

# ============== NEPALI DATE ==============

def get_nepali_date():
    try:
        today = datetime.now()
        bs = NepaliDate.from_datetime(today)
        return f"{bs.year}/{bs.month:02d}/{bs.day:02d}"
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")

# ============== READ NEWS ==============

def extract_news():
    path = Path(INPUT_FILE)

    if not path.exists():
        print("News input file missing!")
        return []

    content = path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    blocks = re.split(r"(?m)^##\s+", content)
    results = []

    for block in blocks:
        lines = [
            x.strip()
            for x in block.splitlines()
            if x.strip()
        ]

        if not lines:
            continue

        title = lines[0].strip("# -*")

        if len(title) < 10:
            continue

        source = ""
        url = ""

        for line in lines[1:]:
            if line.lower().startswith("source:"):
                source = line.split(":", 1)[1].strip()

            if line.lower().startswith("link:"):
                url = line.split(":", 1)[1].strip()

        if not url:
            match = re.search(r"https?://\S+", block)
            if match:
                url = match.group(0).rstrip(")")

        results.append({
            "title": title,
            "source": source,
            "url": url,
            "image": ""
        })

        if len(results) >= MAX_CARDS:
            break

    return results

# ============== FIND REAL NEWS PHOTO ==============

def get_news_photo(article_url):
    if not article_url:
        return None

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
            )
        }

        response = requests.get(
            article_url,
            headers=headers,
            timeout=25
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        image_url = ""

        meta_names = [
            ("property", "og:image"),
            ("property", "og:image:url"),
            ("name", "twitter:image"),
            ("property", "twitter:image")
        ]

        for attribute, value in meta_names:
            tag = soup.find(
                "meta",
                attrs={attribute: value}
            )

            if tag and tag.get("content"):
                image_url = tag["content"].strip()
                break

        if not image_url:
            print("No article photo:", article_url)
            return None

        image_response = requests.get(
            image_url,
            headers=headers,
            timeout=25
        )

        image_response.raise_for_status()

        img = Image.open(
            BytesIO(image_response.content)
        )

        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")

    except Exception as e:
        print("PHOTO ERROR:", str(e)[:200])
        return None

# ============== TEXT WRAPPING ==============

def wrap_text(draw, text, selected_font, max_width):
    lines = []
    current = ""

    for word in text.split():
        test = current + " " + word if current else word

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=selected_font
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

def draw_wrapped(draw, text, x, y, selected_font,
                 max_width, max_lines=5):

    lines = wrap_text(
        draw,
        text,
        selected_font,
        max_width
    )

    lines = lines[:max_lines]

    for line in lines:
        draw.text(
            (x, y),
            line,
            font=selected_font,
            fill=WHITE,
            direction="ltr"
        )

        box = draw.textbbox(
            (x, y),
            line,
            font=selected_font
        )

        y += (box[3] - box[1]) + 25

    return y

# ============== CREATE NEWS CARD ==============

def create_card(item, number):
    card = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BG
    )

    draw = ImageDraw.Draw(card)

    # Header
    draw.rectangle(
        (0, 0, WIDTH, 155),
        fill=PANEL
    )

    draw.rectangle(
        (0, 0, 14, HEIGHT),
        fill=YELLOW
    )

    draw.text(
        (60, 42),
        "NEWS UPDATE",
        font=font(55),
        fill=YELLOW
    )

    draw.text(
        (WIDTH - 300, 75),
        "NEPALI NEWS",
        font=font(28),
        fill=WHITE
    )

    # News photo
    photo = get_news_photo(item["url"])

    top = 185
    bottom = 770
    photo_box = (55, top, WIDTH - 55, bottom)

    if photo:
        photo = ImageOps.fit(
            photo,
            (WIDTH - 110, bottom - top),
            method=Image.Resampling.LANCZOS
        )

        card.paste(photo, (55, top))
        print("PHOTO ADDED:", number)

    else:
        draw.rounded_rectangle(
            photo_box,
            radius=20,
            fill=PANEL
        )

        draw.text(
            (WIDTH // 2, 475),
            "समाचार",
            font=font(75),
            fill=GREY,
            anchor="mm"
        )

    # Headline
    draw.text(
        (65, 820),
        "मुख्य समाचार",
        font=font(38),
        fill=YELLOW
    )

    draw_wrapped(
        draw,
        item["title"],
        65,
        895,
        font(57),
        WIDTH - 130,
        max_lines=5
    )

    # Source
    if item["source"]:
        draw.text(
            (65, 1125),
            "स्रोत: " + item["source"],
            font=font(27),
            fill=GREY
        )

    # Footer
    draw.line(
        (65, 1180, WIDTH - 65, 1180),
        fill=GREY,
        width=2
    )

    draw.text(
        (65, 1215),
        "मिति: " + get_nepali_date(),
        font=font(32),
        fill=WHITE
    )

    draw.text(
        (WIDTH - 250, 1220),
        f"NEWS {number:02d}",
        font=font(30),
        fill=YELLOW
    )

    output = OUTPUT_DIR / f"news_card_{number:02d}.png"

    card.save(output, optimize=True)

    print("CARD CREATED:", output)

# ============== MAIN ==============

def main():
    news = extract_news()

    print("News found:", len(news))

    if not news:
        print("No news available!")
        return

    for number, item in enumerate(news, 1):
        try:
            create_card(item, number)
        except Exception as error:
            print("CARD ERROR:", number, error)

    print("NEWS CARD GENERATION COMPLETED!")

if __name__ == "__main__":
    main()
