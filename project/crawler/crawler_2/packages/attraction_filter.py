import re

ATTRACTION_KEYWORDS = [
    "công viên", "hồ", "bảo tàng", "di tích", "đền", "chùa", "phủ", "nhà tù",
    "hoàng thành", "văn miếu", "khu vui chơi", "thủy cung", "rạp chiếu phim",
    "phố đi bộ", "trung tâm thương mại", "vincom", "lotte", "aeon", "tổ hợp",
    "cắm trại", "camping", "trượt băng", "bowling", "escape room", "skydeck"
]

EXCLUDE_KEYWORDS = [
    "quán ăn", "nhà hàng", "quán bún", "quán phở", "lẩu", "nướng", "trà sữa",
    "cơm bình dân", "tiệm bánh", "quán nhậu", "sửa xe"
]

def is_valid_attraction(title: str, category: str = "", description: str = "") -> bool:
    content = f"{title} {category} {description}".lower()
    
    # Bỏ qua nếu là quán ăn đơn thuần
    if any(re.search(r"\b" + exc + r"\b", content) for exc in EXCLUDE_KEYWORDS):
        # Nhanh chóng loại trừ ngoại trừ các tổ hợp lớn có chứa nhà hàng
        if not any(kw in content for kw in ["tổ hợp", "khu vui chơi", "trung tâm thương mại"]):
            return False
        
    # Giữ lại nếu chứa từ khóa địa điểm vui chơi
    return any(re.search(r"\b" + kw + r"\b", content) for kw in ATTRACTION_KEYWORDS)