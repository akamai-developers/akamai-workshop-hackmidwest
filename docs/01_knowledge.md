# Lab: Store documents in Object Storage

[Workshop home](../README.md) · [Project paths](build.md) · [Retrieval notebook](../notebooks/02_embeddings_and_retrieval.ipynb)

**Result:** a private bucket holds your source documents, and the starter answers a question from one of them.

**Prerequisites:** [setup](00_prework.md), activated account, configured CLI, working inference key. Allow about 15 minutes for the exercise, plus account or service delays. This lab creates a billable bucket and an access key. It does not require a database or a VM.

Object Storage stores files through an S3-compatible API. The application reads text, creates embeddings, and searches the resulting vectors. With no database configured, the starter keeps those vectors in process memory.

## 1. Create a bucket

Use a unique name in the workshop's Seattle cluster:

```bash
BUCKET=hackmidwest-$(openssl rand -hex 4)
linode-cli obj regenerate-keys
linode-cli obj mb "$BUCKET" --cluster us-sea-1
```

Open **Object Storage > Buckets** in Cloud Manager and find the bucket. `linode-cli obj` may create its own access key for CLI operations. The application gets a separate key below.

## 2. Create a bucket-scoped key

```bash
linode-cli object-storage keys-create \
  --label hackmidwest-key \
  --bucket_access "[{\"region\": \"us-sea\", \"bucket_name\": \"$BUCKET\", \"permissions\": \"read_write\"}]" \
  --text --format id,access_key,secret_key
```

Save the returned values directly in `.env`. The secret is shown at creation; do not screen-share this output. The upload script needs write access. An application that only reads files can use a separate read-only key.

Find the endpoint:

```bash
linode-cli object-storage endpoints --text --format region,endpoint_type,s3_endpoint
```

Use the endpoint for your bucket. The workshop configuration is:

```ini
OBJ_ENDPOINT=https://us-sea-1.linodeobjects.com
OBJ_BUCKET=your-bucket-name
OBJ_ACCESS_KEY=your-access-key
OBJ_SECRET_KEY=your-secret-key
OBJ_KEY_ID=your-key-id
```

`OBJ_KEY_ID` is for cleanup, not application requests. If the workshop endpoint is unavailable to your account, select an available endpoint in Cloud Manager and update your configuration and commands consistently.

## 3. Upload and query

```bash
python scripts/upload.py docs/sample/*.md
linode-cli obj ls "$BUCKET" --cluster us-sea-1
python -m agent --once "Where can I park?"
```

Expect three files, a `search_docs` tool call, and an answer supported by `parking.md`. The sample files contain fictional event details. Check facts and source names rather than expecting identical model wording.

The upload script also indexes text. Without PostgreSQL, those vectors disappear when the script exits; the agent indexes the files in its own process when needed. Connect [PostgreSQL](02_memory.md) to retain vectors across restarts.

## 4. Use the bucket from your own app

This connection uses the same environment variables as the starter. Run it from the workshop directory after filling in `.env`:

```python
import os
import boto3
from dotenv import load_dotenv

load_dotenv(".env", override=True)
s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["OBJ_ENDPOINT"],
    aws_access_key_id=os.environ["OBJ_ACCESS_KEY"],
    aws_secret_access_key=os.environ["OBJ_SECRET_KEY"],
)
bucket = os.environ["OBJ_BUCKET"]
s3.upload_file("docs/sample/parking.md", bucket, "parking.md")
text = s3.get_object(Bucket=bucket, Key="parking.md")["Body"].read().decode("utf-8")
print(text)
```

For an image project, use `upload_file("generated.png", bucket, "generated.png")` after the [image notebook](../notebooks/03_image_generation.ipynb) produces that file. Keep the bucket private unless your application explicitly needs public access.

In the starter, [knowledge.py](../agent/knowledge.py) contains the bucket reader, text chunking, embedding calls, and search. `.md` and `.txt` files are supported. For PDF text extraction, see [the code guide](../agent/README.md#read-other-file-types).

## Verify

Show the bucket in Cloud Manager, then demonstrate an application reading the object or answering from it. A listed bucket alone does not demonstrate the integration.

## Clean up

Keep the bucket if you are continuing. Otherwise, review [cleanup](costs.md) and run `bash scripts/down.sh` to inspect and remove the workshop resources after confirmation. That script can also select other workshop resources in your account, so read its list before confirming. Object Storage service cancellation is a separate account-wide action.

Next: [deploy on a Linode](03_body.md), [add PostgreSQL](02_memory.md), or [adapt the starter](../agent/README.md#make-it-yours).