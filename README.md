# HackMidwest inference workshop

Three hands-on labs for the hackathon's AI endpoint. Each lab is a Jupyter notebook you run on your own laptop against the shared endpoint. No GPU, no cloud account, and no model downloads on your side.

## What you are using

One HTTPS endpoint, compatible with the OpenAI API, running on Akamai Cloud GPUs:

| Capability | Model alias | Backing model |
|---|---|---|
| Chat completions | `hackathon-chat` | Qwen3.8-27B (FP8) on vLLM |
| Embeddings | `hackathon-embedding` | Qwen3-Embedding-0.6B on Text Embeddings Inference |
| Image generation | `hackathon-image` | FLUX.2 klein 4B |

Because it speaks the OpenAI API, the official `openai` package and most frameworks (LangChain, LlamaIndex, Strands, and others) work by changing two settings: the base URL and the API key.

## Before you begin

- Python 3.10 or newer
- Your team's API key from the organizers. One key per team, shared by all members. Treat it like a password: keep it in a backend or a local `.env`, never in frontend code or a public repository.
- About 10 minutes for the quickstart, about 90 minutes for all five notebooks

## Setup

```bash
git clone <this repository>
cd akamai-workshop-hackmidwest
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then paste your team key into .env
jupyter notebook notebooks/
```

The notebooks read `OPENAI_BASE_URL` and `OPENAI_API_KEY` from `.env`. Any script you write can use the same two variables:

```python
from openai import OpenAI
client = OpenAI()  # reads OPENAI_BASE_URL and OPENAI_API_KEY from the environment
```

## Quick reference

Three operations. Every request carries `Authorization: Bearer <team key>` and `Content-Type: application/json`.

**Chat** `POST /v1/chat/completions`

```bash
curl https://ws.akamai-workshops.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "hackathon-chat", "messages": [{"role": "user", "content": "Say hello."}], "max_tokens": 50}'
```

```python
r = client.chat.completions.create(model="hackathon-chat",
        messages=[{"role": "user", "content": "Say hello."}], max_tokens=50)
print(r.choices[0].message.content)
```

Fields: `messages` (required), `max_tokens` (default 512, max 4096), `temperature`, `stream`, `response_format`, `tools`, `tool_choice`. Thinking: `extra_body={"chat_template_kwargs": {"enable_thinking": True}}`.

**Embeddings** `POST /v1/embeddings`

```bash
curl https://ws.akamai-workshops.com/v1/embeddings \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "hackathon-embedding", "input": ["first text", "second text"]}'
```

```python
r = client.embeddings.create(model="hackathon-embedding", input=["first text", "second text"])
vectors = [item.embedding for item in r.data]   # 1,024 floats each
```

Fields: `input` (required; one string or up to 16 strings).

**Images** `POST /v1/images/generations`

```bash
curl https://ws.akamai-workshops.com/v1/images/generations \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "hackathon-image", "prompt": "A yellow bicycle, simple icon", "size": "512x512", "response_format": "b64_json"}'
```

```python
import base64
r = client.images.generate(model="hackathon-image", prompt="A yellow bicycle, simple icon",
        size="512x512", response_format="b64_json")
open("out.png", "wb").write(base64.b64decode(r.data[0].b64_json))
```

Fields: `prompt` (required), `size` (`512x512`, `768x768`, `1024x1024`), `response_format` (`b64_json` only), `n` (always 1), `extra_body={"seed": 7}`.

## Labs

| Lab | What you build | Time |
|---|---|---|
| [0. Quickstart](notebooks/00_quickstart.ipynb) | All three endpoints on one page: URL, body, fields, minimal code. Start here. | 10 min |
| [1. Chat completions](notebooks/01_chat_completions.ipynb) | Streaming, conversations, output limits, long documents, thinking mode, quotas | 25 min |
| [2. Embeddings and retrieval](notebooks/02_embeddings_and_retrieval.ipynb) | Semantic search over your own notes, then grounded answers from the chat model | 20 min |
| [3. Image generation](notebooks/03_image_generation.ipynb) | Sizes, seeds, and handling the image quota | 15 min |
| [4. Tools and structured output](notebooks/04_tools_and_structured_output.ipynb) | JSON-schema replies, function calling, the tool loop | 25 min |

Start with the quickstart. Each lab opens with "The call in one look": the endpoint, a field table, and the minimal call, before anything else.

## Limits that apply to every team

| Limit | Value |
|---|---|
| Requests per minute, all endpoints combined | 60 |
| Chat tokens per minute, input plus output | 100,000 |
| Image requests per minute | 6 |
| Chat context window | 32,768 tokens, about 30,000 usable for input |
| Chat output | 512 tokens by default, 4,096 maximum |
| Embedding inputs per request | 16 |
| Image sizes | 512, 768, or 1,024 square, one image per request |

Exceeding a limit returns `429 Too Many Requests` with an `x-ratelimit-reset` header. Back off and retry; never retry in a tight loop.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `401 invalid credentials` | Wrong or missing key. Check `.env`, and check the printed key in the setup cell starts with `hk_`. |
| Key prints as `sk-...` | Your shell has an OpenAI key set. The notebooks override it; your own scripts should load `.env` with `override=True`. |
| `404` on `client.models.list()` | Only chat completions, embeddings, and image generation exist. Use the aliases above. |
| `422` on embeddings | More than 16 inputs in one request. Batch them. |
| `422` on images | Unsupported option. One square image, `b64_json` only. |
| `429` | A quota or a busy queue. Wait the number of seconds in `x-ratelimit-reset` or `Retry-After`. |
| Empty or truncated chat answer | Check `finish_reason`. `length` means raise `max_tokens`, up to 4,096. |

## Getting help

Organizers and mentors are in the venue and on the event Discord. Include the request ID from the response and the time when you report a problem; never paste your key.
