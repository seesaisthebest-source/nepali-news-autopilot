
import re
import json
import time
import html
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

OUTPUT_JSON = "news_candidates.json"
OUTPUT_MD = "news_candidates.md"

MAX_NEWS = 20
WINDOW_HOURS = 24

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 15) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 "
        "Mobile Safari/537.36"
    )
}

FEEDS = [
    {
        "name": "नेपाल समाचार",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("Nepal")
            + "&hl=ne&gl=NP&ceid=NP:ne"
        ),
    },
    {
        "name": "विश्व समाचार",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("World news")
            + "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
]


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def resolve_article_url(url):
    """Resolve Google News RSS URL to its destination."""

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
            allow_redirects=True,
            stream=True,
        )

        final_url = response.url
        response.close()

        if final_url and "news.google.com" not in final_url:
            return final_url

    except requests.RequestException as error:
        print("URL resolution error:", str(error)[:150])

    return url


def parse_date(value):
    try:
        published = parsedate_to_datetime(value)

        if published.tzinfo is None:
            published = published.replace(
                tzinfo=timezone.utc
            )

        return published.astimezone(timezone.utc)

    except (ValueError, TypeError, OverflowError):
        return None


def get_news():

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(hours=WINDOW_HOURS)
    )

    articles = []
    seen = set()

    for feed in FEEDS:

        print("Reading:", feed["name"])

        try:
            response = requests.get(
                feed["url"],
                headers=HEADERS,
                timeout=25,
            )

            response.raise_for_status()

            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):

                title = clean_text(
                    item.findtext("title", "")
                )

                rss_url = (
                    item.findtext("link", "") or ""
                ).strip()

                pub_date = item.findtext(
                    "pubDate", ""
                )

                if not title or not rss_url:
                    continue

                published = parse_date(pub_date)

                if not published:
                    continue

                if published < cutoff:
                    continue

                key = title.casefold()

                if key in seen:
                    continue

                seen.add(key)

                # Find publisher name from RSS
                source_element = item.find("source")

                source = (
                    clean_text(source_element.text)
                    if source_element is not None
                    else feed["name"]
                )

                print("Resolving:", title[:70])

                article_url = resolve_article_url(
                    rss_url
                )

                articles.append({
                    "title": title,
                    "rss_url": rss_url,
                    "article_url": article_url,
                    "source": source,
                    "published": published.isoformat(),
                    "image_url": None,
                })

                time.sleep(0.5)

        except Exception as error:

            print(
                "Feed error:",
                feed["name"],
                str(error)[:200],
            )

        time.sleep(1)

    articles.sort(
        key=lambda item: item["published"],
        reverse=True,
    )

    return articles[:MAX_NEWS]


def save_news(articles):

    Path(OUTPUT_JSON).write_text(
        json.dumps(
            articles,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Nepali and World News",
        "",
        "Collected: " + datetime.now(
            timezone.utc
        ).isoformat(),
        "",
    ]

    for index, article in enumerate(
        articles,
        start=1,
    ):

        lines.extend([
            f"## {index}. {article['title']}",
            "",
            "Source: " + article["source"],
            "",
            "Article URL: " + article["article_url"],
            "",
            "Published: " + article["published"],
            "",
            "---",
            "",
        ])

    Path(OUTPUT_MD).write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print()
    print("Total news:", len(articles))
    print("Saved:", OUTPUT_JSON)
    print("Saved:", OUTPUT_MD)


def main():

    print("Starting Nepali News Collector...")

    articles = get_news()

    save_news(articles)

    print("News collection completed.")


if __name__ == "__main__":
    main()
