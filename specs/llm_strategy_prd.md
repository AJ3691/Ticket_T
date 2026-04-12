# PRD — LLM Triage Strategy
**Status:** Ready for implementation  
**Owner:** Core Agent  
**Touches:** `app/rules/` only  
**Frozen:** `app/models.py`, `app/rules/base.py`, `app/main.py`, `tests/`

---

## Problem

The current `KeywordStrategy` matches words. It cannot reason.

It fails when:
- The user describes a problem without using exact keywords ("I can't get in" vs "login failed")
- A ticket spans multiple categories ("my SSO broke after the billing upgrade")
- The language is vague, emotional, or non-technical ("nothing works since yesterday")
- A new category appears that has no keywords defined

The scoring is deterministic but brittle. Confidence values are arithmetic, not meaningful. The `why` field is always the same canned text regardless of the actual ticket content.

---

## Goal

Replace the scoring engine with an LLM call that:
1. Reads the actual ticket text
2. Reasons about what's wrong
3. Returns structured recommendations — same shape as today
4. Degrades gracefully to `KeywordStrategy` if the LLM is unavailable

The API contract does not change. The transport does not change. The tests do not change. Only the strategy implementation changes.

---

## Success Criteria

| Criteria | Measurable signal |
|---|---|
| Same interface | `LLMStrategy.recommend()` returns `list[Recommendation]` — identical to `KeywordStrategy` |
| Structured output | LLM returns valid JSON, parsed into `Recommendation` objects, every call |
| Fallback works | If LLM call fails or times out, `KeywordStrategy` result is returned silently |
| Determinism | `temperature=0` + `seed` produces same output for same input |
| No secrets in code | API key from environment variable only |
| Existing tests pass | `pytest -v` → 26 passed, 0 failed (no test changes) |
| New tests added | At least 3 unit tests for `LLMStrategy` behaviour |

---

## Scope

### In scope
- `app/rules/llm.py` — new strategy file
- `app/rules/config.py` — one line change to switch active strategy
- `requirements.txt` — add `openai` and `python-dotenv`
- `.env.example` — document required env vars
- `tests/test_llm_strategy.py` — new test file

### Out of scope (future)
- Streaming responses (separate spec)
- RAG / vector retrieval (separate spec)
- Conversation history / multi-turn (separate spec)
- Fine-tuning or custom models
- Cost tracking / token telemetry (noted as gap, separate spec)

---

## Architecture Decision

### Why a new file, not modifying `keyword.py`

`keyword.py` is owned by the Core Agent and is a working, tested fallback. Keeping it intact means:
- The fallback path always exists
- The parallel can be tested side by side
- Rollback is one line in `config.py`

### Why `config.py` is the switch

```python
# config.py — today
def get_rule():
    return KeywordStrategy()

# config.py — after
def get_rule():
    return LLMStrategy()   # one line change, rollback is trivial
```

This is the strangler fig pattern at the smallest possible scale.

### Why structured output / function calling

The LLM must return `list[Recommendation]` — not markdown, not prose, not a mix. 

Options considered:
1. **Prompt + JSON parse** — fragile, breaks on model variation
2. **JSON mode** — better, but still requires manual schema enforcement  
3. **Function calling / structured output** — LLM is constrained to match the Pydantic schema exactly ← chosen

### Why `temperature=0`

Existing tests assert determinism. `temperature=0` + fixed `seed` preserves that contract.

---

## The Two Implementation Phases

### Phase 1 — Simplest working version

One file. Minimal dependencies. Proves the pipe works.

```
LLMStrategy.recommend()
  → build prompt (system + user)
  → call Azure OpenAI / OpenAI API
  → parse JSON response into list[Recommendation]
  → return result
  → on any failure → return KeywordStrategy().recommend()
```

No caching. No streaming. No token tracking. Just the call and the parse.

### Phase 2 — Production hardening

Extends Phase 1 without changing the interface.

- **Timeout** — hard limit on LLM call (e.g. 10s), falls back on breach
- **Retry with backoff** — 2 retries on transient errors, exponential backoff
- **Token tracking** — log `prompt_tokens`, `completion_tokens`, `cost_usd` per call
- **Semantic caching** — cache responses for near-identical inputs (Redis or in-memory)
- **Prompt versioning** — prompt stored in `prompts/llm_strategy_prompt.md`, not hardcoded
- **Model config** — model name, temperature, max_tokens from env vars, not hardcoded

---

## Prompt Design (Phase 1)

**System prompt intent:**
- Role: senior support triage analyst
- Task: read ticket, return exactly N recommendations
- Output: JSON array matching the Recommendation schema
- Constraints: confidence 0.0–1.0, action short, why 1–2 sentences

**User prompt:**
```
Title: {title}
Description: {description}
Return {top_n} recommendations.
```

**Output schema passed to LLM:**
```json
{
  "recommendations": [
    {
      "action": "string — short next step",
      "confidence": 0.0,
      "why": "string — 1-2 sentences"
    }
  ]
}
```

---

## Environment Variables Required

```
OPENAI_API_KEY=sk-...          # or AZURE_OPENAI_API_KEY
OPENAI_MODEL=gpt-4o-mini       # or azure deployment name
OPENAI_BASE_URL=               # only needed for Azure OpenAI
```

---

## Risks

| Risk | Mitigation |
|---|---|
| LLM returns malformed JSON | Pydantic validation catches it, fallback activates |
| API key not set | Startup check, clear error message, fallback activates |
| Latency too high | 10s timeout, fallback activates |
| Cost spike | Token logging in Phase 2, alert threshold in Phase 3 |
| Model changes output format | Structured output pins the schema, not the prose |

---

## Definition of Done

- [ ] `app/rules/llm.py` exists and implements `TriageStrategy`
- [ ] `app/rules/config.py` returns `LLMStrategy()`
- [ ] `POST /recommendations` returns LLM-generated recommendations
- [ ] Fallback activates when `OPENAI_API_KEY` is missing
- [ ] `pytest -v` → 26 original tests pass + new LLM tests pass
- [ ] `.env.example` documents required vars
- [ ] No secrets in any committed file
