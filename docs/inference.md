# Workshop inference reference

[Workshop home](../README.md) · [Notebooks](../notebooks/README.md) · [Troubleshooting](troubleshooting.md#inference)

The workshop provides a shared inference service hosted on Akamai Cloud. It supports selected OpenAI-compatible operations through one base URL and a team key. This is the event's service configuration, not a specification for every Akamai or OpenAI service.

The values below come from the supplied workshop materials. The instructor should confirm them against the live deployment before the event. Backing models, quotas, and availability can change without requiring a different application architecture.

## Connection

```ini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=paste_your_team_key_here
```

From the workshop directory, load `.env` explicitly. The OpenAI client reads environment variables but does not load `.env` itself.

```python
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env", override=True)
client = OpenAI(timeout=60.0)
```

`override=True` selects the workshop settings even when your shell has another provider's key. Every HTTP request uses `Authorization: Bearer <team-key>` and a JSON body. Keep the key on the backend.

## Operations

| Capability | HTTP path | Alias | Response |
|---|---|---|---|
| Chat and tool calls | `POST /v1/chat/completions` | `hackathon-chat` | `choices[0].message` |
| Text embeddings | `POST /v1/embeddings` | `hackathon-embedding` | `data[i].embedding` |
| Image generation | `POST /v1/images/generations` | `hackathon-image` | `data[0].b64_json` |

Use these aliases rather than guessing a backing model name. The supplied deployment does not expose model listing, the Responses API, audio, image editing, or image input to chat. Check required operations before selecting a framework integration.

## Chat

```python
response = client.chat.completions.create(
    model="hackathon-chat",
    messages=[{"role": "user", "content": "Explain Object Storage in two sentences."}],
    max_tokens=150,
)
print(response.choices[0].message.content)
print(response.choices[0].finish_reason)
```

`messages` carries the conversation. Your application stores history and resends the relevant messages. Use `stream=True` for incremental output. Check `finish_reason`: `length` indicates an incomplete response, while `tool_calls` requests application functions.

For structured results, pass a JSON schema in `response_format` and validate the result. For tool use, pass function definitions in `tools`, validate the returned arguments, execute an allowed function, and send its result back. [Notebook 04](../notebooks/04_tools_and_structured_output.ipynb) demonstrates both.

The deployment's optional thinking mode uses `extra_body={"chat_template_kwargs": {"enable_thinking": True}}`. It consumes output budget and can add latency. Leave it off for the live quickstart.

## Embeddings

```python
response = client.embeddings.create(
    model="hackathon-embedding",
    input=["A document paragraph", "A second paragraph"],
)
vectors = [item.embedding for item in response.data]
print(len(vectors), len(vectors[0]))
```

The workshop configuration returns 1,024 dimensions. Use the same embedding model for documents and queries; re-embed when you change it. [Notebook 02](../notebooks/02_embeddings_and_retrieval.ipynb) uses NumPy for a small in-memory search. The [database lab](02_memory.md) stores vectors in PostgreSQL.

## Images

```python
import base64
from pathlib import Path

response = client.images.generate(
    model="hackathon-image",
    prompt="A yellow bicycle, simple illustration on a white background",
    size="512x512",
    response_format="b64_json",
)
Path("generated.png").write_bytes(base64.b64decode(response.data[0].b64_json))
```

The service returns one PNG per request. Supported square sizes are `512x512`, `768x768`, and `1024x1024`. Pass a seed with `extra_body={"seed": 7}` when comparing prompts under the same deployment configuration. See [notebook 03](../notebooks/03_image_generation.ipynb).

## Deployment limits to confirm

| Limit | Value in the supplied materials |
|---|---|
| Requests per team, all endpoints combined | 60 per minute |
| Chat input and output tokens per team | 100,000 per minute |
| Image requests per team | 6 per minute |
| Chat context, input plus output | 32,768 tokens |
| Chat output | 512 tokens by default; 4,096 maximum |
| Embedding inputs | Up to 16 strings per request |
| Embedding token budget | 8,192 total tokens per request; chunk long text before sending |
| Image prompt | Up to 2,000 characters |
| Image count and response format | `n=1`, `b64_json` |

A key is shared across the team, so notebooks and applications consume the same quota. For `429`, respect the service's retry headers and use bounded retries. In these workshop examples, `x-ratelimit-reset` represents a delay in seconds; that convention is specific to this service. See the notebooks for retry handlers.
