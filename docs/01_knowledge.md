# Guide 01: Knowledge in Object Storage

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)  --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

This guide adds **knowledge**: an Object Storage bucket that holds the documents your agent answers from. It also starts **memory**, the PostgreSQL database, because the database takes the longest to create and guide 02 needs it.

## Overview

Right now the agent knows only what the model learned in training. Ask it where to park at your venue and it has nothing to go on. In this guide you give it documents.

Object Storage is Akamai's S3-compatible file storage. You put files in a bucket, and any program with an access key can read them over HTTPS. The agent lists your bucket, cuts each text file into chunks of about 500 words, turns each chunk into a vector of 1,024 numbers with the embedding model, and searches those vectors by meaning when you ask a question.

You create three things by hand with `linode-cli`: the database, the bucket, and an access key that can reach only that bucket. Then you watch the agent fail on an empty bucket, upload a file, and watch it answer.

## Learning objectives

By the end of this guide you will be able to:

- Start a Managed PostgreSQL database with an IP allow list
- Create an Object Storage bucket in Seattle
- Create an access key limited to one bucket, and know why the agent should not get more
- Connect the agent to the bucket through `.env`
- Upload a document and see the agent answer from it
- Find the 30 lines of `agent/knowledge.py` you would change for your own data

## Prerequisites

- [Pre-work](00_prework.md) done: `linode-cli` configured, the virtual environment active, and `python -m agent --once "Say hello"` answering
- About 15 minutes

## Step 1: Start the database

The database is for guide 02, but it takes the longest to be ready, so you start it first and let it build while you work. A Managed Database only accepts connections from addresses on its allow list. Find your laptop's public IP address:

```bash
MY_IP=$(curl -s https://api.ipify.org)
echo $MY_IP
```

```
203.0.113.25
```

Now create the database. This is one PostgreSQL 17 server in Seattle on the smallest plan.

```bash
linode-cli databases postgresql-create \
  --label hackmidwest-db \
  --region us-sea \
  --type g6-nanode-1 \
  --engine postgresql/17 \
  --cluster_size 1 \
  --allow_list "$MY_IP/32"
```

The fields that matter: `--type g6-nanode-1` is the smallest plan, 1 GB of memory for $0.024 an hour. `--cluster_size 1` means one node; 3 would add two standbys for high availability. `--allow_list` takes addresses in CIDR form, and `/32` means exactly one address. An empty allow list would block every connection.

```
┌────────┬────────────────┬────────┬─────────────┬──────────────┬────────────┬─────────┬───────────────┬──────────────┐
│ id     │ label          │ region │ type        │ cluster_size │ engine     │ version │ platform      │ status       │
├────────┼────────────────┼────────┼─────────────┼──────────────┼────────────┼─────────┼───────────────┼──────────────┤
│ 533120 │ hackmidwest-db │ us-sea │ g6-nanode-1 │ 1            │ postgresql │ 17      │ rdbms-default │ provisioning │
└────────┴────────────────┴────────┴─────────────┴──────────────┴────────────┴─────────┴───────────────┴──────────────┘
```

Note the `id`. In Cloud Manager, open **Databases**: `hackmidwest-db` is there with the status Provisioning. Do not wait for it. Move on.

> NOTE: On venue Wi-Fi, everyone shares one public address, so the allow list admits the whole venue network. The database still requires your password and TLS. Guide 03 adds your Linode's address to the list.

## Step 2: Create the bucket

Bucket names are shared by every Akamai customer in a region, so yours needs something unique after `hackmidwest-`. Make a random suffix and keep the name in a variable:

```bash
BUCKET=hackmidwest-$(openssl rand -hex 4)
echo $BUCKET
```

```
hackmidwest-e02dabda
```

Create the bucket in the Seattle cluster, `us-sea-1`:

```bash
linode-cli obj mb $BUCKET --cluster us-sea-1
```

```
Bucket hackmidwest-e02dabda created
```

`linode-cli obj` is the CLI's Object Storage plugin. It talks to the bucket over the S3 API, so it needs an access key of its own. The first time you run it, it creates one named `linode-cli-<you>@<computer>-<number>` and saves it in the CLI's config file. You will see that key in Cloud Manager next to the one you make in step 3.

In Cloud Manager, open **Object Storage > Buckets**. Your bucket is listed in Seattle.

## Step 3: Create an access key for the agent

The agent needs its own key. Give it one that can read and write this bucket and nothing else, so a leaked `.env` exposes one bucket instead of your whole account.

```bash
linode-cli object-storage keys-create \
  --label hackmidwest-key \
  --bucket_access "[{\"region\": \"us-sea\", \"bucket_name\": \"$BUCKET\", \"permissions\": \"read_write\"}]" \
  --text --format id,access_key,secret_key
```

`--bucket_access` lists the buckets the key may touch: one bucket in `us-sea`, with `read_write` permission. `--text` prints plain columns, so a narrow terminal cannot cut off the secret.

```
id	access_key	secret_key
6635050	ABCDEFGHIJKLMNOPQRST	abcdefghijklmnopqrstuvwxyzABCDEFGHIJ0123
```

Copy all three values now. The secret key is shown once; afterwards Cloud Manager and the CLI show it as `[REDACTED]`. In Cloud Manager, open **Object Storage > Access Keys**: `hackmidwest-key` shows as limited to your bucket.

## Step 4: Point the agent at the bucket

The agent reaches the bucket through an S3 endpoint. Each region has one; ask for Seattle's:

```bash
linode-cli object-storage endpoints --text --format region,endpoint_type,s3_endpoint | grep us-sea
```

```
us-sea	E1	us-sea-1.linodeobjects.com
```

Open `.env` and fill in the knowledge block with your values:

```bash
OBJ_ENDPOINT=https://us-sea-1.linodeobjects.com
OBJ_BUCKET=hackmidwest-e02dabda
OBJ_ACCESS_KEY=ABCDEFGHIJKLMNOPQRST
OBJ_SECRET_KEY=abcdefghijklmnopqrstuvwxyzABCDEFGHIJ0123
OBJ_KEY_ID=6635050
```

`OBJ_KEY_ID` is not used by the agent. It lets `scripts/down.sh` find and revoke this key later.

## Step 5: Ask a question the bucket cannot answer yet

Ask about parking. The bucket is empty, so watch what happens:

```bash
python -m agent --once "Where can I park?"
```

```
brain      live      hackathon-chat at https://ws.akamai-workshops.com/v1
knowledge  live      bucket hackmidwest-e02dabda at us-sea-1.linodeobjects.com
memory     fallback  kept in this process only, forgotten on restart. Set DATABASE_URL in .env.
reflexes   off       no cache and no rate limit. Set VALKEY_URL to turn them on.
  [tool] search_docs({"query": "parking options for attendees"})
I don't have parking details in the team documents yet. I'd suggest checking the HackMidwest website or venue page for parking info.
```

The `knowledge` line says `live`: the agent found your bucket. It called `search_docs`, got nothing back, and said so. Without documents, the best a model can do is send you somewhere else, and a careless one invents an answer.

## Step 6: Upload a document and ask again

`scripts/upload.py` puts a file in the bucket and indexes it: it chunks the text, embeds the chunks, and stores the vectors in memory.

```bash
python scripts/upload.py docs/sample/parking.md
```

```
Uploaded docs/sample/parking.md to hackmidwest-e02dabda/parking.md and indexed 1 chunk(s).
No database, so these vectors were not kept. The running agent indexes new files on its next question.
```

The file is in your bucket now:

```bash
linode-cli obj ls $BUCKET --cluster us-sea-1
```

```
2026-10-02 01:15  1260  parking.md
```

Ask again. The four status lines are the same as in step 5, so they are left out here:

```bash
python -m agent --once "Where can I park?"
```

```
  [tool] search_docs({"query": "parking options for attendees"})
Park in Lot C, the gravel lot on the north side of the building next to the loading dock. It's free all weekend if you're wearing a hackathon badge, and it stays open overnight.

Lot A in front of the main entrance is reserved for sponsors and judges, and cars without a sponsor pass get towed after 10 PM.

Street parking on Example Avenue is free after 6 PM Friday and all day Saturday and Sunday.

This is from parking.md.
```

Same question, same model. The difference is one file in your bucket. Upload the other two sample files so the agent knows the schedule and the rules:

```bash
python scripts/upload.py docs/sample/schedule.md docs/sample/rules.md
```

## Step 7: Read the code you just used

Open `agent/knowledge.py`. This is the part that turns a bucket into answers:

```python
class Knowledge:
    def sync(self) -> int:
        """Index files that are new or changed, forget files that are gone. Returns chunks written."""
        files = self.source.files()
        indexed = self.memory.document_keys()
        written = 0
        for key, version in files.items():
            if key not in indexed or self.versions.get(key, version) != version:
                written += self.index(key)
            self.versions[key] = version
        for key in indexed - files.keys():
            self.memory.delete_document(key)
        return written

    def index(self, key: str) -> int:
        """Read one file, chunk it, embed the chunks, and store them. Returns the chunk count."""
        chunks = chunk(self.source.read(key))
        vectors = self.embed([f"{key}\n{text}" for text in chunks])  # the file name helps the match
        self.memory.replace_document(key, chunks, vectors)
        return len(chunks)

    def search(self, query: str, k: int = 3) -> list[Hit]:
        self.sync()  # one list request, so files uploaded a moment ago are searchable
        return self.memory.search(self.embed.one(query), k)
```

`sync()` lists the bucket and compares each file's ETag, which changes when the file does, with what it indexed before. New and changed files get indexed. Deleted files are forgotten. `search()` calls `sync()` first, which is why the running agent picks up files you upload while it runs. `index()` stores the vectors through memory. Until guide 02 that memory is a Python list, so the agent re-indexes everything each time it starts.

To use your own data, change these:

- `TEXT_FILES` at the top of the file lists the extensions the agent reads: `.md` and `.txt`. For PDFs, extract the text in `Bucket.read()` with a library such as `pypdf`.
- `CHUNK_WORDS` sets the chunk size. Smaller chunks give more precise matches and less context per match.
- `Bucket` reads through boto3, the AWS SDK for Python. Any S3 code you find works against Akamai Object Storage with the endpoint URL from step 4.

## Validation

- `linode-cli obj ls $BUCKET --cluster us-sea-1` lists `parking.md`, `rules.md`, and `schedule.md`.
- `python -m agent --once "When does judging start?"` calls `search_docs` and names `schedule.md`.
- The startup line reads `knowledge  live  bucket hackmidwest-... at us-sea-1.linodeobjects.com`.

**Show the judges:** Cloud Manager, **Object Storage > Buckets**, then your bucket and its files. From the terminal, `linode-cli obj ls hackmidwest-e02dabda --cluster us-sea-1` lists the files the agent answers from, and **Access Keys** shows the agent's key limited to that bucket.

## Clean up

Going on to guide 02? Keep everything. The database is still building.

To delete what this guide created, use the bucket name and the ids from steps 1 to 3:

```bash
linode-cli obj rb $BUCKET --recursive --cluster us-sea-1    # the bucket and every file in it
linode-cli object-storage keys-delete 6635050               # the agent's access key
linode-cli databases postgresql-delete 533120               # the database
```

Then empty the `OBJ_*` lines in `.env`. In Cloud Manager, check **Object Storage > Buckets**, **Object Storage > Access Keys**, and **Databases**.

Left running, the database costs $0.024 an hour. Object Storage costs $5 a month for your account until you cancel it, even with no buckets; see [costs.md](costs.md).

`scripts/down.sh` deletes everything the kit created after you confirm. `scripts/up.sh` runs steps 1 to 4 for you when you rebuild: these are the same commands you just typed, in one file.

## Next steps

When the database is active, go to [Guide 02: Memory in Managed PostgreSQL](02_memory.md). To check on it now:

```bash
linode-cli databases postgresql-list --label hackmidwest-db --format id,label,status
```
