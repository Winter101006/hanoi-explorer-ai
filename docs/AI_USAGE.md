# AI Usage & Verification / Sử dụng AI và Kiểm chứng

## Tools and purposes / Công cụ và mục đích

Dự án phân tách rõ hai vai trò sử dụng trí tuệ nhân tạo trong kiến trúc sản phẩm và quy trình phát triển:

1. **Mô hình AI tích hợp trực tiếp trong hệ thống (Runtime AI):**
   - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`: Mã hóa truy vấn và mô tả địa điểm tiếng Việt thành vector ngữ nghĩa 384 chiều chạy cục bộ trên CPU (hoặc qua **ONNX Runtime lượng tử hóa INT8** khi triển khai Docker/Cloud) phục vụ tìm kiếm gần đúng trên ChromaDB.
   - **Google Gemini API** (cấu hình qua `GEMINI_MODEL` và `GEMINI_API_KEY` trong `.env`): Sinh diễn giải câu trả lời tiếng Việt tự nhiên từ tối đa Top-3 địa điểm đã qua kiểm duyệt của tầng truy xuất và xếp hạng. Hệ thống vẫn hoạt động đầy đủ khi không có API key nhờ bộ sinh xác định (deterministic fallback).

2. **Công cụ AI hỗ trợ phát triển phần mềm (Development Assistance):**
   - Trợ lý lập trình AI được sử dụng để rà soát các trường hợp biên xử lý tiếng Việt trong `QueryProcessor`, tối ưu CSS/HTML responsive cho thẻ địa điểm trên giao diện web và hỗ trợ viết ca kiểm thử hồi quy bổ sung.

## Verification / Kiểm chứng chất lượng

- **Kiểm soát đầu ra AI khi vận hành:** Mọi phản hồi từ Google Gemini API đều bị ràng buộc theo JSON Schema (`answer`, `recommendation_ids`, `follow_up`), kiểm tra kiểu dữ liệu và đối chiếu danh sách mã định danh qua `ChatbotResponse.validate_ids()` để bảo đảm chỉ trích dẫn đúng các ID đã truy xuất từ máy chủ. Thông tin hiển thị trên thẻ giao diện (tên, địa chỉ, giờ mở cửa, khoảng giá) luôn đọc trực tiếp từ bản ghi `Place` phía máy chủ, không lấy từ văn bản LLM sinh ra.
- **Kiểm chứng mã nguồn, kiểm thử và số liệu thực nghiệm:** Toàn bộ đoạn mã, quy tắc NLP và số liệu thực nghiệm đều được tác giả (**Phạm Ngọc Huân**) rà soát thủ công và tự thực thi kiểm chứng trực tiếp trên kho mã nguồn:
  - Chạy toàn bộ **67/67** kiểm thử đơn vị và tích hợp (`python -B -m unittest discover -s project/bot/tests -v`).
  - Chạy kiểm chứng hồi quy qua `python -m project.bot.scripts.run_baseline --legacy` (tổng cộng 187 ca gồm 120 ca baseline và 67 ca đơn vị/tích hợp, đạt **183 ca đạt, 0 ca lỗi, 4 ca bỏ qua có chủ đích** gồm `GG-13..15` và `RT-19`) và đối chiếu với báo cáo baseline tại `project/bot/evaluation/reports/baseline.md`.
  - Kiểm tra dữ liệu sạch `project/bot/data/hanoi_places_cleaned.json` xác nhận đúng 1.691 bản ghi và 14 trường theo hợp đồng `CONTRACTS.md`.
