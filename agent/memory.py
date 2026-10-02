"""Memory: conversation history, document vectors, and notes.

With DATABASE_URL set, all of it lives in Managed PostgreSQL and survives a restart.
Vectors sit in a pgvector column, and PostgreSQL finds the closest ones with the
<=> (cosine distance) operator. Without DATABASE_URL, LocalMemory keeps the same
things in Python lists until the process exits.

Notes saved with the remember tool are rows in the documents table whose key starts
with notes/, so recall is the same vector search as search_docs with another filter.
"""
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from .config import host_of

HISTORY_LIMIT = 20  # messages sent back to the model each turn, so long chats fit the context window


@dataclass
class Hit:
    key: str  # the file name in the bucket, or notes/... for a note
    text: str
    score: float  # cosine similarity: 1.0 is the same meaning, 0 is unrelated


def note_key() -> str:
    """A unique key for one note, sortable by time."""
    return f"notes/{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


class LocalMemory:
    """The fallback: plain Python lists, forgotten on restart."""

    def __init__(self, state: str = "fallback",
                 detail: str = "kept in this process only, forgotten on restart. Set DATABASE_URL in .env."):
        self.state, self.detail = state, detail
        self.sessions: dict[str, list[dict]] = {}
        self.rows: list[tuple[str, str, np.ndarray]] = []  # (key, text, vector)

    def history(self, session_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
        return self.sessions.get(session_id, [])[-limit:]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self.sessions.setdefault(session_id, []).append({"role": role, "content": content})

    def document_keys(self) -> set[str]:
        return {key for key, _, _ in self.rows if not key.startswith("notes/")}

    def replace_document(self, key: str, chunks: list[str], vectors: list[list[float]]) -> None:
        self.delete_document(key)
        self.rows += [(key, text, np.asarray(vector, dtype=np.float32)) for text, vector in zip(chunks, vectors)]

    def delete_document(self, key: str) -> None:
        self.rows = [row for row in self.rows if row[0] != key]

    def add_note(self, text: str, vector: list[float]) -> str:
        key = note_key()
        self.rows.append((key, text, np.asarray(vector, dtype=np.float32)))
        return key

    def search(self, vector: list[float], k: int = 3, notes: bool = False) -> list[Hit]:
        rows = [row for row in self.rows if row[0].startswith("notes/") == notes]
        if not rows:
            return []
        matrix = np.stack([row[2] for row in rows])
        query = np.asarray(vector, dtype=np.float32)
        scores = matrix @ query / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(query))
        best = np.argsort(-scores)[:k]
        return [Hit(rows[i][0], rows[i][1], float(scores[i])) for i in best]


class PostgresMemory:
    """Managed PostgreSQL with pgvector. Run scripts/db_init.py once to create the tables."""

    state = "live"

    def __init__(self, url: str):
        self.url = url
        self.lock = threading.Lock()  # the web server shares one connection between threads
        self._connect()
        server = self.conn.execute("SHOW server_version").fetchone()[0].split()[0]
        pgvector = self.conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()[0]
        self.detail = f"PostgreSQL {server} at {host_of(url)}, pgvector {pgvector}"

    def _connect(self) -> None:
        import psycopg
        from pgvector.psycopg import register_vector

        # Keepalives notice a connection that Wi-Fi or a NAT dropped while idle, so a query fails fast
        # and _run() reconnects, instead of hanging for minutes.
        self.conn = psycopg.connect(self.url, autocommit=True, connect_timeout=10, keepalives=1,
                                    keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
        register_vector(self.conn)  # fails here if pgvector is not enabled yet

    def _run(self, sql: str, params=None) -> list[tuple]:
        """Run one statement. If the database dropped an idle connection, reconnect once and retry."""
        import psycopg

        with self.lock:
            try:
                cursor = self.conn.execute(sql, params)
            except psycopg.OperationalError:
                self._connect()
                cursor = self.conn.execute(sql, params)
            return cursor.fetchall() if cursor.description else []

    def history(self, session_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
        rows = self._run(
            "SELECT role, content FROM (SELECT id, role, content FROM messages WHERE session_id = %s"
            " ORDER BY id DESC LIMIT %s) AS recent ORDER BY id",
            (session_id, limit),
        )
        return [{"role": role, "content": content} for role, content in rows]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self._run("INSERT INTO sessions (id) VALUES (%s) ON CONFLICT DO NOTHING", (session_id,))
        self._run("INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)", (session_id, role, content))

    def document_keys(self) -> set[str]:
        rows = self._run("SELECT DISTINCT object_key FROM documents WHERE NOT starts_with(object_key, 'notes/')")
        return {key for (key,) in rows}

    def replace_document(self, key: str, chunks: list[str], vectors: list[list[float]]) -> None:
        with self.lock, self.conn.transaction():  # readers see the old chunks or the new ones, never a mix
            self.conn.execute("DELETE FROM documents WHERE object_key = %s", (key,))
            with self.conn.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO documents (object_key, chunk_index, content, embedding) VALUES (%s, %s, %s, %s)",
                    [(key, i, text, np.asarray(vector, dtype=np.float32))
                     for i, (text, vector) in enumerate(zip(chunks, vectors))],
                )

    def delete_document(self, key: str) -> None:
        self._run("DELETE FROM documents WHERE object_key = %s", (key,))

    def add_note(self, text: str, vector: list[float]) -> str:
        key = note_key()
        self._run(
            "INSERT INTO documents (object_key, chunk_index, content, embedding) VALUES (%s, 0, %s, %s)",
            (key, text, np.asarray(vector, dtype=np.float32)),
        )
        return key

    def search(self, vector: list[float], k: int = 3, notes: bool = False) -> list[Hit]:
        rows = self._run(
            "SELECT object_key, content, 1 - (embedding <=> %(v)s) FROM documents"
            " WHERE starts_with(object_key, 'notes/') = %(notes)s"
            " ORDER BY embedding <=> %(v)s LIMIT %(k)s",
            {"v": np.asarray(vector, dtype=np.float32), "notes": notes, "k": k},
        )
        return [Hit(key, text, float(score)) for key, text, score in rows]


def connect(cfg):
    """PostgreSQL when DATABASE_URL is set and reachable, otherwise the in-process fallback."""
    if not cfg.database_url:
        return LocalMemory()
    try:
        return PostgresMemory(cfg.database_url)
    except Exception as error:  # keep the agent running and say what went wrong
        reason = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
        if "vector type not found" in reason:
            reason = "pgvector is not enabled yet. Run: python scripts/db_init.py"
        return LocalMemory("error", f"PostgreSQL at {host_of(cfg.database_url)} failed ({reason}). "
                                    "Using the in-process fallback.")
