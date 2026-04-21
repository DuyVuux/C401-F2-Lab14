import asyncio
import random
from typing import List, Dict

ALL_DOC_IDS = [
    "healthcare_guideline_SEC1_APPOINTMENT",
    "healthcare_guideline_SEC2_VISIT",
    "healthcare_guideline_SEC3_EMERGENCY",
    "healthcare_guideline_SEC4_PAYMENT",
    "healthcare_guideline_SEC4_BHYT",
    "healthcare_guideline_SEC5_PRIVACY",
    "healthcare_guideline_SEC6_DISCHARGE",
    "healthcare_guideline_SEC7_MEDICATION",
]

KEYWORD_DOC_MAP = {
    "đặt lịch": "healthcare_guideline_SEC1_APPOINTMENT",
    "hủy lịch": "healthcare_guideline_SEC1_APPOINTMENT",
    "dời lịch": "healthcare_guideline_SEC1_APPOINTMENT",
    "hotline": "healthcare_guideline_SEC1_APPOINTMENT",
    "lễ tân": "healthcare_guideline_SEC1_APPOINTMENT",
    "healthcare app": "healthcare_guideline_SEC1_APPOINTMENT",
    "thăm": "healthcare_guideline_SEC2_VISIT",
    "nội trú": "healthcare_guideline_SEC2_VISIT",
    "trẻ em": "healthcare_guideline_SEC2_VISIT",
    "người nhà": "healthcare_guideline_SEC2_VISIT",
    "cấp cứu": "healthcare_guideline_SEC3_EMERGENCY",
    "khẩn cấp": "healthcare_guideline_SEC3_EMERGENCY",
    "đột quỵ": "healthcare_guideline_SEC3_EMERGENCY",
    "nhồi máu": "healthcare_guideline_SEC3_EMERGENCY",
    "chấn thương": "healthcare_guideline_SEC3_EMERGENCY",
    "thanh toán": "healthcare_guideline_SEC4_PAYMENT",
    "tiền mặt": "healthcare_guideline_SEC4_PAYMENT",
    "thẻ tín dụng": "healthcare_guideline_SEC4_PAYMENT",
    "chuyển khoản": "healthcare_guideline_SEC4_PAYMENT",
    "bhyt": "healthcare_guideline_SEC4_BHYT",
    "bảo hiểm": "healthcare_guideline_SEC4_BHYT",
    "trái tuyến": "healthcare_guideline_SEC4_BHYT",
    "đúng tuyến": "healthcare_guideline_SEC4_BHYT",
    "bảo mật": "healthcare_guideline_SEC5_PRIVACY",
    "hồ sơ": "healthcare_guideline_SEC5_PRIVACY",
    "bệnh án": "healthcare_guideline_SEC5_PRIVACY",
    "thông tin": "healthcare_guideline_SEC5_PRIVACY",
    "xuất viện": "healthcare_guideline_SEC6_DISCHARGE",
    "ra viện": "healthcare_guideline_SEC6_DISCHARGE",
    "thuốc": "healthcare_guideline_SEC7_MEDICATION",
    "đơn thuốc": "healthcare_guideline_SEC7_MEDICATION",
}


class MainAgent:
    def __init__(self):
        self.name = "SupportAgent-v1"

    def _retrieve_doc_ids(self, question: str) -> List[str]:
        """Simulated retrieval via keyword matching → returns ranked doc IDs."""
        q_lower = question.lower()
        scores: Dict[str, int] = {}
        for keyword, doc_id in KEYWORD_DOC_MAP.items():
            if keyword in q_lower:
                scores[doc_id] = scores.get(doc_id, 0) + 1

        ranked = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)

        # Fallback: random docs when no keyword matches (simulates retrieval noise)
        if not ranked:
            ranked = random.sample(ALL_DOC_IDS, k=min(2, len(ALL_DOC_IDS)))

        return ranked[:3]

    async def query(self, question: str) -> Dict:
        await asyncio.sleep(0.1)

        retrieved_doc_ids = self._retrieve_doc_ids(question)

        return {
            "answer": f"Dựa trên tài liệu hệ thống, câu trả lời cho câu hỏi của bạn là: [Câu trả lời mẫu từ tài liệu y tế].",
            "retrieved_doc_ids": retrieved_doc_ids,
            "contexts": [
                "Đoạn văn bản trích dẫn 1 dùng để trả lời...",
                "Đoạn văn bản trích dẫn 2 dùng để trả lời...",
            ],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": 150,
                "sources": retrieved_doc_ids,
            },
        }


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Tôi muốn đặt lịch khám, cần có mặt trước bao lâu?")
        print(resp)

    asyncio.run(test())
