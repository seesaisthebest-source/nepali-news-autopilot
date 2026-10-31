
import json
import requests
import xml.etree.ElementTree as ET

from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# ==========================================
# NEWS AUTOMATION SETTINGS
# ==========================================

OUTPUT_FILE = Path("news_candidates.json")
MAX_NEWS_PER_CATEGORY = 7
REQUEST_TIMEOUT = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsAutomation/1.0)"
}

# ==========================================
# RSS NEWS SOURCES
# ==========================================

FEEDS = [
    {
        "name": "NEWS UPDATE",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("latest news Nepal")
            + "&hl=en-US&gl=NP&ceid=NP:en"
        ),
    },
    {
        "name": "WORLD NEWS",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("World latest news")
            + "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "name": "SPORTS NEWS",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("international sports news")
            + "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
]

# ==========================================
# XML HELPERS
# ==========================================

def get_text(element, tag):
    node = element.find(tag)

    if node is not None and node.text:
        return node.text.strip()

    return ""


def get_image(item):
    for element in item.iter():
        tag = element.tag.lower()

        if tag.endswith("thumbnail") or tag.endswith("content"):
            url = element.attrib.get("url", "")

            if url.startswith("http"):
                return url

        if tag.endswith("enclosure"):
            url = element.attrib.get("url", "")
            media_type = element.attrib.get("type", "")

            if url.startswith("http") and media_type.startswith("image/"):
                return url

    return ""


def clean_html(value):
    if not value:
        return ""

    soup = BeautifulSoup(value, "html.parser")
    return soup.get_text(" ", strip=True)


# ==========================================
# COLLECT NEWS FROM RSS
# ==========================================

def collect_feed(feed):
    category = feed["name"]
    feed_url = feed["url"]

    print("Checking:", category)

    try:
        response = requests.get(
            feed_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        items = root.findall(".//item")

        collected = []

        for item in items:

            title = get_text(item, "title")
            article_url = get_text(item, "link")
            description = clean_html(
                get_text(item, "description")
            )

            if not title or not article_url:
                continue

            news_item = {
                "title": title,
                "source": category,
                "article_url": article_url,
                "rss_url": feed_url,
                "image_url": get_image(item),
                "summary": description,
                "published": get_text(item, "pubDate"),
                "collected_at": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            collected.append(news_item)

            if len(collected) >= MAX_NEWS_PER_CATEGORY:
                break

        print(category, "collected:", len(collected))

        return collected

    except Exception as error:
        print("Feed error:", category, error)
        return []


# ==========================================
# MAIN NEWS COLLECTION
# ==========================================

def main():

    all_news = []
    seen_urls = set()

    for feed in FEEDS:

        feed_news = collect_feed(feed)

        for news in feed_news:

            article_url = news["article_url"]

            if article_url in seen_urls:
                continue

            seen_urls.add(article_url)
            all_news.append(news)

    # Save collected news
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_news,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("--------------------------------")
    print("NEWS COLLECTION COMPLETED")
    print("Total news:", len(all_news))
    print("Output file:", OUTPUT_FILE)
    print("--------------------------------")

    if not all_news:
        raise RuntimeError(
            "No news collected. Check RSS feed availability."
        )


if __name__ == "__main__":
    main()
