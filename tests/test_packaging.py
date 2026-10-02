"""The Docker image installs agent/requirements.txt and laptops install requirements.txt. They must agree."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def packages(path: Path) -> set[str]:
    lines = (line.split("#")[0].strip() for line in path.read_text().splitlines())
    return {line for line in lines if line and not line.startswith("-")}


def test_every_agent_package_is_in_the_root_requirements():
    missing = packages(ROOT / "agent" / "requirements.txt") - packages(ROOT / "requirements.txt")
    assert not missing, f"add these to requirements.txt: {sorted(missing)}"
