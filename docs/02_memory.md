# Lab: Keep application data in Managed PostgreSQL

[Workshop home](../README.md) · [Project paths](build.md) · [Retrieval notebook](../notebooks/02_embeddings_and_retrieval.ipynb)

**Result:** conversation messages and document vectors remain available after the application restarts.

**Prerequisites:** [setup](00_prework.md), activated account, database permissions, working inference key. Object Storage is optional; local sample files also work. Allow about 20–30 minutes including provisioning, which can vary. This lab creates a billable database.

PostgreSQL stores records and supports SQL queries. The starter also uses pgvector for embedding similarity search. You manage the schema and application access; Akamai's managed service operates the database infrastructure.

## 1. Create the database

Find your public IPv4 address and check it before using it in the allow list:

```bash
MY_IP=$(curl -fsS https://api.ipify.org)
printf '%s\n' "$MY_IP"
linode-cli databases postgresql-create \
  --label hackmidwest-db \
  --region us-sea \
  --type g6-nanode-1 \
  --engine postgresql/17 \
  --cluster_size 1 \
  --allow_list "$MY_IP/32" \
  --format id,label,region,type,status
```

If `hackmidwest-db` already exists for your team, inspect it and reuse it instead of creating another. Verify the plan and engine are available in your account before creating the resource. This example uses one node and does not provide standby-node redundancy.

The `/32` permits one IPv4 address. On venue Wi-Fi, many participants may share that public address; the database still requires credentials. Do not use an allow list of all addresses to work around a connection issue.

## 2. Wait and configure the connection

```bash
linode-cli databases postgresql-list --label hackmidwest-db --format id,label,status
bash scripts/status.sh
```

The script waits for `active` status and DNS resolution, retrieves connection details, percent-encodes the password, and writes `DATABASE_URL` to `.env`. It does not print the password. If the database remains provisioning, check Cloud Manager; you can interrupt the wait and return later.

For your own application, the connection string has this shape:

```ini
DATABASE_URL=postgresql://akmadmin:<encoded-password>@<host>:<port>/defaultdb?sslmode=require
```

Use the actual host and port returned by the service. `sslmode=require` encrypts the connection; use the supplied CA certificate and `verify-full` when configuring certificate verification. For an application beyond this exercise, create a dedicated database and a user with only the permissions it needs.

## 3. Create the starter schema

```bash
python scripts/db_init.py
```

Expected result: PostgreSQL and pgvector versions, and the `documents`, `messages`, and `sessions` tables. The script applies files in [agent/sql](../agent/sql) in filename order. The existing schema can be applied again.

The `documents.embedding` column is `vector(1024)`, matching this workshop's embedding configuration. Use the same embedding model for documents and queries. Changing models requires re-embedding the stored text, even when vector dimensions match.

For an existing app, apply your own schema instead of the starter's. A standard SQL use case does not require embeddings or pgvector.

## 4. Verify persistence

Run these as separate processes:

```bash
python -m agent --session demo-save --once "Remember that our demo slot is 2:15 PM."
python -m agent --session demo-read --once "When is our demo slot?"
```

Check that the first request calls `remember`, the second calls `recall`, and the startup status reports PostgreSQL rather than process memory. The second request should retrieve the saved time.

The demo's saved notes are shared across sessions. Session IDs organize conversation history but do not provide authentication or private access to notes. Use fictional facts.

## 5. Maintain the allow list

### When your address changes

A timeout often means your current network address is not allowed. Inspect the existing entries first:

```bash
DB_ID=$(linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id)
linode-cli databases postgresql-view "$DB_ID" --format allow_list
```

Use **Databases > your database > Networking** in Cloud Manager to add your current address while retaining other required entries. A CLI `postgresql-update --allow_list` replaces the full list; include every address you intend to retain.

The supplied Linode and LKE deployment scripts add their compute address while retaining existing entries. After a change has taken effect, restart the application if it previously fell back to process memory. Data written to process memory is not automatically migrated into PostgreSQL.

## Inspect the implementation

[agent/memory.py](../agent/memory.py) stores conversation messages, text chunks, and saved notes. The search query orders rows by pgvector cosine distance using `<=>`. The application sends recent messages with each model request; the inference API does not keep the conversation for it. Message count alone does not guarantee that a request fits the model's token limit.

## Verify and clean up

Show the database in Cloud Manager and retrieve a value written by an earlier application process. If you continue to a runtime lab, keep the database. Otherwise use the reviewed resource list in [cleanup](costs.md). Deleting the database removes its data.

Next: [Linode](03_body.md), [LKE](04_lke.md), or [your own application](build.md).
