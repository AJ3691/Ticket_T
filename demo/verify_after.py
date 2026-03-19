"""
Post-demo check — confirms BOTH agents delivered after running concurrently.
Run this after both agents finish.

Usage:
    python demo/verify_after.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

# Force reimport to pick up any file changes
import importlib
import app.rules.keyword
import app.main
importlib.reload(app.rules.keyword)
importlib.reload(app.main)

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
        print(f"  [FAIL] {label}  {detail}")
        failed += 1

print("=" * 50)
print("  POST-DEMO STATE CHECK")
print("=" * 50)
print()
print("  --- API Agent (main.py) ---")

routes = [r.path for r in app.routes]
check("/categories route EXISTS", "/categories" in routes, f"routes={routes}")

r = client.get("/categories")
check("GET /categories returns 200", r.status_code == 200)
if r.status_code == 200:
    body = r.json()
    has_categories = "categories" in body
    check("Response has 'categories' key", has_categories, str(body))
    if has_categories:
        print(f"         categories = {body['categories']}")

print()
print("  --- Core Agent (keyword.py) ---")

keys = [c["key"] for c in CATEGORIES]
check("networking category EXISTS", "networking" in keys, f"keys={keys}")
check(f"Total categories = 7", len(keys) == 7, f"(got {len(keys)})")

r = client.post("/recommendations", json={
    "title": "SSL certificate error",
    "description": "VPN connection timeout, dns resolution failing, firewall blocking port"
})
check("Networking ticket returns 200", r.status_code == 200)
if r.status_code == 200:
    top = r.json()["recommendations"][0]
    print(f"         top result: [{top['confidence']}] {top['action']}")

print()
print("  --- Integration ---")

r = client.get("/health")
check("/health still returns 200", r.status_code == 200)

r = client.post("/recommendations", json={"title": "Cannot log in", "description": "password reset"})
check("Existing /recommendations still works", r.status_code == 200)

r1 = client.post("/recommendations", json={"title": "dns timeout", "description": "ssl certificate vpn"})
r2 = client.post("/recommendations", json={"title": "dns timeout", "description": "ssl certificate vpn"})
check("Determinism still holds after changes", r1.json() == r2.json())

print()
print(f"  {passed} passed  |  {failed} failed")
print("=" * 50)

if failed == 0:
    print("\n  Both agents delivered. Run pytest -v for full suite.\n")
else:
    print(f"\n  {failed} check(s) failed. Review agent output above.\n")

sys.exit(0 if failed == 0 else 1)
