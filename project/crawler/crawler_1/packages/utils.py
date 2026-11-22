import json
import re
import unicodedata
from pathlib import Path


# =========================================================
# TEXT
# =========================================================

def clean_text(text):
    """
    Làm sạch chuỗi:
    - bỏ khoảng trắng thừa
    - bỏ xuống dòng/tab thừa
    - xử lý non-breaking space
    """
    if text is None:
        return ""

    text = str(text)

    text = text.replace("\xa0", " ")
    text = text.replace("\u202f", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_text(text):
    """
    Chuẩn hóa text để so sánh:
    - lowercase
    - bỏ dấu tiếng Việt
    - đổi đ -> d
    - bỏ ký tự đặc biệt
    """
    text = clean_text(text).lower()

    text = unicodedata.normalize(
        "NFD",
        text
    )

    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    text = text.replace(
        "đ",
        "d"
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


# =========================================================
# OPENING HOURS
# =========================================================

def extract_opening_hours(text):
    """
    Tìm giờ mở cửa.

    Hỗ trợ:
        Giờ mở cửa: 10:00 - 22:00
        Giờ mở cửa: 07h00 - 22h00
        10:30 – 14:00 và 17:30 – 22:00
        Cả ngày

    Không tự sinh dữ liệu nếu nguồn không có.
    """
    text = clean_text(text)

    if not text:
        return ""

    label_pattern = (
        r"(?:"
        r"giờ mở cửa"
        r"|giờ hoạt động"
        r"|thời gian hoạt động"
        r"|thời gian mở cửa"
        r")"
    )

    label_match = re.search(
        label_pattern + r"\s*[:：\-]?\s*(.{0,180})",
        text,
        flags=re.IGNORECASE
    )

    if label_match:
        segment = label_match.group(1)

        # Chỉ lấy nội dung trước metadata tiếp theo
        segment = re.split(
            r"\b(?:"
            r"giá bán"
            r"|giá thành"
            r"|giá tham khảo"
            r"|giá trung bình"
            r"|khoảng giá"
            r"|mức giá"
            r"|địa chỉ"
            r"|địa chỉ cơ sở"
            r"|số điện thoại"
            r"|hotline"
            r"|giao hàng"
            r"|menu"
            r"|thực đơn"
            r"|ưu điểm"
            r"|nhược điểm"
            r"|phù hợp"
            r")\b",
            segment,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        all_day = re.search(
            r"\b(cả ngày|24/7|24h/24)\b",
            segment,
            flags=re.IGNORECASE
        )

        if all_day:
            return clean_text(
                all_day.group(1)
            )

    else:
        # Fallback cho nguồn có giờ nhưng không ghi nhãn rõ
        segment = text

    # 10:30 hoặc 10h30 hoặc 10h
    time_token = (
        r"(?:[01]?\d|2[0-3])"
        r"(?:"
        r"\s*:\s*[0-5]\d"
        r"|\s*[hH](?:\s*[0-5]\d)?"
        r")"
    )

    time_range = (
        time_token
        + r"\s*(?:-|–|—|đến|tới)\s*"
        + time_token
    )

    values = re.findall(
        time_range,
        segment,
        flags=re.IGNORECASE
    )

    result = []

    for value in values:
        value = clean_text(value)

        if value not in result:
            result.append(value)

        # Một quán có thể có 2 ca
        if len(result) >= 2:
            break

    return " | ".join(result)


# =========================================================
# PRICE
# =========================================================

def extract_price(text):
    """
    Tìm giá khi website ghi rõ.

    Hỗ trợ:
        Khoảng giá: 150.000 - 200.000 đ/người
        Giá bán: 35.000 – 60.000 VNĐ/bát
        Giá thành: Khoảng 10.000 - 159.000 VNĐ
        Giá tham khảo: 50.000 – 100.000 VNĐ
        Mức giá: 150.000 Vnđ - 250.000 Vnđ/người

    Không lấy phần trăm giảm giá làm price_range.
    """
    text = clean_text(text)

    if not text:
        return ""

    label_pattern = (
        r"(?:"
        r"khoảng giá"
        r"|mức giá"
        r"|giá tham khảo"
        r"|giá trung bình"
        r"|giá bán"
        r"|giá thành"
        r"|giá vé"
        r")"
    )

    match = re.search(
        label_pattern + r"\s*[:：\-]?\s*(.{0,180})",
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    segment = match.group(1)

    # Cắt trước metadata tiếp theo
    segment = re.split(
        r"\b(?:"
        r"giờ mở cửa"
        r"|giờ hoạt động"
        r"|thời gian hoạt động"
        r"|địa chỉ"
        r"|địa chỉ cơ sở"
        r"|số điện thoại"
        r"|hotline"
        r"|giao hàng"
        r"|menu"
        r"|thực đơn"
        r"|ưu điểm"
        r"|nhược điểm"
        r"|phù hợp"
        r")\b",
        segment,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]

    # 150.000 / 150,000 / 150k
    money = (
        r"(?:"
        r"\d{1,3}(?:[.,]\d{3})+"
        r"|\d+(?:[.,]\d+)?\s*[kK]"
        r")"
        r"\s*(?:VNĐ|VND|vnđ|vnd|đồng|đ)?"
    )

    # Khoảng giá
    range_pattern = (
        r"(?:khoảng\s+|từ\s+)?"
        + money
        + r"\s*(?:-|–|—|đến|tới)\s*"
        + money
        + r"(?:\s*/\s*[\wÀ-ỹ]+)?"
    )

    range_match = re.search(
        range_pattern,
        segment,
        flags=re.IGNORECASE
    )

    if range_match:
        value = clean_text(
            range_match.group(0)
        )

        if "%" not in value:
            return value

    # Giá đơn
    single_pattern = (
        r"(?:khoảng\s+|từ\s+)?"
        + money
        + r"(?:\s*/\s*[\wÀ-ỹ]+)?"
    )

    single_match = re.search(
        single_pattern,
        segment,
        flags=re.IGNORECASE
    )

    if single_match:
        value = clean_text(
            single_match.group(0)
        )

        if "%" not in value:
            return value

    return ""


# =========================================================
# ADDRESS
# =========================================================

def extract_address(text):
    """
    Tìm địa chỉ khi website có nhãn Địa chỉ/Vị trí.
    """
    text = clean_text(text)

    if not text:
        return ""

    labelled_pattern = (
        r"(?:"
        r"địa chỉ cơ sở"
        r"|địa chỉ"
        r"|vị trí"
        r")"
        r"\s*[:：\-]\s*"
        r"(.+?)"
        r"(?="
        r"\b(?:"
        r"giờ mở cửa"
        r"|giờ hoạt động"
        r"|thời gian hoạt động"
        r"|giá bán"
        r"|giá thành"
        r"|giá tham khảo"
        r"|giá trung bình"
        r"|khoảng giá"
        r"|mức giá"
        r"|số điện thoại"
        r"|hotline"
        r"|giao hàng"
        r"|menu"
        r"|thực đơn"
        r"|loại hình"
        r"|phù hợp"
        r"|ưu điểm"
        r"|nhược điểm"
        r")\b"
        r"|$)"
    )

    match = re.search(
        labelled_pattern,
        text,
        flags=re.IGNORECASE
    )

    if match:
        return clean_text(
            match.group(1)
        )

    # Fallback:
    # 25 Trần Duy Hưng, Cầu Giấy, Hà Nội
    fallback_pattern = (
        r"\b("
        r"\d+[A-Za-z]?"
        r"(?:[/\-]\d+)?"
        r"\s+"
        r"[^.;|]{3,120}?"
        r"(?:"
        r"Ba Đình"
        r"|Bắc Từ Liêm"
        r"|Cầu Giấy"
        r"|Đống Đa"
        r"|Hà Đông"
        r"|Hai Bà Trưng"
        r"|Hoàn Kiếm"
        r"|Hoàng Mai"
        r"|Long Biên"
        r"|Nam Từ Liêm"
        r"|Tây Hồ"
        r"|Thanh Xuân"
        r")"
        r"[^.;|]{0,50}"
        r")"
    )

    fallback = re.search(
        fallback_pattern,
        text,
        flags=re.IGNORECASE
    )

    if fallback:
        return clean_text(
            fallback.group(1)
        )

    return ""


# =========================================================
# PHONE
# =========================================================

def has_phone(text):
    text = clean_text(text)

    return bool(
        re.search(
            r"(?:\+?84|0)"
            r"[\s.\-]?"
            r"\d{2,3}"
            r"(?:[\s.\-]?\d){6,8}",
            text
        )
    )


# =========================================================
# TXT
# =========================================================

def load_url_file(path):
    path = Path(path)

    if not path.exists():
        return []

    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    result = []

    for line in lines:
        line = clean_text(line)

        if not line:
            continue

        if line.startswith("#"):
            continue

        result.append(line)

    return result


def remove_duplicate_urls(lines):
    result = []
    seen = set()

    for line in lines:
        line = clean_text(line)

        if not line:
            continue

        # Nếu format source|url thì dedup theo URL
        if "|" in line:
            parts = line.split("|", 1)

            source = clean_text(
                parts[0]
            )

            url = clean_text(
                parts[1]
            )

            key = url.lower().rstrip("/")

            output = (
                f"{source}|{url}"
            )

        else:
            key = line.lower().rstrip("/")
            output = line

        if key in seen:
            continue

        seen.add(key)
        result.append(output)

    return result


def save_url_file(path, lines):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    unique = remove_duplicate_urls(
        lines
    )

    content = "\n".join(unique)

    if content:
        content += "\n"

    path.write_text(
        content,
        encoding="utf-8"
    )


# =========================================================
# JSON
# =========================================================

def load_json(path, default=None):
    path = Path(path)

    if default is None:
        default = []

    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return default


def save_json(path, data):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )