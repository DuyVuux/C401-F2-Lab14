import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.llm_judge import (
    LLMJudge,
    _build_user_prompt,
    _calculate_cost,
    _compute_agreement,
    _safe_parse_json,
)


class TestSafeParseJson:
    def test_valid_json(self):
        raw = '{"accuracy": 4, "professionalism": 5, "safety": "pass", "reasoning": "Good"}'
        result = _safe_parse_json(raw)
        assert result["accuracy"] == 4
        assert result["professionalism"] == 5
        assert result["safety"] == "pass"

    def test_json_wrapped_in_markdown(self):
        raw = '```json\n{"accuracy": 3, "professionalism": 4, "safety": "fail", "reasoning": "Bad"}\n```'
        result = _safe_parse_json(raw)
        assert result is not None
        assert result["accuracy"] == 3
        assert result["safety"] == "fail"

    def test_json_with_no_fence_label(self):
        raw = '```\n{"accuracy": 5, "professionalism": 5, "safety": "pass", "reasoning": "OK"}\n```'
        result = _safe_parse_json(raw)
        assert result is not None
        assert result["accuracy"] == 5

    def test_regex_fallback(self):
        raw = 'Some text "accuracy": 4, more "professionalism": 3, and "safety": "pass" here'
        result = _safe_parse_json(raw)
        assert result is not None
        assert result["accuracy"] == 4
        assert result["professionalism"] == 3
        assert result["safety"] == "pass"

    def test_complete_garbage(self):
        raw = "This is complete garbage with no scores at all."
        result = _safe_parse_json(raw)
        assert result is None

    def test_empty_string(self):
        result = _safe_parse_json("")
        assert result is None


class TestCalculateCost:
    def test_gpt4o_cost(self):
        cost = _calculate_cost("gpt-4o", 1000, 500)
        expected = (1000 * 2.50 + 500 * 10.00) / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_claude_cost(self):
        cost = _calculate_cost("claude-3-5-haiku", 2000, 300)
        expected = (2000 * 0.80 + 300 * 4.00) / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_unknown_model_zero_cost(self):
        cost = _calculate_cost("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_zero_tokens(self):
        cost = _calculate_cost("gpt-4o", 0, 0)
        assert cost == 0.0


class TestComputeAgreement:
    def test_same_score(self):
        assert _compute_agreement(4, 4) == 1.0

    def test_diff_one(self):
        assert _compute_agreement(4, 3) == 1.0
        assert _compute_agreement(3, 4) == 1.0

    def test_diff_two(self):
        assert _compute_agreement(5, 3) == 0.5

    def test_diff_large(self):
        assert _compute_agreement(5, 1) == 0.5


class TestBuildUserPrompt:
    def test_prompt_contains_all_parts(self):
        prompt = _build_user_prompt("Question?", "Answer here", "Expected answer")
        assert "Question?" in prompt
        assert "Answer here" in prompt
        assert "Expected answer" in prompt


def _make_mock_judge_response(accuracy=4, professionalism=4, safety="pass", reasoning="Test"):
    return json.dumps({
        "accuracy": accuracy,
        "professionalism": professionalism,
        "safety": safety,
        "reasoning": reasoning,
    })


def _mock_openai_response(content, input_tokens=100, output_tokens=50):
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = input_tokens
    mock_usage.completion_tokens = output_tokens
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    return mock_response


def _mock_anthropic_response(content, input_tokens=100, output_tokens=50):
    mock_usage = MagicMock()
    mock_usage.input_tokens = input_tokens
    mock_usage.output_tokens = output_tokens
    mock_text = MagicMock()
    mock_text.text = content
    mock_response = MagicMock()
    mock_response.content = [mock_text]
    mock_response.usage = mock_usage
    return mock_response


@pytest.fixture
def judge():
    return LLMJudge()


class TestEvaluateMultiJudge:
    @pytest.mark.asyncio
    async def test_agreement_high(self, judge):
        openai_resp = _mock_openai_response(
            _make_mock_judge_response(accuracy=4, professionalism=4, safety="pass")
        )
        anthropic_resp = _mock_anthropic_response(
            _make_mock_judge_response(accuracy=4, professionalism=5, safety="pass")
        )

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=openai_resp)
        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=anthropic_resp)

        judge._openai_client = mock_openai_client
        judge._anthropic_client = mock_anthropic_client

        result = await judge.evaluate_multi_judge("Q?", "Answer", "Expected")

        assert result["agreement_rate"] == 1.0
        assert result["conflict_resolved"] is False
        assert result["final_score"] == 4.0
        assert "gpt-4o" in result["individual_scores"]
        assert "claude-3-5-haiku" in result["individual_scores"]
        assert result["cost_usd"] > 0
        assert result["tokens_used"] > 0
        assert isinstance(result["reasoning"], str)

    @pytest.mark.asyncio
    async def test_conflict_triggers_tiebreaker(self, judge):
        openai_resp = _mock_openai_response(
            _make_mock_judge_response(accuracy=5, professionalism=5, safety="pass")
        )
        anthropic_resp = _mock_anthropic_response(
            _make_mock_judge_response(accuracy=2, professionalism=2, safety="pass")
        )
        tiebreaker_resp = _mock_openai_response(
            _make_mock_judge_response(accuracy=4, professionalism=4, safety="pass")
        )

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[openai_resp, tiebreaker_resp]
        )
        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=anthropic_resp)

        judge._openai_client = mock_openai_client
        judge._anthropic_client = mock_anthropic_client

        result = await judge.evaluate_multi_judge("Q?", "Answer", "Expected")

        assert result["conflict_resolved"] is True
        assert result["agreement_rate"] == 0.5
        assert result["final_score"] == 4.0
        assert "gpt-4o-mini" in result["individual_scores"]

    @pytest.mark.asyncio
    async def test_safety_disagreement_triggers_tiebreaker(self, judge):
        openai_resp = _mock_openai_response(
            _make_mock_judge_response(accuracy=4, professionalism=4, safety="pass")
        )
        anthropic_resp = _mock_anthropic_response(
            _make_mock_judge_response(accuracy=4, professionalism=4, safety="fail")
        )
        tiebreaker_resp = _mock_openai_response(
            _make_mock_judge_response(accuracy=4, professionalism=4, safety="pass")
        )

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[openai_resp, tiebreaker_resp]
        )
        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=anthropic_resp)

        judge._openai_client = mock_openai_client
        judge._anthropic_client = mock_anthropic_client

        result = await judge.evaluate_multi_judge("Q?", "Answer", "Expected")

        assert result["conflict_resolved"] is True

    @pytest.mark.asyncio
    async def test_output_schema_complete(self, judge):
        openai_resp = _mock_openai_response(
            _make_mock_judge_response(accuracy=3, professionalism=3, safety="pass")
        )
        anthropic_resp = _mock_anthropic_response(
            _make_mock_judge_response(accuracy=3, professionalism=4, safety="pass")
        )

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=openai_resp)
        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=anthropic_resp)

        judge._openai_client = mock_openai_client
        judge._anthropic_client = mock_anthropic_client

        result = await judge.evaluate_multi_judge("Q?", "A", "GT")

        required_keys = {"final_score", "agreement_rate", "individual_scores",
                         "conflict_resolved", "cost_usd", "tokens_used", "reasoning"}
        assert required_keys.issubset(set(result.keys()))
        assert isinstance(result["final_score"], float)
        assert isinstance(result["agreement_rate"], float)
        assert isinstance(result["individual_scores"], dict)
        assert isinstance(result["conflict_resolved"], bool)
        assert isinstance(result["cost_usd"], float)
        assert isinstance(result["tokens_used"], int)
        assert isinstance(result["reasoning"], str)

    @pytest.mark.asyncio
    async def test_cost_tracking_accumulates(self, judge):
        openai_resp = _mock_openai_response(
            _make_mock_judge_response(), input_tokens=200, output_tokens=100
        )
        anthropic_resp = _mock_anthropic_response(
            _make_mock_judge_response(), input_tokens=150, output_tokens=80
        )

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=openai_resp)
        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=anthropic_resp)

        judge._openai_client = mock_openai_client
        judge._anthropic_client = mock_anthropic_client

        result = await judge.evaluate_multi_judge("Q?", "A", "GT")

        assert result["tokens_used"] == (200 + 100) + (150 + 80)
        assert result["cost_usd"] > 0
        assert judge._total_tokens == result["tokens_used"]
        assert judge._total_cost > 0


class TestCheckPositionBias:
    @pytest.mark.asyncio
    async def test_no_bias_detected(self, judge):
        resp_original = _mock_openai_response(
            _make_mock_judge_response(accuracy=4)
        )
        resp_swapped = _mock_openai_response(
            _make_mock_judge_response(accuracy=4)
        )

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[resp_original, resp_swapped]
        )
        judge._openai_client = mock_openai_client

        result = await judge.check_position_bias("Response A text", "Response B text")

        assert result["bias_detected"] is False
        assert result["score_original"] == 4
        assert result["score_swapped"] == 4
        assert result["delta"] == 0

    @pytest.mark.asyncio
    async def test_bias_detected(self, judge):
        resp_original = _mock_openai_response(
            _make_mock_judge_response(accuracy=5)
        )
        resp_swapped = _mock_openai_response(
            _make_mock_judge_response(accuracy=2)
        )

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[resp_original, resp_swapped]
        )
        judge._openai_client = mock_openai_client

        result = await judge.check_position_bias("Response A", "Response B")

        assert result["bias_detected"] is True
        assert result["delta"] == 3
        assert result["tokens_used"] > 0
        assert result["cost_usd"] > 0


class TestHasConflict:
    def test_no_conflict(self, judge):
        a = {"accuracy": 4, "professionalism": 4, "safety": "pass"}
        b = {"accuracy": 4, "professionalism": 5, "safety": "pass"}
        assert judge._has_conflict(a, b) is False

    def test_accuracy_conflict(self, judge):
        a = {"accuracy": 5, "professionalism": 4, "safety": "pass"}
        b = {"accuracy": 2, "professionalism": 4, "safety": "pass"}
        assert judge._has_conflict(a, b) is True

    def test_professionalism_conflict(self, judge):
        a = {"accuracy": 4, "professionalism": 5, "safety": "pass"}
        b = {"accuracy": 4, "professionalism": 2, "safety": "pass"}
        assert judge._has_conflict(a, b) is True

    def test_safety_conflict(self, judge):
        a = {"accuracy": 4, "professionalism": 4, "safety": "pass"}
        b = {"accuracy": 4, "professionalism": 4, "safety": "fail"}
        assert judge._has_conflict(a, b) is True


class TestPartialFailure:
    @pytest.mark.asyncio
    async def test_one_model_fails(self, judge):
        openai_resp = _mock_openai_response(
            _make_mock_judge_response(accuracy=4)
        )
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=openai_resp)

        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=RuntimeError("API down")
        )

        judge._openai_client = mock_openai_client
        judge._anthropic_client = mock_anthropic_client

        result = await judge.evaluate_multi_judge("Q?", "A", "GT")

        assert result["agreement_rate"] == 0.0
        assert "error" in result["reasoning"].lower() or "Error" in result["reasoning"]
        assert result["final_score"] == 4.0
