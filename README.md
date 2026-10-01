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
- About one hour for all three labs

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

## Labs

| Lab | What you build | Time |
|---|---|---|
| [1. Chat completions](notebooks/01_chat_completions.ipynb) | First request, streaming, conversations, output limits, long documents, thinking mode, quotas | 25 min |
| [2. Embeddings and retrieval](notebooks/02_embeddings_and_retrieval.ipynb) | Semantic search over your own notes, then grounded answers from the chat model | 20 min |
| [3. Image generation](notebooks/03_image_generation.ipynb) | Sizes, seeds, and handling the image quota | 15 min |

Do them in order. Lab 1 sets up the client the other two reuse.

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
