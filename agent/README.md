# How the agent is put together

The agent is a few hundred lines of Python with no agent framework. Each file maps to one role in the stack picture, so when you change a role you know which file to open.

```
agent/
  __main__.py   python -m agent: the terminal chat
  config.py     reads .env and says which roles are live
  brain.py      the system prompt and the tool loop
  tools.py      the functions the model can call
  memory.py     conversation history
```

## The modules

**`config.py`** reads `.env` into a `Config` object. Only `OPENAI_BASE_URL` and `OPENAI_API_KEY` are required; without them the agent refuses to start and tells you which one is missing. Values in `.env` win over your shell, the same as in the notebooks, so an OpenAI key in your shell cannot break the brain. `status()` builds the lines the agent prints at startup: one per role, `live`, `fallback`, or `off`, with host names but never passwords or keys.

**`brain.py`** holds the system prompt and the tool loop. `Brain.chat()` loads the session's history from memory, adds your message, and calls `run()`. `run()` calls the model, runs every tool it asks for, sends the results back, and repeats until the model answers in prose, at most 5 model calls per message. Each call streams, so the terminal shows the answer as it arrives. `_complete()` rebuilds the tool calls from the streamed chunks: the endpoint sends each call's id and name once, then its arguments in pieces. `build()` connects every service `.env` turns on and hands them to the brain.

**`tools.py`** lists the tools in `SCHEMAS` and runs them in `Tools.run()`. A tool is a plain function that returns a short string. If a tool fails, the error goes back to the model as text, so it can try again or explain. The model never runs anything itself; it can only ask.

**`memory.py`** keeps each session's messages. Without a database it uses `LocalMemory`, a dictionary of lists that is gone when the process exits. The brain sends the last 20 messages back to the model each turn, so long chats still fit the 32,768-token context window.

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

## Swap the model provider

The brain talks to any server that speaks the OpenAI chat completions API with tool calling. Change three lines in `.env`:

```bash
OPENAI_BASE_URL=https://your-provider.example.com/v1
OPENAI_API_KEY=your-key
CHAT_MODEL=the-provider-model-name
```

Embeddings come from `EMBEDDING_MODEL` on the same server. If you change the embedding model, its vectors must have 1,024 dimensions to fit the database column, or you change the column size and index again.

Two habits of this endpoint are built into the code. The brain never sends `tool_choice: "none"`, because the endpoint handles it badly; to stop tool use, leave `tools` out of the request. Thinking is off unless you turn it on, so answers arrive without a reasoning preamble.
