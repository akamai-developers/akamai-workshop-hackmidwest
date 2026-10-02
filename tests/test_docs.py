"""The guides quote real code. Every line of a quoted block must still exist in the file it comes from."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# guide -> code block language -> the files its blocks of that language quote
QUOTED = {
    "docs/01_knowledge.md": {"python": ["agent/knowledge.py"]},
    "docs/02_memory.md": {"python": ["agent/memory.py"], "sql": ["agent/sql/001_init.sql"]},
    "docs/03_body.md": {"python": ["agent/server.py"], "yaml": ["deploy/cloud-init.yaml", "compose.yaml"]},
    "docs/04_lke.md": {"yaml": ["k8s/agent.yaml"]},
    "docs/05_valkey.md": {"python": ["agent/cache.py"]},
}


def quoted_blocks():
    for guide, languages in QUOTED.items():
        text = (ROOT / guide).read_text()
        for number, (language, block) in enumerate(re.findall(r"```(\w+)\n(.*?)```", text, re.S), start=1):
            if language in languages:
                yield pytest.param(block, languages[language], id=f"{guide}-block{number}")


@pytest.mark.parametrize("block, sources", list(quoted_blocks()))
def test_quoted_code_matches_the_source(block, sources):
    lines = set()
    for source in sources:
        lines |= {line.strip() for line in (ROOT / source).read_text().splitlines()}
    missing = [line for line in block.splitlines() if line.strip() and line.strip() not in lines]
    assert not missing, f"these quoted lines are not in {', '.join(sources)}: {missing}"
