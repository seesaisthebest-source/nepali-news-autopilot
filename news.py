
import re
import time
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont
from nepali_datetime import datetime as NepaliDateTime

OUTPUT_FILE = "news_candidates.md"
CARD_DIR = Path("news_cards")
FONT_DIR = Path("fonts")

MAX_NEWS = 20
WINDOW_HOURS = 24

CARD_WIDTH = 1080
CARD_HEIGHT = 1350

FONT_DIR.mkdir(exist_ok=True)
CARD_DIR.mkdir(exist_ok=True)

FONT_PATH = FONT_DIR / "NotoSansDevanagari-Bold.ttf"

FONT_URL = (
    "https://github.com/google/fonts/raw/main/"
    "ofl/notosansdevanagari/"
    "NotoSansDevanagari%5Bwght%5D.ttf"
)

FEEDS = [
    {
        "name": "नेपाल समाचार",
        "query": "Nepal",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("Nepal")
            + "&hl=ne&gl=NP&ceid=NP:ne"
        ),
    },
    {
        "name": "विश्व समाचार",
        "query": "World",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("World news")
            + "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 NepaliNewsAutopilot/1.0"
}


def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return text.strip()


def download_font():
    if FONT_PATH.exists():
        return

    print("Downloading Nepali font...")

    try:
        response = requests.get(
            FONT_URL,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()

        FONT_PATH.write_bytes(response.content)

        print("Nepali font downloaded.")

    except Exception as error:
        print("Font download error:", error)


def get_font(size):
    if FONT_PATH.exists():
        return ImageFont.truetype(
            str(FONT_PATH),
            size=size,
        )

    return ImageFont.load_default()


def get_nepali_date():
    today = NepaliDateTime.now()

    return (
        f"{today.year} साल "
        f"{today.month} महिना "
        f"{today.day} गते"
    )


def get_news():
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=WINDOW_HOURS
    )

    articles = []
    seen = set()

    for feed in FEEDS:
        print("Reading feed:", feed["name"])

        try:
            response = requests.get(
                feed["url"],
                headers=HEADERS,
                timeout=20,
            )

            response.raise_for_status()

            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                title = clean_text(
                    item.findtext("title", "")
                )

                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")

                if not title or not link or not pub_date:
                    continue

                try:
                    published = parsedate_to_datetime(
                        pub_date
                    )

                    if published.tzinfo is None:
                        published = published.replace(
                            tzinfo=timezone.utc
                        )

                    published = published.astimezone(
                        timezone.utc
                    )

                except Exception:
                    continue

                if published < cutoff:
                    continue

                key = title.lower()

                if key in seen:
                    continue

                seen.add(key)

                articles.append({
                    "title": title,
                    "link": link,
                    "source": feed["name"],
                    "published": published,
                })

        except Exception as error:
            print(
                "Feed error:",
                feed["name"],
                str(error)[:200],
            )

        time.sleep(1)

    articles.sort(
        key=lambda article: article["published"],
        reverse=True,
    )

    return articles[:MAX_NEWS]


def create_news_card(article, index):
    width = CARD_WIDTH
    height = CARD_HEIGHT

    image = Image.new(
        "RGB",
        (width, height),
        (12, 20, 38),
    )

    draw = ImageDraw.Draw(image)

    # Background
    draw.rectangle(
        (0, 0, width, 18),
        fill=(220, 35, 45),
    )

    # Header
    draw.text(
        (55, 55),
        "नेपाल समाचार",
        font=get_font(48),
        fill=(255, 255, 255),
    )

    draw.text(
        (55, 125),
        "NEPALI NEWS",
        font=get_font(30),
        fill=(180, 195, 215),
    )

    # Breaking news label
    draw.rounded_rectangle(
        (55, 205, 350, 275),
        radius=15,
        fill=(220, 35, 45),
    )

    draw.text(
        (80, 215),
        "ताजा समाचार",
        font=get_font(36),
        fill=(255, 255, 255),
    )

    # Headline
    headline = article["title"]

    font = get_font(58)

    words = headline.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = (
            current_line + " " + word
        ).strip()

        if draw.textlength(
            test_line,
            font=font,
        ) > width - 110:

            if current_line:
                lines.append(current_line)

            current_line = word

        else:
            current_line = test_line

    if current_line:
        lines.append(current_line)

    y = 340

    for line in lines[:8]:
        draw.text(
            (55, y),
            line,
            font=font,
            fill=(255, 255, 255),
        )

        y += 85

    # News source
    source = article["source"]

    draw.text(
        (55, 1050),
        "स्रोत: " + source,
        font=get_font(32),
        fill=(180, 195, 215),
    )

    # Nepali date
    nepali_date = get_nepali_date()

    draw.text(
        (55, 1120),
        nepali_date,
        font=get_font(34),
        fill=(255, 210, 70),
    )

    # Footer
    draw.rectangle(
        (0, 1240, width, height),
        fill=(220, 35, 45),
    )

    draw.text(
        (55, 1275),
        "NEPALI NEWS AUTOPILOT",
        font=get_font(30),
        fill=(255, 255, 255),
    )

    output_path = CARD_DIR / (
        f"news_card_{index}.png"
    )

    image.save(output_path)

    print("News card saved:", output_path)

    return output_path


def save_news(articles):
    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    lines = [
        "# Nepali + World News Candidates",
        "",
        f"Collected: {now}",
        "",
        "> RSS headlines are candidates, not verified facts. "
        "Check original sources before publishing.",
        "",
    ]

    for index, article in enumerate(
        articles,
        start=1,
    ):
        lines.extend([
            "## " + article["title"],
            "",
            "Source: " + article["source"],
            "",
            "Published: " + article["published"].strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
            "",
            "Link: " + article["link"],
            "",
        ])

        try:
            create_news_card(
                article,
                index,
            )

        except Exception as error:
            print(
                "Card error:",
                str(error)[:200],
            )

    Path(OUTPUT_FILE).write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(
        "Collected",
        len(articles),
        "news candidates.",
    )

    print("Saved:", OUTPUT_FILE)


def main():
    print("Starting Nepali News Collector...")

    download_font()

    articles = get_news()

    save_news(articles)

    print("News collection finished.")


if __name__ == "__main__":
    main()
