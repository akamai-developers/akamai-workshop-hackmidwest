# Changelog

Notable changes to this kit, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

Phase 5, in progress: the optional LKE module. Not yet run on a live cluster.

### Added

- `k8s/agent.yaml`, `k8s/valkey.yaml`, and `k8s/service.yaml`. The agent runs on the public `python:3.12-slim` image and unpacks its code from a ConfigMap, so no image registry is needed. The Service uses a NodeBalancer created as `hackmidwest-nb` through the `linode-loadbalancer-nodebalancer-id` annotation, so it carries the kit's label.
- `scripts/deploy_lke.sh`: a one-node LKE cluster, the kubeconfig, the NodeBalancer, the Secret from `.env`, the code ConfigMap, the database allow list, and a wait for `/health` through the NodeBalancer.
- `docs/04_lke.md`, with each step that needs a live cluster marked unverified.
- `scripts/down.sh` also deletes `hackmidwest-nb` and the local kubeconfig.
- `tests/test_scripts.py`: every script parses, and the `.env` helpers in `scripts/lib.sh` run for real, including reading a missing key under `set -e`, the bug that stopped `scripts/up.sh` in the first live run.

### Changed

After a teachability review of the guides:

- No comments inside command blocks. On macOS, zsh does not treat `#` as a comment at the prompt, so a pasted inline comment broke `linode-cli obj rb` and the README quick start.
- Ids come from lookups by label, such as `linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id`, so commands work in a new terminal and nobody pastes an example id. No `<placeholder>` remains inside a command.
- The pre-work gets the agent answering at step 3, and covers Python 3.9 on macOS and the missing `python3-venv` on Ubuntu and WSL.
- Guide 02 shows forgetting with the same session in a new process, so the process is the only thing that changes.
- Guide 03 drops the restart step, which repeated guide 02's lesson, and adds the agent's log command and the allow-list clean-up. Guide 04 adds `--timeout=600s` to the rollout and `COPYFILE_DISABLE=1` to the tarball for macOS. Guide 05 sends the 21 requests in parallel, so they land in one minute: 20 answered, 1 refused, tested on 2026-10-02.
- The README gains "What this kit is not" and moves the scripts below the guides. `agent/README.md` gains PDF support and the first changes to make before real data.
- `scripts/check_links.sh` also checks that every `#anchor` matches a heading.

### Verified

- The manifests pass `kubeconform -strict` against the Kubernetes 1.33 schemas.
- The pod's startup command, run in Docker with the code tarball mounted at `/code`, answered `/health` 12 seconds after start. The tarball is 18.5 KB.

## [0.4.0] - 2026-10-02

Phase 4: the body on a Linode.

### Added

- `agent/server.py`: FastAPI with the chat page at `/`, `POST /chat` (`{session_id, message}` to `{reply, tools_used}`), and `GET /health`, which lists every role and what it is connected to. Rate-limited sessions get 429; a failed model call gets 502.
- `agent/static/index.html`: a plain chat page, no framework. It shows the four roles from `/health` and keeps one session id per browser.
- `agent/cache.py`: Valkey as the reflexes, with an embedding cache (one day) and a limit of 20 messages a minute per session.
- `Dockerfile`, `compose.yaml` (the agent on port 8000 and Valkey with no published port), `.dockerignore`, and `deploy/cloud-init.yaml` (installs Docker on first boot, holds no secrets).
- `scripts/deploy_linode.sh`: Cloud Firewall, Linode, cloud-init, the database allow list, code and `.env` over SSH, `docker compose up`, and a wait for `/health`. Measured: 3 minutes 9 seconds from start to the first 200.
- `scripts/down.sh`: finds each `hackmidwest-*` resource by its exact name, asks, deletes, and empties `OBJ_*` and `DATABASE_URL` in `.env`. Measured: 13 seconds for five resources.
- `docs/03_body.md` and `docs/05_valkey.md`.
- `tests/test_server.py`: the routes with a fake brain, and the Valkey reflexes with a fake redis.

### Verified on Akamai Cloud

- The deployed agent answered from the bucket, recalled a fact saved from a laptop, and kept its memory across `docker compose restart`.
- The firewall admitted ports 22 and 8000 and blocked 80, 5432, and 6379.
- 21 quick messages from one session got twenty 200 responses and one 429.

## [0.3.0] - 2026-10-02

Phase 3: memory in Managed PostgreSQL with pgvector.

### Added

- `agent/memory.py`: `PostgresMemory` for sessions, messages, document vectors, and notes, with pgvector cosine search in SQL, a reconnect after dropped connections, and TCP keepalives. Without `DATABASE_URL`, or when the database cannot be reached, the agent says why and uses `LocalMemory`.
- The `remember` and `recall` tools. Notes are rows in the documents table under `notes/`, shared by every conversation.
- `agent/sql/001_init.sql`, `scripts/db_init.py` (prints the PostgreSQL and pgvector versions), and the database half of `scripts/up.sh`.
- `scripts/status.sh`: waits for the database and for its host name in DNS, then writes `DATABASE_URL` with `sslmode=require`.
- `docs/02_memory.md` and `tests/test_memory.py`.

### Verified on Akamai Cloud

- `CREATE EXTENSION vector` works for `akmadmin` on Managed PostgreSQL 17.11: pgvector 0.8.6, with vectorscale 0.9.0 available.
- A `g6-nanode-1` database turned active 6 minutes 16 seconds after it was created. Its host name resolved about 2 minutes later.
- A fact saved in one process came back in another session in a new process. With `DATABASE_URL` removed, it was gone.

### Changed

- The system prompt asks for plain text, tells the model to check `recall` for questions about the team, and forbids describing documents that `search_docs` did not return. Temperature is 0.3. In testing, the model skipped `search_docs` and invented parking rules once in about 20 runs before this change and in none of 10 after.

## [0.2.0] - 2026-10-02

Phase 2: knowledge in Object Storage.

### Added

- `agent/knowledge.py`: lists the bucket with boto3, chunks text into about 500 words, embeds in requests of at most 16 inputs and about 5,000 words, and searches by cosine similarity. It indexes new and changed files on each search and forgets deleted ones. Without `OBJ_*` it reads `docs/sample/`.
- The `search_docs` tool, and three sample documents about a made-up venue in `docs/sample/`.
- `scripts/up.sh` (database, bucket, and a bucket-limited access key; `--no-db` skips the database), `scripts/upload.py`, and `scripts/lib.sh` for the shared settings.
- `docs/01_knowledge.md` and `tests/test_knowledge.py`.

### Verified on Akamai Cloud

- With an empty bucket the agent said it had no parking details. After `scripts/upload.py docs/sample/parking.md` it answered from `parking.md`.
- The access key was created limited to one bucket with `read_write`, and a repeat run of `scripts/up.sh` changed nothing.

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
