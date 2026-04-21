# Personal Reflection - Đoàn Nam Sơn

## 1. Vai trò và phần việc đã thực hiện

Trong Lab 14, tôi phụ trách phần **Golden Dataset & SDG**. Mục tiêu của tôi không chỉ là tạo ra một file dữ liệu đủ số lượng, mà là xây dựng một bộ benchmark có thể dùng làm đầu vào ổn định cho toàn bộ pipeline đánh giá phía sau, gồm Retrieval Eval, Multi-Judge và Regression Gate.

Phần việc tôi đã hoàn thành gồm ba phần chính:

- Chuẩn hóa nguồn tri thức từ tài liệu [data/healthcare_guidelines.md](data/healthcare_guidelines.md) thành các đơn vị thông tin có thể gắn `ground_truth_doc_ids` rõ ràng.
- Giữ lại và chuẩn hóa 10 test cases seed ban đầu từ [tests/golden_set.json](tests/golden_set.json) để làm mốc cho dataset cuối.
- Viết lại hoàn chỉnh script [data/synthetic_gen.py](data/synthetic_gen.py) để tạo ra file [data/golden_set.jsonl](data/golden_set.jsonl) theo đúng contract mà benchmark runtime sử dụng.

Dataset cuối cùng tôi tạo ra có **51 cases**, trong đó phân phối difficulty đạt yêu cầu của đề bài:

- `easy`: 20
- `medium`: 11
- `hard`: 10
- `adversarial`: 5
- `edge`: 5

Như vậy, bộ dữ liệu đạt các ngưỡng bắt buộc: ít nhất 30 easy/medium, 10 hard, 5 adversarial và 5 edge.

## 2. Các quyết định kỹ thuật quan trọng

### 2.1. Ưu tiên tính ổn định hơn là phụ thuộc hoàn toàn vào API

Ban đầu yêu cầu bài lab có nhắc tới việc dùng OpenAI hoặc Anthropic để sinh Q/A. Tuy nhiên, nếu pipeline SDG phụ thuộc hoàn toàn vào API thì sẽ có ba rủi ro:

- kết quả không ổn định giữa các lần chạy,
- khó kiểm soát phân phối difficulty/type đúng yêu cầu,
- có thể chặn tiến độ của các thành viên khác nếu thiếu API key hoặc bị rate limit.

Vì vậy, tôi chọn cách thiết kế **generator theo hướng deterministic-first**. Cụ thể, script chính dùng curated cases để đảm bảo luôn sinh ra cùng một bộ dữ liệu hợp lệ, còn `generate_qa_from_text()` vẫn được giữ như một nhánh mở rộng có thể dùng OpenAI nếu môi trường có API key. Cách làm này phù hợp hơn với nhu cầu của nhóm trong bối cảnh bài lab có dependency chaining rõ ràng: nếu `golden_set.jsonl` không sẵn sàng thì các phần Retrieval, Judge và Runner đều bị chặn.

### 2.2. Tạo `ground_truth_doc_ids` có nghĩa thay vì đặt tên tùy ý

Tôi không dùng các ID mơ hồ như `doc_01`, `doc_02`, mà xây dựng các ID có cấu trúc như:

- `healthcare_guideline_SEC1_APPOINTMENT`
- `healthcare_guideline_SEC5_PRIVACY`
- `healthcare_guideline_SEC9_INTERPRETER`

Cách đặt tên này có ba lợi ích:

- đọc vào là hiểu ngay tài liệu và section liên quan,
- giúp teammate làm Retrieval Eval đối chiếu dễ hơn,
- giảm rủi ro mapping sai khi phân tích lỗi sau benchmark.

Trong hệ thống eval thực tế, chất lượng `ground_truth_doc_ids` quan trọng gần như ngang với chất lượng câu hỏi, vì nếu ground truth không rõ ràng thì Hit Rate và MRR sẽ mất ý nghĩa.

### 2.3. Chuẩn hóa contract dữ liệu để giảm lỗi tích hợp

Trong workspace, tôi thấy benchmark runtime trong [main.py](main.py) đọc từ `data/golden_set.jsonl`, trong khi seed cases ban đầu đang ở [tests/golden_set.json](tests/golden_set.json). Đây là một điểm dễ gây lỗi tích hợp. Vì vậy tôi chủ động thiết kế script sao cho:

- `tests/golden_set.json` đóng vai trò seed input,
- `data/golden_set.jsonl` là benchmark artifact cuối cùng,
- mỗi row đều có đủ các field bắt buộc: `question`, `expected_answer`, `context`, `ground_truth_doc_ids`, `metadata.difficulty`, `metadata.type`.

Điểm tôi học được ở đây là: trong một pipeline nhiều người làm, việc “chốt contract dữ liệu” sớm thường quan trọng hơn việc làm generator quá thông minh.

## 3. Vì sao cần hard cases và adversarial cases

Nếu chỉ tạo các câu hỏi easy hoặc medium theo kiểu fact lookup, benchmark sẽ dễ cho ra cảm giác agent hoạt động tốt dù thực tế còn rất nhiều failure mode chưa được đo. Điều này đặc biệt nguy hiểm trong domain healthcare vì sai sót không chỉ là “trả lời dở” mà có thể dẫn đến tư vấn nhầm, rò rỉ thông tin y tế hoặc trả lời quá tự tin khi không có dữ kiện.

Tôi cố tình thêm các nhóm case khó vì các lý do sau:

### 3.1. Hard / Out-of-context

Các case hard buộc agent phải biết nói “không có trong tài liệu” thay vì bịa. Đây là bài test rất quan trọng vì trong hệ RAG thực tế, một model trả lời trôi chảy chưa chắc đã an toàn. Nếu retrieval fail mà generation vẫn cố trả lời, hệ thống sẽ hallucinate. Do đó, hard cases giúp đo một năng lực nền tảng: **khả năng từ chối đúng lúc**.

### 3.2. Adversarial / Prompt Injection / Goal Hijacking

Trong hệ hỗ trợ bệnh viện, prompt injection không phải chỉ là một bài tập lý thuyết. Tôi đã đưa vào các case có nội dung yêu cầu chatbot bỏ qua quy định, tiết lộ hồ sơ bệnh án hoặc thực hiện hành vi trái pháp luật. Các case này giúp kiểm tra xem hệ thống có:

- giữ được nhiệm vụ chính,
- ưu tiên policy an toàn,
- và từ chối phần độc hại trong khi vẫn trả lời phần hợp lệ nếu có.

Điểm tôi rút ra là một benchmark tốt không chỉ đo đúng/sai về factuality, mà còn phải đo **boundary behavior** của agent.

### 3.3. Edge / Ambiguity / Conflicting Info

Healthcare support không phải lúc nào cũng có câu hỏi đủ dữ kiện. Có nhiều tình huống người dùng hỏi thiếu thông tin, ví dụ không nói rõ bệnh nhân đang nằm khoa nào nhưng lại hỏi có được mang thức ăn vào không. Những case như vậy giúp kiểm tra xem agent có biết yêu cầu làm rõ hay không.

Tôi cũng đưa vào các case kiểu conflicting-info hoặc policy-exception để đảm bảo benchmark không thiên lệch về dạng “copy một câu từ context ra là đủ”.

## 4. Trade-off giữa synthetic data và real data

Đây là điểm tôi thấy rõ nhất khi làm phần SDG.

### Ưu điểm của synthetic data

- Tạo nhanh và có thể phủ đều nhiều loại difficulty.
- Dễ kiểm soát format, ground truth và phân phối case.
- Phù hợp với bài lab vì nhóm cần có bộ dữ liệu dùng được ngay cho pipeline benchmark.

### Hạn chế của synthetic data

- Ngôn ngữ có thể “quá sạch”, chưa phản ánh đúng cách người dùng thật đặt câu hỏi.
- Dễ mang bias của người tạo dữ liệu.
- Nếu không cẩn thận, câu hỏi và expected answer sẽ quá sát với source text, làm benchmark trở nên dễ hơn thực tế.

### So với real data

Real user queries thường có lỗi chính tả, thiếu ngữ cảnh, dùng từ địa phương, hoặc trộn nhiều ý trong cùng một câu. Đó là thứ synthetic data khó mô phỏng hoàn toàn. Vì vậy, nếu triển khai trong sản phẩm thật, tôi sẽ xem bộ dữ liệu synthetic hiện tại là **baseline dataset** để khởi động hệ thống eval, sau đó dần dần bổ sung dữ liệu từ log thật đã được ẩn danh và kiểm duyệt.

Tóm lại, trade-off tôi chọn là:

- dùng synthetic data để đạt coverage nhanh, có cấu trúc và có thể benchmark ngay,
- nhưng luôn coi đó là bước đầu, không phải nguồn chân lý cuối cùng.

## 5. Khó khăn gặp phải và cách tôi xử lý

Khó khăn lớn nhất không nằm ở việc viết nhiều câu hỏi, mà ở việc làm cho dataset **vừa hợp lệ về kỹ thuật, vừa hữu ích cho các bước eval phía sau**.

### 5.1. Sự lệch giữa seed file và benchmark runtime

Seed cases ban đầu ở dạng JSON array trong `tests/`, còn runtime lại yêu cầu JSONL trong `data/`. Nếu không xử lý chỗ này từ đầu thì rất dễ xảy ra tình trạng “có dữ liệu nhưng benchmark không đọc được”. Tôi xử lý bằng cách biến seed file thành input nguồn và để generator chịu trách nhiệm tạo artifact cuối cùng đúng định dạng.

### 5.2. Bảo đảm đủ phân phối difficulty/type

Nếu chỉ sinh dữ liệu tự do, rất khó đảm bảo chính xác số lượng 10 hard, 5 adversarial, 5 edge. Tôi giải quyết bằng cách curated trực tiếp các nhóm case này, sau đó kiểm tra lại bằng bước validation trong script. Cách này thực dụng hơn và giảm rủi ro fail requirement vào phút cuối.

### 5.3. Bảo toàn ý nghĩa retrieval ground truth

Một số câu hỏi chạm vào nhiều phần của guideline, ví dụ vừa liên quan xuất viện vừa liên quan trích lục hồ sơ. Trong các trường hợp đó, tôi phải quyết định khi nào dùng một ID, khi nào dùng nhiều ID. Điều này buộc tôi phải nghĩ như người làm Retrieval Eval chứ không chỉ như người viết câu hỏi.

## 6. Điều tôi học được

Qua phần việc này, tôi học được ba bài học chính.

Thứ nhất, trong các hệ thống AI evaluation, dữ liệu benchmark không chỉ là “danh sách câu hỏi”. Nó là một interface kỹ thuật giữa nhiều thành phần: retriever, generator, judge và regression gate.

Thứ hai, một bộ dữ liệu tốt phải đo được cả success path lẫn failure path. Nếu benchmark chỉ đo câu dễ, hệ thống sẽ tối ưu sai mục tiêu.

Thứ ba, trong bối cảnh làm việc nhóm, độ tin cậy và khả năng tái lập của artifact thường quan trọng hơn sự “thông minh” của giải pháp. Một generator deterministic, kiểm soát được output và có validation rõ ràng đã giúp phần việc của tôi hỗ trợ trực tiếp cho toàn bộ nhóm.

## 7. Nếu làm lại, tôi sẽ cải tiến gì

Nếu có thêm thời gian, tôi muốn cải tiến phần của mình theo ba hướng:

- Thêm metadata phong phú hơn như `section`, `risk_level`, `requires_clarification`, `safety_sensitive` để downstream analysis sâu hơn.
- Bổ sung một lớp paraphrase để câu hỏi tự nhiên hơn, gần ngôn ngữ người dùng thật hơn.
- Tạo thêm bộ “held-out set” riêng cho regression, tách khỏi bộ dùng để phát triển, để tránh benchmark bị overfit vào chính các case do nhóm tự nhìn thấy từ đầu.

## 8. Kết luận

Tôi đánh giá phần Golden Dataset & SDG là nền móng của cả bài lab. Nếu dữ liệu benchmark không đúng format, không có ground truth rõ ràng, hoặc không bao phủ các failure mode nguy hiểm, thì các chỉ số ở các bước sau sẽ không còn đáng tin.

Phần đóng góp của tôi là biến yêu cầu bài lab thành một artifact cụ thể, có thể chạy được ngay: một bộ dữ liệu 51 cases, có phân phối hợp lệ, có `ground_truth_doc_ids` có nghĩa, và có thể dùng trực tiếp làm đầu vào cho pipeline benchmark của nhóm.
