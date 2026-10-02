"""Settings for the agent, read from .env and the environment.

Only OPENAI_BASE_URL and OPENAI_API_KEY are required. Each other setting turns on
one Akamai service. When a setting is missing, that part of the agent uses a local
fallback and says so at startup.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DOCS = REPO_ROOT / "docs" / "sample"


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    chat_model: str = "hackathon-chat"
    embedding_model: str = "hackathon-embedding"
    obj_endpoint: str = ""
    obj_bucket: str = ""
    obj_access_key: str = ""
    obj_secret_key: str = ""
    database_url: str = ""
    valkey_url: str = ""

    @property
    def has_bucket(self) -> bool:
        return all([self.obj_endpoint, self.obj_bucket, self.obj_access_key, self.obj_secret_key])


def load(env_file: Path | None = REPO_ROOT / ".env") -> Config:
    """Read .env, then the environment. Values in .env win over your shell, like in the notebooks."""
    if env_file:
        load_dotenv(env_file, override=True)

    def get(name: str, default: str = "") -> str:
        return os.environ.get(name, "").strip() or default

    missing = [name for name in ("OPENAI_BASE_URL", "OPENAI_API_KEY") if not get(name)]
    if missing:
        raise SystemExit(
            f"Missing {' and '.join(missing)}. Copy .env.example to .env and paste your team key."
        )
    return Config(
        base_url=get("OPENAI_BASE_URL"),
        api_key=get("OPENAI_API_KEY"),
        chat_model=get("CHAT_MODEL", "hackathon-chat"),
        embedding_model=get("EMBEDDING_MODEL", "hackathon-embedding"),
        obj_endpoint=get("OBJ_ENDPOINT"),
        obj_bucket=get("OBJ_BUCKET"),
        obj_access_key=get("OBJ_ACCESS_KEY"),
        obj_secret_key=get("OBJ_SECRET_KEY"),
        database_url=get("DATABASE_URL"),
        valkey_url=get("VALKEY_URL"),
    )


def host_of(url: str) -> str:
    """The host and port of a URL, without the user name or password."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return f"{parsed.hostname}:{parsed.port}" if parsed.port else str(parsed.hostname)
