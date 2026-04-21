# Kế Hoạch & Phân Công Nhiệm Vụ - Lab 14: AI Evaluation Factory

## Đề tài: AI Evaluation System cho Healthcare Support Chatbot
Xây dựng hệ thống benchmark tự động để đánh giá chất lượng RAG Agent, bao gồm: tạo Golden Dataset, chạy Multi-Judge, đo Retrieval Quality, so sánh V1 vs V2, và phân tích nguyên nhân gốc rễ.

---

## 1. Thành viên & Điểm mạnh (từ Lab 13)

| Thành viên | Điểm mạnh từ Lab 13 | Vai trò Lab 14 |
| :--- | :--- | :--- |
| **Trần Quang Quí** | Backend/Infra — Logging & PII (100/100) | **Regression Gate + Failure Analysis** |
| **Đoàn Nam Sơn** | LLM Integration — Langfuse Tracing | **Golden Dataset & SDG** |
| **Vũ Đức Duy** | Dashboards & Reporting | **Async Runner + Cost Report** |
| **Hoàng Vĩnh Giang** | Load Testing & Incidents | **Retrieval Eval + Agent Integration** |
| **Nhữ Gia Bách** | SLO/Alerts & Analysis | **Multi-Judge Consensus Engine** |

---

## 2. Chi tiết nhiệm vụ từng thành viên

---

### Trần Quang Quí — Regression Gate + Failure Analysis (10+5 điểm nhóm)
**File chính:** `main.py` (phần regression), `analysis/failure_analysis.md`

**Nhiệm vụ cụ thể:**
- [ ] Implement logic Regression Gate thực sự trong `main.py`:
  - `avg_score`: V2 phải >= V1 (không giảm)
  - `hit_rate`: V2 phải >= V1 - 0.05 (cho phép giảm tối đa 5%)
  - `p95_latency`: V2 phải <= V1 * 1.2 (không chậm hơn 20%)
  - Output: `APPROVE` nếu tất cả pass, `BLOCK RELEASE` kèm lý do cụ thể
- [ ] Lưu kết quả regression vào `reports/summary.json` với field `regression`:
  ```json
  "regression": {"v1_score": 3.5, "v2_score": 4.0, "delta": 0.5, "decision": "APPROVE"}
  ```
- [ ] Sau khi benchmark chạy xong → điền đầy đủ `analysis/failure_analysis.md`:
  - Điền số thực (không để X/Y placeholder)
  - Chọn 3 case tệ nhất, viết 5 Whys thực sự
  - Đề xuất cải tiến + section "Giảm 30% chi phí"
- [ ] Đảm bảo `python check_lab.py` pass hoàn toàn trước khi submit

**Điều kiện làm được:** Cần Bách xong Multi-Judge + Giang xong Retrieval + Duy xong runner → chạy `python main.py` lấy kết quả thực.

**Reflection cá nhân cần đề cập:** Tại sao cần Release Gate tự động; 5 Whys methodology; trade-off giữa Quality và Cost khi làm eval.

---

### Đoàn Nam Sơn — Golden Dataset & SDG (10 điểm nhóm)
**File chính:** `data/synthetic_gen.py`

**Nhiệm vụ cụ thể:**
- [ ] Implement `generate_qa_from_text()` dùng Anthropic/OpenAI API với prompt có cấu trúc để sinh Q/A
- [ ] Tạo **50+ test cases** với phân phối:
  - 30 cases easy/medium (fact-check, thủ tục, hướng dẫn)
  - 10 cases hard: Out-of-context (Agent phải nói "không biết")
  - 5 cases adversarial: Prompt injection, Goal hijacking
  - 5 cases edge: Conflicting info, Ambiguous question
- [ ] Mỗi case có đủ fields: `question`, `expected_answer`, `context`, `ground_truth_doc_ids`, `metadata.difficulty`, `metadata.type`
- [ ] `ground_truth_doc_ids` là list doc ID để `RetrievalEvaluator` tính Hit Rate
- [ ] Chạy `python data/synthetic_gen.py` → tạo `data/golden_set.jsonl` với ≥ 50 dòng
- [ ] Kiểm tra: `python -c "import json; lines=[json.loads(l) for l in open('data/golden_set.jsonl')]; print(len(lines))"`

**Output mẫu:**
```json
{"question": "Quy trình đặt lịch xét nghiệm máu là gì?", "expected_answer": "Bệnh nhân cần...", "context": "Theo nội quy bệnh viện...", "ground_truth_doc_ids": ["doc_hospital_policy_03"], "metadata": {"difficulty": "easy", "type": "procedure"}}
```

**Reflection cá nhân cần đề cập:** Tại sao cần hard/adversarial cases; trade-off giữa synthetic vs. real data; cách tạo ground truth IDs có ý nghĩa.

---

### Vũ Đức Duy — Async Runner + Cost Report (10 điểm nhóm)
**File chính:** `engine/runner.py`, `main.py` (phần cost tracking)

**Nhiệm vụ cụ thể:**
- [ ] Nâng cấp `BenchmarkRunner.run_all()`: thêm progress bar (tqdm), đo tổng thời gian
- [ ] Thêm `Semaphore` vào runner để control concurrency thực sự (không chỉ batch_size)
- [ ] Collect cost data từ mỗi `run_single_test()`: tổng hợp `total_tokens`, `total_cost_usd`
- [ ] Thêm vào `reports/summary.json` các fields:
  - `performance.total_time_seconds`
  - `performance.avg_latency_ms`
  - `performance.p95_latency_ms`
  - `cost.total_tokens_used`
  - `cost.total_cost_usd`
  - `cost.cost_per_eval`
- [ ] Viết section đề xuất: "Cách giảm 30% chi phí eval" trong `analysis/failure_analysis.md` (ví dụ: dùng Haiku thay GPT-4o cho initial scoring)
- [ ] Đảm bảo 50 cases chạy xong **< 2 phút**

**Reflection cá nhân cần đề cập:** Async vs. threading trong Python; Semaphore rate limiting; trade-off giữa tốc độ và chi phí.

---

### Hoàng Vĩnh Giang — Retrieval Eval + Agent Integration (10 điểm nhóm)
**File chính:** `engine/retrieval_eval.py`, `agent/main_agent.py`

**Nhiệm vụ cụ thể:**
- [ ] Nâng cấp `RetrievalEvaluator.evaluate_batch()`: thay placeholder bằng logic thực tế lấy `retrieved_ids` từ Agent response và so với `ground_truth_doc_ids` trong dataset
- [ ] Agent `query()` phải trả về `retrieved_doc_ids` trong response (cần sửa `agent/main_agent.py`)
- [ ] Tính Hit Rate và MRR thực sự cho toàn bộ 50 cases
- [ ] Thêm kết quả vào từng `run_single_test()` result:
  ```json
  "retrieval": {"hit_rate": 0.8, "mrr": 0.65, "retrieved_ids": [...]}
  ```
- [ ] Viết agent thực tế (có thể tái dùng từ Lab trước) hoặc mock có `retrieved_doc_ids` hợp lệ
- [ ] Chứng minh mối liên hệ: cases có hit_rate = 0 → judge_score thấp → Hallucination

**Reflection cá nhân cần đề cập:** Hit Rate vs. MRR — khi nào dùng cái nào; tại sao Retrieval eval quan trọng hơn Generation eval; Hallucination từ retrieval fail.

---

### Nhữ Gia Bách — Multi-Judge Consensus Engine (15 điểm nhóm)
**File chính:** `engine/llm_judge.py`

**Nhiệm vụ cụ thể:**
- [ ] Implement `evaluate_multi_judge()` gọi **thật** 2 model: OpenAI `gpt-4o` + Anthropic `claude-3-5-haiku`
- [ ] Mỗi model chấm điểm độc lập theo rubric: Accuracy (1-5), Professionalism (1-5), Safety (pass/fail)
- [ ] Tính `agreement_rate` = `1.0 if |scoreA - scoreB| <= 1 else 0.5`
- [ ] Logic xử lý xung đột: nếu lệch > 1 điểm → gọi model thứ 3 làm tiebreaker (hoặc lấy median)
- [ ] Implement `check_position_bias()`: swap thứ tự response A/B, check xem Judge có cho điểm khác không
- [ ] Thêm tracking: `tokens_used`, `cost_usd` cho mỗi lần judge

**Output mẫu mong đợi:**
```json
{
  "final_score": 4.0,
  "agreement_rate": 0.8,
  "individual_scores": {"gpt-4o": 4, "claude-3-5-haiku": 4},
  "conflict_resolved": false,
  "cost_usd": 0.003,
  "reasoning": "Cả 2 model đồng ý response đúng về nội dung..."
}
```

**Reflection cá nhân cần đề cập:** Trade-off giữa chi phí multi-judge vs. độ tin cậy; Cohen's Kappa vs. raw agreement; Position Bias là gì và cách detect.

---

## 3. Luồng làm việc & Dependencies

```
Sơn (SDG) → tạo data/golden_set.jsonl
     ↓
Giang (Agent) → implement agent trả về retrieved_doc_ids
     ↓
Bách (Multi-Judge) + Giang (Retrieval Eval) → chạy song song
     ↓
Duy (Async Runner) → kết nối tất cả, chạy benchmark
     ↓
Quí (Regression Gate) → chạy main.py, điền failure_analysis.md
     ↓
Tất cả → viết reflection cá nhân
```

**Blocking dependencies:**
- Sơn phải xong `golden_set.jsonl` trước → mọi người else cần file này để test
- Giang phải có `retrieved_doc_ids` trong agent response → Bách và Retrieval Eval mới tích hợp được
- Bách phải xong multi-judge → Duy mới collect cost data đầy đủ
- **Quí làm cuối** — cần có kết quả benchmark thực từ Duy mới điền được failure_analysis.md

---

## 4. Lộ trình Sprint (4 tiếng)

### Sprint 1 — Nền tảng [Tiếng 1, ~45 phút]
**Mục tiêu:** Có file data + agent chạy được

| Thành viên | Việc cần làm | Done khi |
| :--- | :--- | :--- |
| **Sơn** | Implement `generate_qa_from_text()` với LLM API, chạy ra 50+ cases | `python data/synthetic_gen.py` → `data/golden_set.jsonl` có ≥ 50 dòng |
| **Giang** | Sửa `agent/main_agent.py` để trả về `retrieved_doc_ids`, implement `evaluate_batch()` thực sự | Agent query trả về `{"answer": ..., "retrieved_doc_ids": [...]}` |
| **Bách** | Setup API keys, implement skeleton `evaluate_multi_judge()` với 2 real API calls | Function chạy không lỗi, trả về JSON đúng format |
| **Duy** | Thêm `asyncio.Semaphore`, progress bar, đo latency vào runner | `run_all()` print progress và thời gian tổng |
| **Quí** | Đọc kỹ rubric, chuẩn bị template `failure_analysis.md` + skeleton Regression Gate | `main.py` có 3 điều kiện Gate, chờ kết quả thực để điền |

### Sprint 2 — Integration [Tiếng 2-3, ~90 phút]
**Mục tiêu:** Toàn pipeline chạy end-to-end

| Thành viên | Việc cần làm | Done khi |
| :--- | :--- | :--- |
| **Bách** | Hoàn thiện conflict resolution (tiebreaker), position bias check, cost tracking | `evaluate_multi_judge()` xử lý được mọi trường hợp |
| **Sơn** | Review data quality, thêm 10 hard/adversarial cases nếu thiếu | Có ≥ 10 hard cases trong `golden_set.jsonl` |
| **Giang** | Kết nối `RetrievalEvaluator` vào `BenchmarkRunner.run_single_test()` | Mỗi kết quả có field `retrieval.hit_rate` và `retrieval.mrr` |
| **Duy** | Collect cost data từ multi-judge, tính p95 latency | `reports/summary.json` có đủ fields cost + performance |
| **Quí** | Hoàn thiện Regression Gate logic, chạy thử `python main.py` | Hai file `reports/*.json` tồn tại và đúng format |

### Sprint 3 — Benchmark & Analysis [Tiếng 3, ~60 phút]
**Mục tiêu:** Có kết quả thực, phân tích được

| Thành viên | Việc cần làm |
| :--- | :--- |
| **Quí** | Chạy full benchmark, điền số thực vào `analysis/failure_analysis.md`, viết 5 Whys cho 3 case tệ nhất |
| **Giang** | Phân tích các cases hit_rate = 0, cung cấp cho Quí thông tin về Hallucination |
| **Bách** | Tính agreement rate thực, liệt kê cases 2 judge bất đồng để Quí phân tích |
| **Duy** | Cung cấp cost data thực cho Quí → viết section "Giảm 30% chi phí" |
| **Sơn** | Review toàn bộ dataset, đảm bảo ground_truth_doc_ids mapping đúng |

### Sprint 4 — Polish & Submit [Tiếng 4, ~45 phút]
**Mục tiêu:** Pass check_lab.py, xong reflections

- [ ] **Quí:** Chạy `python check_lab.py` → sửa đến khi pass hoàn toàn, commit + push
- [ ] **Cả nhóm:** Mỗi người viết `analysis/reflections/reflection_[Tên_SV].md`
- [ ] **Quí:** Kiểm tra không có `.env` trong repo trước khi push
- [ ] **Sơn:** Đảm bảo `data/golden_set.jsonl` được add vào `.gitignore`

---

## 5. Checklist nộp bài

- [ ] `reports/summary.json` có `metrics.hit_rate` + `metrics.agreement_rate` + `regression`
- [ ] `reports/benchmark_results.json` có ≥ 50 entries
- [ ] `analysis/failure_analysis.md` đã điền số thực (không còn X/Y)
- [ ] `analysis/reflections/reflection_TranQuangQui.md`
- [ ] `analysis/reflections/reflection_DoanNamSon.md`
- [ ] `analysis/reflections/reflection_VuDucDuy.md`
- [ ] `analysis/reflections/reflection_HoangVinhGiang.md`
- [ ] `analysis/reflections/reflection_NhuGiaBach.md`
- [ ] `python check_lab.py` → không có dòng nào bắt đầu bằng ❌

---

## 6. Điểm liệt cần tránh

> ⚠️ **Nếu chỉ có 1 judge hoặc không có hit_rate trong summary.json → điểm nhóm tối đa 30/60.**

- Quí phải đảm bảo `individual_scores` có **đúng 2 keys khác nhau** (e.g. `gpt-4o` và `claude-3-5-haiku`)
- Giang phải đảm bảo `hit_rate` có trong mỗi benchmark result
- Bách phải đảm bảo `metrics.hit_rate` và `metrics.agreement_rate` có trong `reports/summary.json`
