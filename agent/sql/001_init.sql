-- Memory for the agent. scripts/db_init.py runs every file in agent/sql/ in name order.
-- Every statement is safe to run twice.

-- pgvector adds the vector type and the <=> cosine distance operator.
CREATE EXTENSION IF NOT EXISTS vector;

-- One row per conversation. The terminal uses the id "terminal"; each browser tab gets its own.
CREATE TABLE IF NOT EXISTS sessions  (id TEXT PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT now());

-- Every user and assistant message, in order.
CREATE TABLE IF NOT EXISTS messages  (id BIGSERIAL PRIMARY KEY, session_id TEXT REFERENCES sessions(id),
                                      role TEXT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now());

-- Chunks of the files in the bucket, and notes saved with the remember tool (keys starting with notes/).
-- 1024 is the size of the vectors from hackathon-embedding.
CREATE TABLE IF NOT EXISTS documents (id BIGSERIAL PRIMARY KEY, object_key TEXT NOT NULL, chunk_index INT NOT NULL,
                                      content TEXT NOT NULL, embedding vector(1024) NOT NULL, UNIQUE (object_key, chunk_index));

-- An HNSW index makes nearest-neighbor search fast once there are thousands of chunks.
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_cosine_ops);
