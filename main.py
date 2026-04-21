import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge

# Giả lập các components Expert
class ExpertEvaluator:
    async def score(self, case, resp): 
        # Giả lập tính toán Hit Rate và MRR
        return {
            "faithfulness": 0.9, 
            "relevancy": 0.8,
            "retrieval": {"hit_rate": 1.0, "mrr": 0.5}
        }

def evaluate_regression_gate(v1_metrics, v2_metrics):
    """
    Giang thực hiện: Logic quyết định dựa trên đa chỉ số.
    Chỉ APPROVE khi chất lượng không giảm và Retrieval ổn định.
    """
    decisions = []
    is_passed = True

    # 1. Kiểm tra Điểm trung bình (Score)
    score_delta = v2_metrics['avg_score'] - v1_metrics['avg_score']
    if score_delta < 0:
        is_passed = False
        decisions.append(f"❌ Chất lượng giảm: {score_delta:.2f} điểm")
    
    # 2. Kiểm tra Retrieval (Hit Rate) - Cho phép sai số tối đa 5%
    if v2_metrics['hit_rate'] < (v1_metrics['hit_rate'] - 0.05):
        is_passed = False
        decisions.append(f"❌ Retrieval sụt giảm nghiêm trọng (V2: {v2_metrics['hit_rate']*100:.1f}%)")

    status = "✅ APPROVE" if is_passed else "❌ BLOCK RELEASE"
    reason = "Mọi chỉ số đều đạt hoặc vượt yêu cầu" if is_passed else " | ".join(decisions)
    
    return {
        "decision": status,
        "reason": reason,
        "delta_score": score_delta
    }

async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    runner = BenchmarkRunner(MainAgent(), ExpertEvaluator(), LLMJudge())
    run_result = await runner.run_all(dataset)

    results = run_result["results"]
    performance = run_result["performance"]
    cost = run_result["cost"]

    total = len(results)
    summary = {
        "metadata": {"version": agent_version, "total": total, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
        "metrics": {
            "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
            "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total
        },
        "performance": performance,
        "cost": cost,
    }
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary

async def main():
    # 1. Chạy Benchmark cho bản cũ
    v1_summary = await run_benchmark("Agent_V1_Base")
    
    # 2. Chạy Benchmark cho bản mới
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")
    
    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    # 3. GỌI LOGIC REGRESSION GATE (Phần của Giang)
    regression_result = evaluate_regression_gate(v1_summary['metrics'], v2_summary['metrics'])
    
    print("\n" + "="*50)
    print("📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    print(f"V1 Score: {v1_summary['metrics']['avg_score']:.2f} | Hit Rate: {v1_summary['metrics']['hit_rate']*100:.1f}%")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']:.2f} | Hit Rate: {v2_summary['metrics']['hit_rate']*100:.1f}%")
    print(f"Delta Score: {'+' if regression_result['delta_score'] >= 0 else ''}{regression_result['delta_score']:.2f}")
    print(f"\n📢 QUYẾT ĐỊNH CUỐI CÙNG: {regression_result['decision']}")
    print(f"Lý do: {regression_result['reason']}")
    print("="*50)

    # 4. Lưu trữ báo cáo
    # Tích hợp kết quả Gate vào summary để nộp bài
    v2_summary["regression_decision"] = regression_result

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    print("\n✅ Đã lưu báo cáo tại thư mục reports/")

if __name__ == "__main__":
    asyncio.run(main())
