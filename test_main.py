"""Tests for the /ask API. OpenAI is replaced by a fake, so running them costs nothing."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)
GOOD = '{"answer": "Paris.", "confidence": 0.95, "sources_needed": false}'


@pytest.fixture(autouse=True)
def no_real_openai_calls(monkeypatch):
    """Fail loudly if a test would reach the real OpenAI API."""

    def forbidden(model, question):
        raise AssertionError("Tests must not call OpenAI")

    monkeypatch.setattr(main, "call_model", forbidden)
    monkeypatch.setitem(main._today, "count", 0)


def fake_model(monkeypatch, *outputs):
    """Make the 'model' return these outputs in order, each using 100 input and 20 output tokens."""
    calls = []

    def call_model(model, question):
        calls.append(model)
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120)
        return outputs[len(calls) - 1], usage

    monkeypatch.setattr(main, "call_model", call_model)
    return calls


def test_health_does_not_call_openai():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ask_returns_answer_tokens_and_cost(monkeypatch):
    fake_model(monkeypatch, GOOD)
    r = client.post("/ask", json={"question": "Capital of France?", "model": "gpt-4o-mini"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == {"answer": "Paris.", "confidence": 0.95, "sources_needed": False}
    assert body["tokens_used"] == 120
    assert body["model"] == "gpt-4o-mini"
    assert body["cost_usd"] == pytest.approx((100 * 0.15 + 20 * 0.60) / 1_000_000)
    assert body["attempts"] == [{"attempt": 1, "valid": True, "error": None}]


def test_force_bad_is_caught_by_the_guardrail_then_retried(monkeypatch):
    calls = fake_model(monkeypatch, GOOD)
    body = client.post("/ask", json={"question": "Capital of France?", "force_bad": True}).json()
    first, second = body["attempts"]
    assert first["valid"] is False
    for field in ("answer", "confidence", "sources_needed"):
        assert field in first["error"]
    assert second["valid"] is True
    assert len(calls) == 1  # the bad answer was simulated: only the retry reached the model


def test_two_invalid_outputs_return_502(monkeypatch):
    fake_model(monkeypatch, "not json at all", '{"answer": "Hi"}')
    r = client.post("/ask", json={"question": "Hello?"})
    assert r.status_code == 502
    assert [a["valid"] for a in r.json()["detail"]["attempts"]] == [False, False]


def test_openai_error_returns_502(monkeypatch):
    def out_of_credits(model, question):
        raise RuntimeError("insufficient_quota")

    monkeypatch.setattr(main, "call_model", out_of_credits)
    r = client.post("/ask", json={"question": "Hello?"})
    assert r.status_code == 502
    assert "insufficient_quota" in r.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [
        {"question": "   "},  # empty
        {"question": "x" * 2001},  # too long
        {"question": "Hi", "model": "gpt-5.6-sol"},  # expensive model, not allowed
        {},  # no question
    ],
)
def test_bad_requests_are_rejected_before_any_cost(body):
    assert client.post("/ask", json=body).status_code == 422


def test_daily_limit(monkeypatch):
    fake_model(monkeypatch, GOOD)
    monkeypatch.setattr(main, "DAILY_REQUEST_LIMIT", 1)
    assert client.post("/ask", json={"question": "One"}).status_code == 200
    assert client.post("/ask", json={"question": "Two"}).status_code == 429
