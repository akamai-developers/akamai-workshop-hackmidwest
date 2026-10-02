"""Tools the model can call. Each tool is a plain function that returns a short string.

To add a tool: write the function, add its schema to SCHEMAS, and add one line to
Tools.run. The model only reads the schema, so make the description specific.
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
}


def current_time(timezone: str = "America/Chicago") -> str:
    now = datetime.now(ZoneInfo(timezone))
    return now.strftime("%A, %B %d, %Y, %I:%M %p %Z")


class Tools:
    """The tools one agent offers the model, plus the adapters those tools need."""

    def __init__(self, memory=None):
        self.memory = memory

    def schemas(self) -> list[dict]:
        names = ["current_time"]
        return [{"type": "function", "function": SCHEMAS[name]} for name in names]

    def run(self, name: str, arguments: str, session_id: str) -> str:
        """Run one tool call. Errors go back to the model as text, so it can try again."""
        try:
            args = json.loads(arguments or "{}")
            if name == "current_time":
                return current_time(**args)
            return f"There is no tool named {name}."
        except Exception as error:  # the arguments are model output, so anything can go wrong
            return f"{name} failed: {error}"
