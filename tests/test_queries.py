"""
Manual query runner — run this directly to see real responses.

Usage (from project root):
    python -m tests.test_queries
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

QUERIES = [
    {
        "title": "Cannot log in",
        "description": "I reset my password but still get an error",
        "top_n": 3,
    },
    {
        "title": "Slow dashboard",
        "description": "App freezes and times out on load, very laggy",
    },
    {
        "title": "Wrong invoice charge",
        "description": "I was charged twice for my subscription this month",
    },
    {
        "title": "API webhook failing",
        "description": "Our integration endpoint is not receiving events from the SDK",
    },
    {
        "title": "Missing data after sync",
        "description": "Export shows corrupt and duplicate records after migration",
    },
    {
        "title": "Access denied to admin panel",
        "description": "User role was changed but still getting forbidden error",
    },
    {
        "title": "MFA not working",
        "description": "Two factor auth token keeps failing after SSO login",
        "top_n": 5,
    },
    {
        "title": "Payment refund not processed",
        "description": "Requested refund 2 weeks ago, no receipt and still charged",
        "top_n": 2,
    },
    {
        "title": "Random gibberish ticket",
        "description": "xyzzy nothing matches this at all blorp",
    },
]


def run():
    print("=" * 60)
    print("  Support Ticket Triage — Query Runner")
    print("=" * 60)

    errors = 0

    for i, q in enumerate(QUERIES, 1):
        r = client.post("/recommendations", json=q)
        top_n = q.get("top_n", 3)

        print(f"\n[{i}] {q['title']}")
        print(f"     {q['description'][:60]}{'...' if len(q['description']) > 60 else ''}")
        print(f"     top_n={top_n}  |  status={r.status_code}")

        if r.status_code == 200:
            for rec in r.json()["recommendations"]:
                bar = "#" * int(rec["confidence"] * 20)
                print(f"     [{rec['confidence']:.2f}] {bar:<20s}  {rec['action']}")
        else:
            errors += 1
            print(f"     ERROR: {r.json()}")

    # health + metrics
    print("\n" + "=" * 60)
    health = client.get("/health").json()
    metrics = client.get("/metrics").json()

    print(f"  Health:         {health}")
    print(f"  request_count:  {metrics['request_count']}")
    print(f"  error_count:    {metrics['error_count']}")
    print(f"  total_latency:  {round(metrics['total_latency_ms'], 2)}ms")
    print(f"  avg_latency:    {round(metrics['total_latency_ms'] / metrics['request_count'], 2)}ms")
    print("=" * 60)

    if errors == 0:
        print(f"\n  All {len(QUERIES)} queries returned 200. Engine working correctly.\n")
    else:
        print(f"\n  {errors} queries failed. Check output above.\n")


if __name__ == "__main__":
    run()
