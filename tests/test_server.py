"""The web front with FastAPI's TestClient and a fake brain, plus the Valkey reflexes with a fake redis."""
from types import SimpleNamespace as NS
from unittest import mock

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from agent import cache, config, server
from agent.brain import RateLimited, Reply


class FakeBrain:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def chat(self, session_id, message):
        self.calls.append((session_id, message))
        if self.error:
            raise self.error
        return Reply(f"echo: {message}", ["search_docs"])

    def roles(self):
        return [("brain", "live", "hackathon-chat at https://fake/v1"),
                ("memory", "fallback", "kept in this process only")]

    def status(self):
        return [f"{role} {state} {detail}" for role, state, detail in self.roles()]


@pytest.fixture
def client_with():
    def make(brain):
        server.app.state.brain = brain
        return TestClient(server.app)
    yield make
    del server.app.state.brain


def test_chat_returns_the_reply_and_the_tools_used(client_with):
    brain = FakeBrain()
    response = client_with(brain).post("/chat", json={"session_id": "web-1", "message": "Where can I park?"})
    assert response.status_code == 200
    assert response.json() == {"reply": "echo: Where can I park?", "tools_used": ["search_docs"]}
    assert brain.calls == [("web-1", "Where can I park?")]


def test_chat_rejects_empty_fields(client_with):
    client = client_with(FakeBrain())
    assert client.post("/chat", json={"session_id": "", "message": "hi"}).status_code == 422
    assert client.post("/chat", json={"session_id": "web-1"}).status_code == 422


def test_rate_limit_becomes_429(client_with):
    response = client_with(FakeBrain(RateLimited("Wait a moment."))).post(
        "/chat", json={"session_id": "web-1", "message": "hi"})
    assert response.status_code == 429
    assert response.json()["detail"] == "Wait a moment."


def test_brain_errors_become_502(client_with):
    request = httpx.Request("POST", "https://fake/v1/chat/completions")
    error = openai.APIStatusError("busy", response=httpx.Response(503, request=request), body=None)
    response = client_with(FakeBrain(error)).post("/chat", json={"session_id": "web-1", "message": "hi"})
    assert response.status_code == 502
    assert "did not answer" in response.json()["detail"]


def test_health_lists_every_role(client_with):
    response = client_with(FakeBrain()).get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "brain": {"state": "live", "detail": "hackathon-chat at https://fake/v1"},
        "memory": {"state": "fallback", "detail": "kept in this process only"},
    }


def test_the_chat_page_is_served(client_with):
    response = client_with(FakeBrain()).get("/")
    assert response.status_code == 200
    assert "<title>HackMidwest starter agent</title>" in response.text


class FakeRedis:
    def __init__(self):
        self.data, self.expiries = {}, {}

    def info(self, section):
        return {"redis_version": "7.2.4", "valkey_version": "8.1.4"}

    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def expire(self, key, seconds):
        self.expiries[key] = seconds

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value
        self.expiries[key] = ex


def test_valkey_allows_twenty_messages_a_minute_per_session():
    fake = FakeRedis()
    with mock.patch("redis.Redis.from_url", return_value=fake):
        valkey = cache.Valkey("redis://valkey:6379/0")
    results = [valkey.allow("web-1") for _ in range(cache.RATE_LIMIT + 1)]
    assert results.count(True) == cache.RATE_LIMIT and results[-1] is False
    assert valkey.allow("web-2") is True  # another session has its own count
    assert set(fake.expiries.values()) == {60}
    assert valkey.detail.startswith("Valkey 8.1.4 at valkey:6379")


def test_valkey_caches_vectors_for_a_day():
    fake = FakeRedis()
    with mock.patch("redis.Redis.from_url", return_value=fake):
        valkey = cache.Valkey("redis://valkey:6379/0")
    assert valkey.get_vector("m", "where to park") is None
    valkey.set_vector("m", "where to park", [0.5, 0.25])
    assert valkey.get_vector("m", "where to park") == [0.5, 0.25]
    assert cache.VECTOR_TTL in fake.expiries.values()


def test_without_valkey_everything_is_allowed_and_nothing_cached():
    off = cache.connect(config.Config(base_url="x", api_key="y"))
    assert off.state == "off" and off.allow("web-1") and off.get_vector("m", "t") is None


def test_unreachable_valkey_turns_reflexes_off_with_the_reason():
    cfg = config.Config(base_url="x", api_key="y", valkey_url="redis://valkey:6379/0")
    with mock.patch("redis.Redis.from_url", side_effect=ConnectionError("refused")):
        off = cache.connect(cfg)
    assert off.state == "error" and "refused" in off.detail and off.allow("web-1")
