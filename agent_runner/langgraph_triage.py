"""
Deterministic LangGraph workflow for support ticket triage.

This is the Phase 3 proof of concept: it teaches LangGraph state, nodes, edges,
and streaming without requiring an LLM API key. A future iteration can replace
the draft_recommendations node with an LLM-backed node while keeping the AG-UI
adapter contract unchanged.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class TriageState(TypedDict, total=False):
    title: str
    description: str
    category: str
    recommendations: list[dict[str, Any]]
    final_text: str


CategoryConfig = dict[str, Any]


CATEGORIES: dict[str, CategoryConfig] = {
    "account_access": {
        "keywords": {
            "login",
            "password",
            "reset",
            "locked",
            "account",
            "mfa",
            "2fa",
            "auth",
            "signin",
            "token",
        },
        "recommendations": [
            {
                "action": "Verify the user's identity and reset the account access flow",
                "confidence": 0.94,
                "why": "The ticket mentions login, password, token, or account access symptoms.",
            },
            {
                "action": "Check MFA and session settings for the affected user",
                "confidence": 0.82,
                "why": "Authentication failures are often caused by stale sessions or MFA policy changes.",
            },
            {
                "action": "Review recent auth service errors for this account",
                "confidence": 0.74,
                "why": "Backend auth errors can explain repeated access failures after a reset.",
            },
        ],
    },
    "billing": {
        "keywords": {
            "billing",
            "invoice",
            "payment",
            "charge",
            "refund",
            "card",
            "subscription",
            "plan",
            "receipt",
            "price",
        },
        "recommendations": [
            {
                "action": "Review the latest invoice and payment status",
                "confidence": 0.92,
                "why": "The ticket contains billing or payment language.",
            },
            {
                "action": "Confirm the customer's active plan and renewal date",
                "confidence": 0.8,
                "why": "Subscription state often explains billing confusion.",
            },
            {
                "action": "Escalate disputed charges to the billing queue",
                "confidence": 0.7,
                "why": "Refunds and charge disputes need billing-specific handling.",
            },
        ],
    },
    "networking": {
        "keywords": {
            "dns",
            "network",
            "firewall",
            "vpn",
            "proxy",
            "ssl",
            "certificate",
            "timeout",
            "connection",
            "socket",
            "port",
            "ip",
        },
        "recommendations": [
            {
                "action": "Check DNS resolution and endpoint reachability",
                "confidence": 0.9,
                "why": "Network tickets often start with DNS, timeout, or connection failures.",
            },
            {
                "action": "Verify firewall, proxy, and VPN routing rules",
                "confidence": 0.82,
                "why": "Environment-specific routing can block otherwise healthy services.",
            },
            {
                "action": "Inspect SSL certificate validity and chain configuration",
                "confidence": 0.76,
                "why": "TLS issues can surface as connection failures in clients.",
            },
        ],
    },
    "performance": {
        "keywords": {
            "slow",
            "latency",
            "hang",
            "freeze",
            "loading",
            "performance",
            "lag",
            "delay",
            "crash",
            "memory",
        },
        "recommendations": [
            {
                "action": "Check recent latency and error-rate metrics",
                "confidence": 0.88,
                "why": "The ticket points to degraded speed or responsiveness.",
            },
            {
                "action": "Review resource usage for the affected service",
                "confidence": 0.79,
                "why": "Memory or CPU pressure can cause slow requests and crashes.",
            },
            {
                "action": "Ask for timestamps, account ID, and reproduction steps",
                "confidence": 0.68,
                "why": "Performance issues need concrete timing data to isolate.",
            },
        ],
    },
    "general": {
        "keywords": set(),
        "recommendations": [
            {
                "action": "Collect reproduction details and customer impact",
                "confidence": 0.64,
                "why": "The ticket does not strongly match a specialized category yet.",
            },
            {
                "action": "Route to support triage for initial classification",
                "confidence": 0.58,
                "why": "A human triage pass can identify the correct owner quickly.",
            },
            {
                "action": "Ask for screenshots, logs, and exact timestamps",
                "confidence": 0.52,
                "why": "Additional context is needed before assigning a specialized team.",
            },
        ],
    },
}


def classify_ticket(state: TriageState) -> dict[str, str]:
    text = f"{state.get('title', '')} {state.get('description', '')}".lower()
    best_category = "general"
    best_score = 0

    for category, config in CATEGORIES.items():
        keywords: set[str] = config["keywords"]
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score or (score == best_score and category < best_category):
            best_category = category
            best_score = score

    return {"category": best_category}


def draft_recommendations(state: TriageState) -> dict[str, list[dict[str, Any]]]:
    category = state.get("category", "general")
    config = CATEGORIES.get(category, CATEGORIES["general"])
    return {"recommendations": list(config["recommendations"])}


def format_response(state: TriageState) -> dict[str, str]:
    category = state.get("category", "general")
    recommendations = state.get("recommendations", [])
    lines = [f"Category: {category}", "", "Recommendations:"]

    for index, recommendation in enumerate(recommendations, start=1):
        action = recommendation["action"]
        confidence = recommendation["confidence"]
        why = recommendation["why"]
        lines.append(f"{index}. {action} (confidence: {confidence:.2f})")
        lines.append(f"   Why: {why}")

    return {"final_text": "\n".join(lines)}


def build_triage_graph():
    graph = StateGraph(TriageState)
    graph.add_node("classify_ticket", classify_ticket)
    graph.add_node("draft_recommendations", draft_recommendations)
    graph.add_node("format_response", format_response)
    graph.add_edge(START, "classify_ticket")
    graph.add_edge("classify_ticket", "draft_recommendations")
    graph.add_edge("draft_recommendations", "format_response")
    graph.add_edge("format_response", END)
    return graph.compile()
