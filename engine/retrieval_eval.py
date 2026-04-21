from typing import List, Dict

class RetrievalEvaluator:
    def __init__(self):
        pass

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        """
        TODO: Tính toán xem ít nhất 1 trong expected_ids có nằm trong top_k của retrieved_ids không.
        """
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """
        TODO: Tính Mean Reciprocal Rank.
        Tìm vị trí đầu tiên của một expected_id trong retrieved_ids.
        MRR = 1 / position (vị trí 1-indexed). Nếu không thấy thì là 0.
        """
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        """
        Tính Hit Rate và MRR thực sự cho toàn bộ dataset.
        Mỗi case cần có 'ground_truth_doc_ids' và 'retrieved_doc_ids'.
        """
        hit_rates = []
        mrrs = []
        per_case = []

        for case in dataset:
            expected_ids = case.get("ground_truth_doc_ids", [])
            retrieved_ids = case.get("retrieved_doc_ids", [])

            hit = self.calculate_hit_rate(expected_ids, retrieved_ids)
            mrr = self.calculate_mrr(expected_ids, retrieved_ids)

            hit_rates.append(hit)
            mrrs.append(mrr)
            per_case.append({
                "question": case.get("question", ""),
                "hit_rate": hit,
                "mrr": mrr,
                "retrieved_ids": retrieved_ids,
                "expected_ids": expected_ids,
            })

        avg_hit_rate = sum(hit_rates) / len(hit_rates) if hit_rates else 0.0
        avg_mrr = sum(mrrs) / len(mrrs) if mrrs else 0.0

        return {
            "avg_hit_rate": round(avg_hit_rate, 4),
            "avg_mrr": round(avg_mrr, 4),
            "per_case": per_case,
        }
