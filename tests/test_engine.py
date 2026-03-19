import pytest
from app.engine import get_recommendations
from app.models import Recommendation
from app.rules.keyword import KeywordStrategy
from app.rules.base import TriageStrategy


def test_determinism():
    r1 = get_recommendations("Cannot log in", "I reset my password but still get an error")
    r2 = get_recommendations("Cannot log in", "I reset my password but still get an error")
    assert len(r1) == len(r2)
    for a, b in zip(r1, r2):
        assert a.action == b.action
        assert a.confidence == b.confidence
        assert a.why == b.why


def test_confidence_sorted():
    results = get_recommendations("Cannot log in", "Password reset not working", top_n=10)
    for i in range(len(results) - 1):
        assert results[i].confidence >= results[i + 1].confidence


def test_top_n_limiting():
    for n in [1, 2, 3, 5]:
        results = get_recommendations("login password error", "auth issue", top_n=n)
        assert len(results) <= n


def test_top_n_default():
    results = get_recommendations("login issue", "password not working")
    assert len(results) <= 3


def test_fallback_no_matches():
    results = get_recommendations("xyzzy gibberish", "nothing matches here at all")
    assert isinstance(results, list)


def test_fallback_valid_objects():
    results = get_recommendations("xyzzy gibberish", "nothing matches")
    for r in results:
        assert isinstance(r, Recommendation)
        assert 0.0 <= r.confidence <= 1.0
        assert len(r.action) > 0
        assert len(r.why) > 0


def test_multi_category():
    results = get_recommendations(
        "Slow login after password reset",
        "Performance is terrible and I keep getting locked out",
        top_n=10,
    )
    assert len(results) >= 2
    actions = [r.action for r in results]
    assert len(set(actions)) > 1


def test_single_category():
    results = get_recommendations("invoice problem", "wrong charge on my billing statement")
    assert len(results) >= 1
    assert all(isinstance(r, Recommendation) for r in results)


def test_confidence_range():
    results = get_recommendations("login password reset error locked", "auth token session", top_n=10)
    for r in results:
        assert 0.0 <= r.confidence <= 1.0, f"Out of range: {r.confidence}"


def test_non_empty_fields():
    results = get_recommendations("Cannot log in", "Password error", top_n=10)
    for r in results:
        assert len(r.action) > 0, "Empty action"
        assert len(r.why) > 0, "Empty why"


def test_strategy_interface():
    assert issubclass(KeywordStrategy, TriageStrategy)
