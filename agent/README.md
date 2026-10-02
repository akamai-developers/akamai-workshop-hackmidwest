# Starter code guide

[Workshop home](../README.md) · [Project paths](../docs/build.md)

The starter is a Python application with a terminal interface and a FastAPI server. It calls the workshop inference endpoint, searches documents, and can store conversations and vectors in PostgreSQL. You can use individual components or adapt the complete application.

## Code map

| File | Responsibility |
|---|---|
| `__main__.py` | Terminal chat and one-shot requests |
| `server.py` | Chat page, `POST /chat`, and `GET /health` |
| `config.py` | Environment settings; `.env` overrides shell values |
| `brain.py` | Prompt, streamed model requests, tool dispatch loop |
| `tools.py` | Tool definitions and allowed function dispatch |
| `knowledge.py` | Source files, text chunks, embeddings, and document search |
| `memory.py` | Conversation messages, document vectors, and saved notes |
| `cache.py` | Valkey embedding cache and session counters |
| `sql/001_init.sql` | PostgreSQL schema and pgvector extension |
| `static/index.html` | Browser chat interface |

The existing API status fields are `brain` (inference client), `knowledge` (document source), `memory` (data store), and `reflexes` (cache). `brain: live` means configured; verify a real model request separately.

Without cloud data settings, the starter reads `docs/sample/` and keeps state in process memory. Without Valkey, it runs without the cache or session limit. Inspect startup status when a service is configured but unavailable: some components fall back so that the app can continue.

## Make it yours

The sample documents describe a fictional event. Replace them with your project's `.md` or `.txt` files, then update both the application prompt and the search tool description.

For a connected bucket, remove only the sample objects you intend to replace:

```bash
BUCKET=$(sed -n 's/^OBJ_BUCKET=//p' .env)
linode-cli obj rm "$BUCKET" parking.md --cluster us-sea-1
linode-cli obj rm "$BUCKET" rules.md --cluster us-sea-1
linode-cli obj rm "$BUCKET" schedule.md --cluster us-sea-1
python scripts/upload.py my-docs/*
```

Create `my-docs/` and add your files before running the upload. The script supports file extensions listed in `TEXT_FILES` in `knowledge.py`. If you are staying local, replace the files under `docs/sample/` or change the configured local source path in `config.py`.

In `brain.py`, change the opening sentence of `SYSTEM_PROMPT` to describe your application. In `tools.py`, change the `search_docs` description to describe your documents. The model uses those descriptions when deciding whether to search. Check a question the documents answer and one they do not.

Redeploy with `bash scripts/deploy_linode.sh` or `bash scripts/deploy_lke.sh` from the workshop directory. Each script reuses its existing deployment and copies the current code and settings.


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



## Application limits

The tool loop permits at most five model calls per message. Recent conversation history is limited by message count, not token count. Long messages can still exceed the endpoint's context window.

The demo has no login or HTTPS, and saved notes are shared across sessions. Add authentication, per-user access checks, input validation, and HTTPS before using private information. The Valkey session counter is not an account-level abuse control.

For a maintained deployment, use a dedicated database user, verify the database certificate with the supplied CA, plan backups and restores, and package application dependencies in a container image. These are deployment tasks beyond the workshop exercise.

## Change the model provider

Set `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `CHAT_MODEL`, and `EMBEDDING_MODEL` for a provider supporting the operations the starter uses. Test chat, streamed tool calls, and embeddings separately; API compatibility varies by deployment.

The database schema expects 1,024-dimensional embeddings. If you change the embedding model, re-embed the corpus and invalidate cached vectors. Change the schema dimension too if needed. Matching dimensions alone do not make embeddings from different models comparable.
