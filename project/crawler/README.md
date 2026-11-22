# Crawler Module — Thu thập dữ liệu địa điểm Hà Nội

Mô-đun thu thập dữ liệu tự động (Web Scraping) của dự án **Hanoi Explorer Chatbot (Hanoi Explorer AI)**, chịu trách nhiệm thu thập thông tin thô của các địa điểm ẩm thực, quán cà phê, không gian giải trí, di tích lịch sử và văn hóa trên 12 quận nội thành Hà Nội.

## Purpose and structure / Mục đích và cấu trúc

Mục đích: Cung cấp nguồn dữ liệu thực tế, phong phú và đa dạng làm cơ sở cho toàn bộ hệ thống chatbot tư vấn. Dữ liệu được thu thập từ hai crawler chuyên biệt:
- `crawler_1`: Chuyên thu thập dữ liệu ẩm thực, nhà hàng, quán ăn và quán cà phê (1.375 địa điểm).
- `crawler_2`: Chuyên thu thập dữ liệu các điểm tham quan, di tích văn hóa, tâm linh, giải trí và không gian ngoài trời (317 địa điểm).

Cấu trúc thư mục chi tiết:

```text
crawler/
├── crawler_1/                         # Module thu thập địa điểm ẩm thực & cà phê
│   ├── crawl_food_details.py          # Kịch bản chính cào thông tin chi tiết từng quán ăn
│   ├── requirements.txt               # Thư viện phụ thuộc (selenium, beautifulsoup4)
│   ├── packages/                      # Các tiện ích và bộ lọc xử lý dữ liệu ẩm thực
│   │   ├── description_filter.py      # Lọc và làm sạch mô tả địa điểm
│   │   ├── food_filter.py             # Bộ lọc trích xuất danh mục và món ăn đặc trưng
│   │   ├── logging_handler.py         # Quản lý ghi log quá trình crawl
│   │   ├── selenium_handler.py        # Khởi tạo và quản lý trình duyệt Selenium WebDriver
│   │   └── utils.py                   # Tiện ích chuẩn hóa chuỗi, giá cả, giờ mở cửa
│   └── data/
│       ├── links/                     # Danh sách URL cần cào theo 12 quận (ba_dinh.txt, cau_giay.txt...)
│       └── raw/
│           └── dataset1_hanoi.json    # Kết quả thô 1.375 bản ghi quán ăn & cà phê
├── crawler_2/                         # Module thu thập điểm tham quan, di tích & giải trí
│   ├── crawl_category_links.py        # Kịch bản thu thập danh sách URL địa điểm theo danh mục
│   ├── crawl_attraction_details.py    # Kịch bản cào thông tin chi tiết các điểm tham quan
│   ├── requirements.txt               # Thư viện phụ thuộc (selenium, beautifulsoup4)
│   ├── packages/                      # Tiện ích và bộ lọc chuyên biệt
│   │   ├── attraction_filter.py       # Bộ lọc loại trừ quán ăn, giữ điểm tham quan/văn hóa
│   │   ├── logging_handler.py         # Quản lý ghi log
│   │   ├── selenium_handler.py        # Quản lý Selenium WebDriver
│   │   └── utils.py                   # Tiện ích bóc tách thông tin
│   └── data/
│       ├── links/                     # Danh sách URL 12 quận cho địa điểm vui chơi/di tích
│       └── raw/
│           └── hanoi_attractions.json # Kết quả thô 317 bản ghi điểm tham quan & di tích
└── data/
    └── raw/
        └── hanoi_attractions.json     # Bản sao dữ liệu thô phục vụ pipeline tiền xử lý
```

## Requirements and setup / Yêu cầu và cài đặt

1. **Yêu cầu hệ thống:**
   - Python 3.10 trở lên.
   - Trình duyệt Google Chrome và ChromeDriver tương ứng với phiên bản Chrome trên hệ thống.

2. **Cài đặt thư viện:**
   - Cài đặt các thư viện cần thiết cho crawler từ thư mục gốc của kho:
     ```powershell
     pip install -r project/crawler/crawler_1/requirements.txt
     ```
   - Các gói chính bao gồm `selenium` (tự động hóa điều hướng trình duyệt) và `beautifulsoup4` (bóc tách cấu trúc HTML).

## Inputs and outputs / Đầu vào và đầu ra

- **Đầu vào:**
  - Danh sách liên kết URL của các địa điểm tại Hà Nội được phân theo 12 quận nội thành, lưu trữ trong thư mục `data/links/*.txt` của từng crawler (`ba_dinh.txt`, `cau_giay.txt`, `dong_da.txt`, `hai_ba_trung.txt`, `ha_dong.txt`, `hoan_kiem.txt`, `hoang_mai.txt`, `long_bien.txt`, `nam_tu_liem.txt`, `bac_tu_liem.txt`, `tay_ho.txt`, `thanh_xuan.txt`).
  - Mỗi dòng trong tệp văn bản là một URL hợp lệ của địa điểm cần thu thập dữ liệu.
- **Đầu ra:**
  - `crawler_1/data/raw/dataset1_hanoi.json`: 1.375 bản ghi thô về nhà hàng, quán ăn, quán cà phê kèm các thông tin ban đầu (tên, địa chỉ, khoảng giá, giờ mở cửa, mô tả món ăn, đánh giá).
  - `crawler_2/data/raw/hanoi_attractions.json`: 317 bản ghi thô về địa điểm tham quan, di tích văn hóa, điểm giải trí ngoài trời (tên, danh mục, quận, địa chỉ, mô tả, tiện ích).

## Reproduce the main result / Tái tạo kết quả chính

Để chạy thu thập lại dữ liệu từ nguồn web (thực hiện từ thư mục gốc của kho lưu trữ):

1. **Thu thập danh sách URL địa điểm tham quan (crawler 2):**
   ```bash
   python project/crawler/crawler_2/crawl_category_links.py
   ```

2. **Bóc tách chi tiết dữ liệu ẩm thực & cà phê (crawler 1):**
   ```bash
   python project/crawler/crawler_1/crawl_food_details.py
   ```

3. **Bóc tách chi tiết dữ liệu điểm tham quan & giải trí (crawler 2):**
   ```bash
   python project/crawler/crawler_2/crawl_attraction_details.py
   ```

> *Ghi chú:* Toàn bộ dữ liệu thô đã được thu thập đầy đủ và lưu sẵn trong các thư mục `data/raw/`. Do đó, người dùng có thể chuyển thẳng sang bước tiền xử lý mà không cần chạy lại crawler.

## Known limitations / Giới hạn đã biết

- **Phụ thuộc cấu trúc HTML nguồn:** Quá trình trích xuất dựa trên cấu trúc DOM và bộ chọn XPath/CSS của các trang web nguồn; nếu trang nguồn thay đổi giao diện, kịch bản bóc tách có thể cần được cập nhật.
- **Tốc độ thực thi:** Do sử dụng Selenium để hiển thị và tải nội dung động qua trình duyệt thực, thời gian cào phụ thuộc vào độ trễ mạng và số lượng trang cần xử lý.
- **Dữ liệu thiếu trên trang gốc:** Một số địa điểm không công khai đầy đủ mức giá vé hoặc thời gian mở cửa cụ thể trên website gốc, đòi hỏi công đoạn tiền xử lý phải có cơ chế nội suy và chuẩn hóa giá trị mặc định.
