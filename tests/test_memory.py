"""Memory: the in-process fallback, and PostgresMemory with psycopg mocked."""
import socket
from unittest import mock

import psycopg
import pytest

from agent import config, memory

PG_URL = "postgresql://akmadmin:pa55word@db.example.com:15268/defaultdb?sslmode=require"


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    """PostgresMemory looks up the database's IPv4 address. Answer without the network."""
    answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 0))]
    monkeypatch.setattr(memory.socket, "getaddrinfo", lambda *args, **kwargs: answer)


def test_local_history_is_per_session_and_capped():
    mem = memory.LocalMemory()
    for i in range(30):
        mem.add_message("a", "user", f"message {i}")
    mem.add_message("b", "user", "hello")
    assert len(mem.history("a")) == memory.HISTORY_LIMIT
    assert mem.history("a")[-1] == {"role": "user", "content": "message 29"}
    assert mem.history("b") == [{"role": "user", "content": "hello"}]
    assert mem.history("nobody") == []


def test_local_documents_and_notes_are_searched_separately():
    mem = memory.LocalMemory()
    mem.replace_document("parking.md", ["Park in Lot C."], [[1.0, 0.0]])
    mem.replace_document("food.md", ["Lunch at noon."], [[0.0, 1.0]])
    note = mem.add_note("Our demo is at 2:15 PM.", [0.9, 0.1])

    docs = mem.search([1.0, 0.0])
    assert [h.key for h in docs] == ["parking.md", "food.md"]
    assert docs[0].score == pytest.approx(1.0)
    notes = mem.search([1.0, 0.0], notes=True)
    assert [h.key for h in notes] == [note]
    assert note.startswith("notes/")
    assert mem.document_keys() == {"parking.md", "food.md"}


def test_local_replace_and_delete_document():
    mem = memory.LocalMemory()
    mem.replace_document("parking.md", ["old"], [[1.0, 0.0]])
    mem.replace_document("parking.md", ["new one", "new two"], [[1.0, 0.0], [0.0, 1.0]])
    assert sorted(h.text for h in mem.search([1.0, 1.0], k=5)) == ["new one", "new two"]
    mem.delete_document("parking.md")
    assert mem.search([1.0, 0.0]) == []


def test_no_database_url_means_the_fallback():
    mem = memory.connect(config.Config(base_url="x", api_key="y"))
    assert isinstance(mem, memory.LocalMemory)
    assert mem.state == "fallback"


def test_an_unreachable_database_falls_back_and_says_why_without_the_password():
    cfg = config.Config(base_url="x", api_key="y", database_url=PG_URL)
    with mock.patch("psycopg.connect", side_effect=psycopg.errors.ConnectionTimeout("connection timeout expired")):
        mem = memory.connect(cfg)
    assert isinstance(mem, memory.LocalMemory)
    assert mem.state == "error"
    assert "db.example.com:15268" in mem.detail and "timeout" in mem.detail
    assert "pa55word" not in mem.detail
    # A database drops connections from addresses that are not on its allow list, so they time out.
    assert mem.detail.endswith(memory.ALLOW_LIST_HINT)


def test_other_connection_errors_get_no_allow_list_hint():
    cfg = config.Config(base_url="x", api_key="y", database_url=PG_URL)
    error = psycopg.OperationalError('connection failed: FATAL:  password authentication failed for user "akmadmin"')
    with mock.patch("psycopg.connect", side_effect=error):
        mem = memory.connect(cfg)
    assert "password authentication failed" in mem.detail
    assert "allow list" not in mem.detail


def test_a_database_without_pgvector_points_to_db_init():
    cfg = config.Config(base_url="x", api_key="y", database_url=PG_URL)
    with mock.patch("psycopg.connect"), \
         mock.patch("pgvector.psycopg.register_vector",
                    side_effect=psycopg.ProgrammingError("vector type not found in the database")):
        mem = memory.connect(cfg)
    assert mem.state == "error"
    assert "scripts/db_init.py" in mem.detail


class FakeCursor:
    def __init__(self, rows=(), description=True):
        self.rows, self.description = list(rows), description

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


def connected(*results):
    """A PostgresMemory whose connection answers execute() with the given results, in order."""
    conn = mock.MagicMock()
    conn.execute.side_effect = [FakeCursor([("17.6",)]), FakeCursor([("0.8.0",)]), *results]
    with mock.patch("psycopg.connect", return_value=conn), mock.patch("pgvector.psycopg.register_vector"):
        mem = memory.PostgresMemory(PG_URL)
    return mem, conn


def test_postgres_status_names_versions_but_not_the_password():
    mem, _ = connected()
    assert mem.state == "live"
    assert mem.detail == "PostgreSQL 17.6 at db.example.com:15268, pgvector 0.8.0"


def test_postgres_add_message_creates_the_session_then_the_message():
    mem, conn = connected(FakeCursor(description=None), FakeCursor(description=None))
    mem.add_message("terminal", "user", "hello")
    sessions_sql, sessions_args = conn.execute.call_args_list[2].args
    messages_sql, messages_args = conn.execute.call_args_list[3].args
    assert "INSERT INTO sessions" in sessions_sql and "ON CONFLICT DO NOTHING" in sessions_sql
    assert sessions_args == ("terminal",)
    assert "INSERT INTO messages" in messages_sql
    assert messages_args == ("terminal", "user", "hello")


def test_postgres_history_returns_oldest_first():
    mem, conn = connected(FakeCursor([("user", "hi"), ("assistant", "hello")]))
    assert mem.history("terminal") == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    sql, args = conn.execute.call_args_list[2].args
    assert "ORDER BY id DESC LIMIT" in sql and "ORDER BY id" in sql
    assert args == ("terminal", memory.HISTORY_LIMIT)


def test_postgres_search_filters_notes_and_returns_hits():
    mem, conn = connected(FakeCursor([("notes/1", "Demo at 2:15 PM.", 0.82)]))
    hits = mem.search([0.1] * 4, k=2, notes=True)
    assert hits == [memory.Hit("notes/1", "Demo at 2:15 PM.", 0.82)]
    sql, params = conn.execute.call_args_list[2].args
    assert "<=>" in sql and "starts_with(object_key, 'notes/')" in sql
    assert params["notes"] is True and params["k"] == 2


def test_postgres_reconnects_once_after_a_dropped_connection():
    first, second = mock.MagicMock(), mock.MagicMock()
    first.execute.side_effect = [FakeCursor([("17.6",)]), FakeCursor([("0.8.0",)]),
                                 psycopg.OperationalError("server closed the connection unexpectedly")]
    second.execute.return_value = FakeCursor([("parking.md",)])
    with mock.patch("psycopg.connect", side_effect=[first, second]), mock.patch("pgvector.psycopg.register_vector"):
        mem = memory.PostgresMemory(PG_URL)
        assert mem.document_keys() == {"parking.md"}
    assert mem.conn is second


def test_postgres_connects_over_ipv4_and_keeps_the_host_name():
    conn = mock.MagicMock()
    conn.execute.side_effect = [FakeCursor([("17.6",)]), FakeCursor([("0.8.0",)])]
    with mock.patch("psycopg.connect", return_value=conn) as connect, mock.patch("pgvector.psycopg.register_vector"):
        memory.PostgresMemory(PG_URL)
    assert connect.call_args.args == (PG_URL,)  # the host name stays in the URL, for TLS
    assert connect.call_args.kwargs["hostaddr"] == "192.0.2.10"


def test_ipv4_of_leaves_the_lookup_to_psycopg_when_there_is_no_ipv4_answer(monkeypatch):
    def no_answer(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(memory.socket, "getaddrinfo", no_answer)
    assert memory.ipv4_of(PG_URL) is None


def test_ipv4_of_ignores_settings_that_are_not_a_url():
    assert memory.ipv4_of("host=db.example.com user=akmadmin") is None
