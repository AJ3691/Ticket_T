"""LLM-based triage strategy — multi-provider, defaults to Claude.

Provider selection: LLM_PROVIDER env var (claude | openai | azure)
Default: claude

All providers share the same prompt and parse logic.
Each provider adapter owns only the API call.
On any failure, falls back to KeywordStrategy silently.
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from dotenv import load_dotenv

from app.models import Recommendation
from app.rules.base import TriageStrategy
from app.rules.keyword import KeywordStrategy

load_dotenv()

logger = logging.getLogger(__name__)

# -- Observability -------------------------------------------------------------

@dataclass
class CallResult:
    """Raw output from one LLM API call."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


# Cost per 1M tokens in USD -- verify against provider pricing pages
_COST_PER_1M: dict[str, dict[str, float]] = {
    "claude-opus-4-6":           {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":         {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input":  0.25, "output":  1.25},
    "gpt-4o":                    {"input":  5.00, "output": 15.00},
    "gpt-4o-mini":               {"input":  0.15, "output":  0.60},
}

_llm_metrics: dict[str, int | float] = {
    "llm_calls":           0,
    "llm_fallbacks":       0,
    "total_input_tokens":  0,
    "total_output_tokens": 0,
    "total_cost_usd":      0.0,
    "total_latency_ms":    0.0,
}


def get_llm_metrics() -> dict:
    """Return a snapshot of accumulated LLM call metrics."""
    m = dict(_llm_metrics)
    calls = m["llm_calls"] or 1
    m["avg_latency_ms"] = round(m["total_latency_ms"] / calls, 2)
    m["total_cost_usd"] = round(m["total_cost_usd"], 6)
    return m


def _record(result: CallResult, latency_ms: float, model: str) -> None:
    cost_table = _COST_PER_1M.get(model, {"input": 0.0, "output": 0.0})
    cost = (result.input_tokens * cost_table["input"] +
            result.output_tokens * cost_table["output"]) / 1_000_000
    _llm_metrics["llm_calls"]           += 1
    _llm_metrics["total_input_tokens"]  += result.input_tokens
    _llm_metrics["total_output_tokens"] += result.output_tokens
    _llm_metrics["total_cost_usd"]      += cost
    _llm_metrics["total_latency_ms"]    += latency_ms
    logger.info(
        "llm_call model=%s input_tokens=%d output_tokens=%d cost_usd=%.6f latency_ms=%.1f",
        model, result.input_tokens, result.output_tokens, cost, latency_ms,
    )


# -- Prompt -------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior support triage analyst.

Given a support ticket, return exactly the requested number of recommendations.

Rules:
- action: short next step (one sentence, specific to this ticket)
- confidence: float 0.0-1.0, how likely this action resolves the issue
- why: 1-2 sentences explaining the reasoning for THIS ticket specifically
- sort recommendations by confidence descending

Respond with valid JSON only. No markdown. No preamble. No explanation.

Schema:
{
  "recommendations": [
    {
      "action": "string",
      "confidence": 0.0,
      "why": "string"
    }
  ]
}"""


def _build_user_prompt(title: str, description: str, top_n: int) -> str:
    return (
        f"Title: {title}\n"
        f"Description: {description}\n"
        f"Return {top_n} recommendations."
    )


# -- Provider adapters --------------------------------------------------------

class LLMAdapter(ABC):
    """Minimal interface every provider adapter must implement."""

    @abstractmethod
    def call(self, system: str, user: str, max_tokens: int = 1000) -> CallResult:
        """Call the LLM and return a CallResult with text + token counts."""
        ...

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """True if the adapter is configured and can make calls."""
        ...


class AnthropicAdapter(LLMAdapter):
    """Claude via Anthropic API."""

    def __init__(self):
        self._client = None
        self._model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("AnthropicAdapter: ANTHROPIC_API_KEY not set")
            return
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            logger.info("AnthropicAdapter ready (model=%s)", self._model)
        except Exception as e:
            logger.warning("AnthropicAdapter: init failed -- %s", e)

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def call(self, system: str, user: str, max_tokens: int = 1000) -> CallResult:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=10,
        )
        return CallResult(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


class OpenAIAdapter(LLMAdapter):
    """GPT via OpenAI API."""

    def __init__(self):
        self._client = None
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAIAdapter: OPENAI_API_KEY not set")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            logger.info("OpenAIAdapter ready (model=%s)", self._model)
        except Exception as e:
            logger.warning("OpenAIAdapter: init failed -- %s", e)

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def call(self, system: str, user: str, max_tokens: int = 1000) -> CallResult:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            seed=42,
            max_tokens=max_tokens,
            timeout=10,
            response_format={"type": "json_object"},
        )
        return CallResult(
            text=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )


class AzureOpenAIAdapter(LLMAdapter):
    """GPT via Azure OpenAI."""

    def __init__(self):
        self._client = None
        self._deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        if not all([api_key, endpoint, self._deployment]):
            logger.warning("AzureOpenAIAdapter: missing AZURE_OPENAI_API_KEY, ENDPOINT, or DEPLOYMENT")
            return
        try:
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version,
            )
            logger.info("AzureOpenAIAdapter ready (deployment=%s)", self._deployment)
        except Exception as e:
            logger.warning("AzureOpenAIAdapter: init failed -- %s", e)

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def call(self, system: str, user: str, max_tokens: int = 1000) -> CallResult:
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            seed=42,
            max_tokens=max_tokens,
            timeout=10,
            response_format={"type": "json_object"},
        )
        return CallResult(
            text=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )


# -- Provider registry --------------------------------------------------------

_PROVIDERS: dict[str, type[LLMAdapter]] = {
    "claude": AnthropicAdapter,
    "openai": OpenAIAdapter,
    "azure": AzureOpenAIAdapter,
}


def get_adapter() -> LLMAdapter | None:
    """Return the configured adapter, or None if not ready."""
    provider = os.getenv("LLM_PROVIDER", "claude").lower().strip()
    adapter_class = _PROVIDERS.get(provider)
    if adapter_class is None:
        logger.warning("Unknown LLM_PROVIDER=%r -- valid options: %s", provider, list(_PROVIDERS))
        return None
    adapter = adapter_class()
    if not adapter.is_ready:
        return None
    return adapter


# -- Strategy -----------------------------------------------------------------

class LLMStrategy(TriageStrategy):
    """Recommendation strategy backed by a configurable LLM provider.

    Provider selected by LLM_PROVIDER env var (default: claude).
    Falls back to KeywordStrategy on any failure.
    """

    def __init__(self):
        self._adapter = get_adapter()
        self._fallback = KeywordStrategy()
        if self._adapter is None:
            logger.warning(
                "LLMStrategy: no provider ready -- using KeywordStrategy fallback. "
                "Set LLM_PROVIDER and the matching API key in .env"
            )

    def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
        if self._adapter is None:
            _llm_metrics["llm_fallbacks"] += 1
            return self._fallback.recommend(title, description, top_n)
        try:
            user = _build_user_prompt(title, description, top_n)
            t0 = time.perf_counter()
            result = self._adapter.call(SYSTEM_PROMPT, user)
            latency_ms = (time.perf_counter() - t0) * 1000
            _record(result, latency_ms, getattr(self._adapter, "_model", "unknown"))
            return self._parse(result.text, top_n)
        except Exception as e:
            logger.warning("LLMStrategy: call failed (%s) -- using fallback", e)
            _llm_metrics["llm_fallbacks"] += 1
            return self._fallback.recommend(title, description, top_n)

    def _parse(self, raw: str, top_n: int) -> list[Recommendation]:
        data = json.loads(raw)
        items = data.get("recommendations", [])
        if not items:
            raise ValueError("LLM returned empty recommendations")
        results = []
        for item in items[:top_n]:
            results.append(Recommendation(
                action=item["action"],
                confidence=round(float(item["confidence"]), 2),
                why=item["why"],
            ))
        return results
