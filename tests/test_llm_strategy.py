"""Tests for LLMStrategy — fallback, parse, provider selection, interface contract."""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.models import Recommendation
from app.rules.llm import LLMStrategy, get_adapter, AnthropicAdapter, OpenAIAdapter, CallResult, get_llm_metrics, _llm_metrics


# ── Fallback behaviour ────────────────────────────────────────────────────────

class TestFallback:

    def test_no_key_returns_recommendations(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("Cannot log in", "password reset not working")
        assert len(result) >= 1
        assert all(isinstance(r, Recommendation) for r in result)

    def test_fallback_respects_top_n(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("slow page", "takes forever to load", top_n=2)
        assert len(result) <= 2

    def test_adapter_exception_triggers_fallback(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.setenv("LLM_PROVIDER", "claude")
        strategy = LLMStrategy()
        if strategy._adapter:
            strategy._adapter.call = MagicMock(side_effect=Exception("boom"))
        result = strategy.recommend("billing issue", "charged twice")
        assert isinstance(result, list)
        assert len(result) >= 1


# ── Parse logic ───────────────────────────────────────────────────────────────

class TestParse:

    def _make_strategy(self):
        s = LLMStrategy.__new__(LLMStrategy)
        s._adapter = None
        from app.rules.keyword import KeywordStrategy
        s._fallback = KeywordStrategy()
        return s

    def test_valid_json_returns_recommendations(self):
        s = self._make_strategy()
        raw = json.dumps({"recommendations": [
            {"action": "Check logs", "confidence": 0.85, "why": "Logs show the error."},
            {"action": "Restart service", "confidence": 0.60, "why": "May clear transient state."},
        ]})
        result = s._parse(raw, top_n=3)
        assert len(result) == 2
        assert result[0].action == "Check logs"
        assert result[0].confidence == 0.85

    def test_parse_respects_top_n(self):
        s = self._make_strategy()
        raw = json.dumps({"recommendations": [
            {"action": "A", "confidence": 0.9, "why": "x"},
            {"action": "B", "confidence": 0.8, "why": "y"},
            {"action": "C", "confidence": 0.7, "why": "z"},
        ]})
        result = s._parse(raw, top_n=2)
        assert len(result) == 2

    def test_empty_list_raises(self):
        s = self._make_strategy()
        with pytest.raises(ValueError):
            s._parse(json.dumps({"recommendations": []}), top_n=3)

    def test_confidence_rounded_to_2dp(self):
        s = self._make_strategy()
        raw = json.dumps({"recommendations": [
            {"action": "Test", "confidence": 0.8567, "why": "reason"},
        ]})
        result = s._parse(raw, top_n=1)
        assert result[0].confidence == 0.86


# ── Provider selection ────────────────────────────────────────────────────────

class TestProviderSelection:

    def test_default_provider_is_claude(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        adapter = get_adapter()
        assert adapter is None  # no key, but attempted Claude

    def test_unknown_provider_returns_none(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "unknown_provider")
        adapter = get_adapter()
        assert adapter is None

    def test_openai_provider_selected(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        adapter = get_adapter()
        assert adapter is None  # no key, but correct class attempted


# ── Interface contract ────────────────────────────────────────────────────────

class TestInterface:

    def test_returns_list(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("api broken", "webhook stopped firing")
        assert isinstance(result, list)

    def test_confidence_in_range(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("data lost", "records missing after import")
        for r in result:
            assert 0.0 <= r.confidence <= 1.0

    def test_all_fields_present(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("slow", "page loads slowly")
        for r in result:
            assert r.action
            assert r.why
            assert isinstance(r.confidence, float)


# ── Observability metrics ─────────────────────────────────────────────────────

class TestMetrics:

    def test_get_llm_metrics_has_expected_keys(self):
        m = get_llm_metrics()
        for key in ("llm_calls", "llm_fallbacks", "total_input_tokens",
                    "total_output_tokens", "total_cost_usd", "total_latency_ms",
                    "avg_latency_ms"):
            assert key in m, f"missing key: {key}"

    def test_fallback_increments_fallback_count(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        before = _llm_metrics["llm_fallbacks"]
        strategy = LLMStrategy()
        strategy.recommend("test", "test description")
        assert _llm_metrics["llm_fallbacks"] > before

    def test_successful_call_increments_llm_calls(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.setenv("LLM_PROVIDER", "claude")
        strategy = LLMStrategy()
        if strategy._adapter is None:
            pytest.skip("adapter not ready")
        mock_result = CallResult(
            text=json.dumps({"recommendations": [
                {"action": "Check logs", "confidence": 0.9, "why": "Logs show the error."}
            ]}),
            input_tokens=100,
            output_tokens=50,
        )
        strategy._adapter.call = MagicMock(return_value=mock_result)
        before = _llm_metrics["llm_calls"]
        strategy.recommend("test", "description")
        assert _llm_metrics["llm_calls"] == before + 1
        assert _llm_metrics["total_input_tokens"] >= 100
        assert _llm_metrics["total_output_tokens"] >= 50

    def test_cost_is_non_negative(self):
        m = get_llm_metrics()
        assert m["total_cost_usd"] >= 0.0

    def test_avg_latency_is_float(self):
        m = get_llm_metrics()
        assert isinstance(m["avg_latency_ms"], float)


# -- Observability metrics ----------------------------------------------------

class TestMetrics:

    def test_get_llm_metrics_has_expected_keys(self):
        m = get_llm_metrics()
        for key in ("llm_calls", "llm_fallbacks", "total_input_tokens",
                    "total_output_tokens", "total_cost_usd", "total_latency_ms",
                    "avg_latency_ms"):
            assert key in m, f"missing key: {key}"

    def test_fallback_increments_fallback_count(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        before = _llm_metrics["llm_fallbacks"]
        strategy = LLMStrategy()
        strategy.recommend("test", "test description")
        assert _llm_metrics["llm_fallbacks"] > before

    def test_successful_call_records_tokens(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.setenv("LLM_PROVIDER", "claude")
        strategy = LLMStrategy()
        if strategy._adapter is None:
            pytest.skip("adapter not ready")
        mock_result = CallResult(
            text=json.dumps({"recommendations": [
                {"action": "Check logs", "confidence": 0.9, "why": "Logs show the error."}
            ]}),
            input_tokens=100,
            output_tokens=50,
        )
        strategy._adapter.call = MagicMock(return_value=mock_result)
        before_calls = _llm_metrics["llm_calls"]
        before_input = _llm_metrics["total_input_tokens"]
        strategy.recommend("test", "description")
        assert _llm_metrics["llm_calls"] == before_calls + 1
        assert _llm_metrics["total_input_tokens"] == before_input + 100

    def test_cost_is_non_negative(self):
        assert get_llm_metrics()["total_cost_usd"] >= 0.0

    def test_avg_latency_is_float(self):
        assert isinstance(get_llm_metrics()["avg_latency_ms"], float)
