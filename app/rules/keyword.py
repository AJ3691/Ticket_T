"""Keyword-based triage strategy."""

from app.models import Recommendation
from app.rules.base import TriageStrategy


CATEGORIES = [
    {
        "key": "access",
        "keywords": ["permission", "access", "denied", "forbidden", "role", "admin", "unauthorized", "privilege", "restrict", "blocked", "firewall"],
        "weight": 0.90,
        "actions": [
            {"action": "Check user role and permission assignments", "why": "Access denials often result from missing or misconfigured role assignments."},
            {"action": "Review firewall and IP restriction rules", "why": "Network-level blocks can prevent legitimate access even with correct credentials."},
            {"action": "Audit recent permission changes for this user", "why": "A recent role change may have inadvertently removed necessary access."},
        ],
    },
    {
        "key": "auth",
        "keywords": ["login", "password", "reset", "locked", "credentials", "auth", "token", "session", "sso", "mfa", "2fa", "signin", "signout", "logout"],
        "weight": 0.95,
        "actions": [
            {"action": "Verify account status and recent lockouts", "why": "Login failures after reset often correlate with lockouts or disabled accounts."},
            {"action": "Check auth provider error logs for this user", "why": "The error may be coming from the identity provider, not the app."},
            {"action": "Ask user for exact error code and timestamp", "why": "Pinpointing the time and error code speeds up correlation across systems."},
        ],
    },
    {
        "key": "billing",
        "keywords": ["invoice", "charge", "payment", "refund", "subscription", "billing", "plan", "upgrade", "downgrade", "price", "cost", "receipt"],
        "weight": 0.85,
        "actions": [
            {"action": "Review recent billing transactions for this account", "why": "Unexpected charges often trace to proration, renewal timing, or add-on activation."},
            {"action": "Check subscription plan change history", "why": "Plan changes can generate unexpected charges or affect feature availability."},
            {"action": "Issue prorated refund if charge is confirmed incorrect", "why": "Resolving billing disputes quickly preserves customer trust."},
        ],
    },
    {
        "key": "data",
        "keywords": ["data", "sync", "missing", "lost", "corrupt", "backup", "restore", "export", "import", "duplicate", "merge", "migration"],
        "weight": 0.75,
        "actions": [
            {"action": "Check sync status and last successful sync timestamp", "why": "Data discrepancies often stem from interrupted or failed sync operations."},
            {"action": "Verify backup integrity and restore from last known good state", "why": "Corruption or loss may require rollback to a verified backup."},
            {"action": "Review import/export logs for transformation errors", "why": "Data migration issues frequently arise from field mapping or encoding mismatches."},
        ],
    },
    {
        "key": "integration",
        "keywords": ["api", "integration", "webhook", "endpoint", "connect", "third-party", "plugin", "extension", "oauth", "sdk", "rest", "graphql"],
        "weight": 0.70,
        "actions": [
            {"action": "Check API credentials and token expiry", "why": "Integration failures often stem from expired or revoked API keys."},
            {"action": "Review webhook delivery logs for failures", "why": "Failed webhook deliveries indicate connectivity or authentication issues with the endpoint."},
            {"action": "Test endpoint connectivity and response format", "why": "Third-party API changes can break integrations without notice."},
        ],
    },
    {
        "key": "performance",
        "keywords": ["slow", "timeout", "latency", "loading", "speed", "lag", "hang", "freeze", "unresponsive", "performance", "crash", "memory"],
        "weight": 0.80,
        "actions": [
            {"action": "Check server resource utilization (CPU, memory, I/O)", "why": "Performance degradation typically correlates with resource saturation."},
            {"action": "Review recent deployments for performance regressions", "why": "A new release may have introduced inefficient queries or resource leaks."},
            {"action": "Profile slow operations and identify bottlenecks", "why": "Targeted profiling pinpoints the root cause faster than broad investigation."},
        ],
    },
]

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


class KeywordStrategy(TriageStrategy):
    def __init__(self):
        self.categories = CATEGORIES

    def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
        text = f"{title} {description}".lower()
        scored = []
        for category in self.categories:
            matches = sum(1 for kw in category["keywords"] if kw in text)
            if matches == 0:
                continue
            base = matches / len(category["keywords"])
            confidence = round(min(base * category["weight"], 1.0), 2)
            for i, action_def in enumerate(category["actions"]):
                decay = 1.0 - (i * 0.15)
                action_confidence = round(confidence * decay, 2)
                scored.append({
                    "action": action_def["action"],
                    "confidence": action_confidence,
                    "why": action_def["why"],
                    "sort_key": category["key"],
                })
        scored.sort(key=lambda x: (-x["confidence"], x["sort_key"]))
        if not scored:
            return list(FALLBACK_ACTIONS[:top_n])
        return [
            Recommendation(action=s["action"], confidence=s["confidence"], why=s["why"])
            for s in scored[:top_n]
        ]
