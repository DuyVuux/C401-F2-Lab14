# Reflection — Trần Quang Quí
## Nhiệm vụ: Retrieval Eval + Agent Integration

---

### 1. Hit Rate vs. MRR — Khi nào dùng cái nào?

**Hit Rate** trả lời câu hỏi đơn giản: "Có tìm được tài liệu đúng không?" — chỉ cần 1 trong `ground_truth_doc_ids` xuất hiện trong top-k là tính hit. Đây là metric phù hợp khi mục tiêu chỉ cần biết retrieval có ích hay không, ví dụ: câu hỏi y tế chỉ cần đúng 1 nguồn là đủ trả lời.

**MRR** (Mean Reciprocal Rank) quan tâm thêm đến **thứ tự**: tài liệu đúng nằm ở vị trí 1 hay vị trí 3 trong kết quả trả về? MRR cao nghĩa là tài liệu quan trọng nhất được đẩy lên đầu. Điều này quan trọng khi LLM chỉ đọc vài đoạn đầu (top-1, top-2) để sinh câu trả lời — nếu đúng mà ở vị trí cuối thì vẫn có nguy cơ bị bỏ qua.

**Kết luận thực tế:** Dùng Hit Rate để đánh giá coverage, dùng MRR để đánh giá ranking quality. Một hệ thống tốt cần cả hai.

---

### 2. Tại sao Retrieval Eval quan trọng hơn Generation Eval?

Generation Eval (LLM Judge, RAGAS faithfulness) chỉ đo chất lượng *câu trả lời cuối cùng*. Nhưng nếu retrieval sai, LLM sẽ không có thông tin đúng để dùng — và kết quả là **hallucination có vẻ tự tin**.

Trong thực nghiệm của lab này, khi `hit_rate = 0` (không tìm được tài liệu đúng), agent vẫn trả lời dựa trên nội dung ngẫu nhiên → judge có thể cho điểm trung bình vì câu văn trôi chảy, nhưng nội dung thực tế sai hoàn toàn.

Retrieval Eval phát hiện lỗi sớm hơn ở gốc rễ — giúp distinguish giữa "LLM tệ" và "retrieval tệ", từ đó có hướng cải thiện chính xác hơn.

---

### 3. Hallucination từ Retrieval Fail

Qua phân tích các cases trong benchmark:
- Cases có `hit_rate = 0` là những câu hỏi về chủ đề không có keyword rõ ràng (ví dụ: câu hỏi adversarial, out-of-context, hoặc câu hỏi dùng từ ngữ khác so với keyword trong knowledge base).
- Agent vẫn trả lời những cases này bằng câu "Dựa trên tài liệu hệ thống..." — đây là dạng **hallucination tự tin**: câu trả lời nghe có vẻ chuyên nghiệp nhưng không có cơ sở từ nguồn tài liệu thực.
- Judge score cho những cases này thường thấp hơn khi có ground truth để đối chiếu, nhưng nếu chỉ dùng LLM Judge không có ground truth thì rất khó phát hiện.

**Bài học:** Retrieval metrics là lớp kiểm tra đầu tiên và quan trọng nhất — cần đặt ngưỡng `hit_rate >= 0.7` trước khi tin vào judge score.

---

### 4. Quyết định kỹ thuật

- Dùng keyword-based retrieval thay vì vector search để giữ pipeline đơn giản, dễ debug và không phụ thuộc vào embedding model.
- `RetrievalEvaluator.evaluate_batch()` trả về `per_case` chi tiết để Giang có thể xác định 3 case tệ nhất cho failure analysis.
- `runner.py` được kết nối để mỗi result có `retrieval.hit_rate` và `retrieval.mrr` — đảm bảo `check_lab.py` pass.
