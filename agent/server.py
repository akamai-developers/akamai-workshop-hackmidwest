"""The web front of the agent: a chat page, POST /chat, and GET /health.

    uvicorn agent.server:app --host 0.0.0.0 --port 8000

The brain is built once at startup, the same way the terminal chat builds it.
"""
from contextlib import asynccontextmanager
from pathlib import Path

import openai
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config
from .brain import RateLimited, build

PAGE = Path(__file__).parent / "static" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "brain"):  # tests put a fake brain here first
        app.state.brain = build(config.load())
    for line in app.state.brain.status():
        print(line, flush=True)
    yield


app = FastAPI(title="HackMidwest starter agent", lifespan=lifespan)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)


class ChatReply(BaseModel):
    reply: str
    tools_used: list[str]


@app.post("/chat")
def chat(body: ChatRequest, request: Request) -> ChatReply:
    try:
        reply = request.app.state.brain.chat(body.session_id, body.message)
    except RateLimited as error:
        raise HTTPException(status_code=429, detail=str(error))
    except openai.APIError as error:
        raise HTTPException(status_code=502, detail=f"The brain did not answer: {error}")
    return ChatReply(reply=reply.text, tools_used=reply.tools_used)


@app.get("/health")
def health(request: Request) -> dict:
    """Which Akamai services this agent is using right now. Open it in front of the judges."""
    roles = request.app.state.brain.roles()
    return {"status": "ok", **{role: {"state": state, "detail": detail} for role, state, detail in roles}}


@app.get("/")
def page() -> FileResponse:
    return FileResponse(PAGE)
