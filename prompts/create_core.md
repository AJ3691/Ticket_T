# Task: Create Core Recommendation Engine

> **Target Agent:** agent_core
> **Phase:** 2  |  **Priority:** P0  |  **Estimated Scope:** large

---

## Goal

Create the recommendation engine (`app/engine.py`), keyword strategy (`app/rules/keyword.py`), and strategy config (`app/rules/config.py`) that produce deterministic, ranked recommendations for support tickets. This runs in parallel with the API Agent.

---

## Context

### Current State
- Phase 1 complete: `app/models.py` and `app/rules/base.py` exist and are frozen
- `app/main.py` is being built in parallel by API Agent — do not touch it
- `app/rules/__init__.py` exists (empty)

### Trigger
- Phase 2 kickoff — Core and API agents start simultaneously

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `app/models.py` | `app/models.py` | frozen — Recommendation model |
| `app/rules/base.py` | `app/rules/base.py` | frozen — TriageStrategy interface |

---

## Expected Output

| Output | Location | Shape |
|--------|----------|-------|
| `app/engine.py` | `app/engine.py` | Entry point: `get_recommendations()` |
| `app/rules/keyword.py` | `app/rules/keyword.py` | Concrete `KeywordStrategy` |
| `app/rules/config.py` | `app/rules/config.py` | Strategy selector: `get_rule()` |

---

## Spec: What to Create

### 1. `app/rules/config.py`

Simple strategy selector. Returns the active strategy instance.

```python
"""Strategy selector — returns the active TriageStrategy."""

from app.rules.keyword import KeywordStrategy


def get_rule():
    """Return the active recommendation strategy.
    
    Currently returns KeywordStrategy. To swap strategies,
    change this single line.
    """
    return KeywordStrategy()
```

### 2. `app/engine.py`

Thin orchestration layer. Delegates to the configured strategy.

```python
"""Triage engine — delegates to the configured scoring strategy."""

from app.models import Recommendation
from app.rules.config import get_rule


def get_recommendations(
    title: str,
    description: str,
    top_n: int = 3,
) -> list[Recommendation]:
    """Return ranked recommendations. Same input → same output."""
    rule = get_rule()
    return rule.recommend(title=title, description=description, top_n=top_n)
```

### 3. `app/rules/keyword.py`

This is the core logic file. Implement a deterministic keyword-matching strategy.

#### Scoring Algorithm

1. Combine `title + " " + description` into a single text string
2. Convert to lowercase for matching
3. For each category, count how many of its keywords appear in the text
4. Calculate a base confidence: `matches / total_keywords_in_category`
5. Apply a category weight multiplier (some categories are more common/useful)
6. Normalize confidence to [0.0, 1.0] — clamp if needed
7. Sort by confidence descending
8. Break ties by alphabetical category key (stable, deterministic)
9. Return top_n results

#### Category Definitions

Define at least 6 categories. Each category has:
- A unique key (string, used for tie-breaking sort)
- A list of keywords (10+ per category)
- A list of 3 recommended actions
- A why template for each action
- A weight multiplier (0.5 - 1.0)

**Required categories:**

| Key | Topic | Example Keywords | Weight |
|-----|-------|-----------------|--------|
| `auth` | Authentication / Login | login, password, reset, locked, credentials, auth, token, session, sso, mfa, 2fa, signin, signout, logout | 0.95 |
| `billing` | Billing / Payments | invoice, charge, payment, refund, subscription, billing, plan, upgrade, downgrade, price, cost, receipt | 0.85 |
| `performance` | Performance / Speed | slow, timeout, latency, loading, speed, lag, hang, freeze, unresponsive, performance, crash, memory | 0.80 |
| `access` | Permissions / Access | permission, access, denied, forbidden, role, admin, unauthorized, privilege, restrict, blocked, firewall | 0.90 |
| `data` | Data / Sync | data, sync, missing, lost, corrupt, backup, restore, export, import, duplicate, merge, migration | 0.75 |
| `integration` | Integration / API | api, integration, webhook, endpoint, connect, third-party, plugin, extension, oauth, sdk, rest, graphql | 0.70 |

Each category must define exactly 3 actions with corresponding why explanations.

**Example for `auth` category:**

```python
{
    "key": "auth",
    "keywords": ["login", "password", "reset", "locked", "credentials", "auth", 
                  "token", "session", "sso", "mfa", "2fa", "signin", "signout", "logout"],
    "weight": 0.95,
    "actions": [
        {
            "action": "Verify account status and recent lockouts",
            "why": "Login failures after reset often correlate with lockouts or disabled accounts."
        },
        {
            "action": "Check auth provider error logs for this user",
            "why": "The error may be coming from the identity provider, not the app."
        },
        {
            "action": "Ask user for exact error code and timestamp",
            "why": "Pinpointing the time and error code speeds up correlation across systems."
        }
    ]
}
```

#### Scoring Implementation Details

```python
def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
    text = f"{title} {description}".lower()
    scored = []
    
    for category in self.categories:
        # Count keyword matches
        matches = sum(1 for kw in category["keywords"] if kw in text)
        if matches == 0:
            continue
        
        # Base confidence = match ratio * weight
        base = matches / len(category["keywords"])
        confidence = round(min(base * category["weight"], 1.0), 2)
        
        # Add each action with decaying confidence
        for i, action_def in enumerate(category["actions"]):
            decay = 1.0 - (i * 0.15)  # 0%, 15%, 30% decay per action rank
            action_confidence = round(confidence * decay, 2)
            scored.append({
                "action": action_def["action"],
                "confidence": action_confidence,
                "why": action_def["why"],
                "sort_key": category["key"],  # for tie-breaking
            })
    
    # Sort: confidence descending, then category key ascending (tie-break)
    scored.sort(key=lambda x: (-x["confidence"], x["sort_key"]))
    
    # Convert to Recommendation objects, limit to top_n
    return [
        Recommendation(
            action=s["action"],
            confidence=s["confidence"],
            why=s["why"],
        )
        for s in scored[:top_n]
    ]
```

#### Fallback Behavior

If no keywords match (zero scored results), return a default fallback list:

```python
FALLBACK_ACTIONS = [
    Recommendation(
        action="Gather detailed reproduction steps from the user",
        confidence=0.30,
        why="Without matching a known category, collecting steps helps route the issue correctly."
    ),
    Recommendation(
        action="Search knowledge base for similar past tickets",
        confidence=0.25,
        why="A general search may surface related issues even when keywords don't match directly."
    ),
    Recommendation(
        action="Escalate to Tier 2 support for manual triage",
        confidence=0.20,
        why="When automated triage cannot categorize the issue, human review ensures nothing is missed."
    ),
]
```

Return `FALLBACK_ACTIONS[:top_n]` when no categories match.

---

## Constraints

- **Deterministic:** No `random`, no `time`, no `os.environ` in scoring logic
- **No HTTP:** Do not import FastAPI, Request, or any HTTP library
- **No network:** Strategy must work entirely offline with no API calls
- **No secrets:** No environment variables for core logic
- **Sorted:** Results always sorted by confidence descending
- **Stable ties:** Ties broken by category key alphabetical order
- **Valid range:** All confidence values clamped to [0.0, 1.0]
- **Non-empty:** Action and why strings must never be empty
- Do not modify `app/models.py` or `app/rules/base.py`
- Do not create `app/main.py` — owned by API Agent
- Do not create test files — owned by Test Agent

---

## Process

1. Read `app/models.py` to confirm `Recommendation` shape
2. Read `app/rules/base.py` to confirm `TriageStrategy` interface
3. Create `app/rules/config.py` — strategy selector
4. Create `app/rules/keyword.py` — full keyword strategy with 6+ categories
5. Create `app/engine.py` — thin orchestration
6. Run compile checks on all three files
7. Run import checks
8. Run determinism verification (call twice, compare)
9. Run confidence sorting verification
10. Run top_n limiting verification
11. Run edge case verification (unknown input, valid objects)

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `app/models.py` | Frozen after Phase 1 |
| `app/rules/base.py` | Frozen after Phase 1 |
| `app/main.py` | Owned by API Agent |
| `tests/` | Owned by Test Agent |

---

## Verification

```bash
# 1. Compile checks
python -m py_compile app/engine.py && echo "✓ engine"
python -m py_compile app/rules/keyword.py && echo "✓ keyword"
python -m py_compile app/rules/config.py && echo "✓ config"

# 2. Import checks
python -c "from app.engine import get_recommendations; print('✓ engine imports')"
python -c "from app.rules.keyword import KeywordStrategy; print('✓ strategy imports')"
python -c "from app.rules.config import get_rule; print('✓ config imports')"

# 3. Strategy implements interface
python -c "
from app.rules.keyword import KeywordStrategy
from app.rules.base import TriageStrategy
assert issubclass(KeywordStrategy, TriageStrategy), 'KeywordStrategy must extend TriageStrategy'
print('✓ KeywordStrategy extends TriageStrategy')
"

# 4. Determinism (critical)
python -c "
from app.engine import get_recommendations
r1 = get_recommendations('Cannot log in', 'I reset my password but still get an error')
r2 = get_recommendations('Cannot log in', 'I reset my password but still get an error')
assert len(r1) == len(r2), f'Length mismatch: {len(r1)} vs {len(r2)}'
for i, (a, b) in enumerate(zip(r1, r2)):
    assert a.action == b.action, f'Action mismatch at {i}'
    assert a.confidence == b.confidence, f'Confidence mismatch at {i}'
    assert a.why == b.why, f'Why mismatch at {i}'
print(f'✓ deterministic: {len(r1)} identical results')
"

# 5. Confidence sorting
python -c "
from app.engine import get_recommendations
results = get_recommendations('Cannot log in', 'Password reset not working', top_n=10)
for i in range(len(results) - 1):
    assert results[i].confidence >= results[i+1].confidence, \
        f'Not sorted at index {i}: {results[i].confidence} < {results[i+1].confidence}'
print(f'✓ sorted descending ({len(results)} results)')
"

# 6. top_n limiting
python -c "
from app.engine import get_recommendations
assert len(get_recommendations('test', 'login password', top_n=1)) <= 1
assert len(get_recommendations('test', 'login password', top_n=3)) <= 3
assert len(get_recommendations('test', 'login password', top_n=5)) <= 5
print('✓ top_n limiting works')
"

# 7. Valid Recommendation objects
python -c "
from app.engine import get_recommendations
from app.models import Recommendation
results = get_recommendations('Cannot log in', 'Password reset error')
for r in results:
    assert isinstance(r, Recommendation), f'Not Recommendation: {type(r)}'
    assert 0.0 <= r.confidence <= 1.0, f'Out of range: {r.confidence}'
    assert len(r.action) > 0, 'Empty action'
    assert len(r.why) > 0, 'Empty why'
print(f'✓ all {len(results)} results are valid Recommendations')
"

# 8. Fallback for unknown input
python -c "
from app.engine import get_recommendations
results = get_recommendations('xyzzy gibberish', 'nothing matches here at all')
assert isinstance(results, list), 'Must return a list'
for r in results:
    assert 0.0 <= r.confidence <= 1.0
    assert len(r.action) > 0
print(f'✓ unknown input → {len(results)} fallback results')
"

# 9. Multi-category input
python -c "
from app.engine import get_recommendations
results = get_recommendations(
    'Slow login after password reset',
    'Performance is terrible and I keep getting locked out after resetting my password'
)
assert len(results) >= 2, 'Multi-category input should produce multiple results'
print(f'✓ multi-category → {len(results)} results')
for r in results:
    print(f'  [{r.confidence:.2f}] {r.action}')
"

# 10. No HTTP imports
python -c "
import ast, sys
for path in ['app/engine.py', 'app/rules/keyword.py', 'app/rules/config.py']:
    with open(path) as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, 'module', '') or ''
            names = [a.name for a in node.names]
            for name in [module] + names:
                assert 'fastapi' not in name.lower(), f'HTTP import in {path}: {name}'
                assert 'starlette' not in name.lower(), f'HTTP import in {path}: {name}'
print('✓ no HTTP imports in core layer')
"
```

---

## Deliverable Summary

Return:
- Files created: `app/engine.py`, `app/rules/keyword.py`, `app/rules/config.py`
- What was created: Deterministic recommendation engine with keyword scoring, 6 categories, fallback behavior
- Contract impact: Produces `get_recommendations()` consumed by API Agent
- Tests affected: None — Test Agent creates tests in Phase 3

---

## Rollback Signal

If this task produces incorrect output:
- Delete `app/engine.py`, `app/rules/keyword.py`, `app/rules/config.py` and recreate
- Signal: non-deterministic output, unsorted results, compile failure, HTTP imports in core
- Notify: Orchestrator — Phase 2 integration check will fail
