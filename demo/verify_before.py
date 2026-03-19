"""
Pre-demo check — confirms baseline state BEFORE running agents.
Proves /categories does NOT exist and networking category does NOT exist yet.

Usage:
    python demo/verify_before.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.rules.keyword import CATEGORIES

client = TestClient(app)
passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label} {detail}")
        failed += 1

print("=" * 50)
print("  PRE-DEMO STATE CHECK")
print("=" * 50)

# /categories should NOT exist yet
routes = [r.path for r in app.routes]
check("/categories route does NOT exist yet", "/categories" not in routes,
      f"(found: {routes})")

# networking category should NOT exist yet
keys = [c["key"] for c in CATEGORIES]
check("networking category does NOT exist yet", "networking" not in keys,
      f"(found: {keys})")

# existing routes still work
r = client.get("/health")
check("/health returns 200", r.status_code == 200)

r = client.post("/recommendations", json={"title": "Cannot log in", "description": "password reset"})
check("POST /recommendations returns 200", r.status_code == 200)

check(f"Current categories = {len(keys)}", len(keys) == 6, f"(got {len(keys)})")

print()
print(f"  {passed} passed  |  {failed} failed")
print("=" * 50)

if failed == 0:
    print("\n  Baseline confirmed. Safe to run agents.\n")
    print("  Open 2 terminals and run simultaneously:")
    print()
    print('  Terminal 1 (API Agent):')
    print('  claude "Read agents/agent_api.md and prompts/add_endpoint.md.')
    print('  Add GET /categories that returns supported category keys. Run verification."')
    print()
    print('  Terminal 2 (Core Agent):')
    print('  claude "Read agents/agent_core.md and prompts/add_strategy.md.')
    print('  Add a networking category with keywords: dns, network, firewall, vpn, proxy,')
    print('  ssl, certificate, timeout, connection, socket, port, ip. Run verification."')
    print()
else:
    print("\n  Run python demo/reset.py first to restore baseline.\n")

sys.exit(0 if failed == 0 else 1)
