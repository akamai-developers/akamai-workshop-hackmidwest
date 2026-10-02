# Inference notebooks

[Workshop home](../README.md) · [Setup](../docs/00_prework.md) · [API reference](../docs/inference.md)

Use the shared workshop endpoint from Python. You need a team inference key, but no GPU or cloud account to run these notebooks.

From the workshop directory:

```bash
source .venv/bin/activate
jupyter notebook notebooks/
```

| Notebook | Use it for | Suggested time | Connect it to Akamai Cloud |
|---|---|---|---|
| [00: Quickstart](00_quickstart.ipynb) | One request to each endpoint | 10 minutes | Choose a component in the [project guide](../docs/build.md) |
| [01: Chat](01_chat_completions.ipynb) | Streaming, conversation history, output limits | 25 minutes | [Run the backend](../docs/03_body.md); [store history](../docs/02_memory.md) |
| [02: Retrieval](02_embeddings_and_retrieval.ipynb) | Embed text, rank documents, answer from sources | 20 minutes | [Store files](../docs/01_knowledge.md); [persist vectors](../docs/02_memory.md) |
| [03: Images](03_image_generation.ipynb) | Generate a PNG, choose size, handle quotas | 15 minutes | [Save images in a bucket](../docs/01_knowledge.md#4-use-the-bucket-from-your-own-app) |
| [04: Tools and JSON](04_tools_and_structured_output.ipynb) | Function calls and structured responses | 25 minutes | [Run your application](../docs/03_body.md) or use [LKE](../docs/04_lke.md) |

For the live 30-minute session, run only notebook 00's setup and chat cells. The other notebooks are independent capability labs after setup; you do not need to finish them in numerical order. Within a chosen notebook, run cells from top to bottom unless its instructions say otherwise.

The event facts in the examples are fictional. Model aliases and quotas describe the workshop deployment and may change; use the organizer-confirmed settings in the [API reference](../docs/inference.md). Clear cell outputs before sharing a notebook.
