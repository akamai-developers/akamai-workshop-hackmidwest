# The 30-minute workshop

[Workshop home](../README.md) · [Setup](00_prework.md) · [Instructor guide](instructor.md)

**Outcome:** make a model request, explain how an application uses documents to answer a question, and select an Akamai Cloud component for your project.

Complete setup before the session. If you are still installing tools, follow the demonstration and work with a teammate. No cloud provisioning is required for the core session.

## 0–3 minutes: Define the application

Our example is a document assistant. A user asks a question; the application finds relevant text and asks a model to answer from it.

The challenge is to build an AI application with a component in Akamai Cloud. You can use your own application or adapt this starter. You do not need every service in the example.

## 3–8 minutes: Place the components

Open [Akamai Cloud essentials](cloud.md). Follow the request diagram, then compare:

- Linode and LKE: two places to run application code.
- Object Storage and Block Storage: objects accessed through an API versus a disk attached to compute.
- PostgreSQL and Valkey: durable application records versus temporary cached values.
- Application runtime and inference: your application calls the model over HTTPS.

**Checkpoint:** choose a place to store an uploaded document and a place to run the code that reads it.

## 8–14 minutes: Make a model request

Open [notebook 00](../notebooks/00_quickstart.ipynb). Run **Step 1: Set up your environment**, then the code under **Step 3: Chat**. The raw HTTP example in Step 2 is optional.

Change the user message to a question your project would answer. Run the cell again. Identify the model alias, the messages you sent, the returned answer, and `finish_reason`.

**Checkpoint:** you received a nonempty answer. If the request fails, use [inference troubleshooting](troubleshooting.md#inference).

The embedding and image cells are references for later. Do not run the whole notebook during this segment. Its final validation checks all three operations.

## 14–22 minutes: Answer from a document

The instructor demonstrates a prepared starter connected to Object Storage. Participants can run the local version:

```bash
python -m agent --once "Where can I park?"
```

Look for `search_docs` in the tool log and a reference to `parking.md` in the answer. These are fictional examples, not actual venue directions.

Follow the data:

1. The file lives in a local folder or an Object Storage bucket.
2. Application code splits the text into chunks and requests embeddings.
3. A query embedding is compared with stored document vectors.
4. Retrieved text is sent to the chat model, which writes the answer.

A local run with empty `OBJ_*` settings demonstrates the application logic. The instructor's bucket demonstration shows the cloud integration. Open [notebook 02](../notebooks/02_embeddings_and_retrieval.ipynb) after the session to implement the retrieval steps yourself.

**Checkpoint:** point to the source file and explain why storing a file and searching its meaning are separate operations.

## 22–27 minutes: Choose your implementation

Use [Build your project](build.md) to select one path. Write down:

- What the user provides and what the application returns.
- Which model capability you need.
- Which Akamai Cloud component you will use and what it stores or runs.
- What you will demonstrate to show it is working.

Example: “Upload a club handbook, ask a question, and return an answer with a source. Store the handbook in Object Storage and run the API on a Linode.”

## 27–30 minutes: Verify and continue

Open the lab for your chosen component. Confirm its prerequisites and expected result. Bookmark the [inference reference](inference.md), [troubleshooting](troubleshooting.md), and [cleanup guide](costs.md).

For a 30-minute session, continue independently during the hackathon. For a 60-minute session, proceed below.

## 30–60 minutes: Build session

Use one account per team for the supplied deployment scripts. They use fixed resource labels and should not be run concurrently by teammates against the same account.

| Time | Work | Checkpoint |
|---|---|---|
| 30–35 | Confirm activated account, CLI token, team key, SSH key, and costs | Local model request succeeds |
| 35–48 | Deploy the starter with Object Storage and a Linode | Bucket contains sample files; VM appears in Cloud Manager |
| 48–55 | Ask the deployed app a document question and inspect the service status | Answer uses the source document |
| 55–60 | Replace a document or plan your next component; review teardown | A specific next task and a resource owner |

From the workshop directory with the virtual environment active:

```bash
bash scripts/up.sh --no-db
python scripts/upload.py docs/sample/*.md
bash scripts/deploy_linode.sh
```

The first command creates a bucket and key; the second uploads the fictional documents; the third creates a VM and firewall, installs Docker, and starts the application. It prints the application address. This path does not create PostgreSQL. Inspect the [Linode lab](03_body.md) for the deployment behavior and public access details.

If your team already has an application, use the [Object Storage lab](01_knowledge.md) or [PostgreSQL lab](02_memory.md) to integrate one service instead. Database and LKE provisioning are independent hackathon labs, not requirements for finishing this session.

**Success:** a deployed app answers from a file in your bucket, or your existing app has completed a real operation against the selected Akamai Cloud service. If provisioning is still underway, complete the integration locally and use its lab to finish after the session.
