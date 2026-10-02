"""The tool loop, with the OpenAI client replaced by a fake that replays scripted streams."""
import copy
from types import SimpleNamespace as NS

import pytest

from agent import config
from agent.brain import MAX_STEPS, Brain, RateLimited
from agent.memory import LocalMemory
from agent.tools import Tools

CFG = config.Config(base_url="http://fake/v1", api_key="hk_test")


def text_stream(text):
    """A streamed answer in two pieces, then the usage-only chunk the endpoint sends last."""
    half = len(text) // 2
    return [
        NS(choices=[NS(delta=NS(content=text[:half], tool_calls=None))]),
        NS(choices=[NS(delta=NS(content=text[half:], tool_calls=None))]),
        NS(choices=[]),
    ]


def tool_stream(*calls):
    """Tool calls the way the endpoint streams them: id and name first, then the arguments in pieces."""
    chunks = []
    for index, (call_id, name, arguments) in enumerate(calls):
        chunks.append(NS(choices=[NS(delta=NS(content=None, tool_calls=[
            NS(index=index, id=call_id, function=NS(name=name, arguments=None))]))]))
        for start in range(0, len(arguments), 4):
            chunks.append(NS(choices=[NS(delta=NS(content=None, tool_calls=[
                NS(index=index, id=None, function=NS(name=None, arguments=arguments[start:start + 4]))]))]))
    return chunks


class FakeClient:
    def __init__(self, *streams):
        self.streams = list(streams)
        self.requests = []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))  # the brain keeps appending to the same list
        return iter(self.streams.pop(0))


def make_brain(*streams):
    memory = LocalMemory()
    client = FakeClient(*streams)
    return Brain(CFG, Tools(memory=memory), memory, client=client), client, memory


def test_plain_answer_streams_text_and_saves_history():
    brain, client, memory = make_brain(text_stream("Hello there."))
    pieces = []
    reply = brain.chat("s1", "Say hello", on_text=pieces.append)

    assert reply.text == "Hello there."
    assert reply.tools_used == []
    assert "".join(pieces) == "Hello there."
    assert len(client.requests) == 1
    assert client.requests[0]["stream"] is True
    assert client.requests[0]["messages"][0]["role"] == "system"
    assert memory.history("s1") == [
        {"role": "user", "content": "Say hello"},
        {"role": "assistant", "content": "Hello there."},
    ]


def test_tool_call_runs_the_tool_and_sends_the_result_back():
    brain, client, _ = make_brain(
        tool_stream(("call_1", "current_time", '{"timezone": "America/Chicago"}')),
        text_stream("It is noon."),
    )
    seen = []
    reply = brain.chat("s1", "What time is it?", on_tool=lambda name, args: seen.append((name, args)))

    assert reply.text == "It is noon."
    assert reply.tools_used == ["current_time"]
    assert seen == [("current_time", '{"timezone": "America/Chicago"}')]

    second = client.requests[1]["messages"]
    assistant, tool = second[-2], second[-1]
    assert assistant["tool_calls"][0]["id"] == "call_1"
    assert assistant["tool_calls"][0]["function"]["arguments"] == '{"timezone": "America/Chicago"}'
    assert tool["role"] == "tool" and tool["tool_call_id"] == "call_1"
    assert "CDT" in tool["content"] or "CST" in tool["content"]


def test_parallel_tool_calls_all_run_in_one_round():
    brain, client, _ = make_brain(
        tool_stream(("a", "current_time", '{"timezone": "Asia/Tokyo"}'),
                    ("b", "current_time", '{"timezone": "America/Chicago"}')),
        text_stream("Both times."),
    )
    reply = brain.chat("s1", "Time in Tokyo and Chicago?")

    assert reply.tools_used == ["current_time", "current_time"]
    tool_messages = [m for m in client.requests[1]["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_messages] == ["a", "b"]
    assert "JST" in tool_messages[0]["content"]


def test_step_cap_stops_a_model_that_never_answers():
    streams = [tool_stream((f"c{i}", "current_time", "{}")) for i in range(MAX_STEPS + 3)]
    brain, client, memory = make_brain(*streams)
    reply = brain.chat("s1", "Loop forever")

    assert len(client.requests) == MAX_STEPS
    assert reply.tools_used == ["current_time"] * MAX_STEPS
    assert "stopped after" in reply.text
    assert memory.history("s1")[-1]["content"] == reply.text


def test_history_from_memory_is_sent_on_the_next_turn():
    brain, client, _ = make_brain(text_stream("Noted."), text_stream("Your name is Ada."))
    brain.chat("s1", "My name is Ada.")
    brain.chat("s1", "What is my name?")

    sent = [(m["role"], m["content"]) for m in client.requests[1]["messages"]]
    assert sent[1:] == [
        ("user", "My name is Ada."),
        ("assistant", "Noted."),
        ("user", "What is my name?"),
    ]


def test_sessions_do_not_share_history():
    brain, client, _ = make_brain(text_stream("Noted."), text_stream("I do not know."))
    brain.chat("alice", "My name is Ada.")
    brain.chat("bob", "What is my name?")

    assert [m["role"] for m in client.requests[1]["messages"]] == ["system", "user"]


def test_tool_errors_go_back_to_the_model_as_text():
    tools = Tools()
    assert "no tool named" in tools.run("launch_rocket", "{}", "s1")
    assert "failed" in tools.run("current_time", "{not json", "s1")
    assert "failed" in tools.run("current_time", '{"timezone": "Mars/Base"}', "s1")
    assert "failed" in tools.run("current_time", '{"unexpected": 1}', "s1")


def test_config_refuses_to_start_without_the_brain(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="OPENAI_BASE_URL and OPENAI_API_KEY"):
        config.load(env_file=None)


def test_host_of_drops_user_names_and_passwords():
    assert config.host_of("postgresql://akmadmin:pa55word@db.example.com:12345/defaultdb?sslmode=require") \
        == "db.example.com:12345"
    assert config.host_of("https://us-sea-1.linodeobjects.com") == "us-sea-1.linodeobjects.com"
    assert config.host_of("us-sea-1.linodeobjects.com") == "us-sea-1.linodeobjects.com"
    assert config.host_of("redis://valkey:6379/0") == "valkey:6379"


def test_status_has_one_line_per_role():
    memory = LocalMemory()
    cache = NS(state="off", detail="no cache", allow=lambda session_id: True)
    knowledge = NS(state="live", detail="bucket hackmidwest-abc at us-sea-1.linodeobjects.com")
    brain = Brain(CFG, Tools(), memory, knowledge, cache, client=FakeClient())
    lines = brain.status()
    assert [line.split()[0] for line in lines] == ["brain", "knowledge", "memory", "reflexes"]
    assert lines[1].split()[1] == "live" and lines[2].split()[1] == "fallback"
    assert "hk_test" not in "\n".join(lines)


def test_rate_limited_session_never_reaches_the_model():
    memory = LocalMemory()
    cache = NS(state="live", detail="valkey", allow=lambda session_id: False)
    client = FakeClient(text_stream("never sent"))
    brain = Brain(CFG, Tools(), memory, None, cache, client=client)
    with pytest.raises(RateLimited):
        brain.chat("s1", "hello")
    assert client.requests == [] and memory.history("s1") == []
