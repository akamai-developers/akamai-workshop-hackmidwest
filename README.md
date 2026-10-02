> [!IMPORTANT]
> ### $300 in free credit for Akamai Cloud
> Sign up with the HackMidwest link: **[http://login.linode.com/signup?promo=akm-dev-git-300-72326-P153](http://login.linode.com/signup?promo=akm-dev-git-300-72326-P153)**
>
> Do it the night before. The credit pays for everything in this kit, many times over.

# Akamai Cloud agent starter kit for HackMidwest

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)   --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

## Three ways to use this kit

Each path ends with a small AI agent running on your own Akamai Cloud account. Then you replace its tools and documents with your idea, as [Make it yours](agent/README.md#make-it-yours) shows.

| Path | Time | What you do |
|---|---|---|
| **Guided** | 45 minutes | Do the [pre-work](docs/00_prework.md) the night before. On the day, follow guides [01](docs/01_knowledge.md), [02](docs/02_memory.md), and [03](docs/03_body.md). You type each `linode-cli` command yourself and watch each resource appear in Cloud Manager, so you can create the same services for your own project. You finish with the agent on your Linode, using every service in the picture. |
| **Fast** | 30 minutes | Do the pre-work, then run [three scripts](#the-30-minute-path-and-rebuilding) that replay the guides' commands: Object Storage, a Linode, and a Cloud Firewall, without the managed database. |
| **Self-serve** | 15 minutes each | Optional modules: [Kubernetes on LKE](docs/04_lke.md), [Valkey reflexes](docs/05_valkey.md), and the five [inference notebooks](#brain-the-inference-notebooks). |

## Quick start

From the repository folder, steps 2 and 3 of the [pre-work](docs/00_prework.md) in one block:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
```

The last line makes `.env` only if you have none, so it never wipes keys you already pasted. In a new terminal, you only need `source .venv/bin/activate`. Paste your team key into `.env` with `nano .env`, then ask the agent something:

```bash
python -m agent --once "Say hello"
```

`python -m agent` without `--once` starts a chat in the terminal; type `exit` to quit. The agent prints one status line per role when it starts. Lines that say `fallback` or `off` are the Akamai services you have not connected yet.

## The challenge checklist

The Akamai challenge asks one question: does your project integrate Akamai Cloud services? The kit gives you these, and each one comes with a way to prove it.

| Akamai service | Role | What the agent does with it | Show the judges |
|---|---|---|---|
| Inference endpoint on Akamai Cloud GPUs | brain | Chat, tool calls, and embeddings | The `brain live` line at `/health` |
| Object Storage | knowledge | Reads your documents from a bucket | Cloud Manager, **Object Storage > Buckets**, or `linode-cli obj ls <bucket> --cluster us-sea-1` |
| Managed PostgreSQL with pgvector | memory | Keeps conversations, saved facts, and document vectors | Cloud Manager, **Databases**, or `linode-cli databases postgresql-list --label hackmidwest-db` |
| Linode | body | Runs the agent and Valkey in Docker on a public address | Cloud Manager, **Linodes**, and the chat page at `http://<ip>:8000` |
| Cloud Firewall | body | Lets in only SSH and the agent's port | Cloud Manager, **Firewalls** |
| LKE and a NodeBalancer (optional) | body | Runs the agent on Kubernetes behind a load balancer | Cloud Manager, **Kubernetes** and **NodeBalancers** |

The fastest proof is the agent itself: `http://<your Linode address>:8000/health` names the bucket, the database, and the Valkey it is using right now.

## Labs

| # | Guide | Adds | Minutes |
|---|---|---|---|
| 0 | [Pre-work: account, token, and tools](docs/00_prework.md) | Account with credit, `linode-cli`, `.env` | 15, the night before |
| 1 | [Knowledge in Object Storage](docs/01_knowledge.md) | A bucket, an access key, and documents the agent can search. Starts the database. | 15 |
| 2 | [Memory in Managed PostgreSQL](docs/02_memory.md) | pgvector, and conversations and facts that survive a restart | 10 |
| 3 | [The body on a Linode](docs/03_body.md) | A Linode, a Cloud Firewall, Docker, and Valkey | 20 |
| 4 | [Kubernetes on LKE (optional)](docs/04_lke.md) | An LKE cluster and a NodeBalancer | 15 |
| 5 | [Valkey reflexes (optional)](docs/05_valkey.md) | An embedding cache and a per-session rate limit | 15 |

Rehearsed on 2026-10-02 by pasting every command in the guides: from `git clone` to the agent answering on its Linode took about 15 minutes of commands and waiting. The database took 7.5 of those minutes to start and reach DNS; guide 01 starts it first, so it builds while you work. Reading and typing fill the rest of the 45. The three scripts of the 30-minute path took 3 minutes 40 seconds. [agent/README.md](agent/README.md) explains the code, and every link the guides rely on is in [docs/links.md](docs/links.md).

## The 30-minute path and rebuilding

The scripts in `scripts/` run the same commands as the guides. Use them for the fast path, or to rebuild after you have done the guides once. From the repository folder with the virtual environment active:

```bash
bash scripts/up.sh --no-db
python scripts/upload.py docs/sample/*.md
bash scripts/deploy_linode.sh
```

The first creates the bucket and its access key and writes them to `.env`. The second uploads the sample documents. The third creates the firewall and the Linode, installs Docker, starts the agent, and prints its address. To add the database later, do guide 01, step 1, then guide 02, then run `bash scripts/deploy_linode.sh` again so the Linode gets the new `.env`.

## What this kit is not

- **Not private.** Port 8000 on your Linode is open to anyone, with no login. Anyone who finds the address can chat with your agent, spend your team's inference quota, and read the facts it saved.
- **Not abuse-proof.** The rate limit counts messages per session id, and a client can make a new session id at any time.
- **Not production.** One Linode, one database node, and no backups of your own beyond what Managed Databases keeps.

Fine for a hackathon demo. Before you put real data in it, add a login in front of `/chat` and restrict the firewall.

## Cost and teardown

The guided stack costs about $0.05 an hour, or $1.19 a day, which the $300 credit covers many times over. [docs/costs.md](docs/costs.md) lists the price of every resource, read from the API with `linode-cli`.

Akamai bills a resource until you delete it, even when it is powered off. Each guide ends with the delete commands for what it created. To delete everything the kit made in one go:

```bash
bash scripts/down.sh
```

It finds each `hackmidwest-*` resource by its exact name, shows the list, and deletes them when you type `yes`. It never touches anything else on your account. Two things stay: Object Storage itself keeps billing $5 a month until you cancel it in Cloud Manager, because cancelling deletes every bucket on the account; and the access key that `linode-cli obj` made for itself, named `linode-cli-<you>@<computer>-<number>`, stays under **Object Storage > Access Keys** until you revoke it there.

## Brain: the inference notebooks

The brain is one HTTPS endpoint, compatible with the OpenAI API, running on Akamai Cloud GPUs. Five Jupyter notebooks teach it. They run on your laptop against the shared endpoint. No GPU, no cloud account, and no model downloads on your side.

| Capability | Model alias | Backing model |
|---|---|---|
| Chat completions | `hackathon-chat` | Qwen3.8-27B (FP8) on vLLM |
| Embeddings | `hackathon-embedding` | Qwen3-Embedding-0.6B on Text Embeddings Inference |
| Image generation | `hackathon-image` | FLUX.2 klein 4B |

Because it speaks the OpenAI API, the official `openai` package and most frameworks (LangChain, LlamaIndex, Strands, and others) work by changing two settings: the base URL and the API key.

| Lab | What you build | Time |
|---|---|---|
| [0. Quickstart](notebooks/00_quickstart.ipynb) | All three endpoints on one page: URL, body, fields, minimal code. Start here. | 10 min |
| [1. Chat completions](notebooks/01_chat_completions.ipynb) | Streaming, conversations, output limits, long documents, thinking mode, quotas | 25 min |
| [2. Embeddings and retrieval](notebooks/02_embeddings_and_retrieval.ipynb) | Semantic search over your own notes, then grounded answers from the chat model | 20 min |
| [3. Image generation](notebooks/03_image_generation.ipynb) | Sizes, seeds, and handling the image quota | 15 min |
| [4. Tools and structured output](notebooks/04_tools_and_structured_output.ipynb) | JSON-schema replies, function calling, the tool loop | 25 min |

Each notebook opens with "The call in one look": the endpoint, a field table, and the minimal call. With the virtual environment from the quick start active, open them with:

```bash
jupyter notebook notebooks/
```

The notebooks read `OPENAI_BASE_URL` and `OPENAI_API_KEY` from `.env`. Any script you write can use the same two variables:

```python
from openai import OpenAI
client = OpenAI()  # reads OPENAI_BASE_URL and OPENAI_API_KEY from the environment
```

Your team key is shared by every member and every script. Treat it like a password: keep it in a backend or in `.env`, never in frontend code or a public repository.

### Quick reference

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

### Limits that apply to every team

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

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `401 invalid credentials` | Wrong or missing key. Check `.env`, and check the printed key in the setup cell starts with `hk_`. |
| Key prints as `sk-...` | Your shell has an OpenAI key set. The notebooks and the agent override it from `.env`; your own scripts should load `.env` with `override=True`. |
| `404` on `client.models.list()` | Only chat completions, embeddings, and image generation exist. Use the aliases above. |
| `422` on embeddings | More than 16 inputs in one request. Batch them. |
| `422` on images | Unsupported option. One square image, `b64_json` only. |
| `429` | A quota or a busy queue. Wait the number of seconds in `x-ratelimit-reset` or `Retry-After`. |
| Empty or truncated chat answer | Check `finish_reason`. `length` means raise `max_tokens`, up to 4,096. |

## Getting help

Organizers and mentors are in the venue and on the event Discord. Include the request ID from the response and the time when you report a problem; never paste your key or your Akamai token.
