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


def test_the_add_a_tool_recipe_works_as_written():
    """agent/README.md's example, pasted where the README says, gives the model a tool it can call."""
    section = (ROOT / "agent/README.md").read_text().split("\n## Add a tool\n")[1].split("\n## ")[0]
    definition, dispatch = re.findall(r"```python\n(.*?)```", section, re.S)
    source = (ROOT / "agent/tools.py").read_text()
    end_of_current_time = '    return now.strftime("%A, %B %d, %Y, %I:%M %p %Z")\n'  # "below the current_time() function"
    current_time_lines = '            if name == "current_time":\n                return current_time(**args)\n'
    assert end_of_current_time in source and current_time_lines in source
    source = source.replace(end_of_current_time, f"{end_of_current_time}\n\n{definition}", 1)
    source = source.replace(current_time_lines, current_time_lines + dispatch, 1)
    namespace = {}
    exec(compile(source, "agent/tools.py with the recipe", "exec"), namespace)
    tools = namespace["Tools"]()
    assert "find_table" in [schema["function"]["name"] for schema in tools.schemas()]
    assert tools.run("find_table", '{"team": "Byte Club"}', "s1") == "Table 12"
