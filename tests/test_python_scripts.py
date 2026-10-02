"""scripts/db_init.py and scripts/upload.py, with the database, the bucket, and the model mocked."""
import importlib.util
import sys
from pathlib import Path
from unittest import mock

import psycopg

from agent import config, memory

ROOT = Path(__file__).resolve().parent.parent
PG_URL = "postgresql://akmadmin:pa55word@db.example.com:15268/defaultdb?sslmode=require"


def load(name):
    """Import a file from scripts/, which is a folder of scripts and not a package."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_db_init_points_to_the_allow_list_when_the_connection_times_out(monkeypatch, capsys):
    db_init = load("db_init")
    monkeypatch.setattr(db_init.config, "load", lambda: config.Config(base_url="x", api_key="y", database_url=PG_URL))
    monkeypatch.setattr(db_init.memory, "ipv4_of", lambda url: "192.0.2.10")
    monkeypatch.setattr(db_init.psycopg, "connect",
                        mock.Mock(side_effect=psycopg.errors.ConnectionTimeout("connection timeout expired")))
    assert db_init.main() == 1
    out = capsys.readouterr().out
    assert "db.example.com:15268: connection timeout expired" in out
    assert memory.ALLOW_LIST_HINT in out
    assert "pa55word" not in out


def test_upload_says_why_the_vectors_were_not_kept(monkeypatch, capsys, tmp_path):
    upload = load("upload")
    cfg = config.Config(base_url="x", api_key="y", obj_endpoint="https://us-sea-1.linodeobjects.com",
                        obj_bucket="hackmidwest-test", obj_access_key="a", obj_secret_key="s", database_url=PG_URL)
    broken = memory.LocalMemory("error", "PostgreSQL at db.example.com:15268 failed (connection timeout expired). "
                                         f"Using the in-process fallback. {memory.ALLOW_LIST_HINT}")
    bucket = mock.MagicMock(where="bucket hackmidwest-test at us-sea-1.linodeobjects.com")
    bucket.read.return_value = "Park in Lot C."
    monkeypatch.setattr(upload.config, "load", lambda: cfg)
    monkeypatch.setattr(upload.memory, "connect", lambda cfg: broken)
    monkeypatch.setattr(upload.knowledge, "Bucket", lambda cfg: bucket)
    monkeypatch.setattr(upload.knowledge, "Embedder", lambda cfg: lambda texts: [[1.0, 0.0] for _ in texts])
    path = tmp_path / "parking.md"
    path.write_text("Park in Lot C.")
    monkeypatch.setattr(sys, "argv", ["upload.py", str(path)])

    assert upload.main() == 0
    out = capsys.readouterr().out
    bucket.upload.assert_called_once_with(path, "parking.md")
    assert "indexed 1 chunk(s)" in out
    assert "These vectors were not kept. PostgreSQL at db.example.com:15268 failed" in out
    assert memory.ALLOW_LIST_HINT in out
    assert "No database" not in out
