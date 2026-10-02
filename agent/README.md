# How the agent is put together

The agent is a few hundred lines of Python with no agent framework. Each file maps to one role in the stack picture, so when you change a role you know which file to open.

```
agent/
  __main__.py       python -m agent: the terminal chat
  server.py         the web front: the chat page, POST /chat, GET /health
  config.py         reads .env
  brain.py          the system prompt, the tool loop, and build(), which wires the rest
  tools.py          the functions the model can call
  knowledge.py      documents from the Object Storage bucket, chunked and embedded
  memory.py         history, document vectors, and notes, in PostgreSQL with pgvector
  cache.py          Valkey: the embedding cache and the per-session rate limit
  sql/001_init.sql  the tables, created by scripts/db_init.py
  static/index.html the chat page
```

## The modules

**`config.py`** reads `.env` into a `Config` object. Only `OPENAI_BASE_URL` and `OPENAI_API_KEY` are required; without them the agent refuses to start and tells you which one is missing. Values in `.env` win over your shell, the same as in the notebooks, so an OpenAI key in your shell cannot break the brain. `host_of()` turns a URL into its host and port, which is how status lines show where a service is without printing its password.

**`brain.py`** holds the system prompt and the tool loop. `Brain.chat()` checks the rate limit, loads the session's history from memory, adds your message, and calls `run()`. `run()` calls the model, runs every tool it asks for, sends the results back, and repeats until the model answers in prose, at most 5 model calls per message. Each call streams, so the terminal shows the answer as it arrives. `_complete()` rebuilds the tool calls from the streamed chunks: the endpoint sends each call's id and name once, then its arguments in pieces. `build()` connects every service `.env` turns on and hands them to the brain. `status()` prints one line per role: `live`, `fallback`, `off`, or `error`.

**`tools.py`** lists the tools in `SCHEMAS` and runs them in `Tools.run()`. A tool is a plain function that returns a short string. If a tool fails, the error goes back to the model as text, so it can try again or explain. There are four: `current_time`, `search_docs` (knowledge), and `remember` and `recall` (memory).

**`knowledge.py`** reads documents from the bucket with boto3, the AWS SDK for Python, which works against Akamai Object Storage when you give it the endpoint URL. `chunk()` cuts text into pieces of about 500 words, keeping paragraphs together. `Embedder` turns text into 1,024-number vectors, at most 16 texts and about 5,000 words per request, the endpoint's limits. `Knowledge.sync()` indexes files that are new or changed since it last looked and forgets deleted ones; `search()` syncs, then asks memory for the closest chunks. Without `OBJ_*` settings it reads `docs/sample/` instead.

**`memory.py`** stores three things: each session's messages, the document chunks with their vectors, and the notes the `remember` tool saves. `PostgresMemory` keeps them in Managed PostgreSQL, where the `vector` column from pgvector and its `<=>` cosine distance operator do the search in SQL. Notes are rows in the documents table whose key starts with `notes/`, so `recall` is the same search with a different filter. Without `DATABASE_URL`, `LocalMemory` keeps the same things in Python lists until the process exits. It connects over IPv4, because the allow list holds IPv4 addresses: on a network with IPv6, a connection would try IPv6 first, be dropped, and wait out the 10-second timeout before it tried IPv4. If the database is set but unreachable, the agent says why and uses the fallback instead of crashing. The brain sends the last 20 messages back to the model each turn, so long chats fit the 32,768-token context window.

**`cache.py`** is the reflexes. With `VALKEY_URL` set, it caches the vector for each question text for a day and allows each session 20 messages a minute. Without it, both are off and nothing else changes.

**`server.py`** is the web front. It builds the brain once at startup, then serves the chat page at `/`, `POST /chat` with `{"session_id": "...", "message": "..."}`, and `GET /health`, which lists every role and its state. A rate-limited session gets HTTP 429, and a failed model call gets 502.

**`__main__.py`** is the terminal front end. Status lines and tool calls go to stderr, and the answer goes to stdout, so `python -m agent --once "..." > answer.txt` captures only the answer. `--session` picks the conversation; the default is `terminal`.

## Add a tool

1. Write a function in `tools.py` that takes simple arguments and returns a short string.
2. Add its schema to `SCHEMAS`. The `description` is the only thing the model reads when it decides whether to call the tool, so say exactly what it does and when to use it.
3. Add its name to the list in `Tools.schemas()` and one line to `Tools.run()`.

For example, a tool that looks up a team's table number:

```python
TABLES = {"byte club": "Table 12", "null pointers": "Table 4"}

def find_table(team: str) -> str:
    return TABLES.get(team.lower(), f"No table found for {team}.")

SCHEMAS["find_table"] = {
    "name": "find_table",
    "description": "Find which table a hackathon team sits at, by team name.",
    "parameters": {"type": "object", "properties": {"team": {"type": "string"}}, "required": ["team"]},
}
```

Then in `Tools.run()`:

```python
            if name == "find_table":
                return find_table(**args)
```

Restart the agent and ask "Where does Byte Club sit?". The terminal shows `[tool] find_table({"team": "Byte Club"})` before the answer.

## Read other file types

The agent reads `.md` and `.txt` files. To read PDFs, add `pypdf` to `agent/requirements.txt` and `requirements.txt`, add `".pdf"` to `TEXT_FILES` in `knowledge.py`, and extract the text in `Bucket.read()`:

```python
    def read(self, key: str) -> str:
        body = self.s3.get_object(Bucket=self.name, Key=key)["Body"].read()
        if key.lower().endswith(".pdf"):
            from io import BytesIO
            from pypdf import PdfReader
            return "\n\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(body)).pages)
        return body.decode("utf-8", errors="replace")
```

`scripts/upload.py` checks `TEXT_FILES` too, so PDFs upload once the extension is in the list. Scanned PDFs have no text to extract; they need OCR first.

## Before you put real data in it

The kit is built for a weekend demo. These are the first things to change for anything more:

- **Add a login.** `POST /chat` answers anyone who can reach port 8000, and anyone can read the facts saved with `remember`. Put an API key check in `server.py`, or restrict the Cloud Firewall rule for port 8000 to the addresses that should reach it.
- **Verify the database's certificate.** `sslmode=require` encrypts the connection but does not check who answers. `linode-cli databases postgresql-ssl-cert <database-id>` returns the CA certificate, base64-encoded. Save it decoded as `ca.crt` and use `sslmode=verify-full&sslrootcert=ca.crt` in `DATABASE_URL`.
- **Use an application user.** Akamai's docs say `akmadmin` and `defaultdb` are for administration. Create a database and a user with only the rights the agent needs.
- **Plan for more vectors.** pgvector with an HNSW index handles hundreds of thousands of chunks. The managed PostgreSQL also offers the `vectorscale` extension (0.9.0 on 2026-10-02) for larger collections.

## Swap the model provider

The brain talks to any server that speaks the OpenAI chat completions API with tool calling. Change three lines in `.env`:

```bash
OPENAI_BASE_URL=https://your-provider.example.com/v1
OPENAI_API_KEY=your-key
CHAT_MODEL=the-provider-model-name
```

Embeddings come from `EMBEDDING_MODEL` on the same server. If you change the embedding model, its vectors must have 1,024 dimensions to fit the database column, or you change the column size and index again.

Two habits of this endpoint are built into the code. The brain never sends `tool_choice: "none"`, because the endpoint handles it badly; to stop tool use, leave `tools` out of the request. Thinking is off unless you turn it on, so answers arrive without a reasoning preamble.
