# External Resources / Tài nguyên bên ngoài

## Resources and provenance / Tài nguyên và nguồn gốc

- **Mô hình nhúng đa ngôn ngữ:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (HuggingFace / Sentence-Transformers, ánh xạ văn bản tiếng Việt sang vector 384 chiều; hỗ trợ bản lượng tử hóa ONNX INT8 khi triển khai Docker).
- **Cơ sở dữ liệu vector:** `ChromaDB` (`>= 1.0, < 2`) dùng chỉ mục HNSW với khoảng cách cosine.
- **Dịch vụ sinh ngôn ngữ:** Google Gemini REST API (`gemini_client.py`), gọi trực tiếp khi cấu hình `GEMINI_API_KEY` và `GEMINI_MODEL`.
- **Thư viện Web, kiểm thử và thu thập dữ liệu:** `Flask` (`>= 3.1, < 4`), `python-dotenv` (`>= 1, < 2`), `pytest` (`>= 8, < 9`), cùng `Selenium` và `BeautifulSoup4` (trong `project/crawler/`), `onnxruntime` và `sentencepiece` (trong `Dockerfile`).
- **Dữ liệu địa điểm:** Dữ liệu thô được thu thập từ 323 URL công khai (298 URL ở `crawler_1` và 25 URL ở `crawler_2`) về địa điểm/ẩm thực tại 12 quận nội thành Hà Nội, sau đó hợp nhất và làm sạch thành `project/bot/data/hanoi_places_cleaned.json` (1.691 bản ghi).
- **Nền tảng triển khai trực tuyến (Cloud Hosting):** Dịch vụ **Render** dùng để lưu trữ và vận hành bản demo web công khai tại https://hanoi-explorer-ai.onrender.com/ (repo triển khai: https://github.com/Winter101006/hanoi-explorer-render).

## License or access conditions / Giấy phép hoặc điều kiện truy cập

- `paraphrase-multilingual-MiniLM-L12-v2` và `sentence-transformers`: giấy phép **Apache 2.0**, tải công khai qua HuggingFace Hub (không yêu cầu token trả phí).
- `ChromaDB` và `Selenium`: giấy phép **Apache 2.0**.
- `Flask` và `python-dotenv`: giấy phép **BSD-3-Clause**.
- `pytest`, `BeautifulSoup4` và `onnxruntime`: giấy phép **MIT**.
- **Google Gemini API:** dịch vụ thương mại có hạn mức miễn phí theo API key cá nhân của người triển khai; khóa API không được đưa lên GitHub (chỉ khai báo mẫu rỗng trong `project/bot/.env.example`).

## Download, setup, and preprocessing / Tải xuống, cài đặt và tiền xử lý

- Tệp dữ liệu đã tiền xử lý `project/bot/data/hanoi_places_cleaned.json` (1.691 địa điểm) được lưu trực tiếp trong kho để đảm bảo tái tạo ngay phần truy xuất và đánh giá mà không cần crawl lại web nguồn. Nếu muốn chạy lại bước hợp nhất từ dữ liệu thô đã lưu trong `crawler_1`/`crawler_2`, chạy `python project/preprocessing/preprocess.py`.
- Thư mục bộ nhớ đệm mô hình `project/bot/model_cache/` và chỉ mục vector `project/bot/chroma_db/` nằm trong `.gitignore` nên không được commit lên GitHub. Sau khi cài gói bằng `pip install -r project/bot/requirements.txt`, chạy `python -m project.bot.scripts.index_data` (cần kết nối Internet ở lần đầu để tải trọng số `MiniLM-L12-v2` về `project/bot/model_cache/` và tạo collection `hanoi_cleaned_minilm_v1` trong `project/bot/chroma_db/`).

## Reproducibility limits / Giới hạn tái tạo

- **Không lưu tệp nhị phân lớn trên Git:** Cần chạy `python -m project.bot.scripts.index_data` một lần sau khi clone repo để dựng lại `model_cache/` và `chroma_db/` trước khi khởi động server hoặc chạy test retrieval trên ChromaDB thật.
- **Thu thập dữ liệu web nguồn:** Các script trong `project/crawler/` phụ thuộc vào cấu trúc HTML của trang nguồn công khai tại thời điểm thu thập; nếu trang nguồn thay đổi giao diện, kết quả crawl lại có thể khác, do đó bộ dữ liệu sạch `hanoi_places_cleaned.json` được đóng gói sẵn để làm mốc tái tạo ổn định.
- **Phản hồi live từ Google Gemini API:** Các ca gọi Gemini trực tiếp (`GG-13..15` khi bật `--live`) phụ thuộc vào API key cá nhân, hạn mức quota và tính không tất định của LLM; toàn bộ phần retrieval, ranking, fallback và 67 ca `unittest` không phụ thuộc vào kết nối Gemini.
- **Bản demo trực tuyến trên Render:** Đường dẫn https://hanoi-explorer-ai.onrender.com/ sử dụng gói lưu trữ đám mây miễn phí (512MB RAM, chạy ONNX INT8) nên có thể mất 30–50 giây khởi động lại (cold start) sau thời gian không có truy cập; việc kiểm thử tự động và tái tạo kết quả chuẩn được thực hiện độc lập trên môi trường cục bộ với bộ dữ liệu `hanoi_places_cleaned.json`.
