from PIL import Image, ImageDraw, ImageFont, features
import feedparser
import requests
import nepali_datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from io import BytesIO
import os

WIDTH, HEIGHT = 1080, 1350
OUTPUT_DIR = "news_cards"

BG = "#101820"
RED = "#E63946"
WHITE = "#FFFFFF"
GRAY = "#DDE3E8"

FONT_REGULAR = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NepaliNewsCard/3.0)"
}

FEEDS = [
    (
        "नेपाल समाचार",
        "https://news.google.com/rss/search?q=नेपाल&hl=ne&gl=NP&ceid=NP:ne"
    ),
    (
        "विश्व समाचार",
        "https://news.google.com/rss/search?q=विश्व+समाचार&hl=ne&gl=NP&ceid=NP:ne"
    )
]


def nepali_digits(value):
    digits = "०१२३४५६७८९"
    return str(value).translate(
        str.maketrans("0123456789", digits)
    )


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
        raise FileNotFoundError(
            "Nepali font not found: " + path
        )

    if not features.check("raqm"):
        raise RuntimeError(
            "Pillow RAQM support is missing. Check news.yml."
        )

    return ImageFont.truetype(
        path,
        size,
        layout_engine=ImageFont.Layout.RAQM
    )


def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()

        box = draw.textbbox(
            (0, 0),
            test,
            font=font,
            direction="ltr",
            language="ne"
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


def is_google_placeholder(url):
    host = urlparse(url).netloc.lower()

    # Google News article pages are not image files.
    # googleusercontent.com is deliberately allowed.
    blocked = [
        "news.google.com",
        "google.com"
    ]

    return any(
        host == item or host.endswith("." + item)
        for item in blocked
    )


def get_article_photo(entry):
    article_url = entry.get("link", "")
    candidates = []

    # First try the publisher article page.
    if article_url:
        try:
            response = requests.get(
                article_url,
                headers=HEADERS,
                timeout=20,
                allow_redirects=True
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for attrs in [
                {"property": "og:image"},
                {"name": "twitter:image"},
                {"property": "og:image:secure_url"}
            ]:
                tag = soup.find("meta", attrs=attrs)

                if tag and tag.get("content"):
                    image_url = urljoin(
                        response.url,
                        tag["content"]
                    )
                    candidates.append(image_url)

        except requests.RequestException as error:
            print("Article page error:", error)

    # RSS image links are fallback candidates.
    for item in entry.get("media_content", []):
        if item.get("url"):
            candidates.append(item["url"])

    for item in entry.get("media_thumbnail", []):
        if item.get("url"):
            candidates.append(item["url"])

    for item in entry.get("enclosures", []):
        if item.get("href"):
            candidates.append(item["href"])

    # Remove duplicate URLs.
    candidates = list(dict.fromkeys(candidates))

    for url in candidates:
        if is_google_placeholder(url):
            continue

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if "image/" not in content_type:
                continue

            photo = Image.open(
                BytesIO(response.content)
            ).convert("RGB")

            # Reject very small icons.
            if photo.width < 400 or photo.height < 250:
                continue

            ratio = photo.width / photo.height

            if ratio < 0.65 or ratio > 2.8:
                continue

            return photo

        except Exception as error:
            print("Photo skipped:", error)

    return None


def crop_cover(photo, width, height):
    photo = photo.copy()

    scale = max(
        width / photo.width,
        height / photo.height
    )

    new_size = (
        int(photo.width * scale),
        int(photo.height * scale)
    )

    photo = photo.resize(
        new_size,
        Image.Resampling.LANCZOS
    )

    left = (photo.width - width) // 2
    top = (photo.height - height) // 2

    return photo.crop((
        left,
        top,
        left + width,
        top + height
    ))


def create_card(title, source, photo, number):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BG
    )

    # News photograph.
    photo_area = crop_cover(
        photo,
        WIDTH,
        720
    )

    image.paste(photo_area, (0, 0))

    draw = ImageDraw.Draw(image)

    # Red news heading.
    draw.rectangle(
        (0, 720, WIDTH, 850),
        fill=RED
    )

    category_font = load_font(48, True)

    draw.text(
        (55, 755),
        "ताजा समाचार",
        font=category_font,
        fill=WHITE,
        direction="ltr",
        language="ne"
    )

    # Automatically adjust headline font size.
    headline_font = None
    lines = []

    for size in [54, 50, 46, 42, 38]:
        test_font = load_font(size, True)

        test_lines = wrap_text(
            title,
            test_font,
            draw,
            WIDTH - 120
        )

        if len(test_lines) <= 4:
            headline_font = test_font
            lines = test_lines
            break

    if headline_font is None:
        headline_font = load_font(38, True)

        lines = wrap_text(
            title,
            headline_font,
            draw,
            WIDTH - 120
        )[:4]

        if lines:
            lines[-1] += "..."

    y = 900

    for line in lines:
        draw.text(
            (60, y),
            line,
            font=headline_font,
            fill=WHITE,
            direction="ltr",
            language="ne"
        )

        y += 65

    # Footer.
    draw.rectangle(
        (0, 1190, WIDTH, HEIGHT),
        fill="#202B36"
    )

    source_font = load_font(34, True)
    date_font = load_font(30)

    draw.text(
        (60, 1210),
        source,
        font=source_font,
        fill=WHITE,
        direction="ltr",
        language="ne"
    )

    draw.text(
        (60, 1270),
        "मिति: " + nepali_date(),
        font=date_font,
        fill=GRAY,
        direction="ltr",
        language="ne"
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    filename = f"news_{number:02d}.png"
    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    image.save(
        path,
        format="PNG"
    )

    print("Created:", path)


def main():
    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # Remove previous PNG cards.
    for filename in os.listdir(OUTPUT_DIR):
        if filename.lower().endswith(".png"):
            os.remove(
                os.path.join(OUTPUT_DIR, filename)
            )

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

            photo = get_article_photo(entry)

            if photo is None:
                print("Skipped: no usable photo")
                continue

            count += 1

            create_card(
                title,
                source,
                photo,
                count
            )

    print("Total cards created:", count)

    if count == 0:
        raise RuntimeError(
            "No news cards were created. "
            "No usable photos were found."
        )


if __name__ == "__main__":
    main()
