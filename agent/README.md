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

**`knowledge.py`** reads documents from the bucket with boto3, the AWS SDK for Python, which works against Akamai Object Storage when you give it the endpoint URL. `chunk()` cuts text into pieces of about 500 words, keeping paragraphs together. `Embedder` turns text into 1,024-number vectors, at most 16 texts and about 5,000 words per request, the endpoint's limits. `Knowledge.sync()` indexes files that are new or changed since it last looked and forgets deleted ones; `search()` syncs, then asks memory for the closest chunks. A file it cannot read is left out and tried again at the next search, and the `knowledge` status line names it. Without `OBJ_*` settings it reads `docs/sample/` instead.

**`memory.py`** stores three things: each session's messages, the document chunks with their vectors, and the notes the `remember` tool saves. `PostgresMemory` keeps them in Managed PostgreSQL, where the `vector` column from pgvector and its `<=>` cosine distance operator do the search in SQL. Notes are rows in the documents table whose key starts with `notes/`, so `recall` is the same search with a different filter. Without `DATABASE_URL`, `LocalMemory` keeps the same things in Python lists until the process exits. It connects over IPv4, because the allow list holds IPv4 addresses: on a network with IPv6, a connection would try IPv6 first, be dropped, and wait out the 10-second timeout before it tried IPv4. If the database is set but unreachable, the agent says why and uses the fallback instead of crashing. A timeout is what an address missing from the allow list looks like, so that message also points to guide 02, step 5. The brain sends the last 20 messages back to the model each turn, so long chats fit the 32,768-token context window.

**`cache.py`** is the reflexes. With `VALKEY_URL` set, it caches the vector for each question text for a day and allows each session 20 messages a minute. Without it, both are off and nothing else changes. If Valkey stops answering while the agent runs, the agent keeps going without them.

**`server.py`** is the web front. It builds the brain once at startup, then serves the chat page at `/`, `POST /chat` with `{"session_id": "...", "message": "..."}`, and `GET /health`, which lists every role and its state. A rate-limited session gets HTTP 429, and a failed model call gets 502.

**`__main__.py`** is the terminal front end. Status lines and tool calls go to stderr, and the answer goes to stdout, so `python -m agent --once "..." > answer.txt` captures only the answer. `--session` picks the conversation; the default is `terminal`.

## Make it yours

The kit answers questions about a made-up hackathon venue. Do this after guide 03, because guides 02 and 03 check their work with the sample files. To turn the kit into your project, change three things, then ship them.

**Your documents.** Put your `.md` and `.txt` files in a folder named `my-docs` in the repository folder. Take the three sample files out of the bucket, or the agent keeps answering questions about parking. Remove them before you upload, so a file of yours named `rules.md` is not deleted with them:

```bash
BUCKET=$(grep '^OBJ_BUCKET=' .env | cut -d= -f2)
linode-cli obj rm $BUCKET parking.md --cluster us-sea-1
linode-cli obj rm $BUCKET rules.md --cluster us-sea-1
linode-cli obj rm $BUCKET schedule.md --cluster us-sea-1
python scripts/upload.py my-docs/*
```

```
parking.md removed from hackmidwest-e02dabda
rules.md removed from hackmidwest-e02dabda
schedule.md removed from hackmidwest-e02dabda
```

Then `upload.py` prints one `Uploaded ... and indexed N chunk(s).` line per file, as in guide 01, step 6. The agent forgets a removed file the next time it searches, on your laptop and on the Linode.

**What the agent is for.** Two strings tell the model what the agent is for: the first sentence of `SYSTEM_PROMPT` in `brain.py`, and the `description` of `search_docs` in `tools.py`. The model reads them when it decides whether to search, so rewrite both for your documents. Tested on 2026-10-02 with a bike shop's returns and repairs policy in place of the samples. With the two strings unchanged, the agent skipped the search for 5 of 12 questions. Asked "Do you fix flat tires, and what does it cost?", it answered "I'm the starter agent for your HackMidwest team, so I can't fix flat tires." With these two changes, all 12 searched and answered from the file.

In `agent/brain.py`, replace the line that starts with `"You are the starter agent` with your own version of this line:

```python
    "You are the help desk agent for Northwind Bikes, a bike shop. Answer in short, plain sentences, as plain text "
```

In `agent/tools.py`, replace the first two lines of the `search_docs` description with your own version of these:

```python
        "description": "Search the documents in the team's Object Storage bucket by meaning, such as the shop's "
        "returns, repairs, warranty, and bike fitting. Use it for questions about the shop or the documents. "
```

Write your project where they say Northwind Bikes, and your documents' topics where they say returns, repairs, warranty, and bike fitting. Restart the agent and ask a question only your documents answer. The terminal shows `[tool] search_docs(...)` before the answer.

**Your tools.** To drop one of the four tools, delete its entry from `SCHEMAS` in `tools.py`. To add one, follow [Add a tool](#add-a-tool).

**Ship it.** The judges open the chat page on the Linode, and it runs the code from guide 03 until you copy yours. After every code change, copy the code and rebuild. These are the commands from [guide 03, step 6](../docs/03_body.md#step-6-copy-the-code-and-start-the-containers), after the address lookup from step 3:

```bash
LINODE_IP=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format ipv4)
scp -r agent docs Dockerfile compose.yaml .dockerignore .env root@$LINODE_IP:/opt/hackmidwest/
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose up -d --build"
echo "http://$LINODE_IP:8000"
```

Open the address it prints and ask a question only your documents answer. Under the answer, the page lists `search_docs` after `tools used:`, and the answer names one of your files. If the page does not load, read the log with `ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose logs agent"`.

Ship every change. With a database, the laptop and the Linode share the document vectors. A Linode on old code deletes the vectors of any file its code does not read, such as your PDFs, each time it searches.

## Add a tool

1. Write a function in `tools.py` that takes simple arguments and returns a short string.
2. Add its schema to `SCHEMAS`. The model gets every tool in `SCHEMAS` with each request. It never sees your function, only the schema. It decides whether to call the tool from the `description` and the system prompt, so say exactly what the tool does and when to use it.
3. Call your function from `Tools.run()`, which runs the tools the model asks for.

For example, a tool that looks up a team's table number. Paste this into `tools.py`, below the `current_time()` function:

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

Then, in `Tools.run()`, below the two lines for `current_time`:

```python
            if name == "find_table":
                return find_table(**args)
```

Restart the agent and ask "Where does Byte Club sit?". The terminal shows `[tool] find_table({"team": "Byte Club"})`, then the answer, `Byte Club sits at Table 12.`

## Read other file types

The agent reads `.md` and `.txt` files. To read PDFs:

1. Add `pypdf` to `agent/requirements.txt` and to `requirements.txt`.
2. With the virtual environment active, install it on your laptop: `pip install -r requirements.txt`.
3. In `knowledge.py`, change `TEXT_FILES` to `TEXT_FILES = (".md", ".txt", ".pdf")`.
4. In `knowledge.py`, replace `Bucket.read()` with this version:

```python
    def read(self, key: str) -> str:
        body = self.s3.get_object(Bucket=self.name, Key=key)["Body"].read()
        if key.lower().endswith(".pdf"):
            from io import BytesIO
            from pypdf import PdfReader
            return "\n\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(body)).pages)
        return body.decode("utf-8", errors="replace")
```

5. Ship it with the commands in [Make it yours](#make-it-yours). The rebuild installs `pypdf` on the Linode. Until then, the Linode cannot read PDFs.

`scripts/upload.py` checks `TEXT_FILES` too, so PDFs upload once the extension is in the list. Scanned PDFs have no text to extract; they need OCR first.

A file the agent cannot read does not stop the others. If you skip step 2, for example, `upload.py` puts the PDF in the bucket and says:

```
Uploaded manual.pdf to hackmidwest-e02dabda/manual.pdf, but could not read it (No module named 'pypdf'). The agent tries it again at each search. Fix the cause and upload it again, or take it out of the bucket:
  linode-cli obj rm hackmidwest-e02dabda manual.pdf --cluster us-sea-1
```

Here the fix is step 2, not `obj rm`. With the virtual environment active, run `pip install -r requirements.txt`, then `python scripts/upload.py manual.pdf` again, and restart the agent. Take a file out of the bucket only when it stays unreadable, such as a damaged PDF.

Until you fix it, the agent answers from every other file, and its `knowledge` line names the file when it starts:

```
knowledge  live      bucket hackmidwest-e02dabda at us-sea-1.linodeobjects.com. Could not read manual.pdf (No module named 'pypdf').
```

Copy-protected PDFs are encrypted, even when they open without a password. The agent cannot read them without the `cryptography` package, and names the reason: `cryptography>=3.1 is required for AES algorithm`. To read them, add `cryptography` to both requirements files and install again. On an Intel Mac, pip has to build `cryptography` from source. That needs Rust and OpenSSL from Homebrew. See [its install notes](https://cryptography.io/en/latest/installation/).

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
