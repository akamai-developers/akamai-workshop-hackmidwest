"""Enable pgvector and create the agent's tables in your Managed PostgreSQL database.

    python scripts/db_init.py

Runs every file in agent/sql/ in name order, then prints the PostgreSQL and
pgvector versions it found. Safe to run again.
"""
import sys
from pathlib import Path

import psycopg

from agent import config

SQL_DIR = Path(__file__).resolve().parent.parent / "agent" / "sql"


def main() -> int:
    cfg = config.load()
    if not cfg.database_url:
        print("DATABASE_URL is empty in .env. When the database is active, run: bash scripts/status.sh")
        return 1
    try:
        conn = psycopg.connect(cfg.database_url, autocommit=True, connect_timeout=10)
    except psycopg.OperationalError as error:
        print(f"Could not connect to {config.host_of(cfg.database_url)}: {str(error).strip()}")
        print("Check that the database is active and that your current IP address is on its allow list.")
        return 1
    with conn:
        for path in sorted(SQL_DIR.glob("*.sql")):
            conn.execute(path.read_text())
            print(f"ran agent/sql/{path.name}")
        server = conn.execute("SHOW server_version").fetchone()[0]
        pgvector = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()[0]
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename").fetchall()
    print(f"PostgreSQL {server}")
    print(f"pgvector {pgvector}")
    print(f"tables: {', '.join(name for (name,) in tables)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
