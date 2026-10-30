
import re
import time
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

OUTPUT_FILE = "news_candidates.md"
MAX_NEWS = 20
WINDOW_HOURS = 24

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

    for article in articles:
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

    articles = get_news()

    save_news(articles)

    print("News collection finished.")


if __name__ == "__main__":
    main()
