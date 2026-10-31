
import re
import json
import time
import html
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urljoin
from html.parser import HTMLParser

OUTPUT_JSON = "news_candidates.json"
OUTPUT_MD = "news_candidates.md"

MAX_NEWS = 20
WINDOW_HOURS = 36

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 "
        "Safari/537.36"
    )
}

FEEDS = [
    {
        "name": "नेपाल समाचार",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote("Nepal news")
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


class ImageMetadataParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):

        attrs = dict(attrs)

        if tag == "meta":

            key = (
                attrs.get("property")
                or attrs.get("name")
                or attrs.get("itemprop")
                or ""
            ).lower()

            content = attrs.get("content", "").strip()

            if key in [
                "og:image",
                "og:image:url",
                "twitter:image",
                "twitter:image:src",
                "image",
            ] and content:
                self.images.append(content)

        if tag == "link":

            rel = attrs.get("rel", "").lower()
            href = attrs.get("href", "").strip()

            if "image_src" in rel and href:
                self.images.append(href)


def parse_date(value):

    try:
        published = parsedate_to_datetime(value)

        if published.tzinfo is None:
            published = published.replace(
                tzinfo=timezone.utc
            )

        return published.astimezone(timezone.utc)

    except Exception:
        return None


def resolve_article_url(url):

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=25,
            allow_redirects=True,
        )

        final_url = response.url
        response.close()

        if (
            final_url
            and "news.google.com" not in final_url
        ):
            return final_url

    except requests.RequestException as error:

        print(
            "URL resolution error:",
            str(error)[:150]
        )

    return url


def extract_rss_image(item):

    namespaces = [
        "{http://search.yahoo.com/mrss/}content",
        "{http://search.yahoo.com/mrss/}thumbnail",
        "{http://www.w3.org/2005/Atom}link",
    ]

    for namespace in namespaces:

        for element in item.findall(".//" + namespace):

            image_url = (
                element.attrib.get("url")
                or element.attrib.get("href")
                or ""
            )

            if image_url.startswith("https://") or image_url.startswith("http://"):
                return image_url

    enclosure = item.find("enclosure")

    if enclosure is not None:

        image_url = enclosure.attrib.get("url", "")

        if image_url.startswith(("https://", "http://")):
            return image_url

    return ""


def extract_article_image(article_url):

    if not article_url:
        return ""

    if "news.google.com" in article_url:
        return ""

    try:

        response = requests.get(
            article_url,
            headers=HEADERS,
            timeout=25,
            allow_redirects=True,
        )

        response.raise_for_status()

        parser = ImageMetadataParser()
        parser.feed(
            response.text[:1500000]
        )

        for image in parser.images:

            image_url = urljoin(
                response.url,
                image
            )

            if image_url.startswith(
                ("https://", "http://")
            ):

                print(
                    "NEWS IMAGE FOUND:",
                    image_url[:120]
                )

                return image_url

    except Exception as error:

        print(
            "Image extraction error:",
            str(error)[:180]
        )

    return ""


def get_news():

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(hours=WINDOW_HOURS)
    )

    articles = []
    seen = set()

    for feed in FEEDS:

        print("Reading feed:", feed["name"])

        try:

            response = requests.get(
                feed["url"],
                headers=HEADERS,
                timeout=25,
            )

            response.raise_for_status()

            root = ET.fromstring(
                response.content
            )

            for item in root.findall(".//item"):

                title = clean_text(
                    item.findtext("title", "")
                )

                rss_url = (
                    item.findtext("link", "") or ""
                ).strip()

                published = parse_date(
                    item.findtext("pubDate", "")
                )

                if not title or not rss_url:
                    continue

                if not published or published < cutoff:
                    continue

                key = title.casefold()

                if key in seen:
                    continue

                seen.add(key)

                source_element = item.find("source")

                source = (
                    clean_text(source_element.text)
                    if source_element is not None
                    and source_element.text
                    else feed["name"]
                )

                print("Resolving:", title[:70])

                article_url = resolve_article_url(
                    rss_url
                )

                # First try image information from RSS.
                image_url = extract_rss_image(item)

                # If RSS has no image, inspect publisher page.
                if not image_url:

                    image_url = extract_article_image(
                        article_url
                    )

                if image_url:

                    print("REAL NEWS PHOTO FOUND!")

                else:

                    print(
                        "NO NEWS PHOTO FOUND:",
                        title[:70]
                    )

                articles.append({

                    "title": title,

                    "rss_url": rss_url,

                    "article_url": article_url,

                    "source": source,

                    "published": published.isoformat(),

                    "image_url": image_url,

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

        "Collected: "
        + datetime.now(
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

            "Article URL: "
            + article["article_url"],

            "",

            "Published: "
            + article["published"],

            "",

            "Image URL: "
            + (article["image_url"] or ""),

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
