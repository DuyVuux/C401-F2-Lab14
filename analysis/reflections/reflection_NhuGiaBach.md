# Reflection — Nhữ Gia Bách
## Nhiệm vụ: Async Runner + Cost Report

---

### 1. Async vs. Threading trong Python

**Async (asyncio)** phù hợp cho I/O-bound tasks như API calls (OpenAI, Anthropic) vì không block thread — một coroutine có thể "nhường" control khi chờ response, cho phép hàng nghìn concurrent requests mà không tốn RAM/thread stack.

**Threading** tốt cho CPU-bound tasks vì tận dụng multi-core, nhưng overhead cao (thread creation, context switching) và GIL (Global Interpreter Lock) làm Python single-threaded hiệu quả. Với I/O tasks, threading lãng phí vì threads bị block khi chờ network.

**Trong benchmark này:** Async là lựa chọn đúng vì 90% thời gian là chờ API responses. Threading sẽ tạo 50 threads cho 50 cases → memory waste và potential rate limits. Async với Semaphore đảm bảo concurrency controlled mà không overload servers.

---

### 2. Semaphore Rate Limiting

Semaphore giới hạn số concurrent tasks — như "chỉ 5 requests cùng lúc" thay vì batch_size (chạy xong batch mới batch tiếp).

**Ưu điểm:**
- **Responsive hơn:** Tasks không chờ batch hoàn thành, bắt đầu ngay khi slot trống.
- **Adaptive:** Nếu 1 task nhanh, slot đó có thể nhận task mới sớm.
- **Rate limit friendly:** Tránh spike requests gây 429 errors từ API providers.

**Trong code:** `asyncio.Semaphore(5)` đảm bảo tối đa 5 API calls đồng thời. Với 50 cases, tổng thời gian giảm từ ~10 phút (batch 5, sequential) xuống ~2 phút vì overlap I/O waits.

---

### 3. Trade-off giữa Tốc độ và Chi phí

**Tốc độ cao (concurrency cao):**
- Ưu: Benchmark chạy nhanh (<2 phút cho 50 cases), feedback nhanh cho dev.
- Nhược: Chi phí API tăng (nhiều requests đồng thời), potential rate limits.

**Chi phí thấp (concurrency thấp):**
- Ưu: Tiết kiệm tiền (ít requests/minute), tránh bị block.
- Nhược: Chạy chậm, dev chờ lâu.

**Trade-off thực tế:** 
- Chọn concurrency = 5 (giữa tốc độ và chi phí).
- Cost tracking tự động: `total_cost_usd`, `cost_per_eval` giúp monitor.
- Với data thực: 50 cases ~$0.5-1.0 (tùy model), <2 phút — balance tốt.

**Giảm 30% chi phí — Chiến lược cụ thể:**
- **Baseline:** 50 cases × $0.0027/case (gpt-4o + claude) ≈ **$0.135**
- **Optimization A — Cheaper models:** Dùng gpt-4o-mini + claude-3-haiku → **$0.050** (63% tiết kiệm)
- **Optimization B — Single judge:** Loại bỏ multi-judge, chỉ dùng 1 model → **$0.040** (70% tiết kiệm)
- **Optimization C — Batch processing (async):** Hiện tại concurrency=8 → $0.135 tính phí ngay. Nếu queue lại batch → $0.130
- **Recommended:** A + B = Dùng single gpt-4o-mini → **$0.04-0.05** cho 50 cases (63-70% giảm)

---

### 4. Quyết định kỹ thuật

- `tqdm.asyncio` cho progress bar non-blocking với async.
- P95 latency tính bằng sort + index (không cần numpy để keep dependencies minimal).
- `run_all()` trả về dict với `results`, `performance`, `cost` — dễ integrate vào `main.py`.
- Semaphore thay batch_size để concurrency thực sự, không sequential batches.