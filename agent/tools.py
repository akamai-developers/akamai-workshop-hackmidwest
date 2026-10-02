"""Tools the model can call. Each tool is a plain function that returns a short string.

To add a tool: write the function, add its schema to SCHEMAS, and call the function
from Tools.run. The model only reads the schema, so make the description specific.
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

SCHEMAS = {
    "current_time": {
        "name": "current_time",
        "description": "Get the current date and time. Use it for any question about today, now, "
        "or how long until something happens.",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA time zone such as America/Chicago. Leave it out for Kansas City time.",
                },
            },
        },
    },
    "search_docs": {
        "name": "search_docs",
        "description": "Search the documents in the team's Object Storage bucket by meaning, such as the event "
        "schedule, the rules, and venue details like parking. Use it for questions about the event or the documents. "
        "Returns the closest passages and their file names.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for, in plain words"}},
            "required": ["query"],
        },
    },
    "remember": {
        "name": "remember",
        "description": "Save a fact for later: a name, a decision, a deadline, anything the user asks you to keep. "
        "Saved facts are shared by every conversation with this agent.",
        "parameters": {
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "The fact, as one complete sentence"}},
            "required": ["fact"],
        },
    },
    "recall": {
        "name": "recall",
        "description": "Look up facts saved earlier with remember, in this conversation or any other: names, "
        "times, decisions, anything someone asked you to keep. Use it for questions about the user or their team, "
        "such as their own demo time or team name, before searching documents.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for, in plain words"}},
            "required": ["query"],
        },
    },
}


def current_time(timezone: str = "America/Chicago") -> str:
    now = datetime.now(ZoneInfo(timezone))
    return now.strftime("%A, %B %d, %Y, %I:%M %p %Z")


class Tools:
    """The tools one agent offers the model, plus the adapters those tools need."""

    def __init__(self, knowledge=None, memory=None):
        self.knowledge = knowledge
        self.memory = memory

    def schemas(self) -> list[dict]:
        """Every tool in SCHEMAS, except the ones that need a service this agent was built without."""
        missing = set()
        if not self.knowledge:
            missing |= {"search_docs", "remember", "recall"}
        if not self.memory:
            missing |= {"remember", "recall"}
        return [{"type": "function", "function": schema} for name, schema in SCHEMAS.items() if name not in missing]

    def run(self, name: str, arguments: str, session_id: str) -> str:
        """Run one tool call. Errors go back to the model as text, so it can try again."""
        try:
            args = json.loads(arguments or "{}")
            if name == "current_time":
                return current_time(**args)
            if name == "search_docs" and self.knowledge:
                return self.search_docs(**args)
            if name == "remember" and self.memory:
                return self.remember(**args)
            if name == "recall" and self.memory:
                return self.recall(**args)
            return f"There is no tool named {name}."
        except Exception as error:  # the arguments are model output, so anything can go wrong
            return f"{name} failed: {error}"

    def search_docs(self, query: str) -> str:
        hits = self.knowledge.search(query)
        if not hits:
            return "No documents found. The bucket has no text files yet."
        return "\n\n".join(f"[{hit.key}, similarity {hit.score:.2f}]\n{hit.text}" for hit in hits)

    def remember(self, fact: str) -> str:
        self.memory.add_note(fact, self.knowledge.embed.one(fact))
        return f"Saved: {fact}"

    def recall(self, query: str) -> str:
        hits = self.memory.search(self.knowledge.embed.one(query), k=3, notes=True)
        if not hits:
            return "No saved facts yet."
        return "\n".join(f"- {hit.text} (similarity {hit.score:.2f})" for hit in hits)
