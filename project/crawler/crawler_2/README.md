# Hanoi Attraction Crawler

Mô-đun thu thập dữ liệu các địa điểm vui chơi, tham quan, giải trí tại Hà Nội phục vụ cho Chatbot tư vấn.

## Cấu trúc thư mục

```text
crawler/
├── data/
│   ├── links/                      # Chứa các file .txt danh sách URL theo từng quận (ba_dinh.txt, cau_giay.txt,...)
│   └── raw/
│       └── hanoi_attractions.json  # File JSON kết quả đầu ra
├── packages/
│   ├── __init__.py
│   ├── attraction_filter.py        # Bộ lọc loại trừ quán ăn, giữ địa điểm vui chơi
│   ├── logging_handler.py          # Quản lý log
│   ├── selenium_handler.py         # Khởi tạo Selenium ChromeDriver
│   └── utils.py                    # Tiện ích xử lý chuỗi
├── crawl_attraction_details.py     # Script chính để cào dữ liệu
└── requirements.txt                # Các thư viện phụ thuộc