"""Chat with the agent in the terminal.

    python -m agent                   chat until you type exit or press Ctrl+D
    python -m agent --once "Hello"    answer one message and exit

Status lines and tool calls go to stderr. The model's answer is the only thing on stdout.
"""
import argparse
import sys

import openai

from . import config
from .brain import build


class Printer:
    """Streams the answer to stdout and shows each tool call as it happens."""

    def __init__(self, prefix: str):
        self.prefix = prefix
        self.midline = False

    def text(self, chunk: str) -> None:
        if not self.midline:
            print(self.prefix, end="")
            self.midline = True
        print(chunk, end="", flush=True)

    def tool(self, name: str, arguments: str) -> None:
        self.end_line()
        print(f"  [tool] {name}({arguments})", file=sys.stderr, flush=True)

    def end_line(self) -> None:
        if self.midline:
            print(flush=True)
            self.midline = False


def ask(brain, session_id: str, message: str, prefix: str) -> bool:
    printer = Printer(prefix)
    try:
        brain.chat(session_id, message, on_text=printer.text, on_tool=printer.tool)
        printer.end_line()
        return True
    except openai.APIError as error:
        printer.end_line()
        print(f"[error] the brain did not answer: {error}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m agent", description="Chat with the HackMidwest starter agent.")
    parser.add_argument("--once", metavar="MESSAGE", help="answer one message, print the reply, and exit")
    parser.add_argument("--session", default="terminal",
                        help="conversation id. Reuse it to continue a conversation (default: terminal)")
    args = parser.parse_args()

    cfg = config.load()
    for line in config.status(cfg):
        print(line, file=sys.stderr)
    brain = build(cfg)

    if args.once:
        return 0 if ask(brain, args.session, args.once, prefix="") else 1

    print("\nType a message and press Enter. Type exit or press Ctrl+D to quit.\n", file=sys.stderr)
    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if message.lower() in {"exit", "quit"}:
            return 0
        if message:
            ask(brain, args.session, message, prefix="agent> ")


if __name__ == "__main__":
    sys.exit(main())
