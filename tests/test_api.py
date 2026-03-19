import pytest
from fastapi.testclient import TestClient
from app.main import app, _metrics


def test_happy_path():
    client = TestClient(app)
    r = client.post("/recommendations", json={
        "title": "Cannot log in",
        "description": "I reset my password but still get an error",
    })
    assert r.status_code == 200
    body = r.json()
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)
    assert len(body["recommendations"]) > 0


def test_response_shape():
    client = TestClient(app)
    r = client.post("/recommendations", json={
        "title": "Cannot log in",
        "description": "Password error",
    })
    for rec in r.json()["recommendations"]:
        assert "action" in rec
        assert "confidence" in rec
        assert "why" in rec
        assert isinstance(rec["confidence"], (int, float))
        assert 0.0 <= rec["confidence"] <= 1.0


def test_determinism_http():
    client = TestClient(app)
    payload = {"title": "Cannot log in", "description": "Password reset not working"}
    r1 = client.post("/recommendations", json=payload)
    r2 = client.post("/recommendations", json=payload)
    assert r1.json() == r2.json()


def test_empty_body():
    client = TestClient(app)
    r = client.post("/recommendations", json={})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_missing_title():
    client = TestClient(app)
    r = client.post("/recommendations", json={"description": "some desc"})
    assert r.status_code == 422


def test_missing_description():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "some title"})
    assert r.status_code == 422


def test_empty_title():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "", "description": "valid"})
    assert r.status_code == 422


def test_empty_description():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "valid", "description": ""})
    assert r.status_code == 422


def test_top_n_too_low():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "x", "description": "y", "top_n": 0})
    assert r.status_code == 422


def test_top_n_too_high():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "x", "description": "y", "top_n": 11})
    assert r.status_code == 422


def test_invalid_json():
    client = TestClient(app)
    r = client.post("/recommendations", content=b"not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_metrics():
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    m = r.json()
    assert "request_count" in m
    assert "error_count" in m
    assert "total_latency_ms" in m


def test_telemetry_request_count():
    client = TestClient(app)
    before = _metrics["request_count"]
    client.get("/health")
    after = _metrics["request_count"]
    assert after > before


def test_telemetry_error_count():
    client = TestClient(app)
    before = _metrics["error_count"]
    client.post("/recommendations", json={})
    after = _metrics["error_count"]
    assert after > before
