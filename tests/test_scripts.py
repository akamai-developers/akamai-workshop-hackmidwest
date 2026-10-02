"""The bash scripts: a syntax check for each, and the .env helpers in scripts/lib.sh run for real."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = sorted((ROOT / "scripts").glob("*.sh"))


@pytest.mark.parametrize("script", SCRIPTS, ids=[s.name for s in SCRIPTS])
def test_every_script_parses(script):
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def scratch_repo(tmp_path: Path, env_text: str | None) -> Path:
    """A copy of the repository layout lib.sh expects: scripts/lib.sh, a stub linode-cli, and .env."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "lib.sh", tmp_path / "scripts" / "lib.sh")
    fake_cli = tmp_path / ".venv" / "bin" / "linode-cli"  # lib.sh refuses to run without linode-cli
    fake_cli.parent.mkdir(parents=True)
    fake_cli.write_text("#!/bin/sh\nexit 0\n")
    fake_cli.chmod(0o755)
    if env_text is not None:
        (tmp_path / ".env").write_text(env_text)
    return tmp_path


def run_with_lib(tmp_path: Path, env_text: str | None, commands: str) -> subprocess.CompletedProcess:
    """Run commands after sourcing lib.sh, the way every script starts."""
    scratch_repo(tmp_path, env_text)
    script = f"set -euo pipefail\nsource scripts/lib.sh\n{commands}\necho done"
    return subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True,
                          env={**os.environ, "HOME": str(tmp_path)})


def test_get_env_of_a_missing_key_is_empty_and_does_not_stop_the_script(tmp_path):
    result = run_with_lib(tmp_path, "OPENAI_API_KEY=hk_x\n", 'value=$(get_env OBJ_KEY_ID)\necho "[$value]"')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["[]", "done"]


def test_get_env_strips_quotes(tmp_path):
    result = run_with_lib(tmp_path, "OBJ_BUCKET='hackmidwest-abc'\nDATABASE_URL=\"postgresql://x\"\n",
                          "get_env OBJ_BUCKET\nget_env DATABASE_URL")
    assert result.stdout.splitlines()[:2] == ["hackmidwest-abc", "postgresql://x"]


def test_set_env_replaces_in_place_adds_new_keys_and_never_duplicates(tmp_path):
    env_text = "OPENAI_API_KEY=hk_x\nOBJ_BUCKET=\n# OBJ_BUCKET=a comment stays a comment\nDATABASE_URL=\n"
    result = run_with_lib(tmp_path, env_text, "\n".join([
        "set_env OBJ_BUCKET hackmidwest-one",
        "set_env OBJ_BUCKET hackmidwest-two",
        "set_env DATABASE_URL 'postgresql://akmadmin:p%24ss@host:15268/defaultdb?sslmode=require'",
        "set_env NEW_KEY 'a&b\\c$d=e/f'",
    ]))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".env").read_text().splitlines() == [
        "OPENAI_API_KEY=hk_x",
        "OBJ_BUCKET=hackmidwest-two",
        "# OBJ_BUCKET=a comment stays a comment",
        "DATABASE_URL=postgresql://akmadmin:p%24ss@host:15268/defaultdb?sslmode=require",
        "NEW_KEY=a&b\\c$d=e/f",
    ]


def test_scripts_stop_without_env_file(tmp_path):
    result = run_with_lib(tmp_path, None, "echo should-not-print")
    assert result.returncode != 0
    assert "cp .env.example .env" in result.stdout
    assert "should-not-print" not in result.stdout
