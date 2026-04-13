# Changelog

All notable changes to this project will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

---

## [0.2.0] — 2026-04-13

### Added
- LLM triage strategy (`app/rules/llm.py`) with multi-provider support: Claude (default), OpenAI, Azure OpenAI
- Automatic fallback to `KeywordStrategy` when no API key is configured or any call fails
- Provider selection via `LLM_PROVIDER` env var
- Observability per LLM call: latency (ms), input/output token counts, estimated cost (USD)
- `/metrics` endpoint now includes LLM stats alongside existing HTTP telemetry
- `.env.example` documenting all provider env vars
- `tests/test_llm_strategy.py` — fallback, parse, provider selection, interface, and metrics tests

### Changed
- `app/rules/config.py` — switched active strategy from `KeywordStrategy` to `LLMStrategy`
- `app/main.py` — `/metrics` merges HTTP and LLM metrics into a single response

---

## [0.1.0] — 2026-04-13

### Added
- FastAPI recommendations endpoint (`POST /recommendations`)
- Keyword-based triage strategy (`app/rules/keyword.py`) with deterministic scoring
- `Recommendation` and `TriageResponse` Pydantic models
- Strategy interface (`app/rules/base.py`) — swappable without route changes
- HTTP telemetry middleware — request count, error count, latency
- `GET /health` and `GET /metrics` endpoints
- Full test suite: API, engine, and keyword strategy tests
