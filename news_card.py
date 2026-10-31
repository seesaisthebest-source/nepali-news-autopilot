# ============== FIND NEWS IMAGE ==============

def download_image(url):

    if not url:
        return None

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if not content_type.startswith("image/"):
            return None

        if len(response.content) > 15 * 1024 * 1024:
            print("Image too large.")
            return None

        img = Image.open(
            BytesIO(response.content)
        )

        img = ImageOps.exif_transpose(img)
        img.load()

        print("REAL NEWS PHOTO DOWNLOADED:", url[:100])

        return img.convert("RGB")

    except Exception as error:

        print("IMAGE DOWNLOAD ERROR:", str(error)[:150])
        return None


def get_news_photo(article_url, saved_image_url=""):

    # 1. पहिले RSS बाट प्राप्त फोटो लिंक जाँच्ने

    if saved_image_url:

        print("Trying saved image URL...")

        photo = download_image(saved_image_url)

        if photo:
            return photo

    # 2. समाचारको वेबपेजबाट OG image खोज्ने

    if not article_url:
        return None

    try:

        print("Checking article for photo:", article_url[:100])

        response = requests.get(
            article_url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.content,
            "html.parser",
        )

        image_url = ""

        meta_options = [
            ("property", "og:image"),
            ("property", "og:image:url"),
            ("name", "twitter:image"),
            ("property", "twitter:image"),
            ("itemprop", "image"),
        ]

        for attribute, value in meta_options:

            tag = soup.find(
                "meta",
                attrs={attribute: value},
            )

            if tag and tag.get("content"):

                image_url = tag["content"].strip()
                break

        if not image_url:

            tag = soup.find(
                "link",
                rel="image_src",
            )

            if tag:
                image_url = tag.get("href", "")

        if not image_url:
            print("No article photo found.")
            return None

        image_url = urljoin(
            response.url,
            image_url,
        )

        print("Found article photo:", image_url[:120])

        return download_image(image_url)

    except Exception as error:

        print("PHOTO ERROR:", str(error)[:180])

    return None
