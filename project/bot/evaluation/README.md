# Evaluation WS3/WS4

`cases.json` chứa kịch bản chưa gán nhãn. Lưu câu hỏi, câu trả lời thật, retrieved
IDs/documents, ranked IDs, SHA-256 JSON nguồn, cấu hình và model trước khi chấm.
Dùng tập development riêng với test. Thực hiện gán nhãn đối chiếu độc lập và điền kết quả retrieval/recommendation vào cùng cấu trúc input runner để đánh giá nhất quán.

Generation annotations gồm total_claims, supported_claims, unsupported_claims và
relevance trong [0,1]. Mỗi factual claim phải supported hoặc unsupported so với
bằng chứng truy xuất. Groundedness và hallucination_rate được tính trên tổng số
claim của các câu đã gán nhãn. Đây là mức bám bằng chứng dataset, chưa xác minh
sự thật bên ngoài. Relevance chấm 0 cho lạc đề, .5 cho đáp ứng một phần, 1 cho đáp
ứng trực tiếp. Conversation passed là boolean sau khi kiểm tra tất cả chuyển đổi
state kỳ vọng trong case. Null nghĩa là chưa đánh giá.

Retrieval row gồm predicted (danh sách ID), relevance (mapping ID sang grade 0–3).
Precision@K dùng mẫu số K; recall dùng tổng relevant ID; NDCG dùng gain 2^grade−1.
Trường hợp không có ID liên quan có recall/NDCG null. Recommendation nhận các nhãn
preference_match, budget_satisfied, location_satisfied trong [0,1], null nếu unknown.
Runner trả labelled counts cùng trung bình; không có nhãn thì metric null.
