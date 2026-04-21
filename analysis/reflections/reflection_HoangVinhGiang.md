# Personal Reflection - Hoàng Vĩnh Giang

## 1. Vai trò và phần việc đã thực hiện

Trong dự án Lab 14, tôi đảm nhận vai trò Chủ biên Failure Analysis và Thiết kế Regression Gate. Đây là chốt chặn cuối cùng trong pipeline để quyết định một phiên bản Agent có đủ tiêu chuẩn để Release hay không. Nhiệm vụ của tôi bao gồm:

- Thiết lập Regression Gate: Xây dựng logic so sánh kết quả giữa phiên bản hiện tại (V2) với bản Baseline (V1) dựa trên các chỉ số: Avg Score, Hit Rate, và Delta Score.
- Phân tích thất bại (Failure Analysis): Trực tiếp kiểm tra (audit) các case bị Judge đánh trượt trong file `benchmark_results.json` để tìm ra các nhóm lỗi hệ thống (Failure Clustering).
- Ra quyết định Release: Dựa trên dữ liệu tổng hợp để đưa ra phán quyết cuối cùng về việc Approve hoặc Block bản phát hành.

## 2. Các quyết định kỹ thuật quan trọng

### 2.1. Quyết định Block Release dựa trên Delta Score

Mặc dù hệ thống vận hành không lỗi về mặt kỹ thuật (no crashes), tôi đã quyết định giữ trạng thái `❌ BLOCK RELEASE` vì chỉ số sụt giảm (-0.02). Quyết định này dựa trên nguyên tắc: "Sự sụt giảm về chất lượng nội dung quan trọng hơn sự ổn định về mặt hạ tầng". Trong domain Healthcare, một câu trả lời an toàn nhưng rỗng tuếch (placeholder) là một thất bại về mặt nghiệp vụ.

### 2.2. Phân nhóm lỗi dựa trên bằng chứng thực tế

Tôi không chỉ nhìn vào con số `avg_score: 1.24` mà trực tiếp đọc phần reasoning của Judge. Quyết định này giúp tôi nhận ra rằng Agent đang "đánh lừa" bộ máy RAGAS (Faithfulness vẫn cao 0.9 do không bịa đặt) nhưng lại thất bại hoàn toàn trước sự kỳ vọng của người dùng thực tế.
### 2.3. Chuẩn hóa contract dữ liệu để giảm lỗi tích hợp

Trong workspace, tôi thấy benchmark runtime trong [main.py](main.py) đọc từ `data/golden_set.jsonl`, trong khi seed cases ban đầu đang ở [tests/golden_set.json](tests/golden_set.json). Đây là một điểm dễ gây lỗi tích hợp. Vì vậy tôi chủ động thiết kế script sao cho:

- `tests/golden_set.json` đóng vai trò seed input,
- `data/golden_set.jsonl` là benchmark artifact cuối cùng,
- mỗi row đều có đủ các field bắt buộc: `question`, `expected_answer`, `context`, `ground_truth_doc_ids`, `metadata.difficulty`, `metadata.type`.

Điểm tôi học được ở đây là: trong một pipeline nhiều người làm, việc “chốt contract dữ liệu” sớm thường quan trọng hơn việc làm generator quá thông minh.

## 3. Khó khăn gặp phải và cách xử lý

Nếu chỉ tạo các câu hỏi easy hoặc medium theo kiểu fact lookup, benchmark sẽ dễ cho ra cảm giác agent hoạt động tốt dù thực tế còn rất nhiều failure mode chưa được đo. Điều này đặc biệt nguy hiểm trong domain healthcare vì sai sót không chỉ là “trả lời dở” mà có thể dẫn đến tư vấn nhầm, rò rỉ thông tin y tế hoặc trả lời quá tự tin khi không có dữ kiện.

Tôi cố tình thêm các nhóm case khó vì các lý do sau:

### 3.1. Đối mặt với "Nghịch lý RAGAS"

Khó khăn lớn nhất là giải thích tại sao các chỉ số như Faithfulness (0.9) và Relevancy (0.8) rất tốt nhưng hệ thống vẫn bị Block. Tôi đã xử lý bằng cách viết một bản phân tích chi tiết, chỉ ra rằng các chỉ số này chỉ đo lường "mối quan hệ" giữa Context và Answer, chứ chưa đo lường được "giá trị thông tin" (Information Density). Từ đó, tôi đề xuất lấy điểm của <b>LLM-Judge (Authority)</b> làm trọng số cao nhất.
### 3.2. Xử lý sự xung đột giữa các Judge (Mini vs Pro)

Khi `gpt-4o-mini` chấm 4 điểm (vì thấy an toàn) và `gpt-4o` chấm 1 điểm (vì thấy vô dụng), tôi phải đóng vai trò là người phân xử cuối cùng. Tôi đã chọn tin vào Judge có năng lực lý luận cao hơn (`gpt-4o`) để đảm bảo tính khắt khe cho bản Failure Analysis.

## 4. Bài học kinh nghiệm

### Vai trò của người "Gác cổng"

Tôi học được rằng người làm Failure Analysis không chỉ là người tìm lỗi, mà là người kết nối các mảnh ghép. Tôi phải hiểu phần Data của Sơn để biết tại sao Hit Rate thấp, hiểu phần Agent của Quí để biết tại sao có placeholder. Lead của khâu cuối cùng chính là người nắm giữ "bức tranh toàn cảnh".

### Tầm quan trọng của Ground Truth

Nếu không có bộ Ground Truth chuẩn từ Sơn, tôi không thể xác định được lỗi là do "tìm sai" hay "trả lời sai". Bài học ở đây là: Mọi bản phân tích thất bại đều chỉ có giá trị khi dữ liệu đối chứng (Expected Answer) đủ mạnh.


## 5. Nếu làm lại, tôi sẽ cải tiến gì

Nếu có thêm thời gian, tôi muốn cải tiến phần của mình theo ba hướng:

- <b>Tự động hóa Failure Clustering</b>: Tôi sẽ viết thêm script để tự động nhóm các case có cùng nguyên nhân lỗi (ví dụ: cùng dùng chung một placeholder) thay vì phải đếm thủ công.
- <b>Xây dựng Dashboard so sánh<b>: Thay vì chỉ nhìn file JSON, tôi muốn có một bảng so sánh song song câu trả lời của V1 và V2 để thấy rõ sự sụt giảm nằm ở đâu.
- <b>Thêm tiêu chí "Thân thiện" (Empathy) vào Gate</b>: Trong y tế, ngoài chính xác, câu trả lời cần sự cảm thông. Tôi sẽ thêm tiêu chí này vào bộ lọc Regression Gate.

