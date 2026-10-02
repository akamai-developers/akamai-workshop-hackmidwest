"""Memory: the conversation history of each session.

Without DATABASE_URL, memory lives in this process and is gone when it exits.
"""

HISTORY_LIMIT = 20  # messages sent back to the model each turn, so long chats fit the context window


class LocalMemory:
    """The fallback: plain Python lists, forgotten on restart."""

    def __init__(self):
        self.sessions: dict[str, list[dict]] = {}

    def history(self, session_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
        return self.sessions.get(session_id, [])[-limit:]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self.sessions.setdefault(session_id, []).append({"role": role, "content": content})


def connect(cfg) -> LocalMemory:
    return LocalMemory()
