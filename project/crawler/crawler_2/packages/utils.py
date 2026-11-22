import re

def clean_text(text: str) -> str:
    """
    Xóa khoảng trắng thừa và ký tự đặc biệt không cần thiết.
    """
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_price_range(text: str) -> dict:
    """
    Trích xuất khoảng giá (VND) từ văn bản mô tả giá vé.
    """
    if not text:
        return {"min_price": 0, "max_price": 0, "is_free": True}

    text_lower = text.lower()
    if "miễn phí" in text_lower or "free" in text_lower:
        return {"min_price": 0, "max_price": 0, "is_free": True}

    # Tìm các chuỗi số đại diện cho giá tiền (ví dụ: 50.000, 100k, 200.000đ)
    numbers = re.findall(r"(\d+[\d\.]*)\s*(?:k|đ|vnd|ngàn|nghìn)?", text_lower)
    parsed_prices = []

    for num in numbers:
        num_clean = num.replace(".", "")
        if num_clean.isdigit():
            val = int(num_clean)
            if val < 1000 and "k" in text_lower:  # Xử lý dạng "50k"
                val *= 1000
            parsed_prices.append(val)

    if parsed_prices:
        return {
            "min_price": min(parsed_prices),
            "max_price": max(parsed_prices),
            "is_free": False
        }

    return {"min_price": None, "max_price": None, "is_free": False}