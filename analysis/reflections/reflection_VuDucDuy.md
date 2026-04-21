# Reflection — Vũ Đức Duy
## Nhiệm vụ: Multi-Judge Consensus Engine

---

### 1. Vai trò và phần việc đã thực hiện

Trong dự án Lab 14, tôi đảm nhận phát triển thành phần **Multi-Judge Consensus Engine** (`engine/llm_judge.py`). Đây là trái tim của hệ thống đánh giá tự động (LLM-as-a-Judge) cho chatbot y tế. 

Nhiệm vụ cụ thể của tôi tập trung vào việc đảm bảo điểm số đầu ra có tính trung thực, khách quan và đáng tin cậy. Các công việc đã thực hiện bao gồm:
- **Xây dựng luồng đánh giá bất đồng bộ (Async Evaluations):** Tích hợp và điều phối gọi đồng thời hai mô hình LLM khác nhau là `gpt-4o` và `claude-3-5-haiku` để đánh giá cùng một cặp câu hỏi - câu trả lời.
- **Phát triển logic giải quyết xung đột (Conflict Resolution & Tiebreaker):** Khi hai giám khảo đưa ra điểm số chênh lệch lớn, hệ thống tự động nhận diện và phân giải xung đột thay vì chỉ lấy trung bình máy móc.
- **Phát hiện thiên kiến vị trí (Position Bias Detection):** Triển khai cơ chế hoán đổi (swapping) vị trí nội dung tham chiếu để kiểm tra xem LLM có ưu ái một vị trí cụ thể nào không.
- **Theo dõi tài nguyên (Usage & Cost Tracking):** Theo dõi số lượng token đã dùng ở cả đầu vào và đầu ra, đồng thời tính toán chi phí (USD) để tối ưu hóa ngân sách chạy các vòng benchmark.

---

### 2. Các quyết định kỹ thuật quan trọng

#### 2.1. Sử dụng Multi-Judge thay vì Single Judge
Việc đánh giá sinh ngôn ngữ tự nhiên thường mang tính chủ quan. Nếu chỉ dùng một mô hình duy nhất (như GPT-4o), hệ thống sẽ dễ bị mắc phải "model bias" (LLM tự chấm điểm cao cho câu trả lời theo đúng văn phong của chính nó). Bằng cách kết hợp GPT-4o (mạnh về logic) và Claude-3-5-haiku (nhanh và sắc bén về chi tiết), tôi tạo ra một "hội đồng", qua đó đánh giá toàn diện hơn. Mặc dù chi phí tăng lên một chút, độ tin cậy thực tế (ground truth alignment) của bài kiểm tra tăng đáng kể.

#### 2.2. Cơ chế Tiebreaker để giải quyết xung đột có chủ ý
Trong thực nghiệm, tôi gặp những case mà `gpt-4o` chấm 4 điểm (thoả mãn điều kiện cơ bản) nhưng `claude-3-5-haiku` chấm 1 điểm (phát hiện ra sai sót chết người trong y tế). Thay vì lấy điểm trung bình (ra 2.5 điểm) che lấp đi vấn đề, tôi thiết kế cơ chế Tiebreaker: nếu khoảng cách điểm (Delta) ≥ 2, kết quả sẽ bị flag (đánh cờ) để một quy trình gắt gao hơn xem xét, hoặc tin tưởng hoàn toàn vào model có khả năng rà soát an toàn tốt hơn tuỳ theo config.

#### 2.3. Tách biệt tầng Evaluation và Async Runner
Để tách riêng rẽ trách nhiệm (Separation of Concerns), tôi thiết kế module `llm_judge.py` chỉ tập trung vào nghiệp vụ chấm điểm, phân tích output và xử lý logic (Consensus). Việc điều phối hàng chục requests và chịu trách nhiệm xử lý Timeout, Rate Limit bằng Semaphore được để cho phần Async Runner (do Bách làm). Quyết định này giúp mã nguồn dễ viết Unit Tests với mock APIs hơn rất nhiều.

---

### 3. Khó khăn gặp phải và cách xử lý

#### 3.1. Parsing JSON từ LLM output thiếu ổn định
Một thách thức lớn với LLM-as-a-Judge là các mô hình đôi khi trả về đoạn text (chatter) bọc ngoài kết quả JSON, gây lỗi `JSONDecodeError`. Để xử lý, tôi đã viết một hàm parsing kết hợp RegEx nhằm trích xuất mọi định dạng block mã ````json...```` một cách mềm dẻo. Đi kèm đó là cơ chế fallback an toàn: nếu thật sự không đọc được sau nhiều nỗ lực parse, hệ thống sẽ log lại lỗi cụ thể và trả về một Error State thay vì crash toàn bộ vòng lặp benchmark hiện tại.

#### 3.2. Cây logic Consensus phức tạp
Đảm bảo luồng xử lý giữa Normal Case (hai Judge đồng thuận), Tiebreaker Case (hai Judge lệch điểm) và Error Case (một hoặc cả hai Judge lỗi API) đòi hỏi nhiều câu lệnh rẽ nhánh if-else dễ gây lỗi nợ kỹ thuật (Technical Debt). Tôi xử lý việc này bằng cách định nghĩa các Dataclass/Pydantic Model tường minh cho `EvaluationResult` và viết Unit Tests phủ hết các edge cases này trước khi bắt đầu tích hợp.

---

### 4. Bài học kinh nghiệm

- **Sự đồng thuận không phải là lấy trung bình cộng:** Trong hệ thống đánh giá y tế, "trung bình cộng" giữa đúng và sai vẫn là sai. Phải xem xét sự khác biệt giữa các giám khảo như một tín hiệu rủi ro (risk signal) chứ không đơn thuần là một nhiễu số liệu.
- **Xử lý ngoại lệ là cốt lõi trong LLM Integration:** Hệ thống gọi API bên ngoài luôn tiềm ẩn rủi ro mạng, rate limit, bị trả về sai format. Thiết kế một Agent hoặc Judge tốt không chỉ nằm ở khả năng viết prompt, mà 60% công sức là ở việc handle gracefully các lỗi để không vỡ luồng benchmark. Mọi dòng code xử lý I/O đều cần có try-except bọc cẩn thận.

---

### 5. Nếu làm lại, tôi sẽ cải tiến gì

Nếu có thêm thời gian hoặc ngân sách, tôi sẽ nâng cấp phần của mình với các điểm sau:
- **Tự động retry với Prompt khắc nghiệt hơn:** Nếu LLM trả về invalid JSON, tôi muốn engine tự động retry gọi lại LLM kèm theo lịch sử lỗi, bắt buộc nó "chỉ trả về JSON hợp lệ" nhằm tăng tỉ lệ đánh giá thành công lên mức 99.9%.
- **Thêm giám khảo thứ ba làm Tiebreaker thực thụ:** Đối với các trường hợp độ lệch > 2 điểm, tôi sẽ cấu hình gọi thêm một giám khảo thứ 3 (ví dụ Gemini 1.5 Pro) để hoàn thiện số biểu quyết, giúp hệ thống hoàn toàn tự chủ mà không cần flag chờ người duyệt thủ công.
- **Ghi chép chi tiết lí do thiên lệch (Bias Logs):** Đẩy thông tin position bias xuống File Database rõ ràng hơn để phân tích xem có phải model A thường ưu ái câu trả lời ngắn, hay model B thường thích câu trả lời có gạch đầu dòng hay không.
