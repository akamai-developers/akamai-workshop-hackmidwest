"""Upload files to your bucket and index them, so the agent can search them.

    python scripts/upload.py docs/sample/parking.md
    python scripts/upload.py my-notes/*.md

Each file lands in the bucket under its own name. Then it is cut into chunks, embedded,
and stored in memory: PostgreSQL when DATABASE_URL is set. Without a database the vectors
die with this script, and the running agent indexes the file itself on its next question.
"""
import argparse
import sys
from pathlib import Path

from agent import config, knowledge, memory


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload files to the bucket and index them.")
    parser.add_argument("files", nargs="+", type=Path, help="text or Markdown files to upload")
    args = parser.parse_args()

    cfg = config.load()
    if not cfg.has_bucket:
        print("The OBJ_* settings in .env are empty. Create the bucket first: guide 01, or bash scripts/up.sh")
        return 1

    store = memory.connect(cfg)
    bucket = knowledge.Bucket(cfg)
    index = knowledge.Knowledge(bucket, store, knowledge.Embedder(cfg), "live", bucket.where)
    for path in args.files:
        if path.suffix.lower() not in knowledge.TEXT_FILES:
            print(f"Skipped {path}: the agent reads {' and '.join(knowledge.TEXT_FILES)} files.")
            continue
        bucket.upload(path, path.name)
        chunks = index.index(path.name)
        print(f"Uploaded {path} to {cfg.obj_bucket}/{path.name} and indexed {chunks} chunk(s).")

    if store.state == "live":
        print(f"The vectors are in {store.detail}.")
    else:
        print("No database, so these vectors were not kept. The running agent indexes new files on its next question.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
