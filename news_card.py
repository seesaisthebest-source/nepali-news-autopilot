
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

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
    "User-Agent": "Mozilla/5.0 NepaliNewsCardBot/1.0"
}

Path(OUTPUT_DIR).mkdir(exist_ok=True)


# ---------------- FONTS ----------------

def load_font(size, bold=False):
    possible_fonts = [
        "NotoSansDevanagari-Bold.ttf" if bold else "NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()


# ---------------- NEWS PARSER ----------------

def read_news():
    path = Path(INPUT_FILE)

    if not path.exists():
        print("ERROR: news_candidates.md file not found.")
        return []

    content = path.read_text(encoding="utf-8")
    articles = []

    # Read markdown headings as news headlines.
    lines = content.splitlines()

    current = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            headline = re.sub(r"^#+\s*", "", line).strip()

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
            url_match = re.search(r"https?://\S+", line)

            if url_match and not current["link"]:
                current["link"] = url_match.group(0).rstrip(")>,")
            
            if line.lower().startswith("source:"):
                current["source"] = line.split(":", 1)[1].strip()

    if current:
        articles.append(current)

    # Alternative: read bullet-style news if no headings exist.
    if not articles:
        for line in lines:
            line = re.sub(r"^\s*[-*•]\s*", "", line).strip()

            if len(line) > 25 and not line.startswith("http"):
                articles.append({
                    "title": line,
                    "source": "समाचार स्रोत",
                    "link": "",
                })

    # Remove duplicate headlines.
    unique = []
    seen = set()

    for article in articles:
        title = article["title"].strip()

        if title and title not in seen:
            seen.add(title)
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
                timeout=15
            )
            response.raise_for_status()

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            image_url = None

            for tag in soup.find_all("meta"):
                key = (
                    tag.get("property")
                    or tag.get("name")
                    or ""
                ).lower()

                if key in ["og:image", "twitter:image"]:
                    image_url = tag.get("content")
                    if image_url:
                        break

            if image_url:
                photo_response = requests.get(
                    image_url,
                    headers=HEADERS,
                    timeout=15
                )
                photo_response.raise_for_status()

                from io import BytesIO

                photo = Image.open(
                    BytesIO(photo_response.content)
                ).convert("RGB")

                return photo

        except Exception as error:
            print("Photo unavailable:", str(error)[:150])

    # Placeholder image
    placeholder = Image.new(
        "RGB",
        (WIDTH, 650),
        "#263746"
    )

    draw = ImageDraw.Draw(placeholder)

    draw.rectangle(
        (100, 100, 980, 550),
        outline="#526879",
        width=8
    )

    draw.ellipse(
        (750, 180, 850, 280),
        fill="#526879"
    )

    draw.line(
        (160, 480, 400, 260, 600, 420, 760, 300, 920, 480),
        fill="#526879",
        width=12
    )

    font = load_font(42, True)

    draw.text(
        (350, 570),
        "तस्बिर उपलब्ध छैन",
        font=font,
        fill=WHITE
    )

    return placeholder


# ---------------- IMAGE FIT ----------------

def crop_photo(photo, target_width, target_height):
    photo = photo.convert("RGB")

    ratio = max(
        target_width / photo.width,
        target_height / photo.height
    )

    new_size = (
        int(photo.width * ratio),
        int(photo.height * ratio)
    )

    photo = photo.resize(
        new_size,
        Image.Resampling.LANCZOS
    )

    left = (photo.width - target_width) // 2
    top = (photo.height - target_height) // 2

    return photo.crop((
        left,
        top,
        left + target_width,
        top + target_height
    ))


# ---------------- TEXT WRAPPING ----------------

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = current + " " + word if current else word

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


# ---------------- CREATE NEWS CARD ----------------

def create_news_card(article, index):
    canvas = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND
    )

    draw = ImageDraw.Draw(canvas)

    # Top breaking-news strip
    draw.rectangle(
        (0, 0, WIDTH, 105),
        fill=RED
    )

    brand_font = load_font(46, True)

    draw.text(
        (45, 22),
        "नेपाली समाचार",
        font=brand_font,
        fill=WHITE
    )

    breaking_font = load_font(30, True)

    draw.text(
        (790, 35),
        "NEWS UPDATE",
        font=breaking_font,
        fill=WHITE
    )

    # Main photo
    photo = get_article_photo(article)

    photo = crop_photo(
        photo,
        WIDTH,
        650
    )

    canvas.paste(photo, (0, 105))

    # Headline area
    draw.rectangle(
        (0, 755, WIDTH, 1240),
        fill=BACKGROUND
    )

    draw.rectangle(
        (45, 790, 58, 900),
        fill=YELLOW
    )

    headline = article.get(
        "title",
        "आजका मुख्य समाचार"
    )

    headline_font = load_font(58, True)

    lines = wrap_text(
        draw,
        headline,
        headline_font,
        940
    )

    y = 800

    for line in lines[:5]:
        draw.text(
            (90, y),
            line,
            font=headline_font,
            fill=WHITE
        )
        y += 88

    # Footer
    draw.rectangle(
        (0, 1240, WIDTH, HEIGHT),
        fill="#07111E"
    )

    source_font = load_font(30, True)
    date_font = load_font(26)

    source = article.get("source", "समाचार स्रोत")

    draw.text(
        (45, 1270),
        "स्रोत: " + source[:35],
        font=source_font,
        fill=MUTED
    )

    date_text = datetime.now().strftime("%Y-%m-%d")

    draw.text(
        (800, 1280),
        date_text,
        font=date_font,
        fill=YELLOW
    )

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
        print("No news articles found in news_candidates.md")
        return

    print("News articles found:", len(articles))

    success = 0

    for index, article in enumerate(articles, start=1):
        try:
            create_news_card(article, index)
            success += 1

        except Exception as error:
            print(
                f"Card {index} failed:",
                str(error)
            )

    print("================================")
    print("News cards created:", success)
    print("Output folder:", OUTPUT_DIR)
    print("================================")


if __name__ == "__main__":
    main()
