# Changelog

## Unreleased

- Replace the long entry page with a short setup and navigation guide.
- Add a 30-minute teaching path, a 60-minute extension, and an instructor guide.
- Organize independent cloud labs and link each inference notebook to project integrations.
- Correct setup paths, clarify deployment assumptions, and remove unsupported guarantees from current instructions.
- Make notebook configuration explicit, hide key values, validate tool arguments, and handle incomplete structured responses.

Earlier entries below describe historical versions and their authors' reported checks. Use the current guides for commands and the verification note for this revision.

Notable changes to this kit, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.7] - 2026-10-02

Turning the sample agent into your own project.

### Added

- `agent/README.md` has a "Make it yours" section for after guide 03: take the three samples out of the bucket with `linode-cli obj rm` and upload your documents, rewrite the two strings that tell the model what the agent is for, drop or add tools, and ship each change to the Linode, then check it on the chat page. The README, guide 01, step 7, and guide 03's Next steps link to it.

### Fixed

- The "Add a tool" example in `agent/README.md` works as pasted. It left out a third edit, a list in `Tools.schemas()`, so the model never saw the new tool: asked "Where does Byte Club sit?", it searched the documents and said it did not know, 3 times out of 3. `Tools.schemas()` now offers every tool in `SCHEMAS`, so the two blocks in the README are enough, and the text says where to paste each one. A new test pastes them into `agent/tools.py` and calls the tool.
- One file the agent cannot read, such as a broken PDF, no longer stops it from searching all the others. Before, the agent's `knowledge` line said `error` without naming the file, every `search_docs` call failed, and `scripts/upload.py` stopped with a traceback. Now the agent answers from the other files, names the unreadable one and the reason on its `knowledge` line, and tries it again at each search, so installing a missing package fixes it. It also drops the old chunks of a file that stopped being readable. `upload.py` prints the reason, says to fix the cause or take the file out of the bucket with `linode-cli obj rm`, then goes on with the next file and exits with 1.
- The PDF recipe in `agent/README.md` says to run `pip install -r requirements.txt` again after adding `pypdf`, to replace `Bucket.read()` rather than add a second one, and to ship the change to the Linode. It shows the message for a missing `pypdf` with its fix, and explains copy-protected PDFs, which need the `cryptography` package. `cryptography` has had no ready-made build for Intel Macs since version 49, so the recipe leaves it optional.
- The agent no longer stops at startup when the bucket fails with an error that has no message.
- `scripts/upload.py` says `Skipped <path>: no such file.` for a path that does not exist, and goes on with the next file. Before, a mistyped name ended in a traceback.

### Verified

- With a bike shop's documents in place of the samples and the event wording unchanged, the agent skipped the search for 5 of 12 questions. It turned down "Do you fix flat tires, and what does it cost?" 3 times out of 3, for example with "I'm the starter agent for your HackMidwest team, so I can't fix flat tires." With the two strings rewritten as "Make it yours" shows, it searched and answered from the right file 12 times out of 12.
- The PDF recipe, applied from the README's text, against a local S3 bucket: without the second `pip install`, a copy-protected PDF, and a broken PDF, each file was skipped with its reason while the agent answered from the others. With `pypdf` installed, it answered from a PDF printed by Chrome; with `cryptography` too, from the copy-protected copy.
- With PostgreSQL memory (local pgvector 0.8.7), a file removed from the bucket lost its rows in the documents table at the agent's next start.
- The "Make it yours" commands, pasted as written against a real bucket in Seattle: `linode-cli obj rm` printed `parking.md removed from <bucket>` for each sample, and the agent then answered from the team's own files and no longer knew about parking. The bucket and its access key were deleted afterwards.

## [0.6.6] - 2026-10-02

What a laptop sees when its address is not on the database's allow list, and how to fix it.

### Added

- Guide 02, step 5, has a section for when your address changes. The allow list holds the address your laptop had in guide 01. At home, in a hotel, or on a phone hotspot, the laptop has a different public address, and the database ignores it. The section shows the message, the three lookups, and the update with and without the Linode from guide 03, and what the first one prints when there is no Linode. Guide 01's allow-list note points to it.
- Guide 04, step 4, says that Akamai adds the IPv4 and IPv6 addresses of all LKE nodes in an account to every database's allow list, every 10 minutes. That is why the node's IPv6 address shows up in the list without anyone typing it. The step's update by hand still lets the agent in at once.

### Changed

- When the connection to the database times out, the agent's `memory` line and `scripts/db_init.py` say that the database ignores addresses that are not on its allow list, and point to guide 02, step 5. Before, the agent said only `connection timeout expired`, `db_init.py` said to check the allow list, and nothing in the kit said how to add a new address. Other connection errors print as before.
- `scripts/upload.py` says why the vectors were not kept when `DATABASE_URL` is set but the database did not answer. Before, it said "No database".
- Guide 02's "Show the judges" line and `docs/links.md` put the allow list on the database's **Networking** tab, where Akamai's [Manage a database](https://techdocs.akamai.com/cloud-computing/docs/aiven-manage-database) page puts it, instead of under Settings.

### Verified

- On a new Managed PostgreSQL database in Seattle (`g6-nanode-1`, PostgreSQL 17.11, pgvector 0.8.6): active 4 minutes 37 seconds after it was created, and in DNS at 7 minutes 7 seconds. After an update took this machine off the allow list, every new connection waited 10 seconds and failed with `connection timeout expired`, starting within 10 seconds of the update. The agent printed the new advice on its `memory` line, and `db_init.py` printed exactly the two lines guide 02 now shows. Guide 02's three lookups and its update without a Linode let the machine back in: a new connection worked about 5 seconds after the update, while the status still said `updating`. The status read `active` 38 seconds after the update. The update for a Linode, run with an empty `LINODE_IP`, stopped with `Request failed: 400` and `Invalid IPv4 or IPv6 address(es): /32` and changed nothing. A connection that was already open when its address left the list did not fail: its next query waited 4 minutes 11 seconds and finished once the address was back. Guide 02's Clean up deleted the database, and the API then answered 404 for it.
- Every bash block of the README and the guides, pasted into bash and into zsh, with GNU tools and with FreeBSD's: 87 blocks and 145 commands, with the same arguments in all four runs.

## [0.6.5] - 2026-10-02

Windows line endings.

### Fixed

- A clone made on Windows runs the scripts. Git for Windows, which VS Code on Windows also uses, checks files out with CRLF line endings by default, and bash then stopped on every script with `set: pipefail: invalid option name`. A new `.gitattributes` makes git check out every file with LF, whatever `core.autocrlf` says.
- The scripts read a `.env` saved with Windows line endings, for example a new file in Notepad holding a teammate's settings. Before, `get_env` in `scripts/lib.sh` kept the CR at the end of each value, so `scripts/up.sh` and `scripts/down.sh` handed `linode-cli obj` a bucket name ending in CR. It stopped with a Python traceback that ends in `Invalid bucket name`, and `down.sh` asked to be run again, which failed the same way. The agent itself was never affected, because python-dotenv drops the CR.

### Verified

- A clone made with `core.autocrlf=true`, the Git for Windows default, checked out all 59 files with CRLF, and 26 of the 80 tests failed. With `.gitattributes`, the same kind of clone checked out all 60 files with LF, and the 82 tests passed. Two new tests fail when either fix is taken out. `tests/test_scripts.py` also passed with FreeBSD's `tr` and with bash 3.2.57.

## [0.6.4] - 2026-10-02

What a brand-new account can run into, and a check of the kit with FreeBSD's command line tools.

### Changed

- The pre-work says sign-up texts a code to your phone, and that Akamai holds a small number of new accounts for a manual review first. Until it ends, creating anything fails with `Your account must be activated before you can use this endpoint`, and Akamai's advice is to check your email. Guide 01 step 1, the first command that creates something, names the same message and says to pair with a teammate until the account clears. Both facts come from Akamai's [Get started](https://techdocs.akamai.com/cloud-computing/docs/getting-started) and [Troubleshooting Cloud Manager errors](https://techdocs.akamai.com/cloud-computing/docs/troubleshooting-cloud-manager-errors) pages, which `docs/links.md` now lists.

### Verified

- The scripts and the guides with the command line tools a Mac is closest to. In a Chimera Linux container, `sed`, `grep`, `awk`, `date`, `mktemp`, `base64`, `wc`, `cut`, `tr`, `head`, `sort`, `uniq`, and `seq` come from FreeBSD 15 (the `chimerautils` 15.0.2 package). `grep -V` prints `2.6.0-FreeBSD`, the same as macOS. `awk` is the BWK awk that macOS also ships, and `tar` is bsdtar 3.8.8. There, the 26 tests in `tests/test_scripts.py`, which run every script against a fake account, passed with bash 5.3 and again with bash 3.2.57, the version macOS ships. A planted GNU-only `sed -i` in `scripts/lib.sh` failed 12 of them and passed with GNU sed, so the tests notice the difference.
- Every bash block of the README and the guides, pasted into bash and into zsh with only the network and cloud commands replaced by stubs, sent the stubs the same arguments with FreeBSD's tools as with GNU's: 84 blocks, 140 commands. The only output that differs is the padding of `uniq -c` in guide 05 step 3, where a Mac prints `  20 200` instead of `     20 200`. `scripts/check_links.sh` printed the same 106 lines with both.

## [0.6.3] - 2026-10-02

Checks for the Python a student brings, from 3.10 to 3.15.

### Changed

- The pre-work asks for Python 3.10 to 3.14 instead of "3.10 or newer", and says what happens on 3.15: `pip install` compiles `pydantic-core`, which takes a few more minutes and a C compiler, and fails without one.
- The README's quick start makes `.env` only when there is none: `[ -f .env ] || cp .env.example .env`. Before, pasting the block a second time replaced `.env` with the example and lost the bucket's secret key, which Akamai shows only once, and the `OBJ_KEY_ID` that `scripts/down.sh` needs to revoke the key. The README also says that a new terminal only needs `source .venv/bin/activate`.

### Verified

- In clean `python:3.X-slim` containers with no compiler, `pip install -r requirements.txt` installed from ready-made wheels on Python 3.10.22, 3.11.17, 3.12.14, 3.13.16, and 3.14.8, in 23 to 37 seconds. On each one, the 80 tests passed and `python -m agent --once "Say hello"` answered from the live endpoint. 3.13 and 3.14 get the same 133 packages as 3.12. On older versions pip picks some older releases: numpy 2.4.6 on 3.11, and numpy 2.2.6 and IPython 8.39.0 on 3.10.
- For the same versions, every package with compiled code has a wheel for Linux x86_64 and for Macs with Apple silicon. On Intel Macs, `argon2-cffi-bindings` 26.1.0, which Jupyter needs, has no wheel, so pip builds it. That build took 6 seconds with only a C compiler.
- On Python 3.15.0rc2 with no compiler, `pip install` failed after 38 seconds on `pydantic-core` 2.46.5, which has no 3.15 wheel. With a C compiler, pip fetched Rust by itself and the install finished in 110 seconds. Then the 80 tests passed and the agent answered. `MarkupSafe` 3.0.3 and `PyYAML` 6.0.3 also had no 3.15 wheels. An upper bound on `requires-python` would stop pip in 3 seconds with a one-line message, but it would also block 3.15 laptops that install fine, so the kit does not add one.

## [0.6.2] - 2026-10-02

Fixes from a fresh review of the agent code.

### Fixed

- The agent keeps answering when Valkey stops while it runs, for example after `docker compose stop valkey` or when the Valkey pod restarts on LKE. Before, every message raised `redis.exceptions.ConnectionError`: `POST /chat` returned a plain-text HTTP 500, and the terminal chat exited with a traceback. Now `get_vector()` counts as a cache miss, `set_vector()` does nothing, and `allow()` lets the message through, the same as running without `VALKEY_URL`. Guide 05 step 4 quotes the new code.
- The chat page shows `Error 500: Internal Server Error` when the server crashes, instead of "Could not reach the agent" and a JSON parse error. A message over 4,000 characters shows `Error 422: String should have at most 4000 characters` instead of `[object Object]`.

### Verified

- With Valkey stopped, the agent's Docker image answered `POST /chat` with HTTP 200, and "Where can I park?" still called `search_docs` and quoted `parking.md` in 4.4 seconds. Before the fix, `Brain.chat()` raised `ConnectionError` at once after a local Valkey container stopped. `tests/test_server.py` has a test that fails on the old code.
- The chat page, opened in a browser through Playwright against the real FastAPI app with a fake brain, showed the reply, the 500, and the 422 messages above.
- `recall` finds notes when the documents table is large. With 3 notes and 30 to 30,000 document chunks in PostgreSQL 17.11 with pgvector 0.8.7, the planner scanned the table for notes every time and returned all 3. The `search_docs` query used the HNSW index and returned 3 chunks every time, because its filter removes only the few notes.
- 80 tests pass.

## [0.6.1] - 2026-10-02

Checks for students on a Mac, where commands are pasted into zsh and the scripts run with bash 3.2 and BSD tools.

### Added

- `tests/fake_cloud.py`, a fake Akamai account that stands in for `linode-cli`, `curl`, `ssh`, `scp`, `kubectl`, and `sleep`. `tests/test_scripts.py` runs `up.sh` twice, `status.sh`, `deploy_linode.sh`, `deploy_lke.sh`, and `down.sh` against it, in the order a team would. The tests check the plans, regions, and allow lists each script asks for, the `.env` it writes, the code archive the LKE pod unpacks, and that `down.sh` deletes the kit's seven resources and none of the account's other ones. Bash, Python, `tar`, `sed`, and `awk` are the real ones on your PATH, so on a Mac the tests run what a student's laptop runs.

### Changed

- Guide 04 and `scripts/deploy_lke.sh` pack the code with `tar --no-xattrs`. A Mac's `tar` stores file attributes, such as the quarantine flag on downloaded files, in the archive, and the pod's GNU `tar` printed one warning per attribute at the top of the agent's log.
- Guide 04 step 2 says what `kubectl get nodes` shows while the node joins the cluster: `No resources found`, then the node as `NotReady` for about 20 seconds. Step 7 adds `Empty reply from server` to the signs that the NodeBalancer is still starting.

### Verified

- Every one of the 84 bash blocks in the README and the guides, pasted in order into zsh 5.9 (`zsh -f -i`), gives the same commands, arguments, and output as bash 5.2. Commands that reach the network ran against stand-ins that record their arguments. Planted zsh traps (an unquoted `?` or `[ ]`, a variable that bash splits, an end-of-line `#` comment, `==` in `[ ]`) all showed up as differences.
- The 26 script tests pass with bash 3.2.57, the version macOS ships, and with `bsdtar` as `tar`.
- An archive made by `bsdtar` from files with attributes unpacks with GNU `tar` 1.35 in `python:3.12-slim`, the pod's image: exit code 0 either way, 32 warnings without `--no-xattrs`, none with it.
- Guide 04, run live from a clone of commit 59a6ba0 between 04:00 and 04:12 UTC, on a database and bucket made with `scripts/up.sh` and `scripts/status.sh`. Every block worked as written, including step 3 with `--save-config` and `--no-xattrs`, the wait for `active` in step 4, and both update commands in step 8, which applied without warnings. The pod's log had no `tar` lines. The Clean up ran in a new terminal with no variables set: deleting the Service removed the NodeBalancer, the last command printed the empty table the guide shows, and the node Linode was gone 34 seconds after `cluster-delete`. `scripts/down.sh` then deleted the database, the bucket, and its key, with the database still `updating` from the allow-list change.
- 79 tests pass.

## [0.6.0] - 2026-10-02

Phase 6: polish and verification.

### Changed

- The README's first screen is the credit link, the stack picture, and the three paths. Its introduction moved under "Three ways to use this kit".
- The header of `scripts/down.sh` says how it finds the cluster's NodeBalancer.
- After a teachability review, guide 04's clean up works in a new terminal: it sets `KUBECONFIG` before deleting the Service, ends by checking that no `hackmidwest-nb` is left, and gives the allow-list commands. Step 4 waits for the database to be `active` again, and step 7 says how to restart the agent when memory comes up as `error`, because the agent connects once, when it starts.
- Guide 04 step 3 creates its objects with `--save-config`, so the `kubectl apply` updates in step 8 and in `scripts/deploy_lke.sh` do not warn. It warns that `--from-env-file` keeps quotes in values, which the laptop agent strips. Step 8 shows how to update the Secret, and the overview draws the LKE deployment.
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

Phase 4: the application on a Linode.

### Added

- `agent/server.py`: FastAPI with the chat page at `/`, `POST /chat` (`{session_id, message}` to `{reply, tools_used}`), and `GET /health`, which lists every role and what it is connected to. Rate-limited sessions get 429; a failed model call gets 502.
- `agent/static/index.html`: a plain chat page, no framework. It shows the four roles from `/health` and keeps one session id per browser.
- `agent/cache.py`: Valkey as the cache, with an embedding cache (one day) and a limit of 20 messages a minute per session.
- `Dockerfile`, `compose.yaml` (the agent on port 8000 and Valkey with no published port), `.dockerignore`, and `deploy/cloud-init.yaml` (installs Docker on first boot, holds no secrets).
- `scripts/deploy_linode.sh`: Cloud Firewall, Linode, cloud-init, the database allow list, code and `.env` over SSH, `docker compose up`, and a wait for `/health`. Measured: 3 minutes 9 seconds from start to the first 200.
- `scripts/down.sh`: finds each `hackmidwest-*` resource by its exact name, asks, deletes, and empties `OBJ_*` and `DATABASE_URL` in `.env`. Measured: 13 seconds for five resources.
- `docs/03_body.md` and `docs/05_valkey.md`.
- `tests/test_server.py`: the routes with a fake brain, and the Valkey cache with a fake redis.

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

Phase 1: foundation and inference.

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

