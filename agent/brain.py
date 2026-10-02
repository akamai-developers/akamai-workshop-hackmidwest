"""The brain: the hackathon chat model, the system prompt, and the tool loop."""
from dataclasses import dataclass, field
from typing import Callable

from openai import OpenAI

from . import memory as memory_store
from .config import Config
from .tools import Tools

SYSTEM_PROMPT = (
    "You are the starter agent for a HackMidwest team. Answer in short, plain sentences. "
    "Use your tools when they help. When a tool returns facts, answer from them and name the file "
    "they came from. If the tools do not have the answer, say so instead of guessing."
)
MAX_STEPS = 5  # model calls per message, so a confused model cannot loop forever
MAX_TOKENS = 1024  # output tokens per model call; the endpoint allows up to 4,096


@dataclass
class Reply:
    text: str
    tools_used: list[str] = field(default_factory=list)


class Brain:
    def __init__(self, cfg: Config, tools: Tools, memory, client: OpenAI | None = None):
        self.cfg = cfg
        self.tools = tools
        self.memory = memory
        self.client = client or OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)

    def chat(self, session_id: str, message: str, on_text: Callable | None = None,
             on_tool: Callable | None = None) -> Reply:
        """Answer one message in a session, then save both sides of the exchange to memory."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.memory.history(session_id),
            {"role": "user", "content": message},
        ]
        reply = self.run(messages, session_id, on_text, on_tool)
        self.memory.add_message(session_id, "user", message)
        self.memory.add_message(session_id, "assistant", reply.text)
        return reply

    def run(self, messages: list[dict], session_id: str, on_text: Callable | None = None,
            on_tool: Callable | None = None) -> Reply:
        """The tool loop: call the model, run the tools it asks for, repeat until it answers in prose."""
        used = []
        for _ in range(MAX_STEPS):
            text, calls = self._complete(messages, on_text)
            if not calls:
                return Reply(text, used)
            messages.append({"role": "assistant", "content": text or None, "tool_calls": [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls
            ]})
            for call in calls:  # the model may ask for several tools at once
                if on_tool:
                    on_tool(call["name"], call["arguments"])
                result = self.tools.run(call["name"], call["arguments"], session_id)
                used.append(call["name"])
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        return Reply(f"I stopped after {MAX_STEPS} model calls without an answer. Try a narrower question.", used)

    def _complete(self, messages: list[dict], on_text: Callable | None) -> tuple[str, list[dict]]:
        """One streamed model call. Returns the text and the tool calls, rebuilt from the chunks."""
        stream = self.client.chat.completions.create(
            model=self.cfg.chat_model,
            messages=messages,
            tools=self.tools.schemas(),  # to forbid tools, leave this out; tool_choice "none" is unreliable here
            max_tokens=MAX_TOKENS,
            stream=True,
        )
        text, calls = [], {}
        for chunk in stream:
            if not chunk.choices:  # the last chunk carries only token usage
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text.append(delta.content)
                if on_text:
                    on_text(delta.content)
            for part in delta.tool_calls or []:  # the id and name arrive once, the arguments in pieces
                call = calls.setdefault(part.index, {"id": "", "name": "", "arguments": ""})
                call["id"] = part.id or call["id"]
                if part.function:
                    call["name"] += part.function.name or ""
                    call["arguments"] += part.function.arguments or ""
        return "".join(text), [calls[index] for index in sorted(calls)]


def build(cfg: Config) -> Brain:
    """Connect every service that .env turns on and hand them to the brain."""
    memory = memory_store.connect(cfg)
    tools = Tools(memory=memory)
    return Brain(cfg, tools, memory)
