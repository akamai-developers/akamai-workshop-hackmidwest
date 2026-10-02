"""Reflexes: Valkey for an embedding cache and a per-session rate limit.

The cache keeps the vector for each question text for a day, so asking the same
thing twice costs one embedding request instead of two. The rate limit allows each
session 20 messages per minute, so one busy browser tab cannot spend the whole
team's quota. Without VALKEY_URL both are off and nothing else changes.
"""
import hashlib
import json
import time

from .config import host_of

RATE_LIMIT = 20  # messages per session per minute
VECTOR_TTL = 24 * 60 * 60  # seconds a cached vector lives


class Off:
    """No Valkey: no cache, and every message is allowed."""

    def __init__(self, state: str = "off",
                 detail: str = "no cache and no rate limit. Set VALKEY_URL to turn them on."):
        self.state, self.detail = state, detail

    def get_vector(self, model: str, text: str) -> list[float] | None:
        return None

    def set_vector(self, model: str, text: str, vector: list[float]) -> None:
        pass

    def allow(self, session_id: str) -> bool:
        return True


class Valkey:
    state = "live"

    def __init__(self, url: str):
        import redis  # Valkey speaks the Redis protocol, so the redis package works unchanged

        self.db = redis.Redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
        server = self.db.info("server")
        version = server.get("valkey_version") or server.get("redis_version")
        self.detail = f"Valkey {version} at {host_of(url)}: embedding cache, {RATE_LIMIT} messages a minute per session"

    def get_vector(self, model: str, text: str) -> list[float] | None:
        cached = self.db.get(_vector_key(model, text))
        return json.loads(cached) if cached else None

    def set_vector(self, model: str, text: str, vector: list[float]) -> None:
        self.db.set(_vector_key(model, text), json.dumps(vector), ex=VECTOR_TTL)

    def allow(self, session_id: str) -> bool:
        """Count this session's messages in the current minute. True while the count is within the limit."""
        key = f"rate:{session_id}:{int(time.time() // 60)}"
        count = self.db.incr(key)
        if count == 1:
            self.db.expire(key, 60)
        return count <= RATE_LIMIT


def _vector_key(model: str, text: str) -> str:
    return f"vector:{model}:{hashlib.sha256(text.encode()).hexdigest()}"


def connect(cfg):
    """Valkey when VALKEY_URL is set and answering, otherwise off."""
    if not cfg.valkey_url:
        return Off()
    try:
        return Valkey(cfg.valkey_url)
    except Exception as error:  # the agent works without reflexes, so keep going
        return Off("error", f"Valkey at {host_of(cfg.valkey_url)} failed ({error}). Running without cache and rate limit.")
