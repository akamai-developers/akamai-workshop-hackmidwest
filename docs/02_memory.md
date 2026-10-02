# Guide 02: Memory in Managed PostgreSQL

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)   --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

This guide adds **memory**: the Managed PostgreSQL database you started in guide 01, with the pgvector extension that stores and searches vectors.

## Overview

The model keeps nothing between requests. The agent's memory has lived in a Python list so far, which is gone the moment the process exits. You will see that first. Then you connect the agent to Managed PostgreSQL, enable pgvector, and watch a fact saved in one conversation come back in another, after a restart.

Three things move into the database: the messages of each conversation, the vectors of your documents, and the notes the agent saves with its `remember` tool. A Managed Database means Akamai runs the server, the backups, and the updates. You get a host name, a port, a user, and a password.

On 2026-10-02 two test databases turned active 5 and 6 minutes after they were created, and their host names answered in DNS 2 to 3 minutes after that. Akamai's documentation says to allow 10 to 15 minutes.

## Learning objectives

By the end of this guide you will be able to:

- Show why memory inside the agent process is not enough
- Read a database's host, port, and credentials with `linode-cli`
- Write a PostgreSQL connection string that requires TLS
- Enable pgvector and create the agent's tables
- Show a conversation and a saved fact surviving a restart
- Find the code in `agent/memory.py` that you would change for your project

## Prerequisites

- [Guide 01](01_knowledge.md) done, with the database from its step 1
- About 10 minutes

## Step 1: Watch the agent forget

The agent has a `remember` tool. Ask it to keep a fact, then ask for that fact from a new process:

```bash
python -m agent --once "Remember that our demo slot is 2:15 PM."
```

```
brain      live      hackathon-chat at https://ws.akamai-workshops.com/v1
knowledge  live      bucket hackmidwest-e02dabda at us-sea-1.linodeobjects.com
memory     fallback  kept in this process only, forgotten on restart. Set DATABASE_URL in .env.
reflexes   off       no cache and no rate limit. Set VALKEY_URL to turn them on.
  [tool] remember({"fact": "The team's demo slot is 2:15 PM."})
Got it, your demo slot is 2:15 PM.
```

```bash
python -m agent --once "When is our demo slot?"
```

The same four status lines print first. They are left out of the outputs below.

```
  [tool] recall({"query": "demo slot time"})
  [tool] search_docs({"query": "demo slot schedule times"})
I don't have a specific demo slot saved for your team. The schedule in schedule.md says judging runs Sunday from 1:00 PM to 3:30 PM, and teams demo at their tables in the order shown on the screen. Each team gets three minutes to demo plus two minutes for questions, per rules.md. Check the screen on Sunday for your exact slot.
```

Your wording will differ. What matters is that `recall` finds nothing, so the agent falls back to the documents in your bucket. Same conversation, new process. The first process saved the fact in a Python list, and the list ended with the process. The second process started with nothing.

## Step 2: Check that the database is ready

```bash
linode-cli databases postgresql-list --label hackmidwest-db --format id,label,status
```

The status must be `active`. While it says `provisioning`, wait a minute and ask again. Then put its id in a variable, the same lookup as in guide 01, and read where the database lives:

```bash
DB_ID=$(linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id)
linode-cli databases postgresql-view $DB_ID --format status,hosts.primary,port
```

```
┌────────┬──────────────────────────────────────────────────────┬───────┐
│ status │ hosts.primary                                        │ port  │
├────────┼──────────────────────────────────────────────────────┼───────┤
│ active │ a123456-akamai-prod-1234567-default.g2a.akamaidb.net │ 15268 │
└────────┴──────────────────────────────────────────────────────┴───────┘
```

`hosts.primary` is the server's host name and `port` is its port. Managed Databases do not use PostgreSQL's usual port 5432.

## Step 3: Read the password

```bash
linode-cli databases postgresql-creds-view $DB_ID
```

```
┌──────────┬──────────────────────────┐
│ username │ password                 │
├──────────┼──────────────────────────┤
│ akmadmin │ <password>               │
└──────────┴──────────────────────────┘
```

`akmadmin` is the administrator account Akamai creates for you. The password on 2026-10-02 was 24 letters, digits, and underscores.

## Step 4: Write DATABASE_URL

A PostgreSQL connection string puts all of it in one line. Add it to `.env` with your password, host, and port, for example with `nano .env`:

```ini
DATABASE_URL=postgresql://akmadmin:<password>@a123456-akamai-prod-1234567-default.g2a.akamaidb.net:15268/defaultdb?sslmode=require
```

`defaultdb` is the database Akamai creates on the server. `sslmode=require` makes the connection use TLS, and the server refuses connections without it.

> NOTE: If the host name does not resolve yet, wait two minutes. A brand-new database can be `active` before its name is in DNS. If your password ever contains characters other than letters, digits, `-`, and `_`, percent-encode them or use `scripts/status.sh`, which does it for you.

## Step 5: Enable pgvector and create the tables

```bash
python scripts/db_init.py
```

```
ran agent/sql/001_init.sql
PostgreSQL 17.11
pgvector 0.8.6
tables: documents, messages, sessions
```

If it says the host name is not in DNS yet, wait two minutes and run it again.

The script runs every file in `agent/sql/`. The first line of `001_init.sql` turns pgvector on, and the documents table uses its `vector` type:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documents (id BIGSERIAL PRIMARY KEY, object_key TEXT NOT NULL, chunk_index INT NOT NULL,
                                      content TEXT NOT NULL, embedding vector(1024) NOT NULL, UNIQUE (object_key, chunk_index));
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_cosine_ops);
```

`vector(1024)` matches the 1,024 numbers the embedding model returns. The HNSW index keeps the search fast once you have thousands of chunks. Every statement says `IF NOT EXISTS`, so running the script twice is safe.

Tested on 2026-10-02: `CREATE EXTENSION vector` works for `akmadmin` on Akamai Managed PostgreSQL 17.

## Step 6: Ask again

Save the fact again. The memory line now says `live`:

```bash
python -m agent --once "Remember that our demo slot is 2:15 PM."
```

```
brain      live      hackathon-chat at https://ws.akamai-workshops.com/v1
knowledge  live      bucket hackmidwest-e02dabda at us-sea-1.linodeobjects.com
memory     live      PostgreSQL 17.11 at a123456-akamai-prod-1234567-default.g2a.akamaidb.net:15268, pgvector 0.8.6
reflexes   off       no cache and no rate limit. Set VALKEY_URL to turn them on.
  [tool] remember({"fact": "The team's demo slot is 2:15 PM."})
Got it, your demo slot is 2:15 PM.
```

This time ask from a different conversation as well as a new process, as a teammate on another laptop would. `--session teammate` picks a second conversation:

```bash
python -m agent --once "When is our demo slot?" --session teammate
```

```
  [tool] recall({"query": "demo slot time"})
Your demo slot is at 2:15 PM.
```

The fact outlived the process that saved it, and a second conversation found it. The conversation itself is stored too. Ask in the first session, from yet another process:

```bash
python -m agent --once "What was the last thing I asked you?"
```

```
You asked me to remember that your demo slot is 2:15 PM.
```

The document vectors moved to the database as well. The first start with `DATABASE_URL` indexed your bucket into the documents table. After that, restarts skip files that have not changed, so they cost no embedding requests.

## Step 7: Read the code you just used

Open `agent/memory.py`. `PostgresMemory` does the same jobs as the in-process fallback, in SQL:

```python
    def history(self, session_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
        rows = self._run(
            "SELECT role, content FROM (SELECT id, role, content FROM messages WHERE session_id = %s"
            " ORDER BY id DESC LIMIT %s) AS recent ORDER BY id",
            (session_id, limit),
        )
        return [{"role": role, "content": content} for role, content in rows]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self._run("INSERT INTO sessions (id) VALUES (%s) ON CONFLICT DO NOTHING", (session_id,))
        self._run("INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)", (session_id, role, content))

    def search(self, vector: list[float], k: int = 3, notes: bool = False) -> list[Hit]:
        rows = self._run(
            "SELECT object_key, content, 1 - (embedding <=> %(v)s) FROM documents"
            " WHERE starts_with(object_key, 'notes/') = %(notes)s"
            " ORDER BY embedding <=> %(v)s LIMIT %(k)s",
            {"v": np.asarray(vector, dtype=np.float32), "notes": notes, "k": k},
        )
        return [Hit(key, text, float(score)) for key, text, score in rows]
```

`history()` returns the last 20 messages, oldest first, which is what the model expects. `search()` is the whole vector search: `<=>` is pgvector's cosine distance, so `ORDER BY embedding <=> ...` returns the closest chunks first, and `1 - distance` turns it into a similarity score. Notes from `remember` are rows whose key starts with `notes/`, so `recall` runs the same query with `notes = true`.

For your project, add tables in a new file such as `agent/sql/002_tasks.sql` and run `python scripts/db_init.py` again. To give each user private notes, put the session id in the note key and filter on it.

## Validation

- The startup line reads `memory  live  PostgreSQL 17... pgvector 0.8...`.
- `python -m agent --once "When is our demo slot?" --session someone-else` answers 2:15 PM.
- `python scripts/db_init.py` prints the pgvector version again and changes nothing.

**Show the judges:** Cloud Manager, **Databases**, then `hackmidwest-db`: PostgreSQL 17 in Seattle, status Active, and your allow list under Settings. From the terminal, `linode-cli databases postgresql-list --label hackmidwest-db` shows it, and the agent's `memory live ... pgvector 0.8.6` line shows it is in use.

## Clean up

If you go on to guide 03, keep the database. The Linode in guide 03 uses it too.

To delete it:

```bash
DB_ID=$(linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id)
linode-cli databases postgresql-delete $DB_ID
```

Then empty `DATABASE_URL` in `.env`. Cloud Manager's **Databases** page no longer lists it. Left running, the database costs $0.024 an hour, up to $16 a month. Deleting it deletes every conversation, vector, and note in it.

## Next steps

Put the agent on its own server in [Guide 03: The body on a Linode](03_body.md).

`scripts/status.sh` does steps 2 to 4 for you when you rebuild: it waits for `active` and for DNS, then writes `DATABASE_URL` to `.env`. These are the same commands you just typed, in one file.
