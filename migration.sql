-- migration.sql
-- Run these once against your database before using the tools.

-- 1. Enable the pgvector extension (needed for the `vector` type and <=> operator)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add an embedding column sized for Groq's nomic-embed-text-v1_5 (768-dim)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS embedding vector(768);

-- 4. An index so similarity search stays fast as the table grows
CREATE INDEX IF NOT EXISTS documents_embedding_idx
    ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);