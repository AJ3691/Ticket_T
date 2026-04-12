# Execution Spec — LLM Triage Strategy (Core Agent)
**Agent:** Core Agent  
**Phase:** 2 (parallel-safe — owns `app/rules/` only)  
**PRD:** `specs/llm_strategy_prd.md`  
**Frozen files — DO NOT TOUCH:** `app/models.py`, `app/rules/base.py`, `app/main.py`, `app/engine.py`, `tests/test_api.py`, `tests/test_engine.py`

---

## Context

Read these files before writing any code:
- `app/rules/base.py` — the interface you must implement
- `app/rules/keyword.py` — the fallback strategy (do not modify)
- `app/rules/config.py` — the one-line switch you will change
- `app/models.py` — the `Recommendation` model you must return

The goal: create `app/rules/llm.py` that implements `TriageStrategy` using an LLM call, then switch `config.py` to use it.

---

## Step 1 — Add dependencies

Add to `requirements.txt` (append, do not remove existing lines):
```
openai>=1.30.0
python-dotenv>=1.0.0
```

Run:
```bash
pip install openai python-dotenv
```

Verify:
```bash
python -c "import openai; print('openai ok')"
python -c "import dotenv; print('dotenv ok')"
```

---

## Step 2 — Create `.env.example`

Create file `.env.example` at project root:
```
# Copy to .env and fill in your values
# Never commit .env

OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
# For Azure OpenAI only:
# AZURE_OPENAI_API_KEY=your-azure-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

Verify `.gitignore` contains `.env` — if not, add it.

---

## Step 3 — Create `app/rules/llm.py`

Create this file exactly. Do not modify any other file in this step.

```python
"""LLM-based triage strategy — Phase 1 (simple, no caching, no streaming)."""

from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv

from app.models import Recommendation
from app.rules.base import TriageStrategy
from app.rules.keyword import KeywordStrategy

load_dotenv()

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior support triage analyst.

Given a support ticket, return exactly the requested number of recommendations.

Rules:
- Each recommendation must have: action (short next step), confidence (0.0-1.0), why (1-2 sentences)
- Sort by confidence descending
- Be specific to the ticket content — do not give generic advice
- Confidence must reflect how likely this action will resolve the issue

Respond with valid JSON only. No markdown, no explanation, no preamble.

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


class LLMStrategy(TriageStrategy):
    """Recommendation strategy backed by an LLM call.

    Falls back to KeywordStrategy if:
    - OPENAI_API_KEY is not set
    - The LLM call fails or times out
    - The response cannot be parsed into Recommendation objects
    """

    def __init__(self):
        self._client = None
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._fallback = KeywordStrategy()
        self._ready = False
        self._init_client()

    def _init_client(self):
        """Initialise OpenAI client. Silently marks as not ready if key missing."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("LLMStrategy: OPENAI_API_KEY not set — will use KeywordStrategy fallback")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self._ready = True
            logger.info("LLMStrategy: OpenAI client initialised (model=%s)", self._model)
        except Exception as e:
            logger.warning("LLMStrategy: failed to initialise client — %s", e)

    def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
        """Return LLM-generated recommendations, falling back to keyword strategy on any error."""
        if not self._ready:
            return self._fallback.recommend(title, description, top_n)

        try:
            return self._call_llm(title, description, top_n)
        except Exception as e:
            logger.warning("LLMStrategy: LLM call failed (%s) — using fallback", e)
            return self._fallback.recommend(title, description, top_n)

    def _call_llm(self, title: str, description: str, top_n: int) -> list[Recommendation]:
        """Make the LLM call and parse the response."""
        user_prompt = (
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Return {top_n} recommendations."
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            seed=42,
            max_tokens=1000,
            timeout=10,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        return self._parse(raw, top_n)

    def _parse(self, raw: str, top_n: int) -> list[Recommendation]:
        """Parse LLM JSON response into Recommendation objects."""
        data = json.loads(raw)
        items = data.get("recommendations", [])
        results = []
        for item in items[:top_n]:
            results.append(
                Recommendation(
                    action=item["action"],
                    confidence=round(float(item["confidence"]), 2),
                    why=item["why"],
                )
            )
        if not results:
            raise ValueError("LLM returned empty recommendations list")
        return results
```

Verify file compiles:
```bash
python -m py_compile app/rules/llm.py && echo "llm.py ok"
```

---

## Step 4 — Switch `config.py`

Replace the contents of `app/rules/config.py` with:

```python
"""Strategy selector — returns the active TriageStrategy."""

from app.rules.llm import LLMStrategy


def get_rule():
    """Return the active recommendation strategy."""
    return LLMStrategy()
```

Verify:
```bash
python -m py_compile app/rules/config.py && echo "config.py ok"
python -c "from app.rules.config import get_rule; r = get_rule(); print(type(r).__name__)"
```

Expected output: `LLMStrategy`

---

## Step 5 — Create `tests/test_llm_strategy.py`

```python
"""Unit tests for LLMStrategy — covers fallback, parse, interface contract."""

import pytest
from unittest.mock import MagicMock, patch

from app.models import Recommendation
from app.rules.llm import LLMStrategy


class TestLLMStrategyFallback:
    """When API key is missing, should fall back to KeywordStrategy silently."""

    def test_no_api_key_returns_recommendations(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("Cannot log in", "I reset my password but still get an error")
        assert len(result) >= 1
        assert all(isinstance(r, Recommendation) for r in result)

    def test_fallback_respects_top_n(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("slow loading", "page takes forever", top_n=2)
        assert len(result) <= 2


class TestLLMStrategyParse:
    """Parse method converts valid JSON into Recommendation objects."""

    def test_parse_valid_response(self):
        monkeypatch_env = {"OPENAI_API_KEY": ""}
        strategy = LLMStrategy.__new__(LLMStrategy)
        strategy._fallback = MagicMock()
        raw = '{"recommendations": [{"action": "Check logs", "confidence": 0.85, "why": "Logs show the error source."}]}'
        result = strategy._parse(raw, top_n=3)
        assert len(result) == 1
        assert result[0].action == "Check logs"
        assert result[0].confidence == 0.85

    def test_parse_respects_top_n(self):
        strategy = LLMStrategy.__new__(LLMStrategy)
        raw = '{"recommendations": [{"action": "A", "confidence": 0.9, "why": "x"}, {"action": "B", "confidence": 0.8, "why": "y"}, {"action": "C", "confidence": 0.7, "why": "z"}]}'
        result = strategy._parse(raw, top_n=2)
        assert len(result) == 2

    def test_parse_empty_raises(self):
        strategy = LLMStrategy.__new__(LLMStrategy)
        with pytest.raises(ValueError):
            strategy._parse('{"recommendations": []}', top_n=3)


class TestLLMStrategyInterface:
    """Satisfies the TriageStrategy contract."""

    def test_returns_list_of_recommendations(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("billing issue", "charged twice this month")
        assert isinstance(result, list)
        assert all(isinstance(r, Recommendation) for r in result)

    def test_confidence_in_range(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        strategy = LLMStrategy()
        result = strategy.recommend("api broken", "webhook stopped firing")
        for r in result:
            assert 0.0 <= r.confidence <= 1.0
```

---

## Step 6 — Smoke test the full stack

### Without API key (fallback path)
```bash
python -c "
from app.rules.config import get_rule
r = get_rule()
result = r.recommend('Cannot log in', 'Password reset not working', top_n=3)
print(f'Got {len(result)} recommendations')
for rec in result:
    print(f'  [{rec.confidence}] {rec.action}')
"
```
Expected: 3 recommendations from KeywordStrategy (auth category)

### With API key (LLM path)
Set your key first:
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key"

# or create .env file from .env.example
```

Then:
```bash
python -c "
from app.rules.config import get_rule
r = get_rule()
result = r.recommend('Cannot log in', 'Password reset not working', top_n=3)
print(f'Got {len(result)} recommendations')
for rec in result:
    print(f'  [{rec.confidence}] {rec.action}')
print(f'Strategy: {type(r).__name__}')
"
```
Expected: 3 recommendations from LLM, `Strategy: LLMStrategy`

### Full endpoint test
```bash
uvicorn app.main:app --port 8000 &
curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title": "Cannot log in", "description": "I reset my password but still get an error"}' \
  | python -m json.tool
```

---

## Step 7 — Run full test suite

```bash
pytest -v
```

**Expected:** All original 26 tests pass + new LLM strategy tests pass.

If any original test fails, do not proceed. The interface contract was broken — review `config.py` and `llm.py` for any unintended changes.

---

## Verification Checklist

- [ ] `app/rules/llm.py` exists and compiles
- [ ] `LLMStrategy` inherits from `TriageStrategy`
- [ ] `recommend()` returns `list[Recommendation]`
- [ ] Fallback activates when `OPENAI_API_KEY` missing
- [ ] Fallback activates when LLM call throws any exception
- [ ] `config.py` returns `LLMStrategy()`
- [ ] `.env.example` created at project root
- [ ] `.env` is in `.gitignore`
- [ ] `pytest -v` passes — 0 failures
- [ ] No API key hardcoded anywhere

---

## Phase 2 additions (do not implement now — separate execution spec)

These are the next layer after Phase 1 is verified working:

1. **Timeout enforcement** — wrap `_call_llm` with `asyncio.wait_for` or `concurrent.futures` timeout
2. **Retry with backoff** — `tenacity` library, 2 retries, exponential backoff on `RateLimitError` and `APIConnectionError`
3. **Token logging** — log `response.usage.prompt_tokens`, `completion_tokens` per call
4. **Prompt versioning** — move `SYSTEM_PROMPT` to `prompts/llm_strategy_prompt.md`
5. **Model config from env** — `OPENAI_MAX_TOKENS`, `OPENAI_TEMPERATURE` as env vars
6. **Azure OpenAI support** — `AzureOpenAI` client when `AZURE_OPENAI_ENDPOINT` is set
