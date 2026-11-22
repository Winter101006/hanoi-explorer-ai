import os
import json
import time
import re
from bs4 import BeautifulSoup
from packages.selenium_handler import init_driver
from packages.attraction_filter import is_valid_attraction
from packages.logging_handler import setup_logger

logger = setup_logger("attraction_crawler")

DATA_DIR = "data/links"
OUTPUT_FILE = "data/raw/hanoi_attractions.json"

def infer_weather_fit(title: str, description: str) -> str:
    """Suy luận thuộc tính weather_fit: Trong nhà / Ngoài trời / Cả hai"""
    content = f"{title} {description}".lower()
    indoor_kw = ["bảo tàng", "rạp chiếu phim", "trung tâm thương mại", "tttm", "vincom", "lotte", "aeon", "bowling", "escape room", "triển lãm", "thủy cung"]
    outdoor_kw = ["công viên", "hồ", "phố đi bộ", "di tích", "đền", "chùa", "cắm trại", "camping", "hoàng thành", "văn miếu", "chợ đêm"]
    
    is_indoor = any(kw in content for kw in indoor_kw)
    is_outdoor = any(kw in content for kw in outdoor_kw)
    
    if is_indoor and is_outdoor:
        return "Trong nhà / Ngoài trời"
    elif is_indoor:
        return "Trong nhà"
    elif is_outdoor:
        return "Ngoài trời"
    return "Trong nhà / Ngoài trời"

def infer_suitable_for(title: str, description: str) -> str:
    """Suy luận thuộc tính suitable_for"""
    content = f"{title} {description}".lower()
    targets = []
    
    if any(kw in content for kw in ["trẻ em", "gia đình", "công viên", "thủy cung", "bảo tàng"]):
        targets.append("Gia đình")
    if any(kw in content for kw in ["cặp đôi", "hẹn hò", "lãng mạn", "cafe", "hồ", "skydeck"]):
        targets.append("Cặp đôi")
    if any(kw in content for kw in ["nhóm bạn", "tổ hợp", "bowling", "escape room", "vui chơi", "chợ đêm", "phố đi bộ"]):
        targets.append("Nhóm bạn")
    if any(kw in content for kw in ["dạo bộ", "sách", "yên tĩnh", "solo"]):
        targets.append("Solo")
        
    if not targets:
        return "Gia đình, Cặp đôi, Nhóm bạn"
    return ", ".join(targets)

def parse_attractions_from_article(driver, url, district_name, start_index):
    """
    Bóc tách từng địa điểm vui chơi giải trí trong bài viết tổng hợp
    """
    driver.get(url)
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    extracted_items = []
    current_index = start_index

    # Tìm các thẻ tiêu đề địa điểm trong bài viết (thường là h2 hoặc h3)
    headings = soup.find_all(["h2", "h3"])
    
    # Danh sách các cụm từ loại trừ trực tiếp quán ăn/nhà hàng
    food_keywords = ["quán", "nhà hàng", "bún", "phở", "lẩu", "nướng", "ẩm thực", "ăn uống", "trà sữa", "bánh"]

    for heading in headings:
        name = heading.get_text(strip=True)
        
        # Lọc bỏ tiêu đề rác hoặc danh mục chung
        if len(name) < 5 or any(k in name.lower() for k in ["lưu ý", "tổng kết", "kinh nghiệm", "hướng dẫn", "mục lục"]):
            continue

        # LOẠI BỎ QUÁN ĂN / NHÀ HÀNG
        if any(f_kw in name.lower() for f_kw in food_keywords):
            # Nếu có chứa từ khóa vui chơi lớn thì giữ lại (VD: Tổ hợp giải trí & Nhà hàng)
            if not any(v_kw in name.lower() for v_kw in ["công viên", "tổ hợp", "trung tâm thương mại", "khu vui chơi"]):
                continue

        # Lấy phần mô tả bên dưới tiêu đề địa điểm
        description_parts = []
        curr = heading.find_next_sibling()
        while curr and curr.name not in ["h2", "h3"]:
            if curr.name in ["p", "ul", "ol"]:
                text = curr.get_text(strip=True)
                if text:
                    description_parts.append(text)
            curr = curr.find_next_sibling()
            
        description = " ".join(description_parts)
        
        # Kiểm tra xem có phải địa điểm vui chơi/tham quan/check-in không
        if not is_valid_attraction(name, "", description):
            continue

        # Trích xuất Giờ mở cửa & Giá vé từ đoạn mô tả (nếu có)
        opening_hours = "08:00 - 22:00"
        time_match = re.search(r"(\d{1,2}h\d{0,2}\s*-\s*\d{1,2}h\d{0,2}|\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})", description)
        if time_match:
            opening_hours = time_match.group(0)

        price_range = "Miễn phí / Tùy hoạt động"
        price_match = re.search(r"(\d+[\d\.]*\s*(?:k|đ|vnd|ngàn|nghìn)?\s*-\s*\d+[\d\.]*\s*(?:k|đ|vnd|ngàn|nghìn)?)", description, re.IGNORECASE)
        if price_match:
            price_range = price_match.group(0)

        # Tạo Schema 9 trường chuẩn
        item_data = {
            "id": f"hn_loc_{current_index:03d}",
            "name": name,
            "district": district_name,
            "category": "Địa điểm vui chơi / Tham quan",
            "opening_hours": opening_hours,
            "price_range": price_range,
            "suitable_for": infer_suitable_for(name, description),
            "weather_fit": infer_weather_fit(name, description),
            "description": description if description else f"Địa điểm vui chơi giải trí nổi tiếng tại quận {district_name}."
        }

        extracted_items.append(item_data)
        current_index += 1

    return extracted_items, current_index

def main():
    driver = init_driver(headless=True)
    all_attractions = []
    global_counter = 1

    district_map = {
        "cau_giay": "Cầu Giấy", "hoan_kiem": "Hoàn Kiếm", "ba_dinh": "Ba Đình",
        "tay_ho": "Tây Hồ", "dong_da": "Đống Đa", "hai_ba_trung": "Hai Bà Trưng",
        "thanh_xuan": "Thanh Xuân", "ha_dong": "Hà Đông", "nam_tu_liem": "Nam Từ Liêm",
        "bac_tu_liem": "Bắc Từ Liêm", "hoang_mai": "Hoàng Mai", "long_bien": "Long Biên"
    }

    if not os.path.exists(DATA_DIR):
        logger.error(f"Thư mục {DATA_DIR} không tồn tại!")
        return

    link_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".txt")]

    for file_name in link_files:
        raw_district = file_name.replace(".txt", "")
        district_display = district_map.get(raw_district, raw_district.title())
        file_path = os.path.join(DATA_DIR, file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]

        for url in urls:
            logger.info(f"Đang bóc tách các địa điểm từ: {url}")
            items, global_counter = parse_attractions_from_article(driver, url, district_display, global_counter)
            
            for item in items:
                all_attractions.append(item)
                logger.info(f"  + Đã lấy thành công [{item['id']}]: {item['name']}")

    driver.quit()

    # Xuất file JSON chuẩn Schema
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_attractions, f, ensure_ascii=False, indent=4)

    logger.info(f"Hoàn thành! Đã thu thập tổng cộng {len(all_attractions)} địa điểm vui chơi giải trí (Không bao gồm quán ăn).")

if __name__ == "__main__":
    main()