# Changelog

Notable changes to this kit, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-10-02

Phase 1: foundation and the brain.

### Added

- `agent/`: a terminal agent with a hand-written tool loop on the plain `openai` SDK. `python -m agent` chats; `python -m agent --once "..."` answers one message for scripts and tests. It streams the answer, caps each message at 5 model calls, and prints one status line per role at startup.
- `agent/tools.py` with the first tool, `current_time`.
- `agent/memory.py` with the in-process fallback, so a terminal conversation has history until the process exits.
- `docs/00_prework.md`: account with the $300 credit link, token scopes, `linode-cli` setup, SSH key, `.env`, and a night-before checklist.
- `docs/links.md`: every page the kit relies on, each with one line on when you need it.
- `docs/costs.md`: hourly and monthly prices of every resource the kit creates, read with `linode-cli` on 2026-10-02.
- `scripts/check_links.sh`: checks every external and relative link in the Markdown files.
- `tests/test_brain.py`: the tool loop, parallel tool calls, the step cap, history, and config, with the OpenAI client mocked.
- `pyproject.toml`, so `python -m agent` works from any folder after `pip install -r requirements.txt`.

### Changed

- `README.md` now opens with the $300 credit link, the stack picture, and the three ways to use the kit. The notebook guide moved to the "Brain: the inference notebooks" section.
- `requirements.txt` adds the agent packages (`fastapi`, `uvicorn`, `boto3`, `psycopg[binary]`, `pgvector`, `redis`, `tzdata`), `linode-cli`, and `pytest`.
- `.env.example` documents every setting the agent reads.
