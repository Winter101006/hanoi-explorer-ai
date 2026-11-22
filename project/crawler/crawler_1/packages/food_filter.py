import re

from urllib.parse import (
    urljoin,
    urlparse
)

from bs4 import (
    BeautifulSoup,
    NavigableString,
    Tag
)

from project.crawler.crawler_1.packages.utils import (
    clean_text,
    normalize_text,
    extract_address,
    extract_opening_hours,
    extract_price,
    has_phone
)


# =========================================================
# 12 QUẬN
# =========================================================

TARGET_DISTRICTS = {
    "Ba Đình": [
        "ba đình"
    ],
    "Bắc Từ Liêm": [
        "bắc từ liêm"
    ],
    "Cầu Giấy": [
        "cầu giấy"
    ],
    "Đống Đa": [
        "đống đa"
    ],
    "Hà Đông": [
        "hà đông"
    ],
    "Hai Bà Trưng": [
        "hai bà trưng"
    ],
    "Hoàn Kiếm": [
        "hoàn kiếm"
    ],
    "Hoàng Mai": [
        "hoàng mai"
    ],
    "Long Biên": [
        "long biên"
    ],
    "Nam Từ Liêm": [
        "nam từ liêm"
    ],
    "Tây Hồ": [
        "tây hồ"
    ],
    "Thanh Xuân": [
        "thanh xuân"
    ]
}


# =========================================================
# HTML HEADING
# =========================================================

HEADING_TAGS = [
    "h2",
    "h3",
    "h4",
    "h5"
]


# =========================================================
# VENUE KEYWORDS
# =========================================================

VENUE_WORDS = [
    "quán",
    "nhà hàng",
    "restaurant",
    "cafe",
    "café",
    "coffee",
    "tiệm",
    "bistro",
    "bakery",
    "bbq",
    "grill",
    "hotpot",
    "pub",
    "bar",
    "lounge"
]


# =========================================================
# PHÂN LOẠI QUÁN ĂN / QUÁN NƯỚC
# =========================================================

# ---------------------------------------------------------
# BƯỚC 1:
# Tìm trực tiếp trong TÊN địa điểm
# ---------------------------------------------------------

DRINK_NAME_PATTERNS = [
    # Cafe / cà phê
    r"\bcafe\b",
    r"\bcoffee\b",
    r"\bca phe\b",

    # Trà
    r"\btra\b",
    r"\btea\b",

    # Bia
    r"\bbia\b",
    r"\bbeer\b",

    # Bar
    r"\bbar\b",

    # Pub
    r"\bpub\b",
]


# ---------------------------------------------------------
# BƯỚC 2:
# Nếu tên không nói rõ thì kiểm tra nội dung.
#
# Chỉ dùng các pattern có NGỮ CẢNH MẠNH.
#
# Không dùng đơn giản:
#     if "tra" in text
#
# vì nhà hàng cũng có thể nhắc đến trà.
# ---------------------------------------------------------

DRINK_DESCRIPTION_PATTERNS = [
    # =====================================================
    # CAFE / COFFEE
    # =====================================================

    r"\bquan (?:cafe|ca phe|coffee)\b",

    r"\btiem (?:cafe|ca phe|coffee)\b",

    r"\bcua hang (?:cafe|ca phe|coffee)\b",

    r"\bchuyen (?:cafe|ca phe|coffee)\b",

    r"\bchuyen ve (?:cafe|ca phe|coffee)\b",

    r"\bmenu quan .*?\b(?:cafe|ca phe|coffee)\b",

    r"\bmenu .*?\bgom .*?\b(?:cafe|ca phe|coffee)\b",

    r"\bmenu .*?\bco .*?\b(?:cafe|ca phe|coffee)\b",

    r"\bphuc vu .*?\b(?:cafe|ca phe|coffee)\b",


    # =====================================================
    # TRÀ / TEA
    # =====================================================

    r"\bquan (?:tra|tea)\b",

    r"\btiem (?:tra|tea)\b",

    r"\bchuyen (?:tra|tea)\b",

    r"\bchuyen ve (?:tra|tea)\b",

    r"\bmenu quan .*?\btra\b",

    r"\bmenu .*?\bgom .*?\btra\b",

    r"\bmenu .*?\bco .*?\btra\b",

    r"\bmenu quan .*?\btea\b",

    r"\bmenu .*?\bgom .*?\btea\b",

    r"\bcac loai tra\b",

    r"\bnhieu loai tra\b",

    r"\btra sua\b",

    r"\btra chanh\b",

    r"\btra hoa qua\b",


    # =====================================================
    # BIA / BEER
    # =====================================================

    r"\bquan bia\b",

    r"\bbia hoi\b",

    r"\bbia tuoi\b",

    r"\bbeer club\b",

    r"\bchuyen bia\b",

    r"\bchuyen ve bia\b",

    r"\bmenu quan .*?\bbia\b",

    r"\bmenu .*?\bgom .*?\bbia\b",

    r"\bmenu .*?\bco .*?\bbia\b",

    r"\bcac loai bia\b",

    r"\bnhieu loai bia\b",


    # =====================================================
    # BAR
    #
    # Không dùng "\bbar\b" đơn lẻ ở description.
    #
    # Ví dụ:
    # "quán có một quầy bar"
    #
    # chưa đủ bằng chứng đây là quán nước.
    # =====================================================

    r"\bquan bar\b",

    r"\bbar cocktail\b",

    r"\bcocktail bar\b",

    r"\brooftop bar\b",

    r"\bbar chill\b",

    r"\bsky bar\b",


    # =====================================================
    # PUB
    # =====================================================

    r"\bquan pub\b",

    r"\bpub chill\b",

    r"\bpub beer\b",
]


def classify_category(
    name,
    text=""
):
    """
    Phân loại category:

        Quán nước
        Quán ăn

    Quy tắc:

    1. Ưu tiên kiểm tra TÊN địa điểm.

    2. Nếu tên không đủ rõ thì kiểm tra nội dung
       bằng các pattern có ngữ cảnh mạnh.

    3. Không gán Quán nước chỉ vì description
       xuất hiện đơn lẻ từ:
           trà
           cafe
           bia
           bar
           pub
    """

    normalized_name = normalize_text(
        name
    )

    normalized_text = normalize_text(
        text
    )

    # =====================================================
    # 1. KIỂM TRA TÊN
    # =====================================================

    for pattern in DRINK_NAME_PATTERNS:

        if re.search(
            pattern,
            normalized_name,
            flags=re.IGNORECASE
        ):
            return "Quán nước"

    # =====================================================
    # 2. KIỂM TRA DESCRIPTION / SECTION
    # =====================================================

    for pattern in DRINK_DESCRIPTION_PATTERNS:

        if re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE
        ):
            return "Quán nước"

    # =====================================================
    # 3. MẶC ĐỊNH
    # =====================================================

    return "Quán ăn"


# =========================================================
# GENERIC HEADINGS
# =========================================================

GENERIC_PATTERNS = [
    r"^top\b",
    r"^danh sach\b",
    r"^goi y\b",
    r"^diem danh\b",

    r"^nhung quan\b",
    r"^nhung nha hang\b",
    r"^cac quan\b",
    r"^cac nha hang\b",
    r"^cac dia diem\b",
    r"^mot vai\b",

    r"^uu dai\b",
    r"^bai viet\b",
    r"^bai viet lien quan\b",
    r"^tin lien quan\b",

    r"^cach thuc\b",
    r"^cach dat\b",
    r"^huong dan\b",

    r"^faq\b",
    r"^cau hoi\b",

    r"^food tour\b",

    r"^mot so luu y\b",
    r"^nam ro gio mo cua\b",
    r"^chon quan theo\b",
    r"^tim hieu gia\b",

    r"^quan an sang ngon\b",
    r"^quan an trua ngon\b",
    r"^quan an toi ngon\b",
    r"^quan an dem ngon\b",
    r"^quan an vat ngon\b",
    r"^quan an nhanh ngon\b",

    r"^quan an[, ]+nha hang\b",
    r"^quan an ngon tai\b",
    r"^quan an ngon tren\b",
    r"^quan an ngon trong\b",
    r"^quan an ngon gan\b",
    r"^quan an ngon o\b",

    r"^quan cafe.*song ao\b",
    r"^quan cafe.*view dep\b",
    r"^quan cafe.*mang phong cach\b",

    r"^cafe.*thien duong\b",

    r"^khach san\b",
    r"^cam nang\b",
    r"^doc them\b",
    r"^xem them\b",

    r"^gian hang\b",
    r"^thong tin\b"
]


# =========================================================
# CHILD HEADING KHÔNG PHẢI QUÁN
# =========================================================

CHILD_METADATA_PATTERNS = [
    r"^dia chi\b",
    r"^gio mo cua\b",
    r"^gio hoat dong\b",

    r"^gia\b",
    r"^bang gia\b",
    r"^muc gia\b",
    r"^khoang gia\b",

    r"^menu\b",
    r"^thuc don\b",

    r"^khong gian\b",
    r"^am thuc\b",
    r"^mon an\b",

    r"^hinh anh\b",

    r"^danh gia\b",
    r"^review\b",

    r"^uu dai\b",
    r"^thong tin\b",

    r"^lien he\b",
    r"^dat ban\b"
]


# =========================================================
# CLEAN NAME
# =========================================================

def clean_candidate_name(name):
    name = clean_text(
        name
    )

    # -----------------------------------------------------
    # Bỏ số thứ tự
    #
    # 1. Quán ABC
    # 1.2 Quán ABC
    # -----------------------------------------------------

    name = re.sub(
        r"^\d+(?:\.\d+)*"
        r"[\.\)\-:]?\s+",
        "",
        name
    )

    # -----------------------------------------------------
    # Bỏ số La Mã CHỈ khi có dấu phân cách.
    #
    # III. Nhà hàng ABC
    # -> Nhà hàng ABC
    #
    # Tránh:
    # Lẩu -> ẩu
    # MONO -> ONO
    # -----------------------------------------------------

    name = re.sub(
        r"^[IVXLCDM]+"
        r"[\.\)\-:]\s*",
        "",
        name,
        count=1,
        flags=re.IGNORECASE
    )

    return clean_text(
        name
    )


# =========================================================
# INVALID NAME
# =========================================================

def is_invalid_name(name):
    normalized = normalize_text(
        name
    )

    if not normalized:
        return True

    if re.fullmatch(
        r"\d+",
        normalized
    ):
        return True

    words = normalized.split()

    if len(words) > 20:
        return True

    if len(name) < 2:
        return True

    return False


# =========================================================
# GENERIC SECTION
# =========================================================

def is_generic_section(name):
    name = clean_text(
        name
    )

    if not name:
        return True

    normalized = normalize_text(
        name
    )

    # -----------------------------------------------------
    # FAQ
    # -----------------------------------------------------

    if name.rstrip().endswith("?"):
        return True

    # -----------------------------------------------------
    # Ví dụ:
    # Gian hàng | Thông tin | Ưu đãi
    # -----------------------------------------------------

    if "|" in name:

        pipe_noise = [
            "uu dai",
            "thong tin",
            "gian hang",
            "bai viet"
        ]

        if any(
            value in normalized
            for value in pipe_noise
        ):
            return True

    # -----------------------------------------------------
    # Tiêu đề tổng hợp
    # -----------------------------------------------------

    if normalized.startswith(
        "quan an ngon "
    ):
        return True

    # -----------------------------------------------------
    # Generic patterns
    # -----------------------------------------------------

    for pattern in GENERIC_PATTERNS:

        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        ):
            return True

    return False


# =========================================================
# VENUE WORD
# =========================================================

def has_venue_word(text):
    normalized = normalize_text(
        text
    )

    return any(
        normalize_text(
            word
        ) in normalized

        for word in VENUE_WORDS
    )


# =========================================================
# DISTRICT
# =========================================================

def detect_districts(text):
    """
    Tìm tất cả district xuất hiện trong section.
    """

    normalized = normalize_text(
        text
    )

    found = []

    for district, aliases in (
        TARGET_DISTRICTS.items()
    ):

        for alias in aliases:

            if normalize_text(
                alias
            ) in normalized:

                found.append(
                    district
                )

                break

    return found


def detect_district(text):
    """
    Chỉ trả district khi tìm được đúng 1 quận.
    """

    found = detect_districts(
        text
    )

    if len(found) == 1:
        return found[0]

    return ""


def is_correct_district(
    expected_district,
    text
):
    """
    Nếu section không ghi quận rõ ràng:
        vẫn cho phép.

    Nếu có quận:
        expected_district phải nằm trong đó.
    """

    found = detect_districts(
        text
    )

    if not found:
        return True

    return expected_district in found


# =========================================================
# HEADING LEVEL
# =========================================================

def heading_level(tag):
    try:

        return int(
            tag.name[1]
        )

    except Exception:

        return 99


# =========================================================
# EXTRACT HEADING SECTION
# =========================================================

def extract_heading_section(heading):
    """
    Lấy nội dung từ heading hiện tại
    đến heading cùng cấp hoặc cao hơn tiếp theo.
    """

    current_level = heading_level(
        heading
    )

    parts = []

    child_headings = []

    # =====================================================
    # DUYỆT ELEMENT
    # =====================================================

    for element in heading.next_elements:

        # -------------------------------------------------
        # HEADING
        # -------------------------------------------------

        if isinstance(
            element,
            Tag
        ):

            if (
                element is not heading
                and element.name
                in HEADING_TAGS
            ):

                level = heading_level(
                    element
                )

                # Heading mới
                if level <= current_level:
                    break

                # Heading con
                child_name = (
                    clean_candidate_name(
                        element.get_text(
                            " ",
                            strip=True
                        )
                    )
                )

                if child_name:

                    child_headings.append(
                        child_name
                    )

        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

        if isinstance(
            element,
            NavigableString
        ):

            # Không lấy text của heading hiện tại
            if heading in element.parents:
                continue

            skip = False

            for parent in element.parents:

                if not isinstance(
                    parent,
                    Tag
                ):
                    continue

                if parent.name in [
                    "script",
                    "style",
                    "noscript",
                    "template",
                    "footer",
                    "nav",
                    "aside"
                ]:

                    skip = True

                    break

            if skip:
                continue

            value = clean_text(
                str(element)
            )

            if value:

                parts.append(
                    value
                )

    # =====================================================
    # LOẠI TEXT TRÙNG
    # =====================================================

    result = []

    seen = set()

    for value in parts:

        key = normalize_text(
            value
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            value
        )

    # =====================================================
    # LOẠI CHILD HEADING TRÙNG
    # =====================================================

    unique_children = []

    child_seen = set()

    for child in child_headings:

        key = normalize_text(
            child
        )

        if not key:
            continue

        if key in child_seen:
            continue

        child_seen.add(
            key
        )

        unique_children.append(
            child
        )

    return {
        "text": clean_text(
            " ".join(
                result
            )
        ),

        "child_headings": (
            unique_children
        )
    }


# =========================================================
# SECTION STATS
# =========================================================

def get_section_stats(text):
    normalized = normalize_text(
        text
    )

    address_count = len(
        re.findall(
            r"\bdia chi(?: co so)?\b",
            normalized
        )
    )

    opening_count = len(
        re.findall(
            r"\b(?:"
            r"gio mo cua"
            r"|gio hoat dong"
            r"|thoi gian hoat dong"
            r")\b",
            normalized
        )
    )

    price_count = len(
        re.findall(
            r"\b(?:"
            r"gia ban"
            r"|gia thanh"
            r"|gia tham khao"
            r"|gia trung binh"
            r"|khoang gia"
            r"|muc gia"
            r")\b",
            normalized
        )
    )

    phone_count = len(
        re.findall(
            r"(?:\+?84|0)"
            r"[\s.\-]?"
            r"\d{2,3}"
            r"(?:[\s.\-]?\d){6,8}",
            text
        )
    )

    return {
        "address_count": (
            address_count
        ),

        "opening_count": (
            opening_count
        ),

        "price_count": (
            price_count
        ),

        "phone_count": (
            phone_count
        )
    }


# =========================================================
# CHILD HEADING CHECK
# =========================================================

def is_metadata_child_heading(name):
    normalized = normalize_text(
        name
    )

    if not normalized:
        return True

    for pattern in (
        CHILD_METADATA_PATTERNS
    ):

        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        ):

            return True

    return False


# =========================================================
# COLLECTION SECTION
# =========================================================

def is_collection_section(
    text,
    child_headings=None
):
    """
    Xác định section hiện tại có chứa
    nhiều địa điểm khác nhau hay không.
    """

    if child_headings is None:

        child_headings = []

    stats = get_section_stats(
        text
    )

    # -----------------------------------------------------
    # Nhiều địa chỉ
    # -----------------------------------------------------

    if stats[
        "address_count"
    ] >= 2:

        return True

    # -----------------------------------------------------
    # Nhiều giờ + nhiều giá
    # -----------------------------------------------------

    if (
        stats[
            "opening_count"
        ] >= 2

        and

        stats[
            "price_count"
        ] >= 2
    ):

        return True

    # -----------------------------------------------------
    # Nhiều số điện thoại + metadata
    # -----------------------------------------------------

    if (
        stats[
            "phone_count"
        ] >= 2

        and

        (
            stats[
                "address_count"
            ] >= 1

            or

            stats[
                "price_count"
            ] >= 2
        )
    ):

        return True

    # -----------------------------------------------------
    # CHILD HEADINGS
    # -----------------------------------------------------

    possible_venues = []

    for child in child_headings:

        if is_metadata_child_heading(
            child
        ):
            continue

        if is_generic_section(
            child
        ):
            continue

        if is_invalid_name(
            child
        ):
            continue

        possible_venues.append(
            child
        )

    if len(
        possible_venues
    ) >= 2:

        return True

    return False


# =========================================================
# VENUE EVIDENCE
# =========================================================

def has_venue_evidence(
    name,
    text
):
    """
    Kiểm tra đây có phải địa điểm thực tế không.
    """

    address = extract_address(
        text
    )

    opening_hours = (
        extract_opening_hours(
            text
        )
    )

    price = extract_price(
        text
    )

    phone = has_phone(
        text
    )

    metadata_count = sum(
        [
            bool(
                address
            ),

            bool(
                opening_hours
            ),

            bool(
                price
            ),

            bool(
                phone
            )
        ]
    )

    # -----------------------------------------------------
    # >= 2 metadata
    # -----------------------------------------------------

    if metadata_count >= 2:
        return True

    # -----------------------------------------------------
    # Address + venue word
    # -----------------------------------------------------

    if (
        address

        and

        has_venue_word(
            name
        )
    ):

        return True

    # -----------------------------------------------------
    # Venue word + giờ/giá
    # -----------------------------------------------------

    if (
        has_venue_word(
            name
        )

        and

        (
            opening_hours
            or
            price
        )

        and

        len(
            text
        ) >= 50
    ):

        return True

    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

    normalized = normalize_text(
        text
    )

    strong_context = [
        "khong gian quan",
        "khong gian nha hang",

        "nha hang co",
        "quan co",

        "thuc don cua quan",
        "thuc don nha hang",

        "menu cua quan",
        "menu nha hang",

        "toa lac tai",
        "chi nhanh",

        "phuc vu thuc khach"
    ]

    context_match = any(
        signal in normalized

        for signal in strong_context
    )

    if (
        context_match

        and

        has_venue_word(
            name
            + " "
            + text
        )
    ):

        return True

    return False


# =========================================================
# FOOD ITEM ONLY
# =========================================================

def looks_like_food_item_only(
    name,
    text
):
    """
    Loại heading chỉ là tên món ăn.
    """

    # -----------------------------------------------------
    # Có evidence rõ ràng đây là địa điểm
    # -----------------------------------------------------

    if has_venue_evidence(
        name,
        text
    ):

        return False

    normalized_name = normalize_text(
        name
    )

    normalized_text = normalize_text(
        text
    )

    food_name_patterns = [
        r"^bun\b",
        r"^pho\b",
        r"^banh\b",
        r"^chao\b",
        r"^cha\b",
        r"^nem\b",
        r"^oc\b",
        r"^xoi\b",
        r"^com\b",
        r"^lau\b",
        r"^che\b",
        r"^ca phe trung\b"
    ]

    food_name_match = any(
        re.search(
            pattern,
            normalized_name
        )

        for pattern
        in food_name_patterns
    )

    food_context = [
        "mon an nay",
        "mon nay",
        "nguyen lieu",
        "cach che bien",
        "huong vi",
        "nuoc dung",
        "an kem",
        "cong thuc",
        "dac san ha noi"
    ]

    context_count = sum(
        1

        for signal
        in food_context

        if signal
        in normalized_text
    )

    if (
        food_name_match

        and

        context_count >= 2
    ):

        return True

    return False


# =========================================================
# FIND DETAIL LINK
# =========================================================

def find_detail_link(
    heading,
    name,
    base_url
):
    candidates = []

    # -----------------------------------------------------
    # Link bao trực tiếp heading
    # -----------------------------------------------------

    parent_link = (
        heading.find_parent(
            "a",
            href=True
        )
    )

    if parent_link:

        candidates.append(
            parent_link
        )

    # -----------------------------------------------------
    # Link trong parent gần heading
    # -----------------------------------------------------

    parent = heading.parent

    if parent:

        candidates.extend(
            parent.find_all(
                "a",
                href=True
            )
        )

    base_host = urlparse(
        base_url
    ).netloc

    name_normalized = normalize_text(
        name
    )

    seen_urls = set()

    for anchor in candidates:

        href = clean_text(
            anchor.get(
                "href",
                ""
            )
        )

        if not href:
            continue

        if href.startswith(
            (
                "#",
                "javascript:",
                "mailto:",
                "tel:"
            )
        ):

            continue

        absolute = urljoin(
            base_url,
            href
        )

        if absolute in seen_urls:
            continue

        seen_urls.add(
            absolute
        )

        parsed = urlparse(
            absolute
        )

        if (
            parsed.netloc
            and
            parsed.netloc
            != base_host
        ):

            continue

        anchor_text = normalize_text(
            anchor.get_text(
                " ",
                strip=True
            )
        )

        if not anchor_text:
            continue

        if (
            name_normalized
            in anchor_text

            or

            anchor_text
            in name_normalized
        ):

            return absolute

    return ""


# =========================================================
# EXTRACT FOOD CANDIDATES
# =========================================================

def extract_food_candidates(
    html,
    expected_district,
    base_url=""
):
    """
    Hàm chính:

    HTML
      ↓
    heading
      ↓
    kiểm tra tên
      ↓
    loại heading tổng hợp
      ↓
    lấy section
      ↓
    loại collection
      ↓
    loại tên món đơn thuần
      ↓
    kiểm tra venue
      ↓
    kiểm tra district
      ↓
    phân loại Quán ăn / Quán nước
      ↓
    trả candidate
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # =====================================================
    # 1. BỎ TAG RÁC
    # =====================================================

    for tag in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "iframe"
        ]
    ):

        tag.decompose()

    results = []

    seen = set()

    # =====================================================
    # 2. DUYỆT HEADING
    # =====================================================

    for heading in soup.find_all(
        HEADING_TAGS
    ):

        raw_name = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        name = clean_candidate_name(
            raw_name
        )

        # -------------------------------------------------
        # Tên không hợp lệ
        # -------------------------------------------------

        if is_invalid_name(
            name
        ):

            continue

        # -------------------------------------------------
        # Heading tổng hợp
        # -------------------------------------------------

        if is_generic_section(
            name
        ):

            continue

        # =================================================
        # 3. LẤY SECTION
        # =================================================

        section = extract_heading_section(
            heading
        )

        text = section.get(
            "text",
            ""
        )

        child_headings = section.get(
            "child_headings",
            []
        )

        if not text:

            continue

        # =================================================
        # 4. LOẠI SECTION CHỨA NHIỀU QUÁN
        # =================================================

        if is_collection_section(
            text,
            child_headings
        ):

            continue

        # =================================================
        # 5. LOẠI TÊN MÓN ĂN
        # =================================================

        if looks_like_food_item_only(
            name,
            text
        ):

            continue

        # =================================================
        # 6. VENUE EVIDENCE
        # =================================================

        if not has_venue_evidence(
            name,
            text
        ):

            continue

        # =================================================
        # 7. DISTRICT
        # =================================================

        if not is_correct_district(
            expected_district,
            text
        ):

            continue

        # =================================================
        # 8. CHỐNG TRÙNG TRONG PAGE
        # =================================================

        key = normalize_text(
            name
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        # =================================================
        # 9. DETAIL LINK
        # =================================================

        detail_url = ""

        if base_url:

            detail_url = find_detail_link(
                heading,
                name,
                base_url
            )

        # =================================================
        # 10. DISTRICT
        # =================================================

        detected_district = (
            detect_district(
                text
            )
        )

        if not detected_district:

            detected_district = (
                expected_district
            )

        # =================================================
        # 11. CATEGORY
        #
        # Quan trọng:
        # truyền cả NAME + TEXT
        # =================================================

        category = classify_category(
            name,
            text
        )

        # =================================================
        # 12. RESULT
        # =================================================

        results.append(
            {
                "name": (
                    name
                ),

                "text": (
                    text
                ),

                "address": (
                    extract_address(
                        text
                    )
                ),

                "district": (
                    detected_district
                ),

                "category": (
                    category
                ),

                "detail_url": (
                    detail_url
                )
            }
        )

    return results