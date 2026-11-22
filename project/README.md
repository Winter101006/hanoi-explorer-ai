# Project materials and reproduction / Mã nguồn và tái tạo kết quả

Thư mục này chứa toàn bộ tài nguyên kỹ thuật, mã nguồn thu thập dữ liệu (crawler), tiền xử lý và chuẩn hóa dữ liệu (preprocessing), hệ thống chatbot tư vấn địa điểm Hà Nội và giao diện Web (bot). Người dùng và nhà tuyển dụng có thể triển khai hoặc tái tạo thực nghiệm trực tiếp thông qua môi trường đám mây hoặc dòng lệnh cục bộ theo hướng dẫn dưới đây.

## Purpose and structure / Mục đích và cấu trúc

Thư mục `project/` chứa toàn bộ mã nguồn của dự án **Hanoi Explorer Chatbot (Hanoi Explorer AI)**, được tổ chức thành ba công đoạn chính: thu thập dữ liệu (crawler), tiền xử lý và chuẩn hóa dữ liệu (preprocessing), và hệ thống chatbot tương tác web (bot). Chi tiết thêm về hợp đồng dữ liệu và các module xem tại [`project/bot/README.md`](bot/README.md).

```text
project/
├── crawler/                       # Module thu thập dữ liệu địa điểm tại Hà Nội
│   ├── crawler_1/                 # Thu thập 1.375 quán ăn & quán cà phê trên 12 quận nội thành
│   ├── crawler_2/                 # Thu thập 317 điểm di tích lịch sử, không gian văn hóa & ngoài trời
│   └── data/                      # Dữ liệu thu thập thô ban đầu
├── preprocessing/                 # Module tiền xử lý và làm sạch dữ liệu
│   ├── preprocess.py              # Làm sạch, hợp nhất, khử trùng lặp và chuẩn hóa lược đồ 14 trường
│   └── README.md                  # Hướng dẫn chi tiết quy trình tiền xử lý dữ liệu
└── bot/                           # Hệ thống chatbot và ứng dụng web
    ├── main.py                    # Điểm khởi chạy máy chủ Flask Web (mặc định tại http://127.0.0.1:5000)
    ├── CONTRACTS.md               # Đặc tả hợp đồng dữ liệu và giao diện giữa các module hệ thống
    ├── requirements.txt           # Danh sách thư viện phụ thuộc (Flask, chromadb, sentence-transformers...)
    ├── .env.example               # Tệp mẫu cấu hình biến môi trường (Gemini API key, ChromaDB collection...)
    ├── data/
    │   └── hanoi_places_cleaned.json   # Cơ sở dữ liệu sạch chuẩn hóa 1.691 địa điểm Hà Nội
    ├── src/
    │   ├── chatbot/               # Các module lõi của chatbot
    │   │   ├── config.py          # Quản lý cấu hình hệ thống và đường dẫn tài nguyên
    │   │   ├── schemas.py         # Định nghĩa cấu trúc dữ liệu và schema JSON
    │   │   ├── data_loader.py     # Tải và xác thực dữ liệu địa điểm
    │   │   ├── embedding.py       # Quản lý mô hình nhúng vector ngữ nghĩa (sentence-transformers)
    │   │   ├── chroma_manager.py  # Quản lý cơ sở dữ liệu vector ChromaDB
    │   │   ├── query_processor.py # Phân tích ý định (intent) và trích xuất thực thể từ truy vấn tiếng Việt
    │   │   ├── retriever.py       # Truy xuất dữ liệu theo ngữ nghĩa vector và bộ lọc ràng buộc cứng
    │   │   ├── recommender.py     # Thuật toán xếp hạng đa tiêu chí và chuẩn hóa trọng số động
    │   │   ├── memory.py          # Quản lý bộ nhớ hội thoại theo phiên (ConversationMemory)
    │   │   ├── prompts.py         # Mẫu prompt định hướng và kiểm soát sinh nội dung
    │   │   ├── gemini_client.py   # Client kết nối Google Gemini API kèm cơ chế retry
    │   │   └── chatbot.py         # Module điều phối tổng thể luồng xử lý truy vấn và phản hồi
    │   └── web/                   # Giao diện người dùng Web (Flask Web Application)
    │       ├── app.py             # Khởi tạo ứng dụng Flask và đăng ký routes
    │       ├── routes/            # Điều hướng các API endpoint (/api/chat, /api/places...)
    │       ├── services/          # Tầng nghiệp vụ xử lý logic chat cho web
    │       ├── templates/         # Giao diện HTML (index.html)
    │       └── static/            # Tài nguyên giao diện tĩnh (CSS, JavaScript, hình ảnh)
    ├── scripts/                   # Kịch bản thực thi và đánh giá
    │   ├── index_data.py          # Tải mô hình nhúng và lập chỉ mục 1.691 địa điểm vào ChromaDB
    │   ├── evaluate.py            # Chạy đánh giá độ chính xác truy xuất trên tập ca kiểm thử
    │   └── run_baseline.py        # Kịch bản chạy bộ chuẩn benchmark (120 ca baseline; 187 ca với --legacy)
    ├── evaluation/                # Dữ liệu và báo cáo đánh giá benchmark
    │   ├── BASELINE.md            # Tài liệu đặc tả bộ chuẩn đánh giá 120 ca
    │   ├── baseline_cases.json    # Tập 120 ca kiểm thử thực nghiệm đa dạng ngữ cảnh (92 dev + 28 holdout)
    │   ├── test_baseline.py       # Kịch bản kiểm tra tự động các ca đánh giá
    │   └── reports/               # Báo cáo kết quả đánh giá thực nghiệm chi tiết
    └── tests/                     # Bộ 67 bài kiểm thử tự động (unit tests & integration tests)
```
## Requirements and setup / Yêu cầu và cài đặt

> **Bản triển khai trực tuyến (Live Demo):** https://hanoi-explorer-ai.onrender.com/ *(có thể trải nghiệm trực tiếp trên trình duyệt; lần truy cập đầu sau khi máy chủ Render nghỉ có thể mất 30–50 giây để khởi động)*.

Yêu cầu hệ thống: **Python 3.10 trở lên** (khuyến nghị Python 3.10 hoặc 3.11).

1. **Khởi tạo môi trường ảo và cài đặt các thư viện cần thiết:**

   - Trên Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     pip install -r project/bot/requirements.txt
     ```
   - Trên Linux / macOS:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r project/bot/requirements.txt
     ```

2. **Cấu hình biến môi trường:**

   Tạo tệp cấu hình `.env` từ mẫu `.env.example`:
   ```powershell
   Copy-Item project/bot/.env.example project/bot/.env
   ```
   (Trên Linux/macOS: `cp project/bot/.env.example project/bot/.env`).

   - Cấu hình các biến chính trong `project/bot/.env`:
     - `CHROMA_PATH`: Đường dẫn lưu trữ cơ sở dữ liệu vector (mặc định: `project/bot/chroma_db`).
     - `CHROMA_COLLECTION`: Tên collection (mặc định: `hanoi_cleaned_minilm_v1`).
     - `GEMINI_API_KEY`: Khóa API Google Gemini (tùy chọn; nếu không điền, hệ thống sẽ tự động kích hoạt cơ chế sinh phản hồi dự phòng xác định - deterministic fallback).
     - `GEMINI_MODEL`: `gemini-flash-lite-latest`.

3. **Tải mô hình nhúng ngữ nghĩa và tạo chỉ mục vector ChromaDB (lần đầu cần mạng):**

   Chạy lệnh sau để tải mô hình `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` về bộ nhớ đệm `project/bot/model_cache/` và lập chỉ mục 1.691 địa điểm vào `project/bot/chroma_db/`:

   ```bash
   python -m project.bot.scripts.index_data
   ```

4. **Khởi chạy ứng dụng Web Chatbot:**

   ```bash
   python project/bot/main.py
   ```

   Mở trình duyệt web và truy cập: `http://127.0.0.1:5000` (hoặc dùng bản trực tuyến tại https://hanoi-explorer-ai.onrender.com/). Sau khi mô hình đã được tải về cục bộ, hệ thống có thể chạy hoàn toàn ngoại tuyến (offline) bằng cách đặt biến môi trường `HF_HUB_OFFLINE=1`.

## Inputs and outputs / Đầu vào và đầu ra

- **Đầu vào ngoại tuyến (Offline Data Inputs):**
  - Dữ liệu thô thu thập từ hai nguồn crawler (`1.692` bản ghi địa điểm tại Hà Nội).
  - Sau khi chạy qua `preprocess.py`, dữ liệu được làm sạch, loại bỏ bản ghi trùng lặp và chuyển đổi thành `project/bot/data/hanoi_places_cleaned.json` gồm `1.691` bản ghi chuẩn hóa theo lược đồ 14 trường (`id`, `name`, `category`, `category_code`, `district`, `address`, `opening_hours`, `price_range`, `suitable_for`, `weather_fit`, `description`, `latitude`, `longitude`, `tags`).
- **Đầu vào trực tuyến (Online User Inputs):**
  - Yêu cầu HTTP `POST` gửi tới endpoint `/api/chat` chứa payload JSON:
    - `message` (chuỗi văn bản tiếng Việt tự nhiên, tối đa 500 ký tự biểu đạt nhu cầu tìm kiếm, ví dụ: *"tìm quán cafe yên tĩnh làm việc ở Cầu Giấy dưới 50k"*).
    - `category`, `district`, `budget` (các bộ lọc tùy chọn từ giao diện người dùng).
    - `session_id` (mã định danh phiên hội thoại để duy trì ngữ cảnh trao đổi nhiều lượt).
- **Đầu ra hệ thống (System Outputs):**
  - Phản hồi JSON có cấu trúc chuẩn hóa:
    - `answer` / `reply`: Đoạn văn bản tư vấn và giải thích tự nhiên bằng tiếng Việt (sinh từ Gemini hoặc qua bộ tạo phản hồi xác định).
    - `places` / `recommendations`: Danh sách tối đa Top-5 địa điểm phù hợp nhất đã được xác thực mã định danh (`validate_ids()`), đầy đủ thông tin chi tiết (tên, phân loại, địa chỉ, khoảng giá, giờ mở cửa, độ tương thích thời tiết, đối tượng phù hợp).
    - `follow_up`: Câu gợi ý hỏi tiếp hoặc câu hỏi làm rõ nhu cầu khi thông tin ban đầu chưa đầy đủ.
    - `status`: Trạng thái xử lý của hệ thống (`success`, `clarification_needed`...).
    - `itinerary`: Giá trị `null` (chủ động tắt do dữ liệu tọa độ GPS chưa được kiểm chứng độc lập).

## Reproduce the main result / Tái tạo kết quả chính

Các bước tái tạo kết quả chính của dự án (thực hiện từ thư mục gốc của kho lưu trữ):

1. **Chạy toàn bộ bộ kiểm thử tự động (67 bài unit tests & integration tests):**

   ```bash
   python -B -m unittest discover -s project/bot/tests -v
   ```

   - **Kết quả mong đợi:** Tất cả **67/67 bài kiểm thử đều đạt (`OK`)** trong thời gian thực thi dưới 1 giây. Kiểm thử bao quát kiểm tra hợp đồng dữ liệu, bộ nạp dữ liệu, phân tích truy vấn NLP, tìm kiếm vector, thuật toán xếp hạng đa tiêu chí, quản lý bộ nhớ phiên và tích hợp API.

2. **Chạy kiểm định độ chính xác các nhóm xử lý truy vấn NLP (`QU`, `CM`, `CR`):**

   *(Yêu cầu đã lập chỉ mục vector bằng `python -m project.bot.scripts.index_data`):*

   ```bash
   python -m pytest project/bot/evaluation/test_baseline.py -k "QU or CM or CR" -v
   ```

   - **Kết quả mong đợi:** Đạt **70/70 ca kiểm thử thành công (100%)**, giải quyết triệt để 15 nhóm lỗi hiểu ngôn ngữ tự nhiên, xử lý ngân sách, ngữ cảnh thời tiết và chuyển đổi quận/thể loại.

3. **Chạy đánh giá bộ chuẩn thực nghiệm Baseline 120 ca (187 ca khi kèm `--legacy`):**

   ```bash
   python -m project.bot.scripts.run_baseline --split development --output project/bot/evaluation/reports-dev
   # Hoặc chạy toàn bộ 187 ca (120 ca baseline + 67 ca unittest/tích hợp):
   python -m project.bot.scripts.run_baseline --legacy
   ```

   - Lệnh sẽ thực thi đánh giá trên tập dữ liệu benchmark (92 ca `development`, 28 ca `holdout`; 183 ca đạt và 4 ca bỏ qua có chủ đích khi chạy đầy đủ với `--legacy`), đo lường các chỉ số Precision@5, Recall@5, NDCG@5 và tỷ lệ vi phạm ràng buộc, xuất báo cáo chi tiết vào thư mục chỉ định.

## Known limitations / Giới hạn đã biết

- **Chưa xác thực tọa độ GPS chi tiết (`coordinates_verified = False`):** Tọa độ trong tập dữ liệu hiện tại chủ yếu lấy theo tâm quận hoặc tuyến phố chính; do đó hệ thống chủ động không tính toán khoảng cách thực tế (km) và giữ trường `itinerary: null` để tránh đưa ra thông tin chỉ dẫn sai lệch.
- **Chưa tích hợp API thời tiết trực tiếp theo thời gian thực:** Endpoint `/api/weather` trả về trạng thái `"unavailable"`; việc gợi ý theo thời tiết hiện tại dựa trên thuộc tính tĩnh `weather_fit` (`Trong nhà` hoặc `Ngoài trời`) đã được gán nhãn trong cơ sở dữ liệu.
- **Phạm vi độ phủ địa bàn:** 1.691 địa điểm tập trung tại 12 quận nội thành Hà Nội (trong đó khoảng 80% là ẩm thực và cà phê), chưa bao phủ các huyện ngoại thành lân cận.
- **Đánh giá tự động cho các câu hỏi mở:** Trong bộ đánh giá chuẩn 120 ca baseline, các trường hợp gọi mô hình Gemini trực tiếp (`GG-13..15`) và câu hỏi mở (`RT-19`) cần có thẩm định con người về chất lượng văn phong và độ liên quan để bảo đảm tính khách quan tuyệt đối.
