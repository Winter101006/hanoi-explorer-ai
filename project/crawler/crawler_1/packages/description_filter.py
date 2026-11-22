import re

from bs4 import (
    BeautifulSoup,
    Tag
)

from project.crawler.crawler_1.packages.utils import (
    clean_text,
    normalize_text
)


NOISE_PHRASES = [
    "xem thêm",
    "đọc thêm",
    "bài viết liên quan",
    "có thể bạn quan tâm",
    "ưu đãi liên quan",
    "ưu đãi mới",
    "cẩm nang du lịch",
    "chia sẻ bài viết",
    "theo dõi chúng tôi",
    "đăng ký nhận tin",
    "tải ứng dụng",
    "đặt bàn qua",
    "cách thức đặt bàn"
]


METADATA_PREFIXES = [
    "địa chỉ",
    "vị trí",
    "giờ mở cửa",
    "mở cửa",
    "giờ hoạt động",
    "thời gian hoạt động",
    "giá",
    "mức giá",
    "khoảng giá",
    "giá tham khảo",
    "điện thoại",
    "hotline",
    "website"
]


def remove_noise_tags(soup):
    for tag in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "iframe",
            "footer",
            "nav"
        ]
    ):
        tag.decompose()


def is_noise_node(node):
    if not isinstance(
        node,
        Tag
    ):
        return False

    current = node

    bad_tokens = [
        "footer",
        "header",
        "sidebar",
        "related",
        "recommend",
        "popup",
        "modal",
        "breadcrumb",
        "advert",
        "banner"
    ]

    for _ in range(6):
        if current is None:
            break

        classes = current.get(
            "class",
            []
        )

        if isinstance(
            classes,
            str
        ):
            classes = [
                classes
            ]

        element_id = current.get(
            "id",
            ""
        )

        attrs = normalize_text(
            " ".join(
                classes
                + [element_id]
            )
        )

        if any(
            token in attrs
            for token in bad_tokens
        ):
            return True

        current = current.parent

    return False


def split_sentences(text):
    text = clean_text(text)

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+|;\s+",
        text
    )

    return [
        clean_text(part)
        for part in parts
        if clean_text(part)
    ]


def is_noise_sentence(
    sentence,
    name=""
):
    normalized = normalize_text(
        sentence
    )

    raw = sentence.lower()

    if not normalized:
        return True

    if name:
        if normalized == normalize_text(
            name
        ):
            return True

    for prefix in METADATA_PREFIXES:
        if normalized.startswith(
            normalize_text(prefix)
        ):
            return True

    for phrase in NOISE_PHRASES:
        if normalize_text(
            phrase
        ) in normalized:
            return True

    code_signals = [
        "function()",
        "document.getelementbyid",
        "queryselector",
        "settimeout(",
        "classlist.add",
        "!important",
        "font awesome",
        "copyright ©"
    ]

    if any(
        signal in raw
        for signal in code_signals
    ):
        return True

    if len(sentence) < 20:
        return True

    return False


def filter_description(
    name,
    text,
    max_chars=1200
):
    sentences = split_sentences(
        text
    )

    result = []
    seen = set()

    for sentence in sentences:
        if is_noise_sentence(
            sentence,
            name
        ):
            continue

        key = normalize_text(
            sentence
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(sentence)

        if len(result) >= 6:
            break

    description = clean_text(
        " ".join(result)
    )

    if len(description) > max_chars:
        description = (
            description[:max_chars]
            .rsplit(
                " ",
                1
            )[0]
            .strip()
        )

    return description