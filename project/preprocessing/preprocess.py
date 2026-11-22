"""
Hanoi Explorer Chatbot - Data Preprocessing & Schema Enrichment Pipeline
Chuẩn hóa dữ liệu thô từ crawler thành dataset sạch 14 trường khớp hoàn toàn
với hệ thống Web (chat_service.py, main.js) và RAG/VectorDB (vector_store.py, itinerary_service.py).
"""
import hashlib
import json
import os
import re
import sys
import unicodedata
from typing import Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 1. Định vị đường dẫn động theo vị trí project/preprocessing/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # .../project/preprocessing
PROJECT_DIR = os.path.dirname(BASE_DIR)                        # .../project

# Tự động quét dữ liệu thô theo cấu trúc hiện tại của repo (và fallback đường dẫn cũ nếu có)
RAW_DIRS = [
    os.path.join(PROJECT_DIR, "crawler", "crawler_1", "data", "raw"),
    os.path.join(PROJECT_DIR, "crawler", "crawler_2", "data", "raw"),
    os.path.join(PROJECT_DIR, "crawler", "data", "raw"),
    os.path.join(PROJECT_DIR, "crawler_1", "data", "raw"),
    os.path.join(PROJECT_DIR, "crawler_2", "data", "raw"),
]
OUTPUT_DIR = os.path.join(PROJECT_DIR, "bot", "data")
OUTPUT_DATA_PATH = os.path.join(OUTPUT_DIR, "hanoi_places_cleaned.json")

DISTRICT_MAP: Dict[str, str] = {
    "ba dinh": "Ba Đình",
    "bac tu liem": "Bắc Từ Liêm",
    "cau giay": "Cầu Giấy",
    "dong da": "Đống Đa",
    "ha dong": "Hà Đông",
    "hai ba trung": "Hai Bà Trưng",
    "hoan kiem": "Hoàn Kiếm",
    "hoang mai": "Hoàng Mai",
    "long bien": "Long Biên",
    "nam tu liem": "Nam Từ Liêm",
    "tay ho": "Tây Hồ",
    "thanh xuan": "Thanh Xuân",
    "son tay": "Sơn Tây",
    "ba vi": "Ba Vì",
    "soc son": "Sóc Sơn",
    "dong anh": "Đông Anh",
    "gia lam": "Gia Lâm",
    "hoai duc": "Hoài Đức",
    "thanh tri": "Thanh Trì",
}

DISTRICT_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "Hoàn Kiếm": (21.0285, 105.8542),
    "Ba Đình": (21.0333, 105.8286),
    "Tây Hồ": (21.0667, 105.8167),
    "Cầu Giấy": (21.0350, 105.7950),
    "Đống Đa": (21.0180, 105.8250),
    "Hai Bà Trưng": (21.0080, 105.8500),
    "Thanh Xuân": (20.9980, 105.8120),
    "Nam Từ Liêm": (21.0150, 105.7650),
    "Bắc Từ Liêm": (21.0550, 105.7600),
    "Hà Đông": (20.9700, 105.7750),
    "Hoàng Mai": (20.9750, 105.8550),
    "Long Biên": (21.0450, 105.8850),
    "Sơn Tây": (21.1380, 105.5050),
    "Ba Vì": (21.0815, 105.3625),
    "Sóc Sơn": (21.3150, 105.8250),
    "Đông Anh": (21.1350, 105.8450),
    "Gia Lâm": (20.9950, 105.9200),
    "Hoài Đức": (21.0180, 105.7150),
    "Thanh Trì": (20.9450, 105.8450),
}

# Tọa độ các tuyến phố / khu vực / địa danh phổ biến tại Hà Nội
KNOWN_LOCATION_COORDINATES: Dict[str, Tuple[float, float]] = {
    # Hoàn Kiếm
    "hồ hoàn kiếm": (21.0285, 105.8542),
    "hồ gươm": (21.0285, 105.8542),
    "tràng tiền": (21.0250, 105.8560),
    "đinh tiên hoàng": (21.0305, 105.8530),
    "nhà thờ lớn": (21.0288, 105.8490),
    "lý quốc sư": (21.0298, 105.8495),
    "bát đàn": (21.0335, 105.8478),
    "hàng buồm": (21.0358, 105.8520),
    "chả cá": (21.0355, 105.8492),
    "đồng xuân": (21.0382, 105.8498),
    "nguyễn hữu huân": (21.0335, 105.8540),
    "tạ hiện": (21.0352, 105.8525),
    "hàng mã": (21.0368, 105.8485),
    "hàng bạc": (21.0335, 105.8515),
    "hàng gai": (21.0315, 105.8495),
    "hàng bông": (21.0295, 105.8465),
    "hàng đào": (21.0330, 105.8505),
    "hàng điếu": (21.0320, 105.8470),
    "cầu gỗ": (21.0328, 105.8532),
    "phùng hưng": (21.0360, 105.8470),
    "tống duy tân": (21.0302, 105.8438),
    "lý thường kiệt": (21.0235, 105.8500),
    "trần hưng đạo": (21.0215, 105.8520),
    "trần nhật duật": (21.0378, 105.8555),
    "phan chu trinh": (21.0225, 105.8565),
    # Ba Đình
    "giang văn minh": (21.0312, 105.8255),
    "tôn thất thiệp": (21.0328, 105.8425),
    "phan huy ích": (21.0432, 105.8442),
    "phan kế bính": (21.0335, 105.8125),
    "linh lang": (21.0338, 105.8110),
    "đào tấn": (21.0330, 105.8085),
    "phan đình phùng": (21.0405, 105.8405),
    "hoàng hoa thám": (21.0410, 105.8205),
    "đội cấn": (21.0365, 105.8220),
    "kim mã": (21.0315, 105.8200),
    "giảng võ": (21.0275, 105.8210),
    "liễu giai": (21.0340, 105.8140),
    "văn cao": (21.0420, 105.8150),
    "ngọc khánh": (21.0290, 105.8160),
    "nguyễn thái học": (21.0300, 105.8360),
    "ngọc hà": (21.0385, 105.8315),
    "thụy khuê": (21.0445, 105.8235),
    "đê la thành": (21.0265, 105.8170),
    "thành công": (21.0215, 105.8155),
    "cống vị": (21.0355, 105.8115),
    "hoàng thành thăng long": (21.0345, 105.8402),
    "chùa một cột": (21.0358, 105.8335),
    "lăng bác": (21.0368, 105.8346),
    "quán thánh": (21.0425, 105.8385),
    # Tây Hồ
    "xuân diệu": (21.0610, 105.8260),
    "quảng an": (21.0620, 105.8220),
    "tô ngọc vân": (21.0645, 105.8245),
    "lạc long quân": (21.0650, 105.8080),
    "âu cơ": (21.0750, 105.8280),
    "nhật tân": (21.0820, 105.8260),
    "yên phụ": (21.0510, 105.8415),
    "trích sài": (21.0485, 105.8135),
    "nhật chiêu": (21.0730, 105.8170),
    "đường thanh niên": (21.0450, 105.8380),
    "phủ tây hồ": (21.0635, 105.8290),
    "chùa trấn quốc": (21.0478, 105.8370),
    "hồ tây": (21.0550, 105.8250),
    # Cầu Giấy
    "trần thái tông": (21.0310, 105.7880),
    "duy tân": (21.0320, 105.7830),
    "tô hiệu": (21.0430, 105.7940),
    "nghĩa tân": (21.0425, 105.7920),
    "xuân thủy": (21.0370, 105.7880),
    "cầu giấy": (21.0350, 105.7950),
    "nguyễn phong sắc": (21.0395, 105.7925),
    "hoàng quốc việt": (21.0460, 105.7960),
    "trung hòa": (21.0120, 105.7980),
    "vũ phạm hàm": (21.0145, 105.7995),
    "trần duy hưng": (21.0085, 105.7990),
    "nguyễn chánh": (21.0115, 105.7930),
    "trần quốc hoàn": (21.0415, 105.7885),
    "chùa hà": (21.0385, 105.7945),
    "phan văn trường": (21.0390, 105.7860),
    "quan hoa": (21.0345, 105.8020),
    # Đống Đa
    "văn miếu": (21.0285, 105.8355),
    "chùa láng": (21.0265, 105.8035),
    "nguyễn văn tuyết": (21.0115, 105.8210),
    "đặng văn ngữ": (21.0090, 105.8335),
    "tôn thất tùng": (21.0032, 105.8305),
    "hoàng cầu": (21.0185, 105.8220),
    "mai anh tuấn": (21.0190, 105.8230),
    "thái hà": (21.0135, 105.8185),
    "chùa bộc": (21.0075, 105.8285),
    "phạm ngọc thạch": (21.0090, 105.8340),
    "tôn đức thắng": (21.0260, 105.8320),
    "ô chợ dừa": (21.0205, 105.8280),
    "xã đàn": (21.0175, 105.8325),
    "nguyễn lương bằng": (21.0200, 105.8260),
    "huỳnh thúc kháng": (21.0195, 105.8115),
    "nguyên hồng": (21.0210, 105.8105),
    "hoàng ngọc phách": (21.0155, 105.8110),
    "láng hạ": (21.0165, 105.8130),
    "khâm thiên": (21.0190, 105.8375),
    # Hai Bà Trưng
    "công viên thống nhất": (21.0145, 105.8445),
    "bà triệu": (21.0150, 105.8505),
    "phố huế": (21.0160, 105.8525),
    "bạch mai": (20.9995, 105.8502),
    "đại cồ việt": (21.0095, 105.8475),
    "trần đại nghĩa": (21.0025, 105.8450),
    "tạ quang bửu": (21.0045, 105.8455),
    "lê thanh nghị": (21.0035, 105.8435),
    "minh khai": (20.9980, 105.8620),
    "times city": (20.9960, 105.8675),
    "lò đúc": (21.0155, 105.8570),
    "lê văn hưu": (21.0182, 105.8532),
    "tô hiến thành": (21.0135, 105.8505),
    "triệu việt vương": (21.0170, 105.8495),
    "bùi thị xuân": (21.0165, 105.8485),
    "trần khát chân": (21.0075, 105.8565),
    # Thanh Xuân
    "nguyễn trãi": (20.9942, 105.8080),
    "công viên thanh xuân": (20.9992, 105.8005),
    "triều khúc": (20.9850, 105.7995),
    "phùng khoang": (20.9885, 105.7925),
    "royal city": (21.0030, 105.8155),
    "lê trọng tấn": (20.9985, 105.8280),
    "lê văn lương": (21.0065, 105.8055),
    "khuất duy tiến": (20.9985, 105.7945),
    "ngụy như kon tum": (20.9995, 105.8030),
    "hoàng văn thái": (20.9990, 105.8235),
    "vương thừa vũ": (21.0010, 105.8220),
    "khương đình": (20.9895, 105.8110),
    "quan nhân": (21.0020, 105.8095),
    "nguyễn tuân": (20.9980, 105.8035),
    "hoàng đạo thúy": (21.0075, 105.8035),
    "tô vĩnh diện": (20.9985, 105.8210),
    # Hà Đông
    "vạn phúc": (20.9774, 105.7768),
    "mỗ lao": (20.9820, 105.7840),
    "aeon mall hà đông": (20.9840, 105.7535),
    "văn quán": (20.9765, 105.7915),
    "yên nghĩa": (20.9525, 105.7485),
    "quang trung": (20.9650, 105.7680),
    # Nam Từ Liêm & Bắc Từ Liêm
    "mỹ đình": (21.0205, 105.7640),
    "đỗ đình thiện": (21.0165, 105.7755),
    "mễ trì": (21.0140, 105.7790),
    "smart city": (21.0035, 105.7430),
    "công viên hòa bình": (21.0645, 105.7895),
    "phạm văn đồng": (21.0550, 105.7820),
    "xuân đỉnh": (21.0690, 105.7890),
    "đông ngạc": (21.0870, 105.7750),
    "tây tựu": (21.0630, 105.7360),
    # Hoàng Mai & Long Biên
    "yên sở": (20.9695, 105.8565),
    "linh đàm": (20.9660, 105.8285),
    "giải phóng": (20.9880, 105.8410),
    "định công": (20.9850, 105.8320),
    "aeon mall long biên": (21.0265, 105.9015),
    "ngọc lâm": (21.0450, 105.8680),
    "gia thụy": (21.0525, 105.8810),
    "bồ đề": (21.0370, 105.8710),
    "nguyễn văn cừ": (21.0480, 105.8750),
}

_PROSE_VERBS = (
    "là một", "nằm tại", "mang đến", "tọa lạc", "nổi tiếng", "sở hữu",
    "được bài trí", "được chế biến", "mang đậm", "là điểm đến", "là quán",
    "thực đơn", "không gian", "quán nhỏ", "quán có", "nhà hàng", "đánh thức",
)


def remove_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u200b-\u200d\ufeff\xa0]", " ", text)
    text = text.replace("–", "-").replace("—", "-").replace("“", '"').replace("”", '"')
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text


def standardize_district(raw_district: str, raw_desc: str = "") -> str:
    for text in (clean_text(raw_district), clean_text(raw_desc)):
        if not text:
            continue
        norm = remove_accents(text).lower()
        for key, standard_name in DISTRICT_MAP.items():
            if re.search(r"\b" + re.escape(key) + r"\b", norm):
                return standard_name
    cleaned = clean_text(raw_district)
    return cleaned if cleaned else "Hà Nội"


def map_category_code(category: str, name: str = "", desc: str = "") -> str:
    """Ánh xạ category text sang đúng 7 mã category_code chuẩn của Web & RAG."""
    cat_l = clean_text(category).lower()
    name_l = clean_text(name).lower()
    desc_l = clean_text(desc).lower()
    combined = f"{cat_l} {name_l}"

    if any(k in combined for k in ["thể thao", "bể bơi", "hồ bơi", "bơi lội", "sân vận động", "jump arena", "leo núi", "bowling"]):
        return "the-thao"

    if any(k in cat_l for k in ["tâm linh", "đền", "chùa", "phủ", "miếu"]) or re.search(
        r"\b(?:chùa|đền|miếu|phủ|thiền viện|nhà thờ lớn)\b", name_l
    ):
        return "tam-linh"

    if any(k in cat_l for k in ["bảo tàng", "di tích", "di sản", "khảo cổ", "làng cổ", "kiến trúc"]):
        return "di-tich"

    if any(k in cat_l for k in ["rạp chiếu phim", "thủy cung", "trung tâm thương mại", "khu vui chơi", "giải trí", "biểu diễn", "sân khấu", "workshop", "triển lãm", "mua sắm", "chợ đêm", "chợ truyền thống"]):
        return "giai-tri"

    if any(k in cat_l for k in ["công viên", "hồ điều hòa", "cảnh quan", "dã ngoại", "cắm trại", "sinh thái", "phố đi bộ", "làng hoa", "vườn thú", "vườn hoa", "làng nghề", "ngắm cảnh", "chụp ảnh"]):
        return "ngoai-troi"

    # Phân loại lại các quán bia hơi / quán nhậu / lẩu nướng từng bị gắn nhầm 'Quán nước' sang 'an-uong'
    if re.search(r"\b(?:bia|beer|brewery|quán nhậu|nhậu|lẩu|nướng)\b", name_l) and not any(
        k in name_l for k in ["cà phê", "cafe", "coffee", "trà sữa", "trà chanh"]
    ):
        return "an-uong"

    if any(k in cat_l for k in ["quán nước", "cà phê", "cafe", "coffee", "trà"]) or any(
        k in name_l for k in ["cà phê", "cafe", "coffee", "roastery", "trà chanh", "trà sữa"]
    ):
        return "ca-phe"

    if any(k in cat_l for k in ["quán ăn", "ẩm thực", "nhà hàng"]):
        return "an-uong"

    if any(k in desc_l for k in ["cà phê", "đồ uống", "trà sữa"]):
        return "ca-phe"
    return "an-uong"


def _looks_like_address(candidate: str) -> bool:
    c = candidate.strip(" .,-:;/")
    if not c or len(c) < 5 or len(c) > 150:
        return False
    c_l = c.lower()
    if any(v in c_l for v in _PROSE_VERBS):
        return False
    return bool(
        re.search(r"(?i)^(?:số|ngõ|ngách|lô|tầng|kđt|tttm|kiot|phố|đường|p\.|q\.|\d+[\w/\-]*)", c)
        or "hà nội" in c_l
        or "quận" in c_l
        or "phường" in c_l
        or "," in c
        or any(kw in c_l for kw in KNOWN_LOCATION_COORDINATES)
    )


def _finalize_address(addr: str, district: str) -> str:
    addr = clean_text(addr).strip(" ,.;:-/")
    addr = re.sub(r"(?i)^(địa chỉ|thông tin liên hệ)\s*:?\s*", "", addr).strip(" ,.;:-/")
    addr = re.sub(r"(?i)\s*(?:https?://\S+.*|\bhttps?\b.*|\+\d[\d\s\-]{5,}.*|(?:sđt|điện thoại|hotline)\s*:.*)$", "", addr)
    addr = re.sub(r"(?i),?\s*\b100000\b", "", addr)
    addr = re.sub(r"(?i),?\s*\bViệt Nam\b", "", addr)
    addr = re.sub(r"(?i)\bTP\.?\s*Hà Nội\b", "Hà Nội", addr)
    addr = re.sub(r"\s*,\s*,+", ", ", addr).strip(" ,.;:-")
    if not addr:
        return f"Quận {district}, Hà Nội" if district != "Hà Nội" else "Hà Nội"
    addr_l = addr.lower()
    dist_l = district.lower()
    if district != "Hà Nội" and dist_l not in addr_l:
        if "hà nội" in addr_l:
            addr = re.sub(r"(?i),?\s*hà nội\s*$", f", Quận {district}, Hà Nội", addr)
        else:
            addr = f"{addr}, Quận {district}, Hà Nội"
    elif "hà nội" not in addr.lower():
        addr = f"{addr}, Hà Nội"
    return clean_text(addr).strip(" ,.")


def extract_address(name: str, raw_desc: str, district: str) -> Tuple[str, Optional[str]]:
    """
    Trích xuất địa chỉ cụ thể từ description (ưu tiên) hoặc từ phần sau dấu '-' của name.
    Trả về (địa_chỉ_chuẩn, đoạn_header_đã_tách_để_loại_khỏi_description).
    """
    desc_c = clean_text(raw_desc)
    name_c = clean_text(name)

    # 1. Tìm cụm "Địa chỉ: ..." (dừng ngay sau ', Hà Nội(, Việt Nam)' hoặc trước các nhãn giờ/giá/món/fb/sđt)
    stop_markers = r"(?=\b(?:Giờ\s*(?:mở\s*cửa|hoạt\s*động)|Thời\s*gian\s*mở\s*cửa|Giá\s*tham\s*khảo|Giá\s*thành|Mức\s*giá|Món\s*ngon\s*gợi\s*ý|Vị\s*trí\s*và\s*không\s*gian|Website(?:\s*/\s*Fanpage)?|Fanpage|Facebook|Hotline|Số\s*điện\s*thoại|SĐT|Điện\s*thoại)\b|$)"
    m_explicit_hn = re.search(r"(?i)(?:Thông tin liên hệ\s*)?Địa chỉ\s*:\s*(.{6,130}?,\s*(?:TP\.?\s*)?Hà Nội(?:\s*,\s*Việt Nam)?)", desc_c)
    if m_explicit_hn:
        cand = m_explicit_hn.group(1).strip(" .,:;-/")
        if _looks_like_address(cand):
            return _finalize_address(cand, district), m_explicit_hn.group(0)

    m_explicit = re.search(rf"(?i)(?:Thông tin liên hệ\s*)?Địa chỉ\s*:\s*(.+?){stop_markers}", desc_c)
    if m_explicit:
        cand = m_explicit.group(1).strip(" .,:;-/")
        if _looks_like_address(cand):
            return _finalize_address(cand, district), m_explicit.group(0)

    # 2. Phần đầu câu có "Thông tin liên hệ <địa chỉ>" hoặc "<Phố, Phường, Quận, Hà Nội> Giờ mở cửa/Giá..."
    m_contact = re.search(rf"(?i)^Thông tin liên hệ\s+(.+?){stop_markers}", desc_c)
    if m_contact:
        cand = m_contact.group(1).strip(" .,:;-/")
        if _looks_like_address(cand):
            return _finalize_address(cand, district), m_contact.group(0)

    m_head = re.search(
        r"^(.{8,140}?)\s*(?=\b(?:Giờ\s*(?:mở\s*cửa|hoạt\s*động)|Thời\s*gian\s*mở\s*cửa|Giá\s*tham\s*khảo|Giá\s*thành|Món\s*ngon\s*gợi\s*ý|Website(?:\s*/\s*Fanpage)?)\b)",
        desc_c,
        flags=re.IGNORECASE,
    )
    if m_head:
        cand = m_head.group(1).strip(" .,:;-/")
        if _looks_like_address(cand):
            return _finalize_address(cand, district), cand

    # 3. Tên quán có dạng "Tên Quán - Số 51 Giang Văn Minh" hoặc "Facebook TÊN QUÁN - 122 Phan Kế Bính"
    if " - " in name_c:
        right = name_c.split(" - ", 1)[1].strip()
        if _looks_like_address(right) and (
            re.match(r"^(?:số\s+|ngõ\s+|lô\s+|tầng\s+|\d+)", right.lower())
            or any(kw in right.lower() for kw in KNOWN_LOCATION_COORDINATES)
        ):
            return _finalize_address(right, district), None

    m_fb_addr = re.search(r"(?i)Facebook\s+[^-.\n]+-\s*(\d+[^.,\n]{4,60})", desc_c)
    if m_fb_addr:
        cand = m_fb_addr.group(1).strip()
        if _looks_like_address(cand):
            return _finalize_address(cand, district), None

    # 4. Đối chiếu tên tuyến phố / địa danh nổi tiếng trong tên địa điểm
    name_l = name_c.lower()
    for kw in sorted(KNOWN_LOCATION_COORDINATES.keys(), key=len, reverse=True):
        if kw in name_l:
            display_kw = re.sub(r"\bAeon\b", "AEON", kw.title())
            if any(x in kw for x in ["hồ", "chùa", "lăng", "văn miếu", "công viên", "hoàng thành", "aeon", "royal", "times", "vincom", "quán thánh", "phủ"]):
                return _finalize_address(display_kw, district), None
            return _finalize_address(f"Khu vực {display_kw}", district), None

    return _finalize_address("", district), None


def standardize_price(price_str: str, raw_desc: str = "") -> str:
    text = clean_text(price_str)
    if not text and raw_desc:
        m = re.search(r"(?i)Giá\s*tham\s*khảo\s*:\s*([^.\n]+)", clean_text(raw_desc))
        if m:
            text = m.group(1).strip()
    if not text:
        return "Tham khảo"
    text = re.sub(r"\b(vnd|vnđ|đ)\b", "VNĐ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*-\s*", " - ", text)
    return text


def standardize_hours(hours_str: str, raw_desc: str = "") -> str:
    text = clean_text(hours_str)
    if not text and raw_desc:
        m = re.search(r"(?i)Giờ\s*(?:mở\s*cửa|hoạt\s*động)\s*:\s*([^.\n]+)", clean_text(raw_desc))
        if m:
            text = m.group(1).strip()
    if not text:
        return "08:00 - 22:00"
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    return text


def standardize_tags(tag_str: str, default_val: str, rules=None, context_text: str = "") -> str:
    text = clean_text(tag_str)
    if not text and rules and context_text:
        ctx_lower = context_text.lower()
        matched = [label for keywords, label in rules if any(kw in ctx_lower for kw in keywords)]
        if matched:
            return ", ".join(matched)
    if not text:
        return default_val

    parts = [p.strip() for p in text.split(",") if p.strip()]
    seen = set()
    unique_parts = []
    for p in parts:
        p_cap = p[0].upper() + p[1:] if len(p) > 1 else p.upper()
        if p_cap.lower() not in seen:
            seen.add(p_cap.lower())
            unique_parts.append(p_cap)
    return ", ".join(unique_parts) if unique_parts else default_val


def clean_description(
    desc_str: str,
    extracted_prefix: Optional[str],
    name: str,
    category: str,
    district: str,
    opening_hours: str,
    price_range: str,
) -> str:
    text = clean_text(desc_str)
    if text:
        if extracted_prefix and extracted_prefix in text:
            text = text.replace(extracted_prefix, " ", 1).strip()

        noise_patterns = [
            r"(?i)\bThông tin liên hệ\s*:?\s*",
            r"(?i)\bĐịa chỉ\s*:\s*[^.\n]+?(?=\b(?:Giờ|Thời gian|Giá|Khoảng giá|Mức giá|Số điện thoại|Vị trí và không gian|Facebook|Website|Fanpage|Hotline|Món|Thực đơn)\b|$)",
            r"(?i)\b(?:Giờ\s*(?:mở\s*cửa|hoạt\s*động)|Thời\s*gian\s*mở\s*cửa)\s*:?\s*(?:(?:\d{1,2}[:hH]\d{0,2}\s*(?:-|đến)\s*\d{1,2}[:hH]\d{0,2}|24/24|24/7|cả ngày)(?:\s*(?:\||và|,)\s*)?)+\.?",
            r"(?i)\b(?:Giá\s*tham\s*khảo|Giá\s*thành|Mức\s*giá|Khoảng\s*giá)\s*:?\s*(?:Khoảng\s*)?[\d\.,]+\s*(?:đồng|vnđ|vnd|đ|k)?(?:\s*(?:-|đến)\s*[\d\.,]+\s*(?:đồng|vnđ|vnd|đ|k)?)?(?:\s*/\s*(?:suất|người|bát|vé|món|phần|ly|cốc))?(?:\s*từ thứ \d+ đến Chủ nhật)?(?:\s*\([^)]*giá tham khảo[^)]*\))?\.?",
            r"(?i)\bQuán ăn chất lượng\s*:\s*[\d.,]+\s*/\s*5\s*(?:\([^)]+\))?",
            r"(?i)\bĐánh giá(?:\s+trên Google)?\s*:?\s*[\d.,]+\s*/\s*5(?:\s*sao)?(?:\s*\([^)]+\))?\.?",
            r"(?i)\(\s*Thường đông khách lúc [^)]+\)",
            r"(?i)\(\s*Ảnh\s*:[^)]+\)",
            r"(?i)(?:https?://)?(?:www\.)?facebook\.com/\S+",
            r"(?i)\bWebsite(?:\s*/\s*Fanpage)?\s*:\s*\S+",
            r"(?i)\bFanpage\s*:\s*\S+",
            r"(?i)\b(?:Số\s*điện\s*thoại|Hotline|SĐT)\s*:\s*(?:Đang cập nhật|[\d\s.\-+()]+)",
            r"(?i)\bĐiện thoại\s+Chỉ đường(?:\s+Website)?",
            r"(?i)\bWebsite\s+Facebook\b",
            r"(?i)\bGiao hàng\s*:\s*(?:Không|Có(?:\s*\([^)]+\))?)",
            r"[Ff]acebook\s*:\s*[^.\n(\)]{2,70}?(?:\(\s*|\.\s+|(?=\s+(?:Quán|Nhà hàng|Nếu bạn|Ngoài|Menu|[A-ZÀ-Ỹ][a-zà-ỹ]{1,15}\s+(?:là|có|nằm|tại|mang|nổi tiếng|chuyên|được|luôn|với|sở hữu))\b)|$)",
            r"(?i)\bVị trí và không gian\s*:\s*",
            r"(?i)^(?:\s*/\s*(?:suất|người|bát|vé|món|phần))+\s*",
        ]
        for pat in noise_patterns:
            text = re.sub(pat, " ", text)

        # Gỡ cụm "Facebook <TÊN QUÁN VIẾT HOA - ĐỊA CHỈ>" dính liền trước câu mô tả viết hoa chữ đầu (case-sensitive)
        text = re.sub(r"[Ff]acebook\s+[A-ZÀ-Ỹ0-9\s\-&']{4,65}(?=[A-ZÀ-Ỹ][a-zà-ỹ])", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" ,.;:-/")
        text = re.sub(r"\s+([.,;:])", r"\1", text)

    if not text or len(text) < 12:
        dist_txt = f"quận {district}" if district != "Hà Nội" else "Hà Nội"
        text = (
            f"{name} là địa điểm thuộc nhóm {category} tại {dist_txt}, Hà Nội. "
            f"Giờ mở cửa tham khảo: {opening_hours}, mức giá: {price_range}."
        )
    return text


def _deterministic_offset(seed_text: str, max_delta: float) -> Tuple[float, float]:
    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()
    lat_val = int(digest[:4], 16) / 65535.0
    lng_val = int(digest[4:8], 16) / 65535.0
    return (
        round((lat_val - 0.5) * 2 * max_delta, 6),
        round((lng_val - 0.5) * 2 * max_delta, 6),
    )


def enrich_coordinates(place_id: str, name: str, address: str, district: str) -> Tuple[float, float]:
    combined = f"{name} {address}".lower()
    matched: Optional[Tuple[float, float]] = None
    for kw in sorted(KNOWN_LOCATION_COORDINATES.keys(), key=len, reverse=True):
        if kw in combined:
            matched = KNOWN_LOCATION_COORDINATES[kw]
            break

    if matched:
        d_lat, d_lng = _deterministic_offset(place_id or combined, max_delta=0.003)
        return round(matched[0] + d_lat, 6), round(matched[1] + d_lng, 6)

    centroid = DISTRICT_CENTROIDS.get(district, DISTRICT_CENTROIDS["Hoàn Kiếm"])
    d_lat, d_lng = _deterministic_offset(place_id or combined, max_delta=0.007)
    return round(centroid[0] + d_lat, 6), round(centroid[1] + d_lng, 6)


def generate_search_tags(
    name: str,
    category: str,
    category_code: str,
    district: str,
    address: str,
    opening_hours: str,
    suitable_for: str,
    weather_fit: str,
    raw_desc: str,
) -> List[str]:
    tags: List[str] = []
    seen = set()

    def add_tag(val: str):
        v = clean_text(val).strip(" ,.;:-").lower()
        if v and len(v) >= 2 and v not in seen:
            seen.add(v)
            tags.append(v)

    add_tag(district)
    add_tag(category_code)
    for part in re.split(r"[/,]", category):
        add_tag(part)
    for part in re.split(r"[,/]", suitable_for):
        add_tag(part)
    for part in re.split(r"[,/]", weather_fit):
        add_tag(part)

    # Từ khóa đường phố / khu vực khớp được
    combined_loc = f"{name} {address}".lower()
    for kw in sorted(KNOWN_LOCATION_COORDINATES.keys(), key=len, reverse=True):
        if kw in combined_loc:
            add_tag(kw)
            break

    # Khung giờ đêm muộn / 24/7
    hours_l = opening_hours.lower()
    if any(k in hours_l for k in ["24/7", "24/24", "00:00", "01:00", "02:00", "03:00", "04:00", "1:00", "2:00"]):
        add_tag("mở khuya")
    if "24/7" in hours_l or "24/24" in hours_l:
        add_tag("24/7")

    # Món ăn đặc trưng từ "Món ngon gợi ý: ..."
    m_dish = re.search(r"(?i)Món\s*ngon\s*gợi\s*ý\s*:\s*([^.\n]+)", clean_text(raw_desc))
    if m_dish:
        for dish in m_dish.group(1).split(",")[:4]:
            add_tag(dish)

    # Từ khóa đặc thù từ tên địa điểm
    for kw in ["bún", "phở", "lẩu", "nướng", "ốc", "bánh mì", "bánh cuốn", "cơm", "chè", "xôi",
               "cà phê", "cafe", "trà sữa", "trà chanh", "chùa", "đền", "bảo tàng", "công viên",
               "hồ", "rạp", "cgv", "aeon", "vincom", "thủy cung", "chay", "hải sản"]:
        if kw in name.lower():
            add_tag(kw)

    return tags[:12]


def build_dedup_key(name: str, district: str, raw_desc: str) -> Tuple[str, str, str]:
    name_norm = re.sub(r"\W+", "", remove_accents(name).lower())
    dist_norm = re.sub(r"\W+", "", remove_accents(district).lower())
    desc_clean = clean_text(raw_desc)
    addr_part = re.split(r"(?i)\b(giờ mở cửa|giá tham khảo|món ngon)\b", desc_clean)[0]
    addr_norm = re.sub(r"\W+", "", remove_accents(addr_part[:70]).lower())
    return (name_norm, dist_norm, addr_norm)


def discover_raw_files() -> List[Tuple[str, str]]:
    """Quét và loại trùng tên file thô giữa crawler_1/crawler_2 và các thư mục fallback."""
    raw_files: List[Tuple[str, str]] = []
    seen_filenames = set()
    for raw_dir in RAW_DIRS:
        if not os.path.exists(raw_dir):
            continue
        for fname in sorted(os.listdir(raw_dir)):
            if fname.endswith(".json") and fname not in seen_filenames:
                seen_filenames.add(fname)
                raw_files.append((fname, os.path.join(raw_dir, fname)))
    return raw_files


def run_preprocessing():
    raw_files = discover_raw_files()
    if not raw_files:
        print("[X] Không tìm thấy file .json nào trong các thư mục raw.")
        return

    weather_rules = [
        (["vỉa hè", "ngoài trời", "sân vườn", "ban công", "rooftop"], "Ngoài trời"),
        (["điều hòa", "máy lạnh", "trong nhà", "phòng lạnh"], "Trong nhà"),
    ]
    suitable_rules = [
        (["gia đình", "trẻ em", "người lớn tuổi"], "Gia đình"),
        (["cặp đôi", "lãng mạn", "hẹn hò"], "Cặp đôi"),
        (["nhóm bạn", "tụ tập", "liên hoan", "sinh nhật"], "Nhóm bạn"),
        (["một mình", "làm việc", "yên tĩnh", "đọc sách"], "Solo"),
    ]

    all_cleaned_records: List[Dict] = []
    seen_keys = set()
    global_id_counter = 1
    total_raw = 0

    print("\n" + "=" * 60)
    print(f"[*] ĐANG GỘP VÀ TIỀN XỬ LÝ {len(raw_files)} FILE DỮ LIỆU THÔ")
    print("=" * 60)

    for filename, raw_path in raw_files:
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        file_valid_count = 0
        removed_dup = 0
        removed_empty = 0

        for item in raw_data:
            name = clean_text(item.get("name", ""))
            if not name:
                removed_empty += 1
                continue

            raw_desc = item.get("description", "")
            district = standardize_district(item.get("district", ""), raw_desc)

            dedup_key = build_dedup_key(name, district, raw_desc)
            if dedup_key in seen_keys:
                removed_dup += 1
                continue
            seen_keys.add(dedup_key)

            place_id = f"hn_loc_{global_id_counter:03d}"
            category = clean_text(item.get("category", "")) or "Khác"
            category_code = map_category_code(category, name, raw_desc)
            opening_hours = standardize_hours(item.get("opening_hours", ""), raw_desc)
            price_range = standardize_price(item.get("price_range", ""), raw_desc)

            address, extracted_prefix = extract_address(name, raw_desc, district)
            desc_cleaned = clean_description(
                raw_desc,
                extracted_prefix=extracted_prefix,
                name=name,
                category=category,
                district=district,
                opening_hours=opening_hours,
                price_range=price_range,
            )

            suitable_for = standardize_tags(
                item.get("suitable_for", ""),
                default_val="Mọi đối tượng",
                rules=suitable_rules,
                context_text=desc_cleaned,
            )
            weather_fit = standardize_tags(
                item.get("weather_fit", ""),
                default_val="Trong nhà / Ngoài trời",
                rules=weather_rules,
                context_text=desc_cleaned,
            )
            lat, lng = enrich_coordinates(place_id, name, address, district)
            tags = generate_search_tags(
                name=name,
                category=category,
                category_code=category_code,
                district=district,
                address=address,
                opening_hours=opening_hours,
                suitable_for=suitable_for,
                weather_fit=weather_fit,
                raw_desc=raw_desc,
            )

            all_cleaned_records.append({
                "id": place_id,
                "name": name,
                "category": category,
                "category_code": category_code,
                "district": district,
                "address": address,
                "opening_hours": opening_hours,
                "price_range": price_range,
                "suitable_for": suitable_for,
                "weather_fit": weather_fit,
                "description": desc_cleaned,
                "latitude": lat,
                "longitude": lng,
                "tags": tags,
            })
            global_id_counter += 1
            file_valid_count += 1

        total_raw += len(raw_data)
        print(f" -> {filename}: Thô {len(raw_data)} | Trùng/rỗng {removed_dup + removed_empty} | Giữ lại {file_valid_count}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(all_cleaned_records, f, ensure_ascii=False, indent=4)

    print("-" * 60)
    print(f"[✓] HOÀN TẤT TIỀN XỬ LÝ & LÀM GIÀU 14 TRƯỜNG: {len(all_cleaned_records)}/{total_raw} bản ghi hợp lệ")
    print(f"[✓] Mã ID liên tục: hn_loc_001 -> hn_loc_{global_id_counter - 1:03d}")
    print(f"[✓] Đã lưu tại: {OUTPUT_DATA_PATH}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_preprocessing()
