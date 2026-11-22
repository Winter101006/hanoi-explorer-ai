# Preprocessing Module — Tiền xử lý và Chuẩn hóa dữ liệu

Mô-đun tiền xử lý và làm sạch dữ liệu của dự án **Hanoi Explorer Chatbot (Hanoi Explorer AI)**, chịu trách nhiệm hợp nhất các nguồn dữ liệu cào thô, khử trùng lặp bản ghi, chuẩn hóa địa chỉ, trích xuất thuộc tính chuyên sâu và làm giàu lược đồ 14 trường thông tin.

## Purpose and structure / Mục đích và cấu trúc

Mục đích: Chuyển đổi 1.692 bản ghi dữ liệu thô phân tán từ hai bộ crawler (`crawler_1` và `crawler_2`) thành tập dữ liệu sạch duy nhất gồm 1.691 bản ghi đạt chuẩn, khớp hoàn toàn với schema nghiệp vụ của Chatbot, cơ sở dữ liệu vector và giao diện Web.

Cấu trúc thư mục:

```text
preprocessing/
├── preprocess.py      # Kịch bản chính thực hiện hợp nhất, làm sạch, khử trùng lặp và làm giàu dữ liệu
└── README.md          # Tài liệu đặc tả quy trình và hướng dẫn sử dụng mô-đun
```

## Requirements and setup / Yêu cầu và cài đặt

1. **Yêu cầu hệ thống:**
   - Python 3.10 trở lên.
   - Sử dụng hoàn toàn các thư viện chuẩn tích hợp sẵn trong Python (`json`, `re`, `hashlib`, `unicodedata`, `os`, `sys`), không yêu cầu cài đặt thêm gói phụ thuộc bên ngoài.

2. **Thiết lập:**
   - Đảm bảo dữ liệu thô đã có sẵn tại các thư mục `project/crawler/crawler_1/data/raw/` và `project/crawler/crawler_2/data/raw/`.

## Inputs and outputs / Đầu vào và đầu ra

- **Đầu vào (Raw Data):**
  - `project/crawler/crawler_1/data/raw/dataset1_hanoi.json`: 1.375 bản ghi địa điểm ăn uống và cà phê.
  - `project/crawler/crawler_2/data/raw/hanoi_attractions.json`: 317 bản ghi điểm tham quan, di tích văn hóa và vui chơi ngoài trời.
  - Tổng số bản ghi thô đầu vào: 1.692 bản ghi.
- **Đầu ra (Enriched Clean Data):**
  - Tệp `project/bot/data/hanoi_places_cleaned.json` chứa 1.691 bản ghi sạch đã được chuẩn hóa theo lược đồ 14 trường chi tiết:
    - `id`: Mã định danh duy nhất của địa điểm theo thứ tự (`hn_loc_001` đến `hn_loc_1691`).
    - `name`: Tên địa điểm đã chuẩn hóa Unicode NFC, loại bỏ ký tự rác và khoảng trắng thừa.
    - `category`: Tên phân loại gốc đã chuẩn hóa (Quán ăn, Quán nước, Di tích lịch sử, Công viên, v.v.).
    - `category_code`: Mã phân loại chuẩn 7 nhóm phục vụ truy vấn (`an-uong`, `ca-phe`, `tam-linh`, `di-tich`, `ngoai-troi`, `giai-tri`, `the-thao`).
    - `district`: Quận/huyện chuẩn hóa (tập trung 12 quận nội thành Hà Nội).
    - `address`: Địa chỉ đã trích xuất và chuẩn hóa định dạng theo tuyến phố/quận.
    - `opening_hours`: Khung giờ mở cửa chuẩn hóa (ví dụ: `"9:00 - 23:00"`).
    - `price_range`: Chuỗi khoảng giá chuẩn hóa (ví dụ: `"200.000 - 300.000 VNĐ"` hoặc `"Miễn phí"`), làm đầu vào cho bộ phân tích số học `parse_price()` trong `data_loader.py`.
    - `suitable_for`: Danh sách đối tượng/mục đích phù hợp (`Gia đình`, `Cặp đôi`, `Nhóm bạn`, `Solo` hoặc `Mọi đối tượng`).
    - `weather_fit`: Nhãn thích hợp không gian/thời tiết (`Trong nhà`, `Ngoài trời`, hoặc `Trong nhà / Ngoài trời`).
    - `description`: Đoạn văn bản mô tả đặc trưng không gian, món ăn và dịch vụ nổi bật sau khi làm sạch.
    - `latitude`, `longitude`: Tọa độ địa lý ước lượng theo tuyến phố hoặc tâm quận (`coordinates_verified=False` ở khâu nạp).
    - `tags`: Danh sách tối đa 12 từ khóa tìm kiếm tổng hợp từ tên, danh mục, quận, phố, món ăn và không gian.

## Reproduce the main result / Tái tạo kết quả chính

Chạy kịch bản tiền xử lý dữ liệu từ thư mục gốc của kho lưu trữ:

```bash
python project/preprocessing/preprocess.py
```

Quy trình xử lý tự động bao gồm các bước:
1. **Quét và nạp dữ liệu:** Đọc toàn bộ 1.692 bản ghi thô từ các thư mục crawler.
2. **Khử trùng lặp (Deduplication):** So khớp tên chuẩn hóa kết hợp địa chỉ, loại bỏ các bản ghi trùng lặp (giảm 1 bản ghi trùng lặp, còn đúng 1.691 bản ghi độc bản).
3. **Chuẩn hóa địa lý & quận:** Ánh xạ tên quận về 12 quận nội thành chuẩn và gán tọa độ tham chiếu theo tuyến phố/quận.
4. **Chuẩn hóa giá và khung giờ:** Dùng biểu thức chính quy (Regex) chuẩn hóa chuỗi khoảng giá (`price_range`) và khung giờ mở cửa (`opening_hours`), tạo đầu vào cho `parse_price()` ở bước nạp dữ liệu.
5. **Gán nhãn ngữ cảnh thông minh:** Tự động phân loại `weather_fit` và `suitable_for` dựa trên tập từ khóa đặc trưng.
6. **Lưu trữ kết quả:** Ghi tập dữ liệu hoàn thiện vào `project/bot/data/hanoi_places_cleaned.json`.

## Known limitations / Giới hạn đã biết

- **Tọa độ địa lý tham chiếu:** Tọa độ GPS kế thừa từ tâm quận hoặc tuyến phố chính (qua từ điển tra cứu tọa độ tĩnh), chưa được đo đạc GPS thực địa chính xác tuyệt đối tới từng số nhà cụ thể.
- **Phân loại thời tiết mang tính tương đối:** Các địa điểm phức hợp (vừa có không gian phòng lạnh trong nhà vừa có khuôn viên sân vườn ngoài trời) được gắn nhãn theo không gian chủ đạo trong mô tả.
