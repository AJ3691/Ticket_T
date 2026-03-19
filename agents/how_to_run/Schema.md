
## How to Run This Agent

### Using Claude Code
```bash
# From the repo root:
claude "Read agents/agent_schema.md and prompts/create_schema.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

### Using any CLI agent (generic)
```bash
# Concatenate agent identity + task prompt → feed to your agent
cat agents/agent_schema.md prompts/create_schema.md | your-agent-cli
```

### Manual verification after agent finishes
```bash
# Quick smoke test — run all of these, all must pass
python -m py_compile app/models.py && echo "[PASS] models compile"
python -m py_compile app/rules/base.py && echo "[PASS] base compile"
python -c "from app.models import TicketInput, Recommendation, TriageResponse; print('[PASS] models import')"
python -c "from app.rules.base import TriageStrategy; print('[PASS] strategy import')"
python -c "
from app.models import TicketInput, Recommendation, TriageResponse
r = Recommendation(action='test', confidence=0.8, why='because')
resp = TriageResponse(recommendations=[r])
print(resp.model_dump_json(indent=2))
print('[PASS] round-trip OK')
"
```

### Verify validation catches bad input
```bash
python -c "
from pydantic import ValidationError
from app.models import TicketInput, Recommendation
errors = 0
try:
    TicketInput(title='', description='valid')
    print('[FAIL] empty title accepted'); errors += 1
except ValidationError:
    print('[PASS] empty title rejected')
try:
    Recommendation(action='x', confidence=1.5, why='y')
    print('[FAIL] confidence > 1.0 accepted'); errors += 1
except ValidationError:
    print('[PASS] confidence > 1.0 rejected')
try:
    TicketInput(title='x', description='y', top_n=0)
    print('[FAIL] top_n=0 accepted'); errors += 1
except ValidationError:
    print('[PASS] top_n=0 rejected')
print(f'Validation tests: {3-errors}/3 passed')
"
```

---
