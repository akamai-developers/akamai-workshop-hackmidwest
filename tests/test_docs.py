"""Check workshop navigation, notebook syntax, and the documented tool recipe."""
import ast
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parent.parent


def markdown_sources():
    for path in sorted(ROOT.rglob("*.md")):
        if not any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            yield path, path.read_text()
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        notebook = json.loads(path.read_text())
        yield path, "\n".join("".join(cell["source"]) for cell in notebook["cells"]
                              if cell["cell_type"] == "markdown")


def heading_ids(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    counts, result = {}, set()
    for title in re.findall(r"^#+ (.+)$", text, flags=re.M):
        slug = re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


@pytest.mark.parametrize("path,text", list(markdown_sources()),
                         ids=lambda value: str(value.relative_to(ROOT)) if isinstance(value, Path) else None)
def test_internal_links(path, text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for link in re.findall(r"\]\(([^)]+)\)", text):
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            continue
        target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        assert target.exists(), f"{path.relative_to(ROOT)} -> {link}"
        if parsed.fragment and target.suffix == ".md":
            assert unquote(parsed.fragment) in heading_ids(target.read_text()), f"Missing heading: {link}"


@pytest.mark.parametrize("path", sorted((ROOT / "notebooks").glob("*.ipynb")), ids=lambda p: p.name)
def test_notebook_code_and_clean_outputs(path):
    notebook = json.loads(path.read_text())
    assert notebook["nbformat"] == 4
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        source = "\n".join(line for line in source.splitlines() if not line.startswith("%pip "))
        ast.parse(source, filename=f"{path.name}:cell-{index}")
        assert cell["execution_count"] is None
        assert cell["outputs"] == []


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

