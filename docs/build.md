# Build your project

[Workshop home](../README.md) · [Cloud essentials](cloud.md) · [Inference reference](inference.md)

Start with one user action and one useful result. Select a model capability, then choose the cloud component that supports that behavior.

## Choose a path

| Project | Model capability | First cloud component | Follow these materials | Working result |
|---|---|---|---|---|
| Document assistant | Chat and embeddings | Object Storage | [Retrieval notebook](../notebooks/02_embeddings_and_retrieval.ipynb), [storage lab](01_knowledge.md) | Answer a question from an uploaded document and name the source |
| Image generator | Image generation | Object Storage | [Image notebook](../notebooks/03_image_generation.ipynb), [storage lab](01_knowledge.md) | Generate a PNG and retrieve it from a bucket |
| Task or workflow assistant | Tool calling and JSON | Linode | [Tools notebook](../notebooks/04_tools_and_structured_output.ipynb), [runtime lab](03_body.md) | Run a defined application function and return its result |
| Assistant with history | Chat | Managed PostgreSQL | [Chat notebook](../notebooks/01_chat_completions.ipynb), [database lab](02_memory.md) | Reload a conversation after the application restarts |
| Containerized API or worker | Any supported operation | LKE | [Quickstart](../notebooks/00_quickstart.ipynb), [LKE lab](04_lke.md) | Send a request through the deployed service |

The standalone notebooks keep their data in the notebook process or local files. The cloud labs show how to move those responsibilities into a deployed application. A database or bucket can be used from an app hosted elsewhere.

## Adapt the starter

1. Run the [local setup](00_prework.md) and ask a sample document question.
2. Choose [Object Storage](01_knowledge.md), [PostgreSQL](02_memory.md), [Linode](03_body.md), or [LKE](04_lke.md). Each lab states what it creates.
3. Replace the fictional documents and update the prompt and tool description using [Make it yours](../agent/README.md#make-it-yours).
4. Add one function or route using the [code guide](../agent/README.md).
5. Check a normal request, a question with no answer in the data, and a request that should fail cleanly.

## Connect an existing app

Use the [inference reference](inference.md) for the endpoint and request shapes. Keep the team key on your server. For Object Storage, the storage lab includes an SDK connection example. For PostgreSQL, use the connection details and TLS settings from the database lab, then apply your own schema.

The supplied scripts deploy the included Python starter and use fixed labels such as `hackmidwest-agent`. Read them before adapting them to an existing application or account. They are not a general deployment system.

## Prepare your demo

Show a single request from input to result. Then identify the cloud resource supporting it.

| Integration | Show the resource | Show the application using it |
|---|---|---|
| Object Storage | Bucket and object in Cloud Manager | Upload and retrieve a file, or answer from it |
| PostgreSQL | Database instance in Cloud Manager | Save a record, restart, and read it again |
| Linode | VM in Cloud Manager | A request to the application running on that VM |
| LKE | Cluster, Deployment, and Service | A request through the service address |
| Shared inference service | Configured endpoint and alias, with key hidden | A successful response and the feature it supports |

`/health` is useful diagnostic context, but it is not sufficient proof of every integration. Show a real operation. Ask the organizers about official eligibility and submission requirements, including whether shared inference alone counts.

## Finish the project handoff

Record setup steps, environment variable names, and a sample request in your project README. Include the Akamai services used and a simple architecture diagram. Keep keys out of code, screenshots, and notebook outputs. Assign one teammate to [review costs and remove resources](costs.md) after the event.
