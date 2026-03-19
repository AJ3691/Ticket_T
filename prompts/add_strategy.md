# Task: Add Strategy

> **Target Agent:** agent_core
> **Phase:** any  |  **Priority:** P1  |  **Estimated Scope:** medium

---

## Goal

Add a new recommendation strategy that implements the `TriageStrategy` interface, or improve the existing `KeywordStrategy`, while preserving determinism and modularity.

---

## How to Use

Pair this prompt with a specific instruction:
```bash
# Example: add a new strategy
claude "Read agents/agent_core.md and prompts/add_strategy.md. Create an EmbeddingStrategy in app/rules/embedding.py that uses cosine similarity on pre-computed vectors. Register it in config.py as an option. Run verification."

# Example: add a new category to keyword strategy
claude "Read agents/agent_core.md and prompts/add_strategy.md. Add a 'networking' category to KeywordStrategy with keywords: dns, network, firewall, vpn, proxy, ssl, certificate, timeout, connection, socket, port, ip. Run verification."

# Example: improve scoring
claude "Read agents/agent_core.md and prompts/add_strategy.md. Improve the keyword scoring algorithm to weight title matches higher than description matches. Preserve determinism. Run verification."
```

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `app/rules/base.py` | `app/rules/base.py` | frozen — TriageStrategy interface |
| `app/models.py` | `app/models.py` | frozen — Recommendation model |
| `app/rules/keyword.py` | `app/rules/keyword.py` | exists — modify or reference |
| `app/rules/config.py` | `app/rules/config.py` | exists — update to register new strategy |
| `app/engine.py` | `app/engine.py` | exists — should NOT need changes |

---

## Process

1. Read `app/rules/base.py` to confirm `TriageStrategy` interface
2. Read `app/models.py` to confirm `Recommendation` shape
3. If adding new strategy: create new file in `app/rules/`, implement `TriageStrategy`
4. If modifying existing: edit `app/rules/keyword.py`
5. Update `app/rules/config.py` to register the new/changed strategy
6. Verify `app/engine.py` still works without changes (it delegates to config)
7. Run determinism check
8. Run full verification

---

## Constraints

- New strategy must implement `TriageStrategy` abstract interface
- Must be deterministic: same input → same output, always
- No randomness, no timestamps, no external state in scoring
- No HTTP imports — core layer stays offline
- No network calls — strategy must work without API keys
- No secrets or environment variables for logic
- Results must be sorted by confidence descending
- All confidence values in [0.0, 1.0]
- `engine.py` should NOT need changes — new strategies plug in via `config.py`
- Do not modify `app/models.py` or `app/rules/base.py`
- Do not modify `app/main.py`

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `app/models.py` | Frozen contract |
| `app/rules/base.py` | Frozen interface |
| `app/main.py` | Owned by API Agent |
| `tests/` | Owned by Test Agent |

---

## Verification

```bash
# Compile check
python -m py_compile app/rules/keyword.py && echo "✓ keyword"
python -m py_compile app/rules/config.py && echo "✓ config"
python -m py_compile app/engine.py && echo "✓ engine"

# Interface compliance
python -c "
from app.rules.base import TriageStrategy
# Import the new/changed strategy and check
from app.rules.config import get_rule
strategy = get_rule()
assert isinstance(strategy, TriageStrategy), f'Not a TriageStrategy: {type(strategy)}'
print(f'✓ {type(strategy).__name__} implements TriageStrategy')
"

# Determinism check
python -c "
from app.engine import get_recommendations
r1 = get_recommendations('Cannot log in', 'Password reset not working')
r2 = get_recommendations('Cannot log in', 'Password reset not working')
for a, b in zip(r1, r2):
    assert a.action == b.action
    assert a.confidence == b.confidence
print(f'✓ deterministic: {len(r1)} results')
"

# Sorting check
python -c "
from app.engine import get_recommendations
results = get_recommendations('login error', 'password reset', top_n=10)
for i in range(len(results) - 1):
    assert results[i].confidence >= results[i+1].confidence
print('✓ sorted by confidence descending')
"

pytest -v
```

---

## Deliverable Summary

Return:
- Files changed/created: list
- Strategy added/modified: name and approach
- Determinism: confirmed with 2-call test
- Sorting: confirmed descending
- Engine changes: none (should be none)
- Tests affected: may need new tests (note for Test Agent)
