import os
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from packages.selenium_handler import init_driver
from packages.logging_handler import setup_logger

logger = setup_logger("links_crawler")

OUTPUT_DIR = "data/links"

# Sử dụng trang nguồn ổn định hỗ trợ tìm kiếm địa điểm du lịch/vui chơi theo quận
DISTRICT_CATEGORY_URLS = {
    "ba_dinh": "https://justfly.vn/discovery/vietnam/hanoi/dia-diem-du-lich-quan-ba-dinh",
    "bac_tu_liem": "https://paracelresort.com/top-13-dia-diem-du-lich-quan-bac-tu-liem-di-dau-choi-gi-ghep-lich-the-nao-cho-hop-ly/",
    "cau_giay": "https://paracelresort.com/top-15-dia-diem-du-lich-quan-cau-giay-di-dau-choi-gi-nen-ghep-tuyen-nao-cho-tien/",
    "dong_da": "https://justfly.vn/discovery/vietnam/hanoi/dia-diem-du-lich-dong-da",
    "ha_dong": "https://paracelresort.com/top-10-dia-diem-du-lich-quan-ha-dong-di-dau-choi-an-gi-chon-diem-nao-hop-nhat/",
    "hai_ba_trung": "https://paracelresort.com/top-12-dia-diem-du-lich-quan-hai-ba-trung-di-dau-choi-gi-ghe-the-nao-cho-dang-cong/",
    "hoan_kiem": "https://justfly.vn/discovery/vietnam/hanoi/dia-diem-du-lich-quan-hoan-kiem",
    "hoang_mai": "https://paracelresort.com/top-10-dia-diem-du-lich-quan-hoang-mai-di-dau-choi-gi-nen-ghe-luc-nao/",
    "long_bien": "https://paracelresort.com/top-12-dia-diem-du-lich-quan-long-bien-di-dau-choi-gi-ghe-luc-nao-la-hop-ly-nhat/",
    "nam_tu_liem": "https://thuexegianggia.com/top-5-dia-diem-du-lich-vui-choi-o-nam-tu-liem/",
    "tay_ho": "https://justfly.vn/discovery/vietnam/hanoi/dia-diem-du-lich-quan-tay-ho",
    "thanh_xuan": "https://quananngonhanoi.com/top-6-quan-bun-cha-ngon-thanh-xuan-ban-do-am-thuc-di-la-ghien/"
}

def crawl_and_save_links():
    driver = init_driver(headless=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for district_key, category_url in DISTRICT_CATEGORY_URLS.items():
        file_path = os.path.join(OUTPUT_DIR, f"{district_key}.txt")
        logger.info(f"Đang quét danh sách link cho quận: {district_key}")

        try:
            driver.get(category_url)
            
            # Đợi tối đa 5 giây cho đến khi các thẻ HTML chính xuất hiện
            time.sleep(3)

            # Cuộn trang 2 lần để kích hoạt lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            district_links = set()

            # Bóc tách tất cả thẻ <a> dẫn tới bài viết/địa điểm
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                # Bắt các link thuộc bài viết địa điểm tham quan/vui chơi
                if href.startswith("http") and ("cam-nang" in href or "dia-diem" in href or "du-lich" in href):
                    if href != category_url:  # Bỏ qua chính trang danh mục
                        district_links.add(href)
                elif href.startswith("/") and ("cam-nang" in href or "dia-diem" in href):
                    full_url = f"https://mytour.vn{href}"
                    district_links.add(full_url)

            # Ghi danh sách link thu được vào file .txt tương ứng
            with open(file_path, "w", encoding="utf-8") as f:
                for link in district_links:
                    f.write(f"{link}\n")

            logger.info(f"Đã tự động lưu {len(district_links)} link vào file {file_path}")

        except Exception as e:
            logger.error(f"Lỗi khi quét link quận {district_key}: {str(e)}")

    driver.quit()
    logger.info("Hoàn tất thu thập link cho tất cả các quận!")

if __name__ == "__main__":
    crawl_and_save_links()