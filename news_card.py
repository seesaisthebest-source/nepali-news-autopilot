def get_article_photo(entry):
    article_url = entry.get("link", "")
    candidates = []

    # RSS media fields
    for field in [
        "media_content",
        "media_thumbnail",
        "enclosures"
    ]:
        for item in entry.get(field, []):
            image_url = (
                item.get("url")
                or item.get("href")
            )

            add_candidate(
                candidates,
                image_url,
                article_url
            )

    # RSS summary, description and content
    for field in ["summary", "description"]:
        find_images_in_text(
            entry.get(field, ""),
            candidates,
            article_url
        )

    for content_item in entry.get("content", []):
        find_images_in_text(
            content_item.get("value", ""),
            candidates,
            article_url
        )

    # Publisher page images
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

            for meta in soup.find_all("meta"):
                key = (
                    meta.get("property")
                    or meta.get("name")
                    or ""
                ).lower()

                if key in [
                    "og:image",
                    "og:image:secure_url",
                    "twitter:image",
                    "twitter:image:src"
                ]:
                    add_candidate(
                        candidates,
                        meta.get("content"),
                        response.url
                    )

            for img in soup.find_all("img"):
                for attr in [
                    "src",
                    "data-src",
                    "data-original",
                    "srcset"
                ]:
                    value = img.get(attr)

                    if not value:
                        continue

                    if attr == "srcset":
                        parts = value.split(",")[0].strip().split()

                        if not parts:
                            continue

                        value = parts[0]

                    add_candidate(
                        candidates,
                        value,
                        response.url
                    )

        except requests.RequestException as error:
            print("Article page error:", error)

    # Remove duplicate candidates
    candidates = list(dict.fromkeys(candidates))

    print("Photo candidates found:", len(candidates))

    # Try to download each candidate
    for url in candidates:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
                allow_redirects=True
            )

            response.raise_for_status()

            # Do not rely only on Content-Type.
            # Some publishers return incorrect headers.
            photo = Image.open(
                BytesIO(response.content)
            )

            photo.load()

            photo = photo.convert("RGB")

            if photo.width < 2 or photo.height < 2:
                continue

            print("Usable photo found:", url)

            return photo

        except Exception as error:
            print("Photo skipped:", str(error)[:250])

    # Safe fallback: make a neutral placeholder.
    # This avoids failing the entire workflow when
    # publisher photos cannot be downloaded.
    print("No real photo available. Using placeholder.")

    placeholder = Image.new(
        "RGB",
        (1080, 720),
        "#263746"
    )

    draw = ImageDraw.Draw(placeholder)

    # Simple decorative news-image placeholder
    draw.rectangle(
        (100, 150, 980, 570),
        outline="#526879",
        width=8
    )

    draw.line(
        (160, 500, 420, 250, 600, 420, 760, 300, 920, 500),
        fill="#526879",
        width=12
    )

    draw.ellipse(
        (760, 200, 850, 290),
        fill="#526879"
    )

    try:
        font = load_font(48, True)

        text = "तस्बिर उपलब्ध छैन"

        box = draw.textbbox(
            (0, 0),
            text,
            font=font,
            direction="ltr",
            language="ne"
        )

        text_width = box[2] - box[0]

        draw.text(
            ((1080 - text_width) // 2, 590),
            text,
            font=font,
            fill="#FFFFFF",
            direction="ltr",
            language="ne"
        )

    except Exception as error:
        print("Placeholder text error:", error)

    return placeholder
