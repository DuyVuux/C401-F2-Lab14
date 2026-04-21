import asyncio
import time
from typing import List, Dict
from tqdm.asyncio import tqdm
from engine.retrieval_eval import RetrievalEvaluator

class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge, concurrency_limit: int = 8):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge
        self.retrieval_evaluator = RetrievalEvaluator()
        self.concurrency_limit = concurrency_limit

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        
        # 1. Gọi Agent
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time
        
        # 2. Tính Retrieval metrics (hit_rate, mrr)
        retrieved_ids = response.get("retrieved_doc_ids", [])
        expected_ids = test_case.get("ground_truth_doc_ids", [])
        retrieval_result = {
            "hit_rate": self.retrieval_evaluator.calculate_hit_rate(expected_ids, retrieved_ids),
            "mrr": self.retrieval_evaluator.calculate_mrr(expected_ids, retrieved_ids),
            "retrieved_ids": retrieved_ids,
        }

        # 3. Chạy RAGAS metrics
        ragas_scores = await self.evaluator.score(test_case, response)
        # Gắn retrieval vào ragas để main.py đọc được
        ragas_scores["retrieval"] = retrieval_result

        # 4. Chạy Multi-Judge
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"]
        )

        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "latency": latency,
            "ragas": ragas_scores,
            "retrieval": retrieval_result,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass"
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> Dict:
        """
        Chạy song song với Semaphore để control concurrency, progress bar, đo tổng thời gian.
        """
        print(f"⚡ Running {len(dataset)} cases with concurrency_limit={self.concurrency_limit}")
        semaphore = asyncio.Semaphore(self.concurrency_limit)
        start_time = time.perf_counter()

        async def run_with_semaphore(case):
            async with semaphore:
                return await self.run_single_test(case)

        tasks = [run_with_semaphore(case) for case in dataset]
        
        results = []
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Benchmarking"):
            result = await coro
            results.append(result)

        total_time = time.perf_counter() - start_time

        # Collect metrics
        latencies = [r["latency"] for r in results]
        costs = [r["judge"].get("cost_usd", 0.0) for r in results]
        tokens = [r["judge"].get("tokens_used", 0) for r in results]

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        if results:
            print(f"✅ Completed in {total_time:.2f}s | Avg {avg_latency * 1000:.1f}ms/case")
        sorted_latencies = sorted(latencies)
        if len(sorted_latencies) > 0:
            p95_idx = max(0, int(0.95 * len(sorted_latencies)) - 1)
            p95_latency = sorted_latencies[p95_idx]
        else:
            p95_latency = 0.0

        total_cost = sum(costs)
        total_tokens = sum(tokens)
        cost_per_eval = total_cost / len(results) if results else 0.0

        return {
            "results": results,
            "performance": {
                "total_time_seconds": round(total_time, 2),
                "avg_latency_ms": round(avg_latency * 1000, 2),
                "p95_latency_ms": round(p95_latency * 1000, 2),
            },
            "cost": {
                "total_tokens_used": total_tokens,
                "total_cost_usd": round(total_cost, 6),
                "cost_per_eval": round(cost_per_eval, 6),
            }
        }
