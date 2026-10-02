# Changelog

Notable changes to this kit, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.1] - 2026-10-02

Checks for students on a Mac, where commands are pasted into zsh and the scripts run with bash 3.2 and BSD tools.

### Added

- `tests/fake_cloud.py`, a fake Akamai account that stands in for `linode-cli`, `curl`, `ssh`, `scp`, `kubectl`, and `sleep`. `tests/test_scripts.py` runs `up.sh` twice, `status.sh`, `deploy_linode.sh`, `deploy_lke.sh`, and `down.sh` against it, in the order a team would. The tests check the plans, regions, and allow lists each script asks for, the `.env` it writes, the code archive the LKE pod unpacks, and that `down.sh` deletes the kit's seven resources and none of the account's other ones. Bash, Python, `tar`, `sed`, and `awk` are the real ones on your PATH, so on a Mac the tests run what a student's laptop runs.

### Changed

- Guide 04 and `scripts/deploy_lke.sh` pack the code with `tar --no-xattrs`. A Mac's `tar` stores file attributes, such as the quarantine flag on downloaded files, in the archive, and the pod's GNU `tar` printed one warning per attribute at the top of the agent's log.

### Verified

- Every one of the 84 bash blocks in the README and the guides, pasted in order into zsh 5.9 (`zsh -f -i`), gives the same commands, arguments, and output as bash 5.2. Commands that reach the network ran against stand-ins that record their arguments. Planted zsh traps (an unquoted `?` or `[ ]`, a variable that bash splits, an end-of-line `#` comment, `==` in `[ ]`) all showed up as differences.
- The 26 script tests pass with bash 3.2.57, the version macOS ships, and with `bsdtar` as `tar`.
- An archive made by `bsdtar` from files with attributes unpacks with GNU `tar` 1.35 in `python:3.12-slim`, the pod's image: exit code 0 either way, 32 warnings without `--no-xattrs`, none with it.
- 79 tests pass.

## [0.6.0] - 2026-10-02

Phase 6: polish and verification.

### Changed

- The README's first screen is the credit link, the stack picture, and the three paths. Its introduction moved under "Three ways to use this kit".
- The header of `scripts/down.sh` says how it finds the cluster's NodeBalancer.
- After a teachability review, guide 04's clean up works in a new terminal: it sets `KUBECONFIG` before deleting the Service, ends by checking that no `hackmidwest-nb` is left, and gives the allow-list commands. Step 4 waits for the database to be `active` again, and step 7 says how to restart the agent when memory comes up as `error`, because the agent connects once, when it starts.
- Guide 04 step 3 creates its objects with `--save-config`, so the `kubectl apply` updates in step 8 and in `scripts/deploy_lke.sh` do not warn. It warns that `--from-env-file` keeps quotes in values, which the laptop agent strips. Step 8 shows how to update the Secret, and the overview draws the LKE body.
- `k8s/service.yaml` gives the cluster's NodeBalancer name as LKE makes it: `lke`, the cluster id, and 12 more characters.
- Guides 01 and 02 say the model words its answers differently each time. Guide 03's allow-list clean up looks up its own variables.
- The arrows in the stack picture line up.

### Verified

- 65 tests pass, and `scripts/check_links.sh` passes. It skips four links: three pages on www.akamai.com and www.linode.com, which block scripts, and this repository while it is private.
- `notebooks/00_quickstart.ipynb` runs against the live endpoint: 9 code cells, no errors. The notebooks in the repository are unchanged.
- Every guide opens with the stack picture and names its role, and has an Overview, Learning objectives, Prerequisites with minutes, numbered steps, Validation, a Show the judges line, Clean up, and Next steps.
- No em-dashes and none of the banned words in the Markdown, Python, shell, or YAML files.

## [0.5.0] - 2026-10-02

Phase 5: the optional LKE module, run live, and a full rehearsal of every guide on Akamai Cloud.

### Added

- `k8s/agent.yaml`, `k8s/valkey.yaml`, and `k8s/service.yaml`. The agent runs on the public `python:3.12-slim` image and unpacks its code from a ConfigMap, so no image registry is needed. The Service of type LoadBalancer makes the cluster create a NodeBalancer.
- `scripts/deploy_lke.sh`: a one-node LKE cluster, the kubeconfig, the Secret from `.env`, the code ConfigMap, the database allow list, the manifests, and a wait for `/health` through the NodeBalancer, which it renames `hackmidwest-nb`.
- `docs/04_lke.md`, with outputs from a live cluster.
- `tests/test_scripts.py`: every script parses, the `.env` helpers in `scripts/lib.sh` run for real, and `scripts/down.sh` succeeds when everything is already gone.
- `tests/test_docs.py`: every line of code a guide quotes must still exist in the file it quotes.

### Changed

From the rehearsal, which pasted every block of guides 00 to 05 into a terminal against a fresh clone:

- The LKE cluster now creates its own NodeBalancer, and guide 04 step 6 renames it `hackmidwest-nb`. The first design made the NodeBalancer by hand and handed it to the Service with the `linode-loadbalancer-nodebalancer-id` annotation, but the cluster's controller runs as a restricted LKE service account that cannot see NodeBalancers you make, so the Service failed with `[403] Unauthorized`. Guide 04's clean up deletes the Service first, which makes the cluster delete the NodeBalancer.
- The agent and `scripts/db_init.py` connect to PostgreSQL over IPv4. On a network with IPv6, each connection tried IPv6 first, was dropped by the IPv4 allow list, and waited out the 10-second connect timeout. An agent start went from 13 seconds to under 3.
- `scripts/down.sh` recognizes "No bucket named" from `linode-cli obj ls`. Before, a second run, or a run after the guides' clean up, stopped with "run this script again" every time. It also finds the cluster's NodeBalancer through the agent Service when step 6 was skipped.
- `scripts/db_init.py` says to wait for DNS when a new database's host name does not resolve yet, instead of pointing at the allow list.
- The guides show what the CLI really prints: the `Using default values: {}` line before create commands, the obj plugin's daily key clean-up notice, narrow `--format` columns that fit an 80-column terminal, SSH timing out before a new Linode boots, Docker's long build log, the 503 before a cluster's kubeconfig is ready, and the NodeBalancer's 45-second warm-up.
- No comments inside command blocks. On macOS, zsh does not treat `#` as a comment at the prompt, so a pasted inline comment broke `linode-cli obj rb` and the README quick start.
- Ids come from lookups by label, such as `linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id`, so commands work in a new terminal and nobody pastes an example id. No `<placeholder>` remains inside a command.
- The pre-work gets the agent answering at step 3, and covers Python 3.9 on macOS and the missing `python3-venv` on Ubuntu and WSL.
- Guide 02 shows forgetting with the same session in a new process, so the process is the only thing that changes. Guide 03 drops the restart step, which repeated guide 02's lesson, and adds the agent's log command and the allow-list clean-up.
- The README gains "What this kit is not", the measured times, and moves the scripts below the guides. `agent/README.md` gains PDF support and the first changes to make before real data.
- `scripts/check_links.sh` also checks that every `#anchor` matches a heading.

### Verified on Akamai Cloud

- The full guided path, from `git clone` to the agent answering on its Linode, took about 15 minutes of commands and waiting. The database was active 4 minutes 44 seconds after it was created and in DNS at 7 minutes 29 seconds.
- LKE 1.36: the kubeconfig was ready 2 minutes 17 seconds after the create command, with the node already Ready. The agent pod was ready 27 seconds after `kubectl apply`, and the NodeBalancer answered 45 seconds after it. All four roles were live through the NodeBalancer.
- The 30-minute path's three scripts took 3 minutes 40 seconds, with memory on its fallback as designed.
- The guides' clean up commands and `scripts/down.sh` removed everything; exact-label and id lookups found nothing left.

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
