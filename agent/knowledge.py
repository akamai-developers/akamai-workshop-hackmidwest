"""Knowledge: documents in an Object Storage bucket, searched by meaning.

The agent lists the bucket, reads each new file, cuts it into chunks of about 500
words, turns each chunk into a vector with the embedding model, and stores the
vectors in memory. A question becomes a vector too, and memory returns the chunks
whose vectors point the same way. Without OBJ_* settings, the files come from
docs/sample/ instead of the bucket.
"""
from pathlib import Path
from urllib.parse import urlparse

from openai import OpenAI

from .config import SAMPLE_DOCS, Config, host_of
from .memory import Hit

TEXT_FILES = (".md", ".txt")  # what the agent can read; add a parser in read() for PDFs
CHUNK_WORDS = 500
BATCH_INPUTS = 16  # the embedding endpoint accepts at most 16 texts per request
BATCH_WORDS = 5000  # and 8,192 tokens per request; 5,000 English words stays under that


def chunk(text: str, size: int = CHUNK_WORDS) -> list[str]:
    """Split text into chunks of about `size` words, keeping paragraphs together when they fit."""
    chunks, current = [], []
    for paragraph in text.split("\n\n"):
        words = paragraph.split()
        if current and len(current) + len(words) > size:
            chunks.append(" ".join(current))
            current = []
        current += words
        while len(current) > size:  # a paragraph longer than one chunk
            chunks.append(" ".join(current[:size]))
            current = current[size:]
    if current:
        chunks.append(" ".join(current))
    return chunks


def reason(error: Exception) -> str:
    """The first line of an error message, or the error's type when it has no message."""
    lines = str(error).strip().splitlines()
    return lines[0] if lines else type(error).__name__


def batches(texts: list[str]):
    """Group texts so no request has more than 16 inputs or about 5,000 words."""
    batch, words = [], 0
    for text in texts:
        size = len(text.split())
        if batch and (len(batch) == BATCH_INPUTS or words + size > BATCH_WORDS):
            yield batch
            batch, words = [], 0
        batch.append(text)
        words += size
    if batch:
        yield batch


class Embedder:
    """Turns text into vectors of 1,024 numbers with the hackathon embedding model."""

    def __init__(self, cfg: Config, cache=None, client: OpenAI | None = None):
        self.model = cfg.embedding_model
        self.cache = cache
        self.client = client or OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, max_retries=4)

    def __call__(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for batch in batches(texts):
            response = self.client.embeddings.create(model=self.model, input=batch)
            vectors += [item.embedding for item in response.data]
        return vectors

    def one(self, text: str) -> list[float]:
        """One vector, from the cache when Valkey has seen this exact text before."""
        vector = self.cache.get_vector(self.model, text) if self.cache else None
        if vector is None:
            vector = self([text])[0]
            if self.cache:
                self.cache.set_vector(self.model, text, vector)
        return vector


class Bucket:
    """Text files in your Object Storage bucket, read through the S3 API with boto3."""

    def __init__(self, cfg: Config):
        import boto3
        from botocore.config import Config as BotoConfig

        endpoint = cfg.obj_endpoint if "://" in cfg.obj_endpoint else f"https://{cfg.obj_endpoint}"
        self.name = cfg.obj_bucket
        self.where = f"bucket {self.name} at {host_of(endpoint)}"
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=urlparse(endpoint).hostname.split(".")[0],  # us-sea-1
            aws_access_key_id=cfg.obj_access_key,
            aws_secret_access_key=cfg.obj_secret_key,
            # Same setting linode-cli uses: newer boto3 adds checksums that Object Storage does not expect.
            config=BotoConfig(request_checksum_calculation="when_required",
                              response_checksum_validation="when_required"),
        )

    def files(self) -> dict[str, str]:
        """Every text file in the bucket, with its ETag, which changes when the file does."""
        found = {}
        for page in self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.name):
            for item in page.get("Contents", []):
                if item["Key"].lower().endswith(TEXT_FILES):
                    found[item["Key"]] = item["ETag"]
        return found

    def read(self, key: str) -> str:
        body = self.s3.get_object(Bucket=self.name, Key=key)["Body"].read()
        return body.decode("utf-8", errors="replace")

    def upload(self, path: Path, key: str) -> None:
        self.s3.upload_file(str(path), self.name, key)


class Folder:
    """The fallback: text files in a folder on this machine."""

    def __init__(self, path: Path = SAMPLE_DOCS):
        self.path = path
        self.where = "docs/sample/ on this machine" if path == SAMPLE_DOCS else f"{path}/"

    def files(self) -> dict[str, str]:
        return {p.name: str(p.stat().st_mtime_ns) for p in sorted(self.path.iterdir())
                if p.suffix.lower() in TEXT_FILES}

    def read(self, key: str) -> str:
        return (self.path / key).read_text(encoding="utf-8", errors="replace")


class Knowledge:
    def __init__(self, source, memory, embed: Embedder, state: str, detail: str):
        self.source, self.memory, self.embed = source, memory, embed
        self.state, self.detail = state, detail
        self.versions: dict[str, str] = {}  # file -> version this process last indexed or saw
        self.unreadable: dict[str, str] = {}  # file -> why it could not be read

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
        try:
            chunks = chunk(self.source.read(key))
        except Exception as error:  # one file it cannot read, such as a broken PDF, must not stop the others
            self.unreadable[key] = reason(error)
            self.memory.delete_document(key)  # chunks of an older version no longer match the bucket
            return 0
        self.unreadable.pop(key, None)
        vectors = self.embed([f"{key}\n{text}" for text in chunks])  # the file name helps the match
        self.memory.replace_document(key, chunks, vectors)
        return len(chunks)

    def search(self, query: str, k: int = 3) -> list[Hit]:
        self.sync()  # one list request, so files uploaded a moment ago are searchable
        return self.memory.search(self.embed.one(query), k)


def connect(cfg: Config, memory, embed: Embedder) -> Knowledge:
    """The bucket when OBJ_* is set, otherwise docs/sample/. Indexes what is there."""
    if cfg.has_bucket:
        source = Bucket(cfg)
        knowledge = Knowledge(source, memory, embed, "live", source.where)
    else:
        source = Folder()
        knowledge = Knowledge(source, memory, embed, "fallback",
                              f"reading {source.where}. Set OBJ_* in .env to use your bucket.")
    try:
        knowledge.sync()
    except Exception as error:  # a wrong key or a missing bucket should not stop the agent
        knowledge.state = "error"
        knowledge.detail = f"{source.where} failed: {reason(error)}"
    if knowledge.unreadable:
        files = "; ".join(f"{key} ({why})" for key, why in knowledge.unreadable.items())
        knowledge.detail = f"{knowledge.detail.rstrip('.')}. Could not read {files}."
    return knowledge
