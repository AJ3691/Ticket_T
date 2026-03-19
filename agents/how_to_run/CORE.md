
## How to Run This Agent

### Using Claude Code
```bash
# From the repo root (Phase 1 must be complete):
claude "Read agents/agent_core.md and prompts/create_core.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

### Manual verification after agent finishes
```bash
# Compile check
python -m py_compile app/engine.py && echo "✓ engine compiles"
python -m py_compile app/rules/keyword.py && echo "✓ keyword compiles"
python -m py_compile app/rules/config.py && echo "✓ config compiles"

# Import check
python -c "from app.engine import get_recommendations; print('✓ engine imports')"
python -c "from app.rules.keyword import KeywordStrategy; print('✓ strategy imports')"
python -c "from app.rules.config import get_rule; print('✓ config imports')"
```

### Verify deterministic ranking
```bash
python -c "
from app.engine import get_recommendations
r1 = get_recommendations('Cannot log in', 'I reset my password but still get an error')
r2 = get_recommendations('Cannot log in', 'I reset my password but still get an error')
assert len(r1) == len(r2), f'Length mismatch: {len(r1)} vs {len(r2)}'
for i, (a, b) in enumerate(zip(r1, r2)):
    assert a.action == b.action, f'Action mismatch at {i}: {a.action} vs {b.action}'
    assert a.confidence == b.confidence, f'Confidence mismatch at {i}: {a.confidence} vs {b.confidence}'
    assert a.why == b.why, f'Why mismatch at {i}: {a.why} vs {b.why}'
print(f'✓ deterministic: {len(r1)} recommendations, identical on both calls')
for r in r1:
    print(f'  [{r.confidence:.2f}] {r.action}')
"
```

### Verify confidence sorting
```bash
python -c "
from app.engine import get_recommendations
results = get_recommendations('Cannot log in', 'Password reset not working', top_n=5)
for i in range(len(results) - 1):
    assert results[i].confidence >= results[i+1].confidence, \
        f'Not sorted: [{i}] {results[i].confidence} < [{i+1}] {results[i+1].confidence}'
print(f'✓ sorted by confidence descending ({len(results)} results)')
"
```

### Verify top_n limiting
```bash
python -c "
from app.engine import get_recommendations
r1 = get_recommendations('test', 'test', top_n=1)
r3 = get_recommendations('test', 'test', top_n=3)
r5 = get_recommendations('test', 'test', top_n=5)
assert len(r1) <= 1, f'top_n=1 returned {len(r1)}'
assert len(r3) <= 3, f'top_n=3 returned {len(r3)}'
assert len(r5) <= 5, f'top_n=5 returned {len(r5)}'
print(f'✓ top_n limiting works: 1→{len(r1)}, 3→{len(r3)}, 5→{len(r5)}')
"
```

### Verify edge cases
```bash
python -c "
from app.engine import get_recommendations
from app.models import Recommendation

# Unknown topic should still return something (fallback categories)
results = get_recommendations('xyzzy gibberish', 'nothing matches here')
assert isinstance(results, list), 'Should return a list'
print(f'✓ unknown topic → list of {len(results)} results')

# All results must be valid Recommendation objects
for r in results:
    assert isinstance(r, Recommendation), f'Not a Recommendation: {type(r)}'
    assert 0.0 <= r.confidence <= 1.0, f'Confidence out of range: {r.confidence}'
    assert len(r.action) > 0, 'Empty action'
    assert len(r.why) > 0, 'Empty why'
print('✓ all results are valid Recommendation objects')
"
```
